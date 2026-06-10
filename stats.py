#!/usr/bin/env python3
"""
Quick stats viewer for split.py test runs.
Reads the latest test_runN.log from RunPod and prints both tables.

Usage:
    python stats.py              # reads latest run log automatically
    python stats.py --run 5      # reads test_run5.log specifically
    python stats.py --local      # read from local file instead of SSH
"""
from __future__ import annotations

import argparse
import re
import statistics
import subprocess
import sys

SSH_CMD = ["ssh", "-i", "~/.ssh/id_ed25519", "-p", "20760",
           "-o", "ConnectTimeout=10", "root@213.173.105.157"]

HISTORICAL = {
    # file_label: {run_number: f1}
    "РС-31-2017/1":  {2: 40, 3: 44, 4: 60, 5: 67, 6: 77, 7: 77, 8: 86, 9: 86, 10: 86, 12: 86},
    "РС-31-2017/2":  {2: 64, 3: 55, 4: 62, 5: 75, 6: 67, 7: 73, 8: 80, 9: 84, 10: 78, 11: 84, 12: 84},
    "РС-31-2017/3":  {2: 45, 3: 64, 4: 64, 5: 79, 6: 86, 7: 90, 8: 93, 9: 93, 10: 93, 12: 93},
    "РС-31-2017/4":  {2: 33, 3: 57, 4: 57, 5: 67, 6: 75, 7: 88, 8: 82, 9: 82, 10: 82, 12: 82},
    "РС-31-2017/5":  {2: 55, 3: 83, 4: 92, 5: 92, 6:100, 7:100, 8:100, 9:100, 10:100, 12:100},
    "РС-31-2017/6":  {2: 67, 3: 80, 4: 73, 5: 73, 6: 83, 7: 83, 8: 83, 9: 83, 10: 83, 12: 83},
    "РС-31-2017/7a": {2: 73, 3: 73, 4: 73, 5: 73, 6: 73, 7: 83, 8: 92, 9: 92, 10: 92, 12: 92},
    "РС-31-2017/7b": {2: 75, 3: 75, 4:100, 5:100, 6:100, 7:100, 8:100, 9:100, 10:100, 12:100},
    "РС-31-2017/8":  {2: 67, 3: 67, 4: 67, 5: 67, 6: 67, 7: 67, 8: 86, 9: 86, 10: 86, 12: 86},
    "РС-32-2017/1":  {2: 49,             5: 73, 6: 77, 7: 88, 8: 92, 9: 92, 10: 93, 12: 92},
    "РС-33-2017/1":  {                   5: 73, 6: 79, 7: 86, 8: 91, 9: 93, 10: 93, 12: 93},
    "РС-33-2017/2":  {                   5: 73, 6: 90, 7: 90, 8: 91, 9: 91, 10: 91, 12: 91},
    "РС-33-2017/3":  {                   5: 84, 6: 75, 7: 82, 8: 82, 9: 75, 10: 75, 12: 75},
    "РС-33-2017/4":  {                   5: 75, 6: 86, 7: 86, 8:100, 9:100, 10:100, 12:100},
    "РС-33-2017/5":  {                   5: 67, 6: 77, 7: 80, 8: 80, 9: 80, 10: 80, 12: 80},
    "РС-33-2017/6":  {                   5: 40, 6: 80, 7: 80, 8: 80, 9: 80, 10: 80, 12: 80},
    "РС-33-2017/7":  {                   5: 75, 6: 89, 7: 89, 8:100, 9:100, 10:100, 12:100},
    "РС-34-2017/1":  {                          6: 81, 7: 79, 8: 85, 9: 85, 12: 85},
    "РС-35-2017/1":  {                          6: 79, 7: 80, 8: 84, 9: 83, 12: 83},
    "РС-36-2017/1":  {                          6: 80, 7: 84, 8: 87, 9: 87, 12: 87},
    "РС-37-2017/1":  {                          6: 73, 7: 75, 8: 84, 9: 81, 12: 81},
    # tests2 — new archive files
    "РС-38-2017/1":  {13:  85}, "РС-38-2017/2":  {13:  92}, "РС-38-2017/3":  {13: 100},
    "РС-38-2017/4":  {13:  80}, "РС-38-2017/5":  {13:  89}, "РС-38-2017/6":  {13: 100},
    "РС-38-2017/7":  {13: 100}, "РС-38-2017/8":  {13:  83}, "РС-38-2017/9":  {13:  74},
    "РС-38-2017/10": {13: 100}, "РС-38-2017/11": {13: 100},
    "РС-39-1-2017/1":  {13:  89}, "РС-39-1-2017/2":  {13:  93}, "РС-39-1-2017/3":  {13:  89},
    "РС-39-1-2017/4":  {13:  86}, "РС-39-1-2017/5":  {13: 100}, "РС-39-1-2017/6":  {13:  91},
    "РС-39-1-2017/7":  {13:  91}, "РС-39-1-2017/8":  {13:  44}, "РС-39-1-2017/9":  {13: 100},
    "РС-39-1-2017/10": {13:  92},
    "РС-39-2-2017/1": {13:  88}, "РС-39-2-2017/2": {13: 100},
    "РС-39-2-2017/3": {13:  86}, "РС-39-2-2017/4": {13:  71},
    "РС-40-2017/1":  {13:  84}, "РС-40-2017/2":  {13:  84}, "РС-40-2017/3":  {13:  77},
    "РС-40-2017/4":  {13: 100}, "РС-40-2017/5":  {13:  94}, "РС-40-2017/6":  {13:  90},
    "РС-40-2017/7":  {13:  88}, "РС-40-2017/8":  {13:  86}, "РС-40-2017/9":  {13:  83},
    "РС-40-2017/10": {13:  83}, "РС-40-2017/11": {13:  89}, "РС-40-2017/12": {13: 100},
    "РС-40-2017/13": {13:  92},
    "РС-41-2017/1":  {13:  92}, "РС-41-2017/2":  {13:  95},
    "РС-41-2017/3":  {13:  93}, "РС-41-2017/4":  {13:  91},
    "РС-42-2017/1":  {13:  89},
    "РС-43-1-2017/1": {13: 100}, "РС-43-1-2017/2": {13:  86}, "РС-43-1-2017/3": {13:  86},
    "РС-43-1-2017/4": {},        "РС-43-1-2017/5": {13:  86}, "РС-43-1-2017/6": {13: 100},
    "РС-43-1-2017/7": {13:  88},
}

