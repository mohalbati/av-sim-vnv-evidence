"""Build docs/technical_report.docx and docs/technical_report.pdf from docs/technical_report.md.

Needs pandoc 3.x, python-docx and Playwright with Chromium (for the PDF).
Run: python scripts/build_report.py
"""
import os, re, subprocess, zipfile, shutil, pathlib
from docx import Document
from docx.shared import Pt, RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

DOCS = pathlib.Path(__file__).resolve().parents[1] / "docs"
MD, DOCX, HTML, PDF = (DOCS / f for f in ("technical_report.md", "technical_report.docx", "_report.html", "technical_report.pdf"))
TITLE = re.search(r'^title: "(.*)"', MD.read_text(encoding="utf-8"), re.M).group(1)


def word():
    subprocess.run(["pandoc", str(MD), "-o", str(DOCX), "--reference-doc", str(DOCS / "ref.docx"), "--toc", "--toc-depth=2",
                    "-M", "toc-title=Contents", "--resource-path", str(DOCS)], check=True, cwd=DOCS)
    d = Document(DOCX)
    for t in d.tables:
        pr = t._tbl.tblPr
        old = pr.find(qn("w:tblBorders"))
        if old is not None: pr.remove(old)
        b = OxmlElement("w:tblBorders")
        for e in ("top", "left", "bottom", "right", "insideH", "insideV"):
            x = OxmlElement("w:" + e); x.set(qn("w:val"), "single"); x.set(qn("w:sz"), "4"); x.set(qn("w:color"), "BFBFBF"); b.append(x)
        pr.append(b)
        for i, row in enumerate(t.rows):
            for c in row.cells:
                if i == 0:
                    sh = OxmlElement("w:shd"); sh.set(qn("w:val"), "clear"); sh.set(qn("w:fill"), "E8EEF8"); c._tc.get_or_add_tcPr().append(sh)
                for p in c.paragraphs:
                    p.paragraph_format.space_before = Pt(1); p.paragraph_format.space_after = Pt(1)
                    for r in p.runs:
                        r.font.size = Pt(8.8); r.font.bold = r.font.bold or i == 0
        h = OxmlElement("w:tblHeader"); h.set(qn("w:val"), "true"); t.rows[0]._tr.get_or_add_trPr().append(h)
    fp = d.sections[0].footer.paragraphs[0]
    fp.alignment = 1
    r = fp.add_run(TITLE + " · page "); r.font.size = Pt(8.5); r.font.color.rgb = RGBColor(0x7F, 0x7F, 0x7F)
    for kind, txt in (("begin", None), (None, "PAGE"), ("end", None)):
        run = fp.add_run(); run.font.size = Pt(8.5)
        if kind:
            f = OxmlElement("w:fldChar"); f.set(qn("w:fldCharType"), kind); run._r.append(f)
        else:
            it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = txt; run._r.append(it)
    d.save(DOCX)
    tmp = str(DOCX) + ".tmp"          # ask Word to refresh the table of contents when the file is opened
    with zipfile.ZipFile(DOCX) as zi, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zo:
        for it in zi.infolist():
            data = zi.read(it.filename)
            if it.filename == "word/settings.xml" and b"updateFields" not in data:
                data = re.sub(rb"(<w:settings[^>]*>)", rb'\1<w:updateFields w:val="true"/>', data, count=1)
            zo.writestr(it, data)
    shutil.move(tmp, DOCX)


def pdf():
    subprocess.run(["pandoc", str(MD), "-s", "--mathml", "--toc", "--toc-depth=2", "-M", "toc-title=Contents", "--embed-resources",
                    "--css", str(DOCS / "report.css"), "--resource-path", str(DOCS), "-o", str(HTML)], check=True, cwd=DOCS)
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        br = p.chromium.launch(); pg = br.new_page()
        pg.goto(HTML.as_uri()); pg.wait_for_timeout(800)
        pg.pdf(path=str(PDF), format="Letter", print_background=True, display_header_footer=True, header_template="<span></span>",
               footer_template=f'<div style="font-size:8px;color:#888;width:100%;text-align:center;font-family:DejaVu Sans,Arial">{TITLE} · <span class="pageNumber"></span>/<span class="totalPages"></span></div>',
               margin={"top": "0.7in", "bottom": "0.75in", "left": "0.8in", "right": "0.8in"})
        br.close()
    os.remove(HTML)


if __name__ == "__main__":
    word(); pdf(); print("wrote", DOCX.name, "and", PDF.name)
