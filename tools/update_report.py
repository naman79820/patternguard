"""Phase 6 (and 7): build report/PatternGuard_Minor_Project_Report_Final.docx from the
original docs/PatternGuard_Minor_Project_Report1.docx. The original is never modified.
Every edit is logged to report/report_edits.md (section, before, after, source).
All values are read from result files produced in this session.

Cover page, certificate, declaration, acknowledgement and student details are not touched.
"""
import copy
import json
import re
import shutil
import sys
from pathlib import Path

from docx import Document
from docx.shared import Inches
from docx.table import Table
from docx.text.paragraph import Paragraph

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "PatternGuard_Minor_Project_Report1.docx"
DST = ROOT / "report" / "PatternGuard_Minor_Project_Report_Final.docx"
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def load(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


ENV = load("report/environment.json")
TESTS = {r["id"]: r for r in load("report/test_results.json")}
RES = load("eval/results.json")
CASES = load("report/case_results_after.json")
CFG = load("extension/config.json")
DSUM = load("report/datasets_summary.json")
BERT = load("eval/distilbert_results.json") if (ROOT / "eval/distilbert_results.json").exists() else None
CATS_JS = (ROOT / "extension/categories.js").read_text(encoding="utf-8")
EXPLAIN = dict(re.findall(r"name: '([^']+)'.*?\n\s+explain: '([^']+)'", CATS_JS))

LOG = []


def log(section, before, after, source):
    LOG.append((section, before, after, source))


# ---------------------------------------------------------------- helpers
def runs(p):
    return p._p.findall(W + "r")


def set_text(p, text, bold=None):
    """Replace a paragraph's text, keeping the first text run's formatting."""
    rs = [r for r in runs(p) if r.find(W + "t") is not None]
    first = rs[0]
    for r in runs(p):
        if r is not first:
            p._p.remove(r)
    for t in first.findall(W + "t")[1:]:
        first.remove(t)
    for el in list(first):
        if el.tag in (W + "tab", W + "br"):
            first.remove(el)
    t = first.find(W + "t")
    t.text = text
    t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    if bold is not None:
        rpr = first.find(W + "rPr")
        for tag in ("b", "bCs"):
            e = rpr.find(W + tag)
            if e is not None:
                rpr.remove(e)
        if bold:
            from docx.oxml import OxmlElement
            rpr.insert(1, OxmlElement("w:b"))


def set_runs(p, parts):
    """parts: [(text, bold)] using the first run as format template."""
    tmpl = copy.deepcopy([r for r in runs(p) if r.find(W + "t") is not None][0])
    for r in runs(p):
        p._p.remove(r)
    for text, bold in parts:
        r = copy.deepcopy(tmpl)
        rpr = r.find(W + "rPr")
        for tag in ("b", "bCs"):
            e = rpr.find(W + tag)
            if e is not None:
                rpr.remove(e)
        if bold:
            from docx.oxml import OxmlElement
            rpr.insert(1, OxmlElement("w:b"))
        for t in r.findall(W + "t")[1:]:
            r.remove(t)
        r.find(W + "t").text = text
        p._p.append(r)


def replace_in(p, old, new):
    for r in runs(p):
        t = r.find(W + "t")
        if t is not None and t.text and old in t.text:
            t.text = t.text.replace(old, new)
            return True
    if old in p.text:
        set_text(p, p.text.replace(old, new))
        return True
    return False


def clone_after(anchor_el, template_p, text=None, parts=None):
    new = copy.deepcopy(template_p._p)
    for d in new.findall(".//" + W + "drawing"):
        d.getparent().getparent().remove(d.getparent())
    anchor_el.addnext(new)
    np_ = Paragraph(new, template_p._parent)
    if parts is not None:
        set_runs(np_, parts)
    elif text is not None:
        set_text(np_, text)
    return np_


def set_cell(cell, text):
    ps = cell.paragraphs
    for extra in ps[1:]:
        extra._p.getparent().remove(extra._p)
    set_text(ps[0], text)


def find_par(doc, startswith, style=None, nth=0):
    hits = [p for p in doc.paragraphs if p.text.strip().startswith(startswith) and (style is None or p.style.name == style)]
    return hits[nth]


def find_table_after(doc, caption_start):
    cap = find_par(doc, caption_start)
    el = cap._p.getnext()
    while el is not None and el.tag != W + "tbl":
        el = el.getnext()
    return cap, Table(el, cap._parent)


def clone_table_after(anchor_el, tmpl_table, header, rows):
    """Copy a table with the same number of columns, keep header and data row formats."""
    new = copy.deepcopy(tmpl_table._tbl)
    trs = new.findall(W + "tr")
    head, body = trs[0], trs[1]
    for tr in trs[1:]:
        new.remove(tr)
    t = Table(new, tmpl_table._parent)
    for c, txt in zip(t.rows[0].cells, header):
        set_cell(c, txt)
    for row in rows:
        tr = copy.deepcopy(body)
        new.append(tr)
    t = Table(new, tmpl_table._parent)
    for r, row in zip(t.rows[1:], rows):
        for c, txt in zip(r.cells, row):
            set_cell(c, txt)
    anchor_el.addnext(new)
    return t


def add_picture_par(anchor_el, template_img_p, path, width_in):
    new = copy.deepcopy(template_img_p._p)
    for r in new.findall(W + "r"):
        new.remove(r)
    anchor_el.addnext(new)
    p = Paragraph(new, template_img_p._parent)
    p.add_run().add_picture(str(path), width=Inches(width_in))
    return p


def fmt(v, d=2):
    return "Not measured" if v is None else f"{v:.{d}f}"


# ---------------------------------------------------------------- main
def main():
    shutil.copyfile(SRC, DST)
    doc = Document(DST)
    caption_tmpl = find_par(doc, "Table 6.6:")
    fig_caption_tmpl = find_par(doc, "Figure 6.1:")
    img_tmpl = Paragraph(fig_caption_tmpl._p.getprevious(), fig_caption_tmpl._parent)
    body_tmpl = find_par(doc, "Software testing checks that each component")
    bullet_tmpl = find_par(doc, "Hinglish performance has not been validated.")
    env = ENV
    pk = env["python_packages"]
    tr = BERT is not None

    # ---------- Abstract (keeps the report consistent with the work done) ----------
    p = find_par(doc, "This report presents PatternGuard")
    before = p.text
    after = ("This report presents PatternGuard, a Chrome browser extension built on Manifest V3 that examines each candidate interface "
             "element in two independent ways: a rule engine over the Document Object Model (DOM) and computed CSS properties, and a "
             "text component over the element's text. The design uses a fine-tuned DistilBERT classifier for the text; the current "
             "prototype uses a rule-based text scorer with the same output shape in its place. The two confidence scores are combined "
             "with category-specific weights and a precision-oriented threshold. Flagged elements are highlighted on the page with a "
             "short plain-language explanation and mapped to one of the thirteen CCPA categories, and the extension computes a per-site "
             "Manipulation Score locally.")
    set_text(p, after); log("Abstract", before, after, "extension/ (implemented components); Table 5.8")
    p = find_par(doc, "The report describes the problem formulation")
    before = p.text
    c = RES["controlled_test_set"]["configs"]["combined"]["overall"]
    y = RES["yada_text_check"]["full"]
    after = ("The report describes the problem formulation, the structural and linguistic analysis methods, the score-fusion procedure, "
             "the system architecture and design diagrams, the implementation and the development status of each component. The "
             f"prototype was evaluated on a controlled test set of {RES['controlled_test_set']['size']['pages']} pages written by the team, "
             f"where the combined configuration reached precision {fmt(c['precision'])}, recall {fmt(c['recall'])} and F1 {fmt(c['f1'])}, "
             "and its text component was checked on two public English datasets (precision "
             f"{fmt(y['precision'])}, recall {fmt(y['recall'])} on the Yada et al. dataset). Evaluation on held-out Indian websites has not yet been carried out.")
    set_text(p, after); log("Abstract", before, after, "eval/results.json")

    # ---------- 1.4: penalties and ASCI study ----------
    p = find_par(doc, "Regulatory activity has continued since then.")
    new_text = ("In August 2026, a written reply in the Rajya Sabha disclosed that the CCPA had imposed penalties for dark patterns on nine "
                "platforms: IndiGo, Zepto, BookMyShow, Physics Wallah, FirstCry, SpiceJet, PharmaEasy, McAfee and Anuj Jindal [17], [18]. "
                "Earlier, in 2024, the ASCI Academy and Parallel examined 53 Indian apps for dark patterns in the study Conscious Patterns [19]. "
                "These reports show that the patterns targeted by this project occur on Indian platforms and that the regulator has begun to act against them.")
    clone_after(p._p, p, new_text)
    log("1.4 Regulatory and Problem Context", "(new paragraph)", new_text, "Task brief (sources listed in Section 3 of extension.txt); references [17] to [19]")

    # ---------- References [17]..[21] ----------
    last_ref = find_par(doc, "[16]")
    refs = [
        ("[17]", "Business Standard, report on CCPA penalties on IndiGo, Zepto, BookMyShow and other platforms for dark patterns, Aug. 2026. [Online]. Available: https://www.business-standard.com/industry/news/ccpa-fines-indigo-zepto-bookmyshow-dark-patterns-quick-commerce-penalty-126080600580_1.html"),
        ("[18]", "ThePrint, report on CCPA action against Zepto, FirstCry, BookMyShow and other platforms, Aug. 2026. [Online]. Available: https://theprint.in/feature/zepto-firstcry-bookmyshow-consumer-protection-board/3007638/"),
        ("[19]", "ASCI Academy and Parallel, \"Conscious Patterns\" (report summary), Advertising Standards Council of India, 2024. [Online]. Available: https://www.ascionline.in/wp-content/uploads/2024/07/Consious-Patterns-Report-Summary.pdf"),
        ("[20]", "Y. Yada et al., ec-darkpattern dataset (dataset/dataset.tsv), GitHub repository, Apache-2.0 licence. [Online]. Available: https://github.com/yamanalab/ec-darkpattern"),
        ("[21]", "A. Mathur et al., dark-patterns data repository (data/final-dark-patterns/dark-patterns.csv), GitHub. [Online]. Available: https://github.com/aruneshmathur/dark-patterns"),
    ]
    anchor = last_ref._p
    for num, text in refs:
        np_ = Paragraph(copy.deepcopy(last_ref._p), last_ref._parent)
        anchor.addnext(np_._p)
        rs = [r for r in runs(np_) if r.find(W + "t") is not None]
        rs[0].find(W + "t").text = num + "\t" if "\t" in last_ref.text[:6] else num + " "
        rs[1].find(W + "t").text = text
        for r in rs[2:]:
            np_._p.remove(r)
        anchor = np_._p
        log("REFERENCES", "(new entry)", f"{num} {text}", "Task brief Section 3 links")

    # ---------- Chapter 3/4 placeholders that the code now answers ----------
    _, t32 = find_table_after(doc, "Table 3.2:")
    for r in t32.rows:
        if r.cells[0].text.strip() == "Privacy":
            before = r.cells[1].text
            after = ("Only the information needed for detection is processed. In the current implementation nothing leaves the browser: "
                     "detection records are kept in chrome.storage.local on the user's machine; per-tab records are deleted when the tab is closed, "
                     "and per-site records remain until the extension is removed. A formal retention policy for a future backend has not been set.")
            set_cell(r.cells[1], after); log("3.2.2 Table 3.2 (Privacy)", before, after, "extension/background.js")
    p = find_par(doc, "Every Chrome extension is described by a manifest file.")
    before = p.text
    after = before.replace("The exact permission set and host patterns used in the project are [To be confirmed from the project's manifest.json].",
                           "The project's manifest.json requests only the storage permission, declares no host_permissions because the extension makes no network requests, and injects the content scripts on all URLs (<all_urls>).")
    set_text(p, after); log("4.2.1 Manifest V3 Structure", before, after, "extension/manifest.json")
    _, t42 = find_table_after(doc, "Table 4.2:")
    for r in t42.rows:
        if r.cells[0].text.strip() == "action":
            before = r.cells[1].text
            after = "Toolbar popup (popup.html) that shows the site's Manipulation Score and the detections on the current page."
            set_cell(r.cells[1], after); log("4.2.1 Table 4.2 (action)", before, after, "extension/manifest.json, extension/popup.html")
        if r.cells[0].text.strip() == "background.service_worker":
            before = r.cells[1].text
            after = "Event-driven script (background.js) that serves config.json, stores detections in chrome.storage and computes the Manipulation Score. No inference service or backend is contacted in the current implementation."
            set_cell(r.cells[1], after); log("4.2.1 Table 4.2 (background.service_worker)", before, after, "extension/background.js")
    p = find_par(doc, "The backend aggregation service receives detection records")
    before = p.text
    after = before.replace("The final schema is [To be confirmed by the project team].",
                           "No backend was built. In the current implementation each record is stored locally with the fields category, name, fused confidence, DOM path, evidence summary and element text, grouped by site and page with a timestamp.")
    set_text(p, after); log("4.7 Backend Aggregation Architecture", before, after, "extension/content.js, extension/background.js")
    p = find_par(doc, "Every reported detection carries a category k*")
    before = p.text
    after = ("Every reported detection carries a category k* from the thirteen CCPA categories. Table 4.5 shows the explanation text that the "
             "extension displays for representative categories. The text is taken from extension/categories.js.")
    set_text(p, after); log("4.11 CCPA Category Mapping and Output", before, after, "extension/categories.js")
    cap, t45 = find_table_after(doc, "Table 4.5:")
    before = cap.text
    set_text(cap, "Table 4.5: Explanation templates by category (extension/categories.js)")
    log("4.11 Table 4.5 caption", before, cap.text, "extension/categories.js")
    set_cell(t45.rows[0].cells[1], "Explanation shown by the extension")
    for r in t45.rows[1:]:
        name = r.cells[0].text.strip()
        if name in EXPLAIN:
            before = r.cells[1].text
            after = f"\"{EXPLAIN[name]}\""
            set_cell(r.cells[1], after); log(f"4.11 Table 4.5 ({name})", before, after, "extension/categories.js")
    p = find_par(doc, "In the intended logical deployment")
    before = p.text
    after = before.replace("The specific hosting platform has not been documented in the available project material and is [To be confirmed by the project team].",
                           "In the current implementation no server components exist, so the deployment consists of the extension alone, loaded in the user's browser.")
    set_text(p, after); log("4.17 Deployment Architecture", before, after, "Repository contents")

    # ---------- 5.1 ----------
    p = find_par(doc, "This chapter describes how each component of PatternGuard is implemented")
    before = p.text
    after = ("This chapter describes how each component of PatternGuard was implemented and records its development status. The source "
             "code is in the project repository (folders extension/, demo/, tests/ and eval/). The status of each component is supported "
             "by a file path or a test identifier. The status categories used in this chapter are defined in Table 5.1.")
    set_text(p, after); log("5.1 Overview and Basis of this Chapter", before, after, "Repository contents")
    _, t51 = find_table_after(doc, "Table 5.1:")
    for r in list(t51.rows):
        if "[Implementation Status]" in r.cells[0].text:
            before = " | ".join(c.text for c in r.cells)
            r._tr.getparent().remove(r._tr)
            log("5.1 Table 5.1", before, "(row removed: every placeholder status has been replaced)", "Table 5.8")
    p = find_par(doc, "The code listings in this chapter are")
    before = p.text
    after = "The code listings in this chapter are short excerpts from the project repository. The source file of each excerpt is named in its caption."
    set_text(p, after); log("5.1 Overview and Basis of this Chapter", before, after, "extension/")

    # ---------- 5.2 Table 5.2 ----------
    p = find_par(doc, "Table 5.2 lists the development environment.")
    before = p.text
    after = "Table 5.2 lists the development environment. Tool versions were read from the development machine (report/environment.json)."
    set_text(p, after); log("5.2 Development Environment", before, after, "report/environment.json")
    _, t52 = find_table_after(doc, "Table 5.2:")
    vals = {
        "Classifier": "Rule-based text scorer (extension/text.js) used as a stand-in; DistilBERT classifier (13 + 1 classes) not integrated",
        "Training framework": (f"PyTorch {pk.get('torch')} with Hugging Face Transformers {pk.get('transformers')} (binary DistilBERT baseline on the Yada et al. dataset only; not used by the extension)"
                               if tr else "Not applicable: no classifier was trained"),
        "Inference service framework": "Not built",
        "Backend framework and database": "Not built; detections stored locally with chrome.storage",
        "Crawler": f"Playwright {env['playwright']} (Python) with Chromium {env['chromium']}, used for automated tests and candidate extraction on local pages; no live-site crawler was built",
        "Operating system and hardware": f"{env['os']}, {env['machine']}, {env['processor']}; Python {env['python']}, Node.js {env['node']}",
        "Version control": env["git"].replace("git version", "Git"),
    }
    for r in t52.rows:
        k = r.cells[0].text.strip()
        if k in vals:
            before = r.cells[1].text
            set_cell(r.cells[1], vals[k]); log(f"5.2 Table 5.2 ({k})", before, vals[k], "report/environment.json" + ("; eval/distilbert_results.json" if k == "Training framework" and tr else ""))

    # ---------- component tables 5.3 to 5.7 ----------
    def status_row(caption, text, src):
        _, t = find_table_after(doc, caption)
        for r in t.rows:
            if r.cells[0].text.strip() == "Current status":
                before = r.cells[1].text
                set_cell(r.cells[1], text); log(f"{caption} Current status", before, text, src)
        return t

    t53 = status_row("Table 5.3:", "Completed: extension/manifest.json, content.js, background.js, popup.html; TC-F01, TC-F02, TC-F04, TC-F05, TC-F08 Pass; TC-F03 Fail (content script runs on all URLs).", "report/test_results.json")
    for r in t53.rows:
        k = r.cells[0].text.strip()
        if k == "Interactions":
            before = r.cells[1].text; after = "Service worker (messages, configuration, local storage of detections). No inference service or backend exists."
            set_cell(r.cells[1], after); log("5.4 Table 5.3 Interactions", before, after, "extension/background.js")
        if k == "Inputs":
            before = r.cells[1].text; after = "Rendered DOM and computed style of the current page; text confidences from the local text scorer (extension/text.js)."
            set_cell(r.cells[1], after); log("5.4 Table 5.3 Inputs", before, after, "extension/content.js")
        if k == "Outputs":
            before = r.cells[1].text; after = "In-page highlights and explanations; detection records stored with chrome.storage; toolbar badge and popup."
            set_cell(r.cells[1], after); log("5.4 Table 5.3 Outputs", before, after, "extension/content.js, extension/background.js")
    t54 = status_row("Table 5.4:", "Partially completed: five rules in extension/rules.js (timer reset, pre-selection, decline contrast and size, fee memory for drip pricing, screen-covering wall) and a hidden-element check; cancellation path length not implemented (TC-S08). Thresholds are set in config.json and not calibrated on a validation split.", "extension/rules.js; report/test_results.json")
    for r in t54.rows:
        if r.cells[0].text.strip() == "Working":
            before = r.cells[1].text
            after = "Implemented checks: countdown reset across reloads, paid option pre-selected before user interaction (HTML, script or ARIA), low-contrast or small decline next to a strong accept, fee not shown on an earlier step of the flow, screen-covering sign-up or app wall, and hidden-element test. Cancellation path length is not measured."
            set_cell(r.cells[1], after); log("5.5 Table 5.4 Working", before, after, "extension/rules.js")
    t55 = status_row("Table 5.5:", ("Text component: rule-based stand-in completed (extension/text.js); DistilBERT classifier not integrated; inference service not built. "
                                     + (f"A binary DistilBERT baseline was trained separately on the Yada et al. dataset (Section 5.7.2) but is not used by the extension." if tr else "")).strip(),
                     "extension/text.js" + ("; eval/distilbert_results.json" if tr else ""))
    for r in t55.rows:
        k = r.cells[0].text.strip()
        if k == "Working":
            before = r.cells[1].text
            after = "Planned: DistilBERT encoder with a 14-way classification head, hosted on an inference service. Current: hand-written regular expressions per category in extension/text.js, run inside the content script."
            set_cell(r.cells[1], after); log("5.7 Table 5.5 Working", before, after, "extension/text.js")
        if k == "Outputs":
            before = r.cells[1].text
            after = "Confidence vector over the 13 categories (the same shape as the planned classifier output); an all-zero vector stands for the negative class."
            set_cell(r.cells[1], after); log("5.7 Table 5.5 Outputs", before, after, "extension/text.js")
        if k == "Interactions":
            before = r.cells[1].text
            after = "Called by the content script for each candidate; no network request is made."
            set_cell(r.cells[1], after); log("5.7 Table 5.5 Interactions", before, after, "extension/content.js")
    status_row("Table 5.6:", "Partially completed: no backend service was built; the Manipulation Score (eq. 3.7) is computed locally in extension/score.js and background.js from detections stored with chrome.storage; all severity weights wk are 1 (config.json, not calibrated).", "extension/score.js, extension/config.json")
    status_row("Table 5.7:", "Proposed: no crawler for live sites was built and no Indian site pages are present in the repository (dataset/raw/ does not exist). Playwright is used for tests and for a candidate-extraction check on local pages (tests/playwright_extract.js, TC-I05).", "Repository contents; report/test_results.json")
    p = find_par(doc, "The content script starts once the document is idle")
    before = p.text
    after = before.replace("whether this has been implemented is [Implementation Status].",
                           "this has been implemented: a MutationObserver triggers a rescan at most once every 3 s (rescanMinIntervalMs in config.json), and text-only changes such as a ticking timer do not trigger one. In the regression test, demo/dark-checkout.html showed 0 redraws during 8 s of idle time.")
    set_text(p, after); log("5.4.2 Content Scripts", before, after, "extension/content.js; report/regression_result.json")

    # ---------- listings ----------
    def code_lines(path, start, end):
        lines = (ROOT / path).read_text(encoding="utf-8").splitlines()
        i = next(k for k, l in enumerate(lines) if start in l)
        j = next(k for k, l in enumerate(lines) if k >= i and end in l)
        return lines[i:j + 1]

    listings = [
        ("Listing 5.1:", "Listing 5.1: Extension manifest (extension/manifest.json)", (ROOT / "extension/manifest.json").read_text(encoding="utf-8").strip().splitlines(),
         "Listing 5.1 shows an illustrative manifest consistent with the design in Chapter 4.", "Listing 5.1 shows the manifest used by the extension."),
        ("Listing 5.2:", "Listing 5.2: Contrast-ratio computation (extension/rules.js)", code_lines("extension/rules.js", "function luminance(rgb)", "return (hi + 0.05) / (lo + 0.05);") + ["  }"],
         "Listing 5.2 shows an illustrative implementation of", "Listing 5.2 shows the implementation in extension/rules.js of"),
        ("Listing 5.3:", "Listing 5.3: Manipulation Score computation (extension/score.js)", code_lines("extension/score.js", "PG.manipulationScore = function", "  };"),
         "Listing 5.3 shows how the Manipulation Score can be computed from logged detections.", "Listing 5.3 shows how the service worker computes the Manipulation Score from the stored detections."),
        ("Listing 5.4:", "Listing 5.4: Score fusion and threshold (extension/content.js)", code_lines("extension/content.js", "const isControl = el.matches(INTERACTIVE_SEL);", "if (c[kStar] >= CFG.tau) {") + ["        // ... record the detection (category kStar, confidence c[kStar]) and highlight the element", "      }"],
         "Listing 5.4 shows an illustrative implementation.", "Listing 5.4 shows the fusion step in the content script. Text evidence for confirm shaming is counted only on controls (Section 6.13)."),
    ]
    for cap_start, new_cap, lines, old_ref, new_ref in listings:
        cap = find_par(doc, cap_start)
        before = cap.text
        set_text(cap, new_cap)
        old_pars = []
        el = cap._p.getnext()
        while el is not None and el.tag == W + "p" and Paragraph(el, cap._parent).text.strip() != "":
            old_pars.append(Paragraph(el, cap._parent))
            el = el.getnext()
        first, mid, last = old_pars[0], old_pars[1], old_pars[-1]
        before_code = "\n".join(p.text for p in old_pars)
        dedent = min(len(l) - len(l.lstrip(" ")) for l in lines if l.strip())
        lines = [l[dedent:] for l in lines]
        anchor = cap._p
        for k, line in enumerate(lines):
            tmpl = first if k == 0 else last if k == len(lines) - 1 else mid
            txt = line.replace(" ", "\u00a0") if line else "\u00a0"
            anchor = clone_after(anchor, tmpl, txt)._p
        for p in old_pars:
            p._p.getparent().remove(p._p)
        log(f"5 {cap_start} caption", before, new_cap, lines and "repository file")
        log(f"5 {cap_start} code", before_code, "\n".join(lines), new_cap[new_cap.index("(") + 1:-1])
        for p in doc.paragraphs:
            if old_ref in p.text:
                b = p.text
                replace_in(p, old_ref, new_ref)
                log(f"5 text referring to {cap_start[:-1]}", b, p.text, "repository file")
    p = find_par(doc, "The contrast and area comparisons are converted")
    before = p.text
    r = CFG["rules"]
    after = (f"The contrast and area comparisons are converted into a structural confidence for the interface-interference category: 1.0 when "
             f"the decline control is both low-contrast (below {r['contrastLimit']}:1 while the accept control is at or above it) and small (accept area "
             f"at least {r['sizeRatio']} times the decline area), and 0.8 when only one condition holds. These thresholds are set in config.json and have not been calibrated on a validation split.")
    set_text(p, after); log("5.6 CSS-Based Feature Extraction", before, after, "extension/rules.js, extension/config.json")
    p = find_par(doc, "The fusion module implements Equations (3.5) and (3.6).")
    before = p.text
    after = before.replace("The weights αk and threshold τ are loaded from configuration so that they can be updated after calibration without code changes.",
                           "The weights αk, the threshold τ, the severity weights and the rule thresholds are loaded from extension/config.json at startup, so they can be changed without code changes (test TC-H05).")
    set_text(p, after); log("5.10 Hybrid Detection Workflow", before, after, "extension/config.json; tests/config_test.py")

    # ---------- 5.7 text classification ----------
    t55_el = t55._tbl
    p = clone_after(t55_el, body_tmpl,
                    "In the current implementation the text component is a rule-based stand-in (extension/text.js). It applies hand-written regular "
                    "expressions for each category to the normalised element text, truncated to 512 characters, and returns a confidence vector over "
                    "the thirteen categories, which is the same output shape that the DistilBERT classifier would return. The DistilBERT classifier "
                    "is not yet integrated into the extension, and no inference service was built. The stand-in has not been trained and its "
                    "Hinglish patterns have not been validated on any dataset.")
    log("5.7 Text Classification Integration", "(new paragraph after Table 5.5)", p.text, "extension/text.js")
    p = find_par(doc, "At inference time the service receives a batch")
    before = p.text
    set_text(p, before + " This workflow belongs to the planned design and has not been implemented.")
    log("5.7.1 DistilBERT Inference Workflow", before, p.text, "Repository contents")
    p = find_par(doc, "The classifier is to be fine-tuned on elements from training sites only")
    before = p.text
    if tr:
        b = BERT
        after = ("The planned fine-tuning on labelled Indian site data with thirteen categories plus a negative class has not been carried out, "
                 "because no labelled site data exist yet. As a first step, a binary DistilBERT baseline (distilbert-base-uncased) was fine-tuned "
                 f"on CPU on the Yada et al. dataset [11], [20], using a stratified 80/20 train/test split with seed {b['seed']}: maximum sequence length "
                 f"{b['hyperparameters']['max_length']}, {b['hyperparameters']['epochs']} epoch(s), batch size {b['hyperparameters']['batch_size']}, learning rate "
                 f"{b['hyperparameters']['learning_rate']}, training time {b['train_seconds']/60:.1f} minutes. It is binary and trained on English text "
                 "from non-Indian shopping sites; it is not wired into the extension. Its results are reported in Table 6.10.")
    else:
        after = ("The planned fine-tuning on elements from training sites only, with validation sites used for model selection and for calibrating "
                 "αk and τ, has not been carried out, because no labelled site data exist yet. Hyper-parameters will be reported when training is carried out.")
    set_text(p, after); log("5.7.2 Fine-Tuning Procedure", before, after, "eval/distilbert_results.json" if tr else "Repository contents")

    # ---------- 5.8 table 5.8 ----------
    p = find_par(doc, "Table 5.8 summarises the development status")
    before = p.text
    after = "Table 5.8 summarises the development status of every major component. Each status is supported by a file path or a test identifier."
    set_text(p, after); log("5.12 Current Implementation Status", before, after, "Table 5.8")
    _, t58 = find_table_after(doc, "Table 5.8:")
    st = {
        "Annotation schema (Table 3.3)": ("Completed", "13 categories in extension/categories.js; weights in extension/config.json; mapping of public dataset categories in report/mapping_mathur_to_ccpa.md"),
        "Playwright crawler and dataset collection": ("Proposed", "No live-site crawler and no saved Indian site pages in the repository; public datasets downloaded to data_public/ [20], [21]"),
        "Four-annotator labelling and Fleiss' kappa pilot": ("Proposed", "No labelled site data; Fleiss' kappa not computed"),
        "DistilBERT fine-tuning": (("Partially completed", "Binary baseline on the Yada et al. dataset only (eval/distilbert_results.json); 13 + 1 class model not trained") if tr
                                   else ("Proposed", "Not trained; rule-based stand-in extension/text.js used instead")),
        "Inference service": ("Proposed", "Not built; TC-I01 and TC-I02 not applicable"),
        "Extension: manifest and content script": ("Completed", "extension/manifest.json, extension/content.js; TC-F01, TC-F02 Pass; TC-F03 Fail"),
        "Rule engine (six checks)": ("Partially completed", "Five rules and a hidden-element check in extension/rules.js; subscription-trap check missing (TC-S08); thresholds not calibrated"),
        "Fusion module and threshold": ("Completed", "extension/content.js, parameters in extension/config.json; TC-H01 to TC-H05 Pass; αk and τ not calibrated on a validation split"),
        "In-page highlights and explanations": ("Completed", "extension/content.js (draw); TC-F04, TC-F05, TC-F08 Pass"),
        "Backend aggregation and Manipulation Score": ("Partially completed", "No backend; S computed locally (extension/score.js, background.js); all wk = 1"),
        "Dashboard": ("Proposed", "Not built; toolbar popup (extension/popup.html) shows S and detections"),
        "Held-out evaluation": ("Proposed", "Live-site evaluation not done; controlled test set and public text datasets evaluated instead (Section 6.2)"),
    }
    for r in t58.rows[1:]:
        k = r.cells[0].text.strip()
        if k in st:
            before = f"{r.cells[1].text} | {r.cells[2].text}"
            set_cell(r.cells[1], st[k][0]); set_cell(r.cells[2], st[k][1])
            log(f"5.12 Table 5.8 ({k})", before, f"{st[k][0]} | {st[k][1]}", "Repository contents; report/test_results.json")

    # ---------- 5.11 ----------
    p = find_par(doc, "Reported elements are highlighted in place")
    before = p.text
    after = ("Reported elements are highlighted in place by drawing an outline around the element and attaching a short explanation that names "
             "the CCPA category and the reason for the flag, using the templates in Table 4.5. The outlines are drawn in a separate shadow-DOM layer "
             "that does not receive clicks, so the page behaves as before (TC-F08). A dashboard was planned but not built; instead, the toolbar popup "
             "shows the site's Manipulation Score S and the detections on the current page with their evidence. Screenshots are given in Appendix C.")
    set_text(p, after); log("5.11 Result Presentation", before, after, "extension/content.js, extension/popup.html")

    # ---------- Tables 6.1 to 6.5 ----------
    for cap in ["Table 6.1:", "Table 6.2:", "Table 6.3:", "Table 6.4:", "Table 6.5:"]:
        _, t = find_table_after(doc, cap)
        for r in t.rows[1:]:
            tid = r.cells[0].text.strip()
            if tid in TESTS:
                rec = TESTS[tid]
                actual = rec["actual"]
                if actual.startswith(rec["status"] + ":"):
                    actual = actual[len(rec["status"]) + 1:].strip()
                txt = f"{rec['status']}. {actual}"
                before = r.cells[3].text
                set_cell(r.cells[3], txt); log(f"6 {cap} {tid}", before, txt, "report/test_results.json")

    # ---------- 6.2 ----------
    size = RES["controlled_test_set"]["size"]
    p = find_par(doc, "Dataset collection and labelling are in progress, and the classifier has not yet been evaluated")
    before = p.text
    after = ("Three kinds of evaluation were carried out. First, the test cases in Tables 6.1 to 6.5 were run automatically in Chromium with the "
             "extension loaded (tests/report_cases.py); their actual outcomes are given in the tables. Second, the extension was evaluated at "
             f"element level on a controlled test set of {size['pages']} pages written by the team ({size['page_states']} page states, "
             f"{size['labelled_dark_pattern_elements']} labelled dark-pattern elements): three demo pages and five reconstructions of practices "
             "reported in CCPA actions, including one fair control page. Third, the text component alone was checked on two public English "
             "datasets, the Yada et al. dataset [11], [20] and the Mathur et al. dataset [8], [21]. No live Indian websites were crawled or "
             "evaluated, and no held-out-site results exist yet. The controlled test set was written together with the rules, so its results show "
             "that the implementation behaves as designed; they do not show performance on unseen websites.")
    set_text(p, after); log("6.2 Current Evaluation Status", before, after, "eval/results.json; report/test_results.json")
    p = find_par(doc, "Testing proceeds from small to large.")
    before = p.text
    after = before.replace("Finally, the full system is evaluated on real sites from the held-out split.",
                           "Evaluation of the full system on real sites from a held-out split is planned and was not carried out in this work.")
    set_text(p, after); log("6.3 Testing Methodology", before, after, "Section 6.2")
    p = find_par(doc, "Comparing these configurations isolates")
    before = p.text
    set_text(p, before + " The same three configurations were compared on the controlled test set (Table 6.6), with all αk set to 0, all αk set to 1, and the values in config.json.")
    log("6.10 Baseline Comparison and Ablation Study Design", before, p.text, "eval/controlled_eval.py")

    # ---------- 6.12 Table 6.6 + new tables + figures ----------
    p = find_par(doc, "Table 6.6 shows the format in which overall results")
    before = p.text
    after = ("Table 6.6 reports the overall element-level results on the controlled test set for the three configurations. Latency is the time "
             "from the page load event to the end of the first scan, including drawing the highlights (Equation 6.4), over the "
             f"{RES['controlled_test_set']['configs']['combined']['latency']['since_load_ms']['n']} full page loads. Per-category results are in "
             "eval/results_table.md. Tables 6.7 and 6.8 report the text checks on the public datasets, and Table 6.9 reports the documented-case results.")
    set_text(p, after); log("6.12 Results Reporting Format", before, after, "eval/results.json")
    cap66, t66 = find_table_after(doc, "Table 6.6:")
    before = cap66.text
    set_text(cap66, "Table 6.6: Overall results on the controlled test set")
    log("6.12 Table 6.6 caption", before, cap66.text, "Phase 6 instruction")
    cmap = {"Text-only baseline": "text_only", "Rule engine only": "rules_only", "PatternGuard (fused)": "combined"}
    for r in t66.rows[1:]:
        k = cmap.get(r.cells[0].text.strip())
        if not k:
            continue
        o = RES["controlled_test_set"]["configs"][k]["overall"]
        la = RES["controlled_test_set"]["configs"][k]["latency"]["since_load_ms"]
        vals = [fmt(o["precision"]), fmt(o["recall"]), fmt(o["f1"]), f"median {la['median']:.1f} ms (max {la['max']:.1f} ms)"]
        for c, v in zip(r.cells[1:], vals):
            set_cell(c, v)
        log(f"6.12 Table 6.6 ({r.cells[0].text.strip()})", "Pending | Pending | Pending | Pending", " | ".join(vals), "eval/controlled_results.json")
    set_cell(t66.rows[0].cells[4], "Latency from load")
    _, t31 = find_table_after(doc, "Table 3.1:")
    anchor = t66._tbl

    def add_table(anchor, intro, caption, tmpl, header, rows):
        p1 = clone_after(anchor, body_tmpl, intro)
        c = clone_after(p1._p, caption_tmpl, caption)
        t = clone_table_after(c._p, tmpl, header, rows)
        log("6.12 " + caption.split(":")[0], "(new table)", caption + "\n" + "\n".join(" | ".join(r) for r in [header] + rows), "eval/results.json")
        return t._tbl

    yf, ys = RES["yada_text_check"]["full"], RES["yada_text_check"]["test_split_seed42"]
    rows = [[m, str(yf[k]) if isinstance(yf[k], int) else f"{yf[k]:.4f}", str(ys[k]) if isinstance(ys[k], int) else f"{ys[k]:.4f}"]
            for m, k in [("Texts (n)", "n"), ("True positives", "tp"), ("False positives", "fp"), ("False negatives", "fn"), ("True negatives", "tn"),
                         ("Accuracy", "accuracy"), ("Precision", "precision"), ("Recall", "recall"), ("F1-score", "f1")]]
    anchor = add_table(anchor,
                       f"The Yada et al. dataset [20] contains {DSUM['yada']['rows']} English texts from shopping websites with binary labels "
                       f"({DSUM['yada']['label_counts']['1']} dark pattern, {DSUM['yada']['label_counts']['0']} not). The text scorer was run on every text, and a text was "
                       "counted as positive when any category fired. Table 6.7 gives the results on the whole file and on a fixed 20% test split (seed 42). "
                       "This check measures only the wording component, on English text from non-Indian sites.",
                       "Table 6.7: Text check of the rule-based text scorer on the Yada et al. dataset", t31,
                       ["Measure", "Full file", "Test split (20%, seed 42)"], rows)
    mrows = [[r["mathur_type"], r["ccpa_category"].replace("_", " "), str(r["n_with_text"]), f"{r['recall_mapped']:.2f}", f"{r['recall_any']:.2f}"]
             for r in RES["mathur_text_check"]["per_type"]]
    anchor = add_table(anchor,
                       f"The Mathur et al. dataset [21] contains {RES['mathur_text_check']['rows_in_file']} dark-pattern strings, of which "
                       f"{RES['mathur_text_check']['rows_with_text']} have text. All rows are dark patterns, so only recall can be measured. Table 6.8 lists "
                       "the types that map cleanly to a CCPA category; the mapping is given in report/mapping_mathur_to_ccpa.md.",
                       "Table 6.8: Recall of the rule-based text scorer on the Mathur et al. dataset", t66,
                       ["Mathur type", "CCPA category", "n", "Recall (mapped category)", "Recall (any category)"], mrows)
    crow = []
    for r in CASES:
        exp = ", ".join(e["category"].replace("_", " ") for e in r["expected"]) or "none"
        det = ", ".join(d["key"].replace("_", " ") for d in r["detected"]) or "none"
        out = "Caught" if r["expected"] and not r["fn"] and not r["fp"] else "Correctly silent" if not r["expected"] and not r["fp"] else f"FN {r['fn']}, FP {r['fp']}"
        src = "[17]" if "business-standard" in r["source"] else "[18]"
        crow.append([f"{r['file'].split('_')[0].replace('case', 'Case ')} ({r['step']})", f"{r['reported_practice'].split(' (')[0]} {src}", exp, det, out])
    tp_b = sum(x["tp"] for x in load("report/case_results_before.json")); fp_b = sum(x["fp"] for x in load("report/case_results_before.json"))
    anchor = add_table(anchor,
                       "Five pages reconstruct practices reported in the CCPA actions [17], [18], with made-up shop names and plain styling; case 5 is a fair "
                       "control. They are rendered with JavaScript, tick options from code and use two-step flows. The expected outcomes were written "
                       f"before the extension was first run on them. In the first run the extension found all {tp_b} expected elements but also produced "
                       f"{fp_b} false positives, caused by a quoted phrase in the case 2 banner; after the rule change described in Section 6.13, the results "
                       "were as shown in Table 6.9.",
                       "Table 6.9: Results on the reconstructed CCPA cases", t66,
                       ["Case (step)", "Reported practice and source", "Expected", "Detected", "Outcome"], crow)
    if tr:
        b = BERT
        brow = [[m, f"{b['distilbert'][k]:.4f}", f"{b['regex_same_split'][k]:.4f}"] for m, k in
                [("Accuracy", "accuracy"), ("Precision", "precision"), ("Recall", "recall"), ("F1-score", "f1")]]
        brow.insert(0, ["Test texts (n)", str(b["test_n"]), str(b["test_n"])])
        anchor = add_table(anchor,
                           "Table 6.10 compares the binary DistilBERT baseline (Section 5.7.2) with the rule-based text scorer on the same Yada et al. test "
                           "split. Both are binary and the data are English text from non-Indian shopping sites, so the comparison says nothing yet about "
                           "Indian or Hinglish text. The DistilBERT model is not used by the extension.",
                           "Table 6.10: Binary DistilBERT baseline and rule-based text scorer on the Yada et al. test split", t31,
                           ["Measure", "DistilBERT (binary)", "Rule-based text scorer"], brow)
    figs = [("eval/figures/fig_controlled_prf.png", "Figure 6.2: Precision, recall and F1-score of the three configurations on the controlled test set"),
            ("eval/figures/fig_yada_share_flagged.png", "Figure 6.3: Share of Yada et al. texts flagged by the text scorer, by original category"),
            ("eval/figures/fig_mathur_recall.png", "Figure 6.4: Recall of the text scorer on Mathur et al. types with a clean CCPA mapping"),
            ("eval/figures/fig_scan_latency.png", "Figure 6.5: Scan time per page state on the controlled test set")]
    for path, capt in figs:
        ip = add_picture_par(anchor, img_tmpl, ROOT / path, 5.8)
        c = clone_after(ip._p, fig_caption_tmpl, capt)
        anchor = c._p
        log("6.12 " + capt.split(":")[0], "(new figure)", capt, path)

    # ---------- 6.13 ----------
    h = find_par(doc, "6.13 Planned Error Analysis", style="Heading 2")
    replace_in(h, "6.13 Planned Error Analysis", "6.13 Error Analysis"); log("6.13 heading", "6.13 Planned Error Analysis", "6.13 Error Analysis", "Phase 6 instruction")
    for p in doc.paragraphs:
        if p.text.startswith("6.13 Planned Error Analysis") and p.style.name != "Heading 2":
            replace_in(p, "6.13 Planned Error Analysis", "6.13 Error Analysis"); log("Table of contents", "6.13 Planned Error Analysis", "6.13 Error Analysis", "heading change")
    p = find_par(doc, "Once results are available, error analysis will be based")
    before = p.text
    after = ("The errors below were taken from the evaluation outputs (eval/text_results.json and eval/controlled_results.json). Personal names "
             "and places in dataset strings are replaced with placeholders in angle brackets. One rule was changed as a result of the case "
             "studies: text evidence for confirm shaming is now counted only on controls the user can choose, because the case 2 banner quoted the "
             "phrase \"No I will take risk\" in an ordinary paragraph and was reported on both steps (report/changes.md).")
    set_text(p, after); log("6.13 Error Analysis", before, after, "report/error_analysis.md")
    ea = (ROOT / "report/error_analysis.md").read_text(encoding="utf-8")
    items = re.findall(r"^\d+\. \*\*(.+?)\*\* (.+)$", ea, flags=re.M)
    anchor = p._p
    for title, body in items:
        body = body.replace("`", "")
        np_ = clone_after(anchor, bullet_tmpl, parts=[(title + " ", True), (body, False)])
        anchor = np_._p
        log("6.13 Error Analysis", "(new list item)", f"{title} {body}", "report/error_analysis.md")

    # ---------- 7.9 ----------
    lim = [
        f"No live-site or held-out-site results are available. The evaluation used a controlled test set of {size['pages']} pages written by the team and two public English text datasets.",
        "Hinglish performance has not been validated.",
        "The weights αk, the threshold τ, the rule thresholds and the severity weights wk are set in config.json but have not been calibrated on a validation split; all wk are 1.",
        "Some statutory categories involve intent, which interface features cannot prove; outputs are indicators for review, not legal findings.",
        "The design targets Chromium-based browsers and does not cover mobile applications.",
        "The text component is a rule-based stand-in. The DistilBERT classifier, inference service, backend, dashboard and crawler have not been built (Table 5.8)."
        + (" A binary DistilBERT baseline was trained separately but is not integrated." if tr else ""),
        "The content script runs on all URLs (TC-F03), and no rules exist for subscription trap and nagging (TC-S08).",
    ]
    old = []
    el = find_par(doc, "The current limitations of the project are:")._p.getnext()
    while el is not None and Paragraph(el, bullet_tmpl._parent).style.name == "List Paragraph":
        old.append(Paragraph(el, bullet_tmpl._parent)); el = el.getnext()
    before = "\n".join(p.text for p in old)
    anchor = old[0]._p.getprevious()
    for p in old:
        p._p.getparent().remove(p._p)
    for text in lim:
        anchor = clone_after(anchor, bullet_tmpl, text)._p
    log("7.9 Current Limitations", before, "\n".join(lim), "Table 5.8; report/test_results.json; extension/config.json")

    # ---------- 8.3 to 8.6 ----------
    c = RES["controlled_test_set"]["configs"]
    ups = {
        "On the basis of the evidence available for this report": (
            "8.3 Work Completed So Far",
            "The following work has been completed: the problem formulation and design requirements; the system architecture; the category-to-signal "
            "mapping; the score-fusion and Manipulation Score formulation; a Manifest V3 Chrome extension with a rule engine of five structural checks, "
            "a rule-based text scorer, fusion with weights read from config.json, in-page highlights with explanations and a popup showing the "
            "Manipulation Score; three demo pages and five reconstructed CCPA case pages; automated tests for every test case in Chapter 6; and an "
            "evaluation on the controlled test set and on two public text datasets." + (" A binary DistilBERT baseline was also trained on the Yada et al. dataset." if tr else "")),
        "The implementation status of the extension, rule engine": (
            "8.4 Current Development Status",
            f"Table 5.8 records the status of each component. Of the {len(TESTS)} test cases in Chapter 6, "
            f"{sum(1 for t in TESTS.values() if t['status'] == 'Pass')} passed, {sum(1 for t in TESTS.values() if t['status'] == 'Fail')} failed (TC-F03), "
            f"{sum(1 for t in TESTS.values() if t['status'] == 'Not applicable')} were not applicable because the backend, dashboard and inference service "
            f"were not built, and {sum(1 for t in TESTS.values() if t['status'] == 'Not implemented')} was not implemented (TC-S08). On the controlled test set the "
            f"combined configuration reached F1 {fmt(c['combined']['overall']['f1'])}, compared with {fmt(c['rules_only']['overall']['f1'])} for rules only and "
            f"{fmt(c['text_only']['overall']['f1'])} for text only. No held-out-site results are available."),
        "The remaining work consists of": (
            "8.5 Remaining Work",
            "The remaining work consists of collecting and labelling pages from Indian websites with four annotators and measuring agreement; "
            "fine-tuning the DistilBERT classifier for thirteen categories plus a negative class and serving it through an inference service; "
            "building the backend and dashboard; adding the subscription-trap and nagging rules; restricting the content script to target sites; "
            "calibrating αk, τ, the rule thresholds and wk on a validation split; and carrying out the held-out evaluation and error analysis described in Chapter 6."),
    }
    for start, (sec, text) in ups.items():
        p = find_par(doc, start)
        before = p.text
        set_text(p, text); log(sec, before, text, "Table 5.8; report/test_results.json; eval/results.json")
    p = find_par(doc, "Its central idea, that manipulation can be carried")
    before = p.text
    add = (" The prototype shows the idea working on a controlled test set: neither rules alone nor text alone found every labelled element, "
           "while the combination did. Because the test pages were written together with the rules, this result must be confirmed on unseen websites.")
    set_text(p, before + add); log("8.6 Final Conclusion", before, p.text, "eval/results.json")

    # ---------- Appendix B ----------
    p = find_par(doc, "Fusion weights, the decision threshold and severity weights are intended")
    before = p.text
    after = ("Fusion weights, the decision threshold, severity weights and rule thresholds are stored in extension/config.json and loaded when the "
             "extension starts, so they can be changed without code changes (requirement R4, test TC-H05). Table B.1 lists their current values. "
             "None has been calibrated on a validation split.")
    set_text(p, after); log("Appendix B", before, after, "extension/config.json")
    _, tb1 = find_table_after(doc, "Table B.1:")
    al = {}
    for cc in CFG["categories"]:
        al.setdefault(cc["alpha"], []).append(cc["key"].replace("_", " "))
    alpha_txt = "; ".join(f"{a} for {len(v)} categor{'y' if len(v) == 1 else 'ies'} ({', '.join(v)})" for a, v in sorted(al.items(), reverse=True))
    r = CFG["rules"]
    sev = sorted({cc["severity"] for cc in CFG["categories"]})
    cur = {"αk": alpha_txt, "τ": str(CFG["tau"]),
           "Rule thresholds": f"contrastLimit {r['contrastLimit']}; sizeRatio {r['sizeRatio']}; overlayCoverage {r['overlayCoverage']}; timerSlackSeconds {r['timerSlackSeconds']}; memoryMinutes {r['memoryMinutes']}",
           "wk": f"{sev[0]} for all 13 categories" if len(sev) == 1 else ", ".join(f"{c['key']}: {c['severity']}" for c in CFG["categories"])}
    grid = tb1._tbl.find(W + "tblGrid")
    cols = grid.findall(W + "gridCol")
    total = sum(int(cc.get(W + "w")) for cc in cols)
    neww = [int(total * f) for f in (0.16, 0.30, 0.18, 0.36)]
    newcol = copy.deepcopy(cols[-1]); grid.append(newcol)
    for cc, wv in zip(grid.findall(W + "gridCol"), neww):
        cc.set(W + "w", str(wv))
    for row in tb1.rows:
        tc = copy.deepcopy(row._tr.findall(W + "tc")[-1])
        row._tr.append(tc)
        for tcel, wv in zip(row._tr.findall(W + "tc"), neww):
            tcw = tcel.find(W + "tcPr").find(W + "tcW")
            if tcw is not None:
                tcw.set(W + "w", str(wv))
    set_cell(tb1.rows[0].cells[3], "Current value (config.json)")
    for row in tb1.rows[1:]:
        k = row.cells[0].text.strip()
        set_cell(row.cells[3], cur.get(k, "Not applicable"))
        log(f"Appendix B Table B.1 ({k})", "(new column)", cur.get(k, "Not applicable"), "extension/config.json")

    # ---------- Appendix C ----------
    p = find_par(doc, "Implementation screenshots:")
    before = p.text
    set_runs(p, [("Implementation screenshots:", True), (" Figures C.1 to C.7 below, captured from the extension running in Chromium on the demo and case pages (tools/screenshots.py, tests/run_cases.py). No dashboard exists, so none is shown.", False)])
    log("Appendix C", before, p.text, "report/screenshots/")
    shots = [("report/screenshots/appc_dark_checkout_reload.png", 5.6, "Figure C.1: Extension highlights on demo/dark-checkout.html after one reload (five detections)"),
             ("report/screenshots/appc_popup_dark_checkout.png", 2.8, "Figure C.2: Toolbar popup with the Manipulation Score and the detections for demo/dark-checkout.html"),
             ("report/screenshots/appc_spa_addons.png", 5.6, "Figure C.3: Detections on the add-ons step of demo/spa-booking.html (options ticked by script and an ARIA switch)"),
             ("report/screenshots/appc_fair_checkout.png", 5.6, "Figure C.4: The fair page demo/fair-checkout.html with no detections"),
             ("report/screenshots/appc_popup_fair_checkout.png", 2.8, "Figure C.5: Toolbar popup for the fair page, showing no detections"),
             ("report/screenshots/case3_quick_commerce_checkout_after.png", 5.6, "Figure C.6: Reconstructed quick-commerce case, checkout step: drip pricing and basket sneaking"),
             ("report/screenshots/case2_airline_risk_addons_after.png", 5.6, "Figure C.7: Reconstructed airline case: the opt-out \"No I will take risk\" reported as confirm shaming")]
    anchor = find_par(doc, "Publication acceptance or payment proof:")._p
    for path, wdt, capt in shots:
        ip = add_picture_par(anchor, img_tmpl, ROOT / path, wdt)
        c = clone_after(ip._p, fig_caption_tmpl, capt)
        anchor = c._p
        log("Appendix C " + capt.split(":")[0], "(new figure)", capt, path)

    # ---------- lists of figures and tables (manual tables in the front matter) ----------
    lof, lot = doc.tables[1], doc.tables[2]

    def add_list_rows(t, entries, after_no=None):
        tmpl = t.rows[-1]._tr
        anchor_tr = tmpl
        if after_no:
            for r in t.rows:
                if r.cells[0].text.strip() == after_no:
                    anchor_tr = r._tr
        for no, name in entries:
            tr_ = copy.deepcopy(tmpl)
            anchor_tr.addnext(tr_)
            anchor_tr = tr_
        rows_ = {id(r._tr): r for r in t.rows}
        cur_ = anchor_tr
        new_rows = []
        for r in t.rows:
            pass
        # set texts for the inserted rows (found by order after the anchor)
        trs = [r for r in t.rows]
        idx = [i for i, r in enumerate(trs) if r._tr is anchor_tr][0]
        for (no, name), r in zip(entries, trs[idx - len(entries) + 1: idx + 1]):
            set_cell(r.cells[0], no); set_cell(r.cells[1], name); set_cell(r.cells[2], "")
            log("List of figures/tables", "(new row)", f"{no} {name} (page number to be filled in Word)", "new caption")

    add_list_rows(lof, [(c.split(":")[0].replace("Figure ", ""), c.split(": ", 1)[1]) for _, c in figs], after_no="6.1")
    add_list_rows(lof, [(c.split(":")[0].replace("Figure ", ""), c.split(": ", 1)[1]) for _, _, c in shots])
    new_tables = [("6.7", "Text check of the rule-based text scorer on the Yada et al. dataset"),
                  ("6.8", "Recall of the rule-based text scorer on the Mathur et al. dataset"),
                  ("6.9", "Results on the reconstructed CCPA cases")] + ([("6.10", "Binary DistilBERT baseline and rule-based text scorer on the Yada et al. test split")] if tr else [])
    add_list_rows(lot, new_tables, after_no="6.6")
    for r in lot.rows:
        no = r.cells[0].text.strip()
        if no == "6.6":
            b = r.cells[1].text; set_cell(r.cells[1], "Overall results on the controlled test set"); log("List of tables", b, "Overall results on the controlled test set", "caption change")
        if no == "4.5":
            b = r.cells[1].text; set_cell(r.cells[1], "Explanation templates by category (extension/categories.js)"); log("List of tables", b, r.cells[1].text, "caption change")

    doc.save(DST)

    # ---------- edit log ----------
    L = ["# Report edits", "", f"Source: docs/PatternGuard_Minor_Project_Report1.docx (unchanged). Output: {DST.relative_to(ROOT)}.",
         "Generated by tools/update_report.py, which rebuilds the copy from the original on every run.", "",
         "| # | Section | Before | After | Source of the value |", "|---|---|---|---|---|"]
    esc = lambda s: str(s).replace("|", "\\|").replace("\n", "<br>")
    for i, (s, b, a, src) in enumerate(LOG, 1):
        L.append(f"| {i} | {esc(s)} | {esc(b)} | {esc(a)} | {esc(src)} |")
    (ROOT / "report/report_edits.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"saved {DST.relative_to(ROOT)} with {len(LOG)} logged edits")


if __name__ == "__main__":
    main()
