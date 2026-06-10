#!/usr/bin/env python3
"""Score rotation detection against ground truth, degrees-exact.
Usage: python eval_rotation.py <folder> [--dpi 150] [--arm legacy|osd]
rotation_truth.json format: {"file.pdf": {"3": 90, "7": 270}, ...}
  (1-indexed page -> true CCW degrees; pages absent from the map are upright/0)
"""
import argparse, json, sys
from pathlib import Path
from pypdf import PdfReader
from split import _load_page, load_model, setup_logging, MODEL_PATH, DEFAULT_DPI, _infer, _parse_json
import rotation as rot

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    ap.add_argument("--arm", choices=["legacy", "osd"], default="osd")
    ap.add_argument("--model", default=MODEL_PATH)
    args = ap.parse_args()

    folder = Path(args.folder).resolve()
    truth = json.loads((folder / "rotation_truth.json").read_text(encoding="utf-8"))

    logger = setup_logging(folder / "rot_eval_logs")
    model = processor = config = None
    if args.arm == "legacy":
        model, processor, config = load_model(args.model, logger)

    TP = FP = FN = wrong_deg = 0
    for name, page_map in truth.items():
        pdf = folder / name
        total = len(PdfReader(str(pdf)).pages)
        true_rot = {int(k): int(v) for k, v in page_map.items()}
        for p in range(1, total + 1):
            img = _load_page(pdf, p, args.dpi)
            if args.arm == "osd":
                pred = rot.query_rotation_osd_first(img, p, logger)
            else:
                pred = rot.query_rotation(img, p, model, processor, config, logger,
                                          infer_fn=_infer, parse_fn=_parse_json,
                                          corroborate_fn=None)
            t = true_rot.get(p, 0)
            if pred != 0 and t != 0 and pred == t:
                TP += 1
            elif pred != 0 and t != 0 and pred != t:
                wrong_deg += 1; FP += 1; FN += 1
                print(f"  WRONG-DEG {name} p{p}: pred={pred} true={t}")
            elif pred != 0 and t == 0:
                FP += 1
                print(f"  FP {name} p{p}: pred={pred} size={img.size}")
            elif pred == 0 and t != 0:
                FN += 1
                print(f"  FN {name} p{p}: true={t} size={img.size}")
            del img

    P = TP / (TP + FP) if TP + FP else 0.0
    R = TP / (TP + FN) if TP + FN else 0.0
    print(f"\n=== Rotation (degrees-exact, arm={args.arm}) ===")
    print(f"TP={TP} FP={FP} FN={FN} (of which wrong-degrees={wrong_deg})")
    print(f"Precision={P:.2%}  Recall={R:.2%}")

if __name__ == "__main__":
    main()
