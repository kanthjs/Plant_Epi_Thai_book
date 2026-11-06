"""Rewrite ToUnicode CMaps of the APS math fonts so text extraction yields real symbols.

The MathematicalPi / MT-Symbol / MT-Extra / EuclidSymbol fonts in these PDFs carry
custom /Differences glyph names (H11005, cent, yen ...) and ToUnicode maps that are
empty or wrong. We rebuild ToUnicode from the glyph names, using a table that was
checked visually against rendered glyphs.
"""
import re, sys, pymupdf

H = {  # Linotype MathematicalPi "H" glyph names
    "H11001": "+", "H11002": "−", "H11003": "×", "H11005": "=", "HS11005": "≠",
    "H11008": "∝", "H11009": "±", "H11011": "∼", "H11013": "≡", "H11015": "≈",
    "H11021": "<", "H11022": ">", "H11032": "′", "H11033": "″", "H11034": "°",
    "H11061": "≅", "H11080": "·", "H11128": "∂", "H11341": "|", "H11349": "≤",
    "H11350": "≥", "H11408": "′", "H11623": "□", "H17004": "◆", "H17009": "▲",
    "H17033": "●", "H17039": "■", "H20848": "∫", "H5037": "ℵ", "H5133": "ℓ",
}
UPPER = "ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ"
for i, c in enumerate(UPPER):
    H[f"H{9001 + i}"] = c
LOWER = "αβγδεζηθικλμνξοπρσςτυφχψω"
for i, c in enumerate(LOWER):
    H[f"H{9251 + i}"] = c
H["H9277"] = "ϑ"; H["H9278"] = "ϕ"

SYMBOL_LETTERS = dict(zip("abcdefghijklmnopqrstuvwxyz",
                          "αβχδεφγηιϕκλμνοπθρστυϖωξψζ"))
SYMBOL_LETTERS.update(dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ",
                               "ΑΒΧΔΕΦΓΗΙϑΚΛΜΝΟΠΘΡΣΤΥςΩΞΨΖ")))
MATHPI_ITALIC = dict(a="α", c="ψ", d="δ", f="φ", g="γ", h="η", i="ι", j="ξ", k="κ",
                     l="λ", m="μ", r="ρ", s="σ", t="τ", u="θ", v="ω", w="φ", y="υ",
                     z="ζ", V="Ω")
NAMED = {  # MT-Symbol (MathType encoding), MT-Extra, EuclidSymbol
    "summation": "∑", "greaterequal": "≥", "lessequal": "≤", "plus": "+", "equal": "=",
    "less": "<", "greater": ">", "hyphen": "−", "minus": "−", "slash": "/",
    "parenleft": "(", "parenright": ")", "bracketleft": "[", "bracketright": "]",
    "braceleft": "{", "braceright": "}", "asterisk": "*", "bullet": "•",
    "cent": "′", "sterling": "≤", "yen": "×", "ordfeminine": "≈", "ordmasculine": "…",
    "plusminus": "±", "logicalnot": "ℜ", "degree": "ϒ", "divide": "√", "at": "≅",
    "asciitilde": "∼", "AE": "→", "Acircumflex": "∑",
    "lozenge": "·", "pi": "∏", "quoteright": "’",
    "circumflexnosp": "\u0302",
    "tildenosp": "̃", "slurabove": "̑", "slurbelow": "̯",
    "midhorizellipsis": "⋯", "ellipsis": "…", "lscript": "ℓ", "dotmath": "⋅",
    "partialdiff": "∂", "infinity": "∞", "xi": "ξ", "alpha": "α", "psi": "ψ",
    "theta": "θ", "omega": "ω", "mu": "μ", "space": " ",
    "two": "2", "three": "3", "zero": "0", "one": "1",
}
# delimiter/extension pieces of large brackets: only appear inside display equations
PIECES = {"Aacute", "Ecircumflex", "Edieresis", "Egrave", "Iacute", "Icircumflex",
          "Idieresis", "Igrave", "Oacute", "Ocircumflex", "Uacute", "cedilla",
          "underscore", "ae", "Ydieresis", "Atilde", "Adieresis", "Aring", "Ccedilla",
          "Eacute", "Ntilde", "Odieresis", "Otilde", "Ograve", "Ugrave", "Ucircumflex",
          "Udieresis", "dagger", "daggerdbl", "ogonek", "hungarumlaut", "quotesinglbase",
          # MathType MT-Symbol uses these names for large-delimiter pieces (checked visually)
          "circumflex", "tilde", "macron", "breve", "dotaccent", "ring", "radical",
          "integral", "fraction"}


