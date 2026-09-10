#!/usr/bin/env python3
"""Validate the OSD->CCW mapping: synthetically rotate known-upright text pages
and check corroborate_tesseract returns the CCW degrees that undo the rotation.
Usage: python test_osd_mapping.py <pdf> <page> [<page> ...]   # pick upright TEXT pages
"""
import sys
from pathlib import Path
from split import _load_page
from rotation import corroborate_tesseract

pdf = Path(sys.argv[1]); pages = [int(p) for p in sys.argv[2:]]
fails = 0
for pg in pages:
    base = _load_page(pdf, pg, 150)
    for applied_ccw, needed_ccw in [(0, 0), (90, 270), (180, 180), (270, 90)]:
        img = base.rotate(applied_ccw, expand=True) if applied_ccw else base
        res = corroborate_tesseract(img)
        if res is None:
            print(f"p{pg} applied={applied_ccw}: ABSTAIN (low text? pick a denser page)")
            continue
        is_rot, deg, conf = res
        ok = deg == needed_ccw
        fails += (not ok)
        print(f"p{pg} applied={applied_ccw} -> OSD says fix={deg} "
              f"(need {needed_ccw}) conf={conf:.2f} {'OK' if ok else 'FAIL'}")
print(f"\n{'MAPPING VALIDATED' if fails == 0 else f'{fails} FAILURES - fix _OSD_TO_CCW before Stage 1'}")