FILE_ORDER = list(HISTORICAL.keys())

# Maps Image_*.pdf stem fragments to canonical file labels
STEM_TO_LABEL = {
    "162710373":  "РС-31-2017/1",
    "163444215":  "РС-31-2017/2",
    "164052657":  "РС-31-2017/3",
    "164505881":  "РС-31-2017/4",
    "164959043":  "РС-31-2017/5",
    "165204533":  "РС-31-2017/6",
    "082511233":  "РС-31-2017/7a",
    "082544031":  "РС-31-2017/7b",
    "082646183":  "РС-31-2017/8",
    "142044854":  "РС-32-2017/1",
    "083553577":  "РС-33-2017/1",
    "084031203":  "РС-33-2017/2",
    "084303475":  "РС-33-2017/3",
    "084552444":  "РС-33-2017/4",
    "084837699":  "РС-33-2017/5",
    "085002901":  "РС-33-2017/6",
    "085108460":  "РС-33-2017/7",
    "142438096":  "РС-34-2017/1",
    "143041245":  "РС-35-2017/1",
    "145428614":  "РС-36-2017/1",
    "144119764":  "РС-37-2017/1",
    # tests2
    "00112022025150141364": "РС-38-2017/1",
    "00112022025150602624": "РС-38-2017/2",
    "00112022025150752825": "РС-38-2017/3",
    "00112022025150812039": "РС-38-2017/3",
    "00112022025150911173": "РС-38-2017/4",
    "00112022025151043346": "РС-38-2017/5",
    "00112022025151409676": "РС-38-2017/6",
    "00112022025151707631": "РС-38-2017/7",
    "00112022025151905807": "РС-38-2017/8",
    "00112022025152055492": "РС-38-2017/9",
    "00112022025152419268": "РС-38-2017/10",
    "00112022025152506863": "РС-38-2017/11",
    "00112032025085648873": "РС-39-1-2017/1",
    "00112032025085744589": "РС-39-1-2017/1",
    "00112032025085926726": "РС-39-1-2017/2",
    "00112032025090305070": "РС-39-1-2017/3",
    "00112032025090602611": "РС-39-1-2017/4",
    "00112032025090815252": "РС-39-1-2017/5",
    "00112032025091015415": "РС-39-1-2017/6",
    "00112032025091427168": "РС-39-1-2017/7",
    "00112032025091543997": "РС-39-1-2017/8",
    "00112032025091711797": "РС-39-1-2017/9",
    "00112032025091922264": "РС-39-1-2017/10",
    "00112032025092145226": "РС-39-2-2017/1",
    "00112032025092428958": "РС-39-2-2017/2",
    "00112032025092620813": "РС-39-2-2017/3",
    "00112032025092829405": "РС-39-2-2017/4",
    "00112032025093915512": "РС-40-2017/1",
    "00112032025094527845": "РС-40-2017/2",
    "00112032025094846815": "РС-40-2017/3",
    "00112032025095132937": "РС-40-2017/4",
    "00112032025095430597": "РС-40-2017/5",
    "00112032025095815725": "РС-40-2017/6",
    "00112032025100240074": "РС-40-2017/7",
    "00112032025100557573": "РС-40-2017/8",
    "00112032025100907662": "РС-40-2017/9",
    "00112032025100818580": "РС-40-2017/10",
    "00112032025100958948": "РС-40-2017/11",
    "00112032025101052041": "РС-40-2017/12",
    "00112032025101244833": "РС-40-2017/13",
    "00112032025101623915": "РС-41-2017/1",
    "00112032025101849563": "РС-41-2017/2",
    "00112032025102146338": "РС-41-2017/3",
    "00112032025103052017": "РС-41-2017/4",
    "00112032025103907268": "РС-42-2017/1",
    "00112032025104025668": "РС-43-1-2017/1",
    "00112032025104150824": "РС-43-1-2017/2",
    "00112032025104517665": "РС-43-1-2017/3",
    "00112032025104555202": "РС-43-1-2017/4",
    "00112032025104731513": "РС-43-1-2017/5",
    "00112032025104926545": "РС-43-1-2017/6",
    "00112032025105212117": "РС-43-1-2017/7",
}

