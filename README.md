# ตำราภาษาไทยด้วย Quarto book

## สิ่งที่ต้องติดตั้ง
1. Quarto 1.9 ขึ้นไป
2. TeX: `quarto install tinytex` (หรือ TeX Live เต็มชุด)
3. ฟอนต์ Sarabun (Google Fonts) ติดตั้งลงเครื่อง
4. R + แพ็กเกจ `tidyverse`, `knitr`

## สั่ง render
```bash
quarto preview                 # ดูฉบับเว็บแบบสด ระหว่างเขียน
quarto render --to pdf         # ฉบับพิมพ์
quarto render                  # ทั้งเว็บและ PDF -> โฟลเดอร์ _book/
```

## โครงไฟล์
- `_quarto.yml`  ตั้งค่าเล่ม รายชื่อบท ฟอนต์ ขนาดกระดาษ (B5)
- `preamble.tex` ตัดคำไทย (XeTeX + ICU) และป้ายภาษาไทยในเล่ม PDF
- `custom.scss`  ฟอนต์และระยะบรรทัดของฉบับเว็บ
- `references.bib` บรรณานุกรม (ส่งออกจาก Zotero + Better BibTeX ได้)

## เพิ่มบทใหม่
สร้างไฟล์ `02-xxx.qmd` แล้วเพิ่มชื่อไฟล์ใน `chapters:` ของ `_quarto.yml`

## จุดที่ควรตรวจในฉบับพิมพ์
คำทับศัพท์หรือชื่อเฉพาะที่ไม่มีในพจนานุกรม ICU อาจตัดบรรทัดผิดที่
แก้เฉพาะจุดด้วยการครอบคำนั้นใน `\mbox{...}` (เฉพาะ PDF)
หรือใส่ zero-width space (U+200B) ตรงจุดที่ยอมให้ตัด

## เลย์เอาต์ขอบกว้าง (แบบ socviz.co)
- เชิงอรรถ `^[...]` การอ้างอิง และคำบรรยายรูป ไปอยู่ขอบขวาอัตโนมัติ (ตั้งใน `_quarto.yml`)
- วางข้อความหรือรูปไว้ที่ขอบ: `::: {.column-margin}` หรือ `#| column: margin` ใน chunk
- รูปกว้างเต็มหน้า: `#| column: page` หรือ `#| column: body-outset`

## เผยแพร่ฉบับเว็บ (GitHub Pages)
```bash
quarto publish gh-pages      # ครั้งแรกจะสร้าง branch gh-pages ให้
```
แล้วไปที่ GitHub > Settings > Pages เลือก branch `gh-pages`
