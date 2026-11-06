"""Coverage checks: every numbered equation imaged once; no prose swallowed into an equation crop;
word count of the Markdown vs the PDF text layer."""
import re, sys, glob, pymupdf
sys.path.insert(0, "/home/claude/work")
from equations import find_regions, EQNUM

for f in sorted(glob.glob("/home/claude/work/fixed/chapter-*.pdf"), key=lambda s: int(re.search(r"chapter-(\d+)", s).group(1))):
    n = int(re.search(r"chapter-(\d+)", f).group(1))
    if n == 1:
        continue
    d = pymupdf.open(f)
    nums, covered, prose_hits = [], set(), []
    pdf_words = 0
    for pno, p in enumerate(d):
        regs = find_regions(p)
        for b in p.get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                t = "".join(s["text"] for s in l["spans"]).strip()
                r = pymupdf.Rect(l["bbox"])
                if EQNUM.match(t) or re.search(r"\s\(([1-9]\d?\.\d{1,3}[a-z]?)\)$", t):
                    nums.append(t)
                    if any(r.intersects(g) for g in regs):
                        covered.add(t)
                elif len(re.findall(r"[A-Za-z]{3,}", t)) >= 6:
                    for g in regs:
                        if r.intersects(g) and (r & g).height > r.height * 0.6:
                            prose_hits.append((pno + 1, t[:70]))
        pdf_words += len(re.findall(r"[A-Za-z]{3,}", p.get_text()))
    try:
        md = open(f"/home/claude/work/out/ch{n:02d}/ch{n:02d}.md").read()
        md_words = len(re.findall(r"[A-Za-z]{3,}", re.sub(r"\(figures/[^)]*\)|\{[^}]*\}", "", md)))
    except FileNotFoundError:
        md_words = None
    missing = [x for x in nums if x not in covered]
    print(f"ch{n}: eq-numbers {len(nums)} missing {len(missing)} {missing[:6]} | prose-in-eq {len(prose_hits)} {prose_hits[:3]} | words pdf {pdf_words} md {md_words}")