# Overall rotation P / R / F1 per run (from OVERALL RESULTS block in each log)
HISTORICAL_ROTATION = {
    6: {"p": 71.0, "r": 79.4, "f1": 75.0},
    7: {"p": 71.0, "r": 79.4, "f1": 75.0},  # same pod session, rotation unchanged
    8: {"p": 71.0, "r": 79.4, "f1": 75.0},  # rotation detection not changed in R8
    # R9/R12 overall rotation parse returned P=100/R=0 (stats parsing artefact); omitted
    13: {"p": 37.0, "r": 29.8, "f1": 33.0},  # tests2 baseline; rotation needs work
}


def fetch_log(run: int | None, local: bool) -> str:
    if local:
        import glob
        logs = sorted(glob.glob("test_run*.log"), reverse=True)
        if not logs:
            sys.exit("No test_run*.log found locally.")
        path = logs[0] if run is None else f"test_run{run}.log"
        with open(path, errors="replace") as f:
            return f.read()

    if run is None:
        # find the latest log on the server
        result = subprocess.run(
            SSH_CMD + ["ls /workspace/test_run*.log 2>/dev/null | sort -V | tail -1"],
            capture_output=True, text=True
        )
        path = result.stdout.strip()
        if not path:
            sys.exit("No test_run*.log found on server.")
    else:
        path = f"/workspace/test_run{run}.log"

    result = subprocess.run(
        SSH_CMD + [f"cat {path} | tr -d '\\0'"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        sys.exit(f"SSH failed: {result.stderr}")
    return result.stdout


def parse_time(line: str):
    """Extract HH:MM:SS from a log line, return as total seconds or None."""
    m = re.match(r"(\d{2}):(\d{2}):(\d{2})", line)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + int(m.group(3))
    return None


def parse_log(log: str) -> tuple[int, dict[str, int], dict[str, dict], dict[str, int], dict]:
    """Returns (run_number_guess, {label: boundary_f1}, {label: timing_info},
                {label: rotation_f1}, overall_rotation_dict)."""
    run_num = 6
    results: dict[str, int] = {}
    rot_results: dict[str, int] = {}
    timing: dict[str, dict] = {}
    overall_rot: dict = {}
    current_label = None
    file_start_ts = None
    current_pages = None
    boundary_done = False

    for line in log.splitlines():
        # detect current file
        m = re.search(r"File\s+:\s+\S+/(Image_\S+\.pdf)", line)
        if m:
            stem = m.group(1)
            for key, label in STEM_TO_LABEL.items():
                if key in stem:
                    current_label = label
                    file_start_ts = parse_time(line)
                    current_pages = None
                    boundary_done = False
                    break
            continue

        # detect page count
        m = re.search(r"end-of-document detection \((\d+) pages\)", line)
        if m and current_label:
            current_pages = int(m.group(1))
            continue

        # detect boundary result
        m = re.search(r"Boundaries — TP=\d+ FP=\d+ FN=\d+.*F1=(\d+)%", line)
        if m and current_label and not boundary_done:
            results[current_label] = int(m.group(1))
            end_ts = parse_time(line)
            if file_start_ts is not None and end_ts is not None:
                elapsed = (end_ts - file_start_ts) % 86400
                timing[current_label] = {"seconds": elapsed, "pages": current_pages}
            boundary_done = True
            continue

        # detect rotation result per file (only store when there's actual rotation data)
        m = re.search(r"Rotations\s+— TP=(\d+) FP=(\d+) FN=(\d+).*F1=(\d+)%", line)
        if m and current_label:
            tp, fp, fn, f1 = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
            if tp + fp + fn > 0:
                rot_results[current_label] = f1
            current_label = None
            continue

        # detect overall rotation block
        m = re.search(r"Precision\s*:\s*([\d.]+)%", line)
        if m and "ROTATION" in log[max(0, log.find(line)-200):log.find(line)]:
            overall_rot["precision"] = float(m.group(1))
        m = re.search(r"Recall\s*:\s*([\d.]+)%", line)
        if m and "ROTATION" in log[max(0, log.find(line)-200):log.find(line)]:
            overall_rot["recall"] = float(m.group(1))
        m = re.search(r"F1 score\s*:\s*([\d.]+)%", line)
        if m and "ROTATION" in log[max(0, log.find(line)-200):log.find(line)]:
            overall_rot["f1"] = float(m.group(1))

    return run_num, results, timing, rot_results, overall_rot


def print_timing(timing: dict[str, dict]) -> None:
    if not timing:
        return

    total_secs = sum(t["seconds"] for t in timing.values())
    total_pages = sum(t["pages"] for t in timing.values() if t["pages"])
    n = len(timing)
    avg_pdf_secs = total_secs / n
    avg_pages = total_pages / n if total_pages else 0
    avg_page_secs = total_secs / total_pages if total_pages else 0

    def hms(s):
        h, rem = divmod(int(s), 3600)
        m, sec = divmod(rem, 60)
        if h:
            return f"{h}h {m}m {sec}s"
        if m:
            return f"{m}m {sec}s"
        return f"{sec}s"

    rows = [
        ["Total test time",      hms(total_secs)],
        ["PDFs completed",       str(n)],
        ["Avg time per PDF",     hms(avg_pdf_secs)],
        ["Avg PDF length",       f"{avg_pages:.1f} pages"],
        ["Avg time per page",    f"{avg_page_secs:.1f}s"],
    ]
    col0 = max(len(r[0]) for r in rows)
    col1 = max(len(r[1]) for r in rows)
    print("\n| " + "Metric".ljust(col0) + " | " + "Value".ljust(col1) + " |")
    print("| " + "-" * col0 + " | " + "-" * col1 + " |")
    for label, val in rows:
        print("| " + label.ljust(col0) + " | " + val.ljust(col1) + " |")
    print()


def print_tables(current_run: int, current: dict[str, int]) -> None:
    # Include all runs that appear in HISTORICAL plus the current run.
    historical_runs = set()
    for file_runs in HISTORICAL.values():
        historical_runs.update(file_runs.keys())
    all_runs = sorted(historical_runs | {current_run})

    run_data: dict[int, dict[str, int | None]] = {}
    for r in all_runs:
        run_data[r] = {}
        for f in FILE_ORDER:
            if r == current_run:
                run_data[r][f] = current.get(f)
            else:
                run_data[r][f] = HISTORICAL.get(f, {}).get(r)

    _LABELS = {
        2: "Run 2 (baseline)", 3: "Run 3", 4: "Run 4",
        5: "Run 5 (no guard)", 6: "Run 6 (next-page gate)",
        7: "Run 7 (one-page fix)", 8: "Run 8 (start-detect)",
        9: "Run 9", 10: "Run 10 (corroborator)", 11: "Run 11 (decoupled)", 12: "Run 12",
        13: "Run 13 (tests2 baseline)", 14: "Run 14 (f-string fix)",
    }
    run_labels = {**_LABELS, current_run: f"Run {current_run} (current)"}

    def fmt(v):
        return f"{v}%" if v is not None else "—"

    # build per-file rows
    run_cols = [f"R{r}" for r in all_runs]
    rows = []
    for f in FILE_ORDER:
        rows.append([f] + [fmt(run_data[r][f]) for r in all_runs])

    headers = ["File"] + run_cols
    col_w = [max(len(h), max(len(row[i]) for row in rows)) for i, h in enumerate(headers)]

    def md_row(cells):
        return "| " + " | ".join(c.ljust(col_w[i]) for i, c in enumerate(cells)) + " |"

    def md_sep(aligns):
        parts = []
        for i, a in enumerate(aligns):
            w = col_w[i]
            if a == "c":
                parts.append(":" + "-" * (w - 2) + ":")
            elif a == "r":
                parts.append("-" * (w - 1) + ":")
            else:
                parts.append("-" * w)
        return "| " + " | ".join(parts) + " |"

    # --- per-file table ---
    print()
    print(md_row(headers))
    print(md_sep(["l"] + ["c"] * len(all_runs)))
    for row in rows:
        print(md_row(row))

    # --- summary table ---
    sum_headers = ["Run", "N", "Avg F1", "Std Dev", "Min", "Max"]
    sum_rows = []
    for r in all_runs:
        scores = [v for v in run_data[r].values() if v is not None]
        if not scores:
            continue
        label = run_labels.get(r, f"Run {r}")
        avg = statistics.mean(scores)
        std = statistics.stdev(scores) if len(scores) > 1 else 0.0
        sum_rows.append([label, str(len(scores)), f"{avg:.1f}%", f"±{std:.1f}%",
                         f"{min(scores)}%", f"{max(scores)}%"])

    sum_w = [max(len(h), max(len(row[i]) for row in sum_rows))
             for i, h in enumerate(sum_headers)]

    def sum_row(cells):
        return "| " + " | ".join(c.ljust(sum_w[i]) for i, c in enumerate(cells)) + " |"

    print()
    print(sum_row(sum_headers))
    print("| " + " | ".join(
        (":" + "-" * (sum_w[i] - 2) + ":" if i > 0 else "-" * sum_w[i])
        for i in range(len(sum_headers))
    ) + " |")
    for row in sum_rows:
        print(sum_row(row))
    print()


def print_rotation_table(current_run: int, rot_results: dict[str, int], overall_rot: dict) -> None:
    """Print per-file rotation F1 for current run + overall rotation summary across all runs."""
    if not rot_results and not overall_rot:
        return

    _LABELS = {
        2: "Run 2 (baseline)", 3: "Run 3", 4: "Run 4",
        5: "Run 5 (no guard)", 6: "Run 6 (next-page gate)",
        7: "Run 7 (one-page fix)", 8: "Run 8 (start-detect)",
        9: "Run 9", 10: "Run 10 (corroborator)", 11: "Run 11 (decoupled)", 12: "Run 12",
        13: "Run 13 (tests2 baseline)", 14: "Run 14 (f-string fix)",
    }
    run_labels = {**_LABELS, current_run: f"Run {current_run} (current)"}

    # Per-file rotation for current run
    if rot_results:
        print("\n**PAGE ROTATION — per file (current run)**\n")
        rows = [[f, f"{rot_results[f]}%"] for f in FILE_ORDER if f in rot_results]
        if rows:
            col0 = max(len(r[0]) for r in rows)
            print(f"| {'File'.ljust(col0)} | Rotation F1 |")
            print(f"| {'-'*col0} | :---------: |")
            for f, v in rows:
                print(f"| {f.ljust(col0)} | {v:^11} |")

    # Overall rotation summary across all runs
    all_runs = sorted(set(HISTORICAL_ROTATION.keys()) | {current_run})
    sum_rows = []
    for r in all_runs:
        label = run_labels.get(r, f"Run {r}")
        if r == current_run and overall_rot:
            p = overall_rot.get("precision", 0)
            rc = overall_rot.get("recall", 0)
            f1 = overall_rot.get("f1", 0)
        elif r in HISTORICAL_ROTATION:
            p = HISTORICAL_ROTATION[r]["p"]
            rc = HISTORICAL_ROTATION[r]["r"]
            f1 = HISTORICAL_ROTATION[r]["f1"]
        else:
            continue
        sum_rows.append([label, f"{p:.1f}%", f"{rc:.1f}%", f"{f1:.1f}%"])

    if sum_rows:
        headers = ["Run", "Precision", "Recall", "F1"]
        col_w = [max(len(h), max(len(r[i]) for r in sum_rows)) for i, h in enumerate(headers)]
        print()
        print("| " + " | ".join(h.ljust(col_w[i]) for i, h in enumerate(headers)) + " |")
        print("| " + " | ".join("-" * col_w[i] for i in range(len(headers))) + " |")
        for row in sum_rows:
            print("| " + " | ".join(row[i].ljust(col_w[i]) for i in range(len(headers))) + " |")
        print()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", type=int, default=None, help="Log number to read (default: latest)")
    parser.add_argument("--local", action="store_true", help="Read from local file instead of SSH")
    parser.add_argument("--file", type=str, default=None, help="Write output to this file instead of stdout")
    args = parser.parse_args()

    import sys, io
    print("Fetching log…", end=" ", flush=True)
    log = fetch_log(args.run, args.local)
    print("done.")

    run_num = args.run or 6
    _, results, timing, rot_results, overall_rot = parse_log(log)

    buf = io.StringIO()
    _real_stdout = sys.stdout
    sys.stdout = buf

    print(f"Files completed in current run: {len(results)}")
    print_timing(timing)
    print_tables(run_num, results)
    print_rotation_table(run_num, rot_results, overall_rot)

    sys.stdout = _real_stdout
    output = buf.getvalue()

    if args.file:
        with open(args.file, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Output written to {args.file}")

    print(output, end="")


if __name__ == "__main__":
    main()
