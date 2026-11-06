"""Find display equations, save each as PNG, and replace it in the PDF with a placeholder line.

Display equations in these APS chapters are MathType objects whose text layer is scrambled
(or hidden), so the faithful thing to carry into Markdown is the rendered equation itself.
"""
import re, pymupdf

EQNUM = re.compile(r"^\(([1-9]\d?\.\d{1,3}[a-z]?)\)$")
MATHFONT = re.compile(r"Pi|MT-|Euclid")


def columns(page, lines=None):
    """Column extents from the text itself (left/right pages have different margins)."""
    w = page.rect.width
    wide = [x["r"] for x in (lines or []) if x["r"].width > 150]
    if len(wide) < 4:
        return [(36, w / 2 - 6), (w / 2 + 2, w - 36)]
    left = min(r.x0 for r in wide); right = max(r.x1 for r in wide)
    mid = (left + right) / 2
    lcol = [r for r in wide if r.x1 < mid + 20]
    rcol = [r for r in wide if r.x0 > mid - 20]
    med = lambda v, d: sorted(v)[len(v) // 2] if v else d
    l1 = med([r.x1 for r in lcol], mid - 9)
    r0 = med([r.x0 for r in rcol], mid + 9)
    return [(left, l1), (r0, right)]


def find_regions(page):
    W = page.rect.width
    lines = []
    for b in page.get_text("dict")["blocks"]:
        if b["type"] != 0:
            continue
        for l in b["lines"]:
            t = "".join(s["text"] for s in l["spans"]).strip()
            if not t:
                continue
            fonts = [s["font"] for s in l["spans"] if s["text"].strip()]
            lines.append(dict(r=pymupdf.Rect(l["bbox"]), t=t,
                              math=any(MATHFONT.search(f) for f in fonts)))
    seen = {(round(x["r"].x0), round(x["r"].y0)) for x in lines}
    hidden = []  # glyphs drawn but dropped by get_text (common for MathType objects)
    for tr in page.get_texttrace():
        r = pymupdf.Rect(tr["bbox"])
        if r.is_empty or r.height > 40:
            continue
        hidden.append(r)
    bars = [pymupdf.Rect(d["rect"]) for d in page.get_drawings()
            if pymupdf.Rect(d["rect"]).height < 2.5 and 3 < pymupdf.Rect(d["rect"]).width < 250]
    imgs = [pymupdf.Rect(i["bbox"]) for i in page.get_image_info()]
    try:  # real tables only: a "table" that holds an equation number is a MathType equation array
        for t in page.find_tables().tables:
            tb = pymupdf.Rect(t.bbox)
            if not any(re.search(r"\(([1-9]\d?\.\d{1,3}[a-z]?)\)$", x["t"]) and x["r"].intersects(tb) for x in lines):
                imgs.append(tb)
    except Exception:
        pass
    lines = [x for x in lines if not any(x["r"].intersects(im) for im in imgs)]

    regions = []
    all_prose = []
    for cl, cr in columns(page, lines):
        inside = lambda r: r.x0 >= cl - 3 and r.x1 <= cr + 3
        col_lines = [x for x in lines if inside(x["r"])]
        ENDNUM = re.compile(EQNUM.pattern.replace("^", r"(?:^|\s)"))
        nums = [x for x in col_lines if ENDNUM.search(x["t"]) and x["r"].x1 > cl + (cr - cl) * 0.5]
        for x in nums:
            x["num"] = ENDNUM.search(x["t"]).group(1)

        def row_words(x):  # words on the same visual line, across fragments
            r = x["r"]
            return sum(len(re.findall(r"[A-Za-z]{3,}", y["t"])) for y in col_lines
                       if min(r.y1, y["r"].y1) - max(r.y0, y["r"].y0) > 0.5 * min(r.height, y["r"].height))

        def proseish(x):
            if "num" in x:
                return False
            words = re.findall(r"[A-Za-z]{3,}", x["t"])
            if row_words(x) >= 6 and x["r"].height < 14:
                return True  # part of a sentence that runs across this line
            real = [w for w in words if w.lower() not in ("exp", "log", "min", "max", "for", "and", "otherwise")]
            if (x["math"] and len(words) < 4 or len(real) < 2) and re.search(r"[=≈≤≥<>]", x["t"]):
                return False  # an equation line that happens to start at the margin
            starts_left = x["r"].x0 < cl + 8
            return (starts_left and (len(words) >= 2 or x["r"].width > (cr - cl) * 0.5)
                    or len(words) >= 4 and x["r"].width > (cr - cl) * 0.6)

        prose = [x["r"] for x in col_lines if proseish(x)]
        all_prose.extend(prose)
        # full-width text (table notes, wide captions) also fences equations in
        prose += [x["r"] for x in lines if x["r"].width > (cr - cl) * 1.3
                  and len(re.findall(r"[A-Za-z]{3,}", x["t"])) >= 4]
        def inline(r):  # shares its text line with prose -> inline math, not display
            return any(min(r.y1, p.y1) - max(r.y0, p.y0) > 0.5 * min(r.height, p.height) for p in prose)

        seeds = [x["r"] for x in nums]
        seeds += [x["r"] for x in col_lines
                  if not proseish(x) and (x["math"] or re.search(r"[=≈≤≥<>]", x["t"]))
                  and x["r"].x1 < cr - 18 and (x["r"].x0 > cl + 18 or x["r"].x0 < cl + 8)
                  and not inline(x["r"]) and not x["t"].startswith(("•", "∑ "))
                  and len(x["t"]) >= 3 and x["r"].height >= 7
                  and len(re.findall(r"[A-Za-z]{3,}", x["t"])) < 4
                  and re.search(r"[=≈≤≥<>∑∏∫√±×∝∂]", x["t"])]
        if not seeds:
            continue
        centred = lambda r: r.x0 > cl + 12  # display maths is indented/centred; prose starts at the margin
        # lines that get_text missed but texttrace sees, starting at the margin, are prose too
        prose += [r for r in hidden if inside(r) and r.x0 < cl + 4 and r.width > (cr - cl) * 0.5 and r.height < 14
                  and not any(min(r.y1, x["r"].y1) - max(r.y0, x["r"].y0) > 2 for x in nums)]
        ink = [x["r"] for x in col_lines if not proseish(x) and not inline(x["r"])
               and (centred(x["r"]) or x["math"] or re.search(r"[=≈≤≥<>]", x["t"]))]
        ink += [r for r in hidden if inside(r) and centred(r) and not inline(r)
                and not any(r.intersects(p) and (r & p).height > r.height * .5 for p in prose)]
        ink += [r for r in bars if inside(r) and centred(r)]
        ink = [r for r in ink if not any(r.intersects(im) for im in imgs)]
        ink.sort(key=lambda r: r.y0)
        # grow clusters around seeds
        for s in seeds:
            if any(s.intersects(g) for g in regions):
                continue
            y0, y1 = s.y0, s.y1
            changed = True
            while changed:
                changed = False
                for r in ink:
                    if r.y0 <= y1 + 6 and r.y1 >= y0 - 6 and (r.y0 < y0 or r.y1 > y1):
                        y0, y1 = min(y0, r.y0), max(y1, r.y1); changed = True
            g = pymupdf.Rect(cl, y0, cr, y1)
            above = [p.y1 for p in prose if p.y1 <= g.y0 + 2]
            below = [p.y0 for p in prose if p.y0 >= g.y1 - 2]
            top = max(above) if above else g.y0 - 3
            bot = min(below) if below else g.y1 + 3
            reg = pymupdf.Rect(cl - 2, max(top, g.y0 - 3), cr + 5, min(bot, g.y1 + 3))
            mid = (s.y0 + s.y1) / 2
            for pr in prose:  # never swallow a prose line whose middle falls inside
                c = (pr.y0 + pr.y1) / 2
                if pr.y0 <= mid <= pr.y1:
                    continue  # the seed's own line
                if reg.y0 < c < reg.y1 and pr.x1 > cl and pr.x0 < cr:
                    if c > mid:
                        reg.y1 = min(reg.y1, pr.y0)
                    else:
                        reg.y0 = max(reg.y0, pr.y1)
            if reg.height < 9:
                continue
            num = next((x["num"] for x in nums if x["r"].intersects(reg)), None)
            regions.append(reg)
            regions[-1].num = num
    # merge overlapping regions in same column
    regions.sort(key=lambda r: (r.x0, r.y0))
    out = []
    for r in regions:
        between = out and any(out[-1].y1 - 1 < (p.y0 + p.y1) / 2 < r.y0 + 1 and p.x0 < r.x1 and p.x1 > r.x0
                              for p in all_prose)
        if out and abs(out[-1].x0 - r.x0) < 1 and r.y0 <= out[-1].y1 + 14 and not between:
            n = getattr(out[-1], "num", None) or getattr(r, "num", None)
            nums = [x for x in (getattr(out[-1], "num", None), getattr(r, "num", None)) if x]
            m = out[-1] | r; m.num = ",".join(dict.fromkeys(nums)) or None
            out[-1] = m
        else:
            out.append(r)
    # an unnumbered "equation" that carries running words is a worked calculation inside the
    # text (e.g. "Virginia, logit(p) = -0.16, SE = 0.12. The difference"): keep it as text
    STOP = {"exp", "log", "min", "max", "for", "and", "the", "otherwise", "logit", "odds", "rate"}
    def wordy(r):
        txt = " ".join(x["t"] for x in lines if r.contains(x["r"]) or (x["r"] & r).get_area() > 0.6 * x["r"].get_area())
        return len([w for w in re.findall(r"[A-Za-z]{3,}", txt) if w.lower() not in STOP]) >= 3
    out = [r for r in out if getattr(r, "num", None) or not wordy(r)]
    out.sort(key=lambda r: (r.x0 > page.rect.width / 2, r.y0))
    return out


def extract(doc, chapter, figdir, prefix="eq"):
    """Render equations to PNG and swap them for placeholders. Returns {token: (file, num)}."""
    table = {}
    k = 0
    for pno, page in enumerate(doc):
        regs = find_regions(page)
        toks = []
        for r in regs:
            k += 1
            token = f"EQIMG{chapter:02d}x{k:03d}"
            fname = f"{prefix}{chapter}-{k:03d}.png"
            page.get_pixmap(dpi=220, clip=r).save(f"{figdir}/{fname}")
            table[token] = (fname, getattr(r, "num", None), pno)
            toks.append(token)
        for r, token in zip(regs, toks):
            page.add_redact_annot(r, text=token, fontname="helv", fontsize=7, align=0, fill=(1, 1, 1))
        if regs:
            page.apply_redactions(images=pymupdf.PDF_REDACT_IMAGE_NONE,
                                  graphics=pymupdf.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED)
    return table
