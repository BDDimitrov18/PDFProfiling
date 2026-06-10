#!/usr/bin/env python3
"""
rotation.py — Page rotation detection and smoothing for split.py.

All public functions accept infer_fn and parse_fn as callables so they can be
tested independently without loading the vision model.

    infer_fn(prompt, images, model, processor, config, logger, max_tokens) -> str | None
    parse_fn(text, logger) -> dict
    corroborate_fn(img) -> tuple[bool, int | None, float] | None
        Returns (is_rotated, suggested_deg_ccw_or_None, conf_0_1), or None to abstain.
"""
from __future__ import annotations

import logging
from typing import Callable


def query_rotation(
    img,
    page_num: int,
    model,
    processor,
    config,
    logger: logging.Logger,
    infer_fn: Callable,
    parse_fn: Callable,
    corroborate_fn: Callable | None = None,
) -> int:
    """
    Ask the model whether page_num needs rotation to read correctly.
    Returns degrees to rotate counter-clockwise (0, 90, 180, or 270).

    When corroborate_fn is None: current behaviour (confidence-threshold gate).
    When corroborate_fn is provided: corroborator replaces the confidence gate —
    see decision table in the body below.
    """
    prompt = (
        f"Look at this scanned document page (page {page_num}).\n"
        "Is the text and content correctly oriented for normal reading (horizontal lines of text)?\n\n"
        "Return the counter-clockwise rotation needed to make it read correctly:\n"
        "  0   — already correct\n"
        "  90  — rotate 90° counter-clockwise (text currently runs upward along the right edge)\n"
        "  180 — rotate 180° (page is upside down)\n"
        "  270 — rotate 270° counter-clockwise (text currently runs downward along the left edge)\n\n"
        "IMPORTANT: Decorative borders, diagonal stamps, diamond logos, or angled watermarks "
        "do NOT mean the page is rotated. Only report non-zero rotation if the main body text "
        "lines are clearly not horizontal.\n\n"
        "Respond ONLY with JSON:\n"
        '{"rotation": <0 or 90 or 180 or 270>, "confidence": <0-100>, '
        '"reason": "<one sentence: describe the text orientation you observe>"}'
    )
    raw = infer_fn(prompt, [img], model, processor, config, logger, max_tokens=80)
    logger.debug(f"  Rotation check p{page_num}: {repr((raw or '')[:200])}")
    data = parse_fn(raw or "", logger)
    try:
        rotation = int(data.get("rotation", 0))
        confidence = float(data.get("confidence", 0))
    except (TypeError, ValueError):
        return 0
    reason = str(data.get("reason", "")).strip()
    if rotation not in (0, 90, 180, 270):
        return 0

    if corroborate_fn is None:
        # Legacy path: confidence-threshold gate (back-compat / A/B arm).
        _CONFIDENCE_THRESHOLD = 95
        if rotation != 0 and confidence < _CONFIDENCE_THRESHOLD:
            logger.debug(
                f"  Rotation {rotation}° suggested for p{page_num} but "
                f"confidence {confidence:.0f}% < {_CONFIDENCE_THRESHOLD}% — skipping"
            )
            return 0
        if rotation != 0 and reason:
            logger.info(f"  Rotation reason: {reason}")
        return rotation

    # Corroborator path — get corroboration result first for diagnostics.
    try:
        corr = corroborate_fn(img)
    except Exception as exc:
        logger.warning(f"  [ROT-CORR] p{page_num} corroborator raised {exc!r} — abstaining")
        corr = None

    logger.info(
        f"  [ROT-DIAG] p{page_num} model={rotation}°/{confidence:.0f}% "
        f"size={img.size} corr={corr}"
    )

    # Decision table (model_rot = rotation parsed above):
    if corr is None:
        # Corr abstains: conservative default — trust model only if it says 0.
        if rotation == 0:
            return 0
        logger.info(f"  [ROT-DIAG] p{page_num} corr abstained, model={rotation}° — returning 0 (conservative)")
        return 0

    corr_is_rotated, corr_deg, corr_conf = corr

    if rotation != 0 and corr_is_rotated:
        # Both agree page is sideways — trust model for direction.
        if reason:
            logger.info(f"  Rotation reason: {reason}")
        return rotation

    if rotation != 0 and not corr_is_rotated:
        # Model says rotated, corroborator disagrees — precision fix.
        logger.info(
            f"  [ROT-DIAG] p{page_num} model={rotation}° overridden by corr (not rotated, conf={corr_conf:.2f}) → 0"
        )
        return 0

    if rotation == 0 and corr_is_rotated:
        # Model says upright, corroborator sees sideways — recall fix.
        result = corr_deg if corr_deg is not None else 90
        logger.info(
            f"  [ROT-DIAG] p{page_num} model=0° overridden by corr (rotated, deg={corr_deg}, conf={corr_conf:.2f}) → {result}°"
        )
        return result

    # rotation == 0 and not corr_is_rotated — both agree upright.
    return 0


