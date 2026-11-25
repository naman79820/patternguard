"""Dump a .docx body in order: paragraphs (with style) and tables, with indexes."""
import sys
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph

def iter_block(doc):
    for child in doc.element.body.iterchildren():
        tag = child.tag.split('}')[1]
        if tag == 'p':
            yield Paragraph(child, doc)
        elif tag == 'tbl':
            yield Table(child, doc)

doc = Document(sys.argv[1])
pi = ti = 0
out = []
for b in iter_block(doc):
    if isinstance(b, Paragraph):
        t = b.text.strip()
        has_img = bool(b._p.xpath('.//w:drawing'))
        if t or has_img:
            out.append(f"P{pi} [{b.style.name}]{' [IMG]' if has_img else ''} {t}")
        pi += 1
    else:
        out.append(f"=== TABLE {ti} style={b.style.name if b.style is not None else None} rows={len(b.rows)}")
        for r in b.rows:
            cells = []
            for c in r.cells:
                cells.append(c.text.strip().replace('\n', ' / '))
            out.append("  | " + " | ".join(cells))
        ti += 1
open(sys.argv[2], 'w', encoding='utf-8').write("\n".join(out))
print(pi, ti)
