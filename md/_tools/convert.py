"""PDF chapter -> Quarto-ready Markdown.  usage: convert.py <fixed.pdf> <chapter-no> <outdir>"""
import os, re, sys, pathlib, pymupdf, pymupdf4llm
sys.path.insert(0, os.path.dirname(__file__))
from equations import extract

src, n, outdir = sys.argv[1], int(sys.argv[2]), pathlib.Path(sys.argv[3])
figdir = outdir / "figures"
figdir.mkdir(parents=True, exist_ok=True)

doc = pymupdf.open(src)
eqs = extract(doc, n, str(figdir))
tmp = outdir / "_redacted.pdf"
doc.save(tmp)
doc.close()

md = pymupdf4llm.to_markdown(str(tmp), write_images=True, image_path=str(figdir), dpi=200,
                             header=True, footer=True, use_ocr=False, force_text=False)
tmp.unlink()
(outdir / "_raw.md").write_text(md)
print(n, "equations:", len(eqs), "chars:", len(md))