def smooth_rotation_log(
    rotation_log: dict[int, int],
    logger: logging.Logger,
    corroboration: dict[int, int] | None = None,
) -> dict[int, int]:
    """
    Conservative integer smoothing pass over a {page: degrees} map. No model calls.

    Rules (adjacency by actual page number p-1/p+1, not list position):
      1. Fill a single upright (0°) page between two neighbours with the same non-zero
         rotation (both p-1 and p+1 must be present and equal).
      2. Zero out a single non-zero page between two upright neighbours.
      3. If corroboration is provided: a rotated run of length ≥2 may absorb a single
         adjacent upright page IFF corroboration marks that page as rotated.
         At most one page extension per side of each run.

    Returns a new dict with smoothing applied (does not mutate the input).
    """
    smoothed = dict(rotation_log)
    page_set = set(smoothed.keys())

    # Rules 1 and 2: iterate over all pages present in the log.
    for p in sorted(page_set):
        prev_p, next_p = p - 1, p + 1
        if prev_p not in page_set or next_p not in page_set:
            continue
        prev_r = smoothed[prev_p]
        curr_r = smoothed[p]
        next_r = smoothed[next_p]

        if curr_r == 0 and prev_r != 0 and prev_r == next_r:
            smoothed[p] = prev_r
            logger.info(f"  [ROT-SMOOTH] p{p} filled {prev_r}° (between two {prev_r}° neighbours)")
        elif curr_r != 0 and prev_r == 0 and next_r == 0:
            smoothed[p] = 0
            logger.info(f"  [ROT-SMOOTH] p{p} zeroed (lone {curr_r}° between two upright neighbours)")

    # Rule 3: corroborated run-edge extension.
    if corroboration:
        # Identify contiguous rotated runs in the smoothed log.
        rotated_pages = sorted(p for p, deg in smoothed.items() if deg != 0)
        if rotated_pages:
            # Build runs of consecutive rotated pages.
            runs: list[list[int]] = []
            current_run = [rotated_pages[0]]
            for p in rotated_pages[1:]:
                if p == current_run[-1] + 1:
                    current_run.append(p)
                else:
                    runs.append(current_run)
                    current_run = [p]
            runs.append(current_run)

            for run in runs:
                if len(run) < 2:
                    continue
                run_deg = smoothed[run[0]]  # representative rotation for this run

                # Try to extend left (page before run start).
                left_candidate = run[0] - 1
                if (
                    left_candidate in page_set
                    and smoothed[left_candidate] == 0
                    and corroboration.get(left_candidate, 0) != 0
                ):
                    smoothed[left_candidate] = run_deg
                    logger.info(
                        f"  [ROT-SMOOTH] p{left_candidate} extended into run "
                        f"(corroboration={corroboration[left_candidate]}°, run_deg={run_deg}°)"
                    )

                # Try to extend right (page after run end).
                right_candidate = run[-1] + 1
                if (
                    right_candidate in page_set
                    and smoothed[right_candidate] == 0
                    and corroboration.get(right_candidate, 0) != 0
                ):
                    smoothed[right_candidate] = run_deg
                    logger.info(
                        f"  [ROT-SMOOTH] p{right_candidate} extended into run "
                        f"(corroboration={corroboration[right_candidate]}°, run_deg={run_deg}°)"
                    )

    return smoothed


# ---------------------------------------------------------------------------
# Candidate corroborators — pick the winner via your separate rotation test.
# ---------------------------------------------------------------------------

def corroborate_aspect(img) -> tuple[bool, int | None, float]:
    """
    Aspect-ratio corroborator. Never abstains.

    A landscape-oriented page (width > height * threshold) is assumed to be a
    portrait page rotated 90°. Dataset prior: all truth rotations are 90°.

    Returns (is_rotated, suggested_deg_ccw, confidence).
    Tune THRESHOLD against your ROT-DIAG log if needed.
    """
    THRESHOLD = 1.15
    w, h = img.size
    is_rot = w > h * THRESHOLD
    return (is_rot, 90 if is_rot else 0, 0.9 if is_rot else 0.7)


def corroborate_tesseract(img) -> tuple[bool, int | None, float] | None:
    """
    Tesseract OSD corroborator. Abstains (returns None) on low-text pages.

    Requires: apt-get install -y tesseract-ocr && pip install pytesseract

    OSD returns a raw 'orientation' angle (clockwise CW). Mapping to CCW:
      OSD 0   → CCW 0    (upright)
      OSD 90  → CCW 270  (text runs down left edge; rotate 270° CCW to fix)
      OSD 180 → CCW 180  (upside down)
      OSD 270 → CCW 90   (text runs up right edge; rotate 90° CCW to fix)

    NOTE: Validate the mapping empirically from your test's truth-rotated rows —
    this mapping is derived from convention but should be confirmed against actual
    pages in this archive.

    Returns (is_rotated, suggested_deg_ccw, confidence), or None on abstain.
    """
    try:
        import pytesseract
    except ImportError:
        return None  # abstain if pytesseract not installed

    try:
        osd = pytesseract.image_to_osd(img, output_type=pytesseract.Output.DICT)
    except Exception:
        # "Too few characters" or any other OSD failure → abstain
        return None

    # Empirically (test_osd_mapping.py), tesseract's reported orientation angle
    # already equals the CCW degrees needed to correct the page on this corpus —
    # so the mapping is the identity. (The earlier 90<->270 swap failed the
    # synthetic round-trip test on every 90/270 case.)
    _OSD_TO_CCW = {0: 0, 90: 90, 180: 180, 270: 270}
    raw_angle = int(osd.get("orientation", 0))
    ccw_deg = _OSD_TO_CCW.get(raw_angle, 0)
    osd_conf = float(osd.get("orientation_conf", 0.0))

    # Low OSD confidence → abstain rather than mislead.
    if osd_conf < 2.0:
        return None

    is_rot = ccw_deg != 0
    conf_mapped = min(0.95, osd_conf / 10.0)  # rough normalisation; tune if needed
    return (is_rot, ccw_deg, conf_mapped)
