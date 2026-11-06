"""Clean pymupdf4llm output into Quarto-ready Markdown.
usage: postprocess.py <outdir> <chapter-no> <title-for-yaml> <pages>"""
import re, sys, pathlib

outdir, n = pathlib.Path(sys.argv[1]), int(sys.argv[2])
pages = sys.argv[3] if len(sys.argv) > 3 else ""
raw = (outdir / "_raw.md").read_text()
figdir = outdir / "figures"

raw = raw.replace("￿", "")

# ---- figures: rename pymupdf4llm image files, make paths relative ----
k = 0
def ren(m):
    global k
    k += 1
    old = pathlib.Path(m.group(1)).name
    new = f"fig{n}-img{k:02d}.png"
    if (figdir / old).exists():
        (figdir / old).rename(figdir / new)
    return f"![](figures/{new})"
raw = re.sub(r"!\[\]\(([^)]*_redacted\.pdf-[^)]*\.png)\)", ren, raw)

# ---- display equations ----
def eqrep(m):
    tok = m.group(1)
    num = int(tok.split("x")[1])
    return f"\n\n![](figures/eq{n}-{num:03d}.png){{.equation width=60%}}\n\n"
raw = re.sub(r"(?m)^#+\s*(EQIMG\d+x\d+)\s*$", lambda m: eqrep(m), raw)
raw = re.sub(r"(EQIMG\d+x\d+)", lambda m: eqrep(m), raw)

blocks = [b.strip() for b in re.split(r"\n\s*\n", raw) if b.strip()]

# ---- drop page furniture (running heads come through as small-caps <mark> runs) ----
def running_head(b):
    if "<mark>" not in b:
        return False
    plain = re.sub(r"</?mark>", "", b)
    return not re.search(r"[a-z]", plain) and len(plain) < 120

keep = []
for b in blocks:
    if running_head(b):
        continue
    b = re.sub(r"</?mark>", "", b)
    if re.match(r"^(The Study of Plant Disease Epidemics|Copyright ©|ISBN)", b):
        continue
    if re.fullmatch(r"\**\d{1,3}\**", b):  # stray page / chapter numbers
        continue
    keep.append(b)

# ---- headings: keep numbered ones and the chapter title, demote the rest ----
out = []
title_done = False
for b in keep:
    m = re.match(r"^(#+)\s+(.*)$", b, re.S)
    if m:
        text = re.sub(r"\*\*", "", m.group(2)).strip()
        if not title_done:
            out.append(f"# {text} {{#sec-ch{n}}}"); title_done = True; continue
        num = re.match(r"^(\d+(?:\.\d+)+)\s", text)
        if num:
            depth = num.group(1).count(".") + 1  # 4.1 -> ##, 4.4.1 -> ###
            out.append("#" * min(depth, 4) + " " + text); continue
        if text.lower().startswith(("suggested reading", "references")):
            out.append("## " + text); continue
        out.append(text)  # e.g. "and" between equations
        continue
    out.append(b)
keep = out

# ---- re-join paragraphs split by columns, pages, figures and tables ----
def floating(b):
    return b.startswith(("![](figures/fig", "|", "**FIG", "**Fig", "**TABLE", "**Table"))

def body(b):
    return not (floating(b) or b.startswith(("#", "![", "- ", "> ", "<")))

def ends(b):
    return re.search(r'[.:;?!”)\]]\**_?\s*$', b) is not None

i = 0
while i < len(keep):
    b = keep[i]
    if body(b):
        j = i + 1
        while j < len(keep) and floating(keep[j]):
            j += 1
        if j < len(keep) and body(keep[j]):
            nxt = keep[j]
            first = re.sub(r"^[_*(\s]+", "", nxt)[:1]
            if not ends(b) or first.islower():
                keep[i] = b.rstrip() + " " + nxt.lstrip()
                del keep[j]
                continue
    i += 1

# ---- figure captions: fold into the image right before them ----
merged = []
for b in keep:
    m = re.match(r"^\*\*FIG\.\s*(\d+\.\d+)\.\*\*\s*(.*)$", b, re.S)
    if m:
        cap = m.group(2).strip()
        if merged and re.fullmatch(r"!\[\]\(figures/fig[^)]*\)", merged[-1]):
            fid = m.group(1).replace(".", "-")
            merged[-1] = merged[-1].replace("![]", f"![{cap}]") + f"{{#fig-{fid}}}"
            continue
        b = f"**Fig. {m.group(1)}.** {cap}"
    b = re.sub(r"^\*\*TABLE\s+(\d+\.\d+)\.\*\*", r"**Table \1.**", b)
    merged.append(b)

text = "\n\n".join(merged)

# ---- tidy inline spacing left by span joins ----
text = re.sub(r"\(\s+([_*])", r"(\1", text)
text = re.sub(r"([_*])\s+([,.;:)\]])", r"\1\2", text)
text = re.sub(r"_\s+_", " ", text)
text = re.sub(r"[ \t]+\n", "\n", text)
text = re.sub(r"(?<=\S)  +", " ", text)

hdr = f'---\nchapter: {n}\nsource: "Madden, Hughes & van den Bosch (2007). The Study of Plant Disease Epidemics. APS Press{", pp. " + pages if pages else ""}"\n---\n\n'
(outdir / f"ch{n:02d}.md").write_text(hdr + text.strip() + "\n")
print(n, "blocks", len(merged), "images", k)
