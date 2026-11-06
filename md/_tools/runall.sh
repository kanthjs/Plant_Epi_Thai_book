#!/bin/bash
cd /home/claude/work
for f in fixed/chapter-*.pdf; do
  n=$(basename $f | sed -E 's/chapter-([0-9]+)-.*/\1/')
  [ "$n" = "1" ] && continue
  d=out/ch$(printf %02d $n)
  rm -rf $d
  python3 convert.py $f $n $d 2>&1 | grep -v "^Warning\|RapidOCR\|Tesseract\|^===\|^$"
  python3 postprocess.py $d $n
done
echo ALLDONE