def glyph_to_uni(font, name):
    if name in H:
        return H[name]
    if font.startswith("MathPiOne") and name in MATHPI_ITALIC:
        return MATHPI_ITALIC[name]
    # MathType's MT-Symbol names these two the other way round (verified by glyph widths:
    # 'summation' is 460 units = bullet, 'bullet' is 713 units = summation sign)
    if font.startswith("MT-Symbol") and name == "summation":
        return "•"
    if font.startswith("MT-Symbol") and name == "bullet":
        return "∑"
    if font.startswith("MT-Symbol") and len(name) == 1 and name.isalpha():
        return SYMBOL_LETTERS[name]
    if name in NAMED:
        return NAMED[name]
    if name in PIECES:
        return ""
    if len(name) == 1:
        return name
    return None


def parse_diff(obj):
    body = obj.split("/Differences", 1)[1].split("]", 1)[0]
    code, mp = 0, {}
    for t in re.findall(r"\d+|/[\w.]+", body):
        if t[0] == "/":
            mp[code] = t[1:]; code += 1
        else:
            code = int(t)
    return mp


def cmap(mp):
    lines = []
    for code, uni in sorted(mp.items()):
        hexu = "".join(f"{b:02X}" for b in uni.encode("utf-16-be")) if uni else "FFFF"
        lines.append(f"<{code:02X}> <{hexu}>")
    chunks = [lines[i:i + 100] for i in range(0, len(lines), 100)]
    body = "".join(f"{len(c)} beginbfchar\n" + "\n".join(c) + "\nendbfchar\n" for c in chunks)
    return ("/CIDInit /ProcSet findresource begin 12 dict begin begincmap\n"
            "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def\n"
            "/CMapName /Fix def /CMapType 2 def\n"
            "1 begincodespacerange <00> <FF> endcodespacerange\n" + body +
            "endcmap CMapName currentdict /CMap defineresource pop end end")


def fix(doc):
    unknown = set()
    done = set()
    for page in doc:
        for fx in page.get_fonts():
            xref, name = fx[0], fx[3].split("+")[-1]
            if xref in done or not any(k in name for k in ("Pi", "MT-", "Euclid")):
                continue
            done.add(xref)
            o = doc.xref_object(xref)
            m = re.search(r"/Encoding (\d+) 0 R", o)
            if not m:
                continue
            enc = doc.xref_object(int(m.group(1)))
            if "/Differences" not in enc:
                continue
            mp = {}
            for code, g in parse_diff(enc).items():
                u = glyph_to_uni(name, g)
                if u is None:
                    unknown.add((name, g)); u = ""
                mp[code] = u
            tu = re.search(r"/ToUnicode (\d+) 0 R", o)
            if tu:  # keep old entries for codes outside /Differences
                old = doc.xref_stream(int(tu.group(1))).decode("latin-1")
                for blk in re.findall(r"beginbfchar(.*?)endbfchar", old, re.S):
                    for a, u in re.findall(r"<([0-9a-fA-F]{2})>\s*<([0-9a-fA-F]+)>", blk):
                        mp.setdefault(int(a, 16), bytes.fromhex(u).decode("utf-16-be"))
                for blk in re.findall(r"beginbfrange(.*?)endbfrange", old, re.S):
                    for a, b, u in re.findall(r"<(\w+)>\s*<(\w+)>\s*<(\w+)>", blk):
                        for k in range(int(a, 16), int(b, 16) + 1):
                            mp.setdefault(k, chr(int(u, 16) + k - int(a, 16)))
            if tu:
                doc.update_stream(int(tu.group(1)), cmap(mp).encode())
            else:
                nx = doc.get_new_xref()
                doc.update_object(nx, "<<>>")
                doc.update_stream(nx, cmap(mp).encode())
                doc.xref_set_key(xref, "ToUnicode", f"{nx} 0 R")
    return unknown


if __name__ == "__main__":
    d = pymupdf.open(sys.argv[1])
    unk = fix(d)
    d.save(sys.argv[2], garbage=1)
    if unk:
        print("UNKNOWN", sorted(unk))
