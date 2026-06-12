"""nomenclature_match.py — match VLM-transcribed document titles against the official
Bulgarian construction nomenclature (номенклатура_цяла.xls).

STANDALONE, CPU-only, deterministic. ZERO integration into split.py — this module is a
data/experiment tool, never imported by the pipeline.

============================  NEUTRAL-DEFAULT (HARD DESIGN RULE)  ============================
match_title() returns a band ∈ {MATCH, AMBIGUOUS, NONE}. Any future integration MUST treat
AMBIGUOUS and NONE *identically* to "no nomenclature signal". The nomenclature table can only
ever ADD confidence to a boundary decision — it must NEVER subtract from, veto, or block a
boundary. A wrong or loose match is therefore required to be harmless by construction.
(Enforced by test_neutral_default in test_nomenclature_match.py.)

Band thresholds here are PROVISIONAL and for REPORTING ONLY — they are NOT tuned. Final
thresholds come later from TP/FP score distributions, tuned on dev only. Callers should use the
raw per-level scores (returned alongside the band) to re-band; the band is a convenience label.
============================================================================================

Matching is multi-level and deterministic:
  (1) exact squashed equality
  (2) squashed containment, either direction (guarded against tiny entries)
  (3) character-trigram Jaccard on the squashed forms (noise-robust scorer)
  (4) token-set partial ratio (difflib) for multi-word entries / single-token edit robustness
Normalization (applied to BOTH table entries and transcribed titles): NFC → lowercase → fold
Latin→Cyrillic homoglyphs → strip quotes/punctuation/№/dashes → produce a squashed form (all
whitespace removed, defeats letter-spaced scans like 'Н А К Л О Н Е Н') and a token list.
Transcribed titles additionally have identifier tails stripped (tokens bearing digits/№ — permit
numbers, dates, slash-codes) so 'СКИЦА № 15-158202' reduces to the type 'скица'.
"""
import re
import unicodedata
import difflib

XLS_DEFAULT = "номенклатура_цяла.xls"

# Latin→Cyrillic homoglyph fold. Applied AFTER lowercasing; the uppercase entries from the spec
# (B→В, H→Н, T→Т, M→М, K→К, P→Р, C→С, E→Е, A→А, O→О, X→Х) are folded to their lowercase forms.
_HOMOGLYPH = {
    "a": "а", "e": "е", "o": "о", "p": "р", "c": "с", "x": "х", "y": "у",
    "b": "в", "h": "н", "t": "т", "m": "м", "k": "к",
}

_PUNCT = re.compile(r"[\"'«»“”„`’‘()\[\]{}.,;:!?/\\|№#*+\-–—_]+")
_WS = re.compile(r"\s+")
_HAS_DIGIT = re.compile(r"[0-9]")

# Drawing-sheet entry names — the experiment reports these SEPARATELY from administrative docs
# (hypothesis: sheet-types concentrate on FPs). Matched by normalized squashed form.
_SHEET_DISPLAY = ["Разрез", "Фасада", "План", "Ситуация", "План покрив", "Кофражен план", "Детайли"]


def _fold(s: str) -> str:
    return "".join(_HOMOGLYPH.get(ch, ch) for ch in s)


def normalize(text: str, strip_identifiers: bool = False):
    """NFC → lower → homoglyph-fold → (optionally drop identifier tokens) → strip punctuation
    → collapse whitespace. Returns (squashed, tokens). When strip_identifiers (transcribed
    titles), tokens containing a digit or № are dropped before punctuation stripping, leaving
    only the document-type words."""
    s = unicodedata.normalize("NFC", text or "").lower()
    s = _fold(s)
    if strip_identifiers:
        s = " ".join(t for t in s.split() if not _HAS_DIGIT.search(t) and "№" not in t and "#" not in t)
    s = _PUNCT.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    tokens = s.split()
    squashed = "".join(tokens)
    return squashed, tokens


def _trigrams(s: str):
    s = f"  {s} "
    return {s[i:i + 3] for i in range(len(s) - 2)}


def _jaccard_trigram(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    A, B = _trigrams(a), _trigrams(b)
    if not A or not B:
        return 0.0
    return len(A & B) / len(A | B)


def _token_set_ratio(t1, t2) -> float:
    """difflib ratio on the sorted unique-token strings. For single-token titles this is an
    edit-similarity on the word itself (robust to one drop/substitution)."""
    if not t1 or not t2:
        return 0.0
    s1 = " ".join(sorted(set(t1)))
    s2 = " ".join(sorted(set(t2)))
    return difflib.SequenceMatcher(None, s1, s2).ratio()


def _contained(q: str, e: str) -> bool:
    """Squashed containment either direction, guarded: the shorter string must be ≥5 chars and
    ≥50% the length of the longer — stops tiny entries ('акт') from matching inside long titles
    ('нотариаленакт')."""
    if not q or not e:
        return False
    short, long = (q, e) if len(q) <= len(e) else (e, q)
    if len(short) < 5 or (len(short) / len(long)) < 0.45:
        return False
    return short in long


# Provisional bands — REPORTING ONLY, not tuned (see module docstring).
PROV_MATCH_TRIGRAM = 0.74
PROV_MATCH_TOKENSET = 0.80
PROV_AMBIG_TRIGRAM = 0.50
PROV_AMBIG_TOKENSET = 0.72


ACTIONABLE_BANDS = frozenset({"MATCH"})
NEUTRAL_BANDS = frozenset({"AMBIGUOUS", "NONE"})


def is_confidence_signal(band: str) -> bool:
    """NEUTRAL-DEFAULT enforcement helper. Only MATCH may ever be used to ADD confidence to a
    boundary decision. AMBIGUOUS and NONE are BOTH treated as 'no nomenclature signal' — never
    actionable, never allowed to subtract from or block a boundary. Any integration MUST gate on
    this function, not on the raw band string. (See test_neutral_default.)"""
    return band in ACTIONABLE_BANDS


def _band(scores: dict) -> str:
    if scores["exact"] or scores["containment"] \
            or scores["trigram"] >= PROV_MATCH_TRIGRAM or scores["token_set"] >= PROV_MATCH_TOKENSET:
        return "MATCH"
    if scores["trigram"] >= PROV_AMBIG_TRIGRAM or scores["token_set"] >= PROV_AMBIG_TOKENSET:
        return "AMBIGUOUS"
    return "NONE"


def load_nomenclature(path: str = XLS_DEFAULT):
    """Parse the .xls into a list of entries: {code, name, category, squashed, tokens,
    is_sheet_type}. `category` is the X000-code section heading the row falls under (codes
    divisible by 1000 are section headings)."""
    import xlrd
    sheet_squashed = {normalize(n)[0] for n in _SHEET_DISPLAY}
    wb = xlrd.open_workbook(str(path))
    sh = wb.sheet_by_index(0)
    entries = []
    category = None
    for r in range(sh.nrows):
        raw_code = sh.cell_value(r, 0)
        name = str(sh.cell_value(r, 1)).strip()
        try:
            code = int(float(raw_code))
        except (TypeError, ValueError):
            code = None
        if code is not None and code % 1000 == 0:
            category = name  # X000 section heading defines the category for following rows
        if not name:
            continue
        squashed, tokens = normalize(name)
        entries.append({
            "code": code, "name": name, "category": category,
            "squashed": squashed, "tokens": tokens,
            "is_sheet_type": squashed in sheet_squashed,
        })
    return entries


def match_title(title: str, entries):
    """Match a (possibly noisy) transcribed title against the nomenclature.
    Returns (best_entry | None, level_scores: dict, band: str). Deterministic."""
    q_sq, q_tok = normalize(title, strip_identifiers=True)
    best = None
    best_scores = {"exact": 0, "containment": 0, "trigram": 0.0, "token_set": 0.0}
    best_key = (-1, -1, -1.0, -1.0)
    for e in entries:
        if not e["squashed"]:
            continue
        exact = 1 if q_sq and q_sq == e["squashed"] else 0
        contain = 1 if _contained(q_sq, e["squashed"]) else 0
        tri = _jaccard_trigram(q_sq, e["squashed"])
        tok = _token_set_ratio(q_tok, e["tokens"])
        key = (exact, contain, tri, tok)
        if key > best_key:
            best_key = key
            best = e
            best_scores = {"exact": exact, "containment": contain,
                           "trigram": round(tri, 4), "token_set": round(tok, 4)}
    return best, best_scores, _band(best_scores)


def top_matches(title: str, entries, k: int = 3):
    """Return the top-k candidate entries with their scores (for AMBIGUOUS-band inspection)."""
    q_sq, q_tok = normalize(title, strip_identifiers=True)
    scored = []
    for e in entries:
        if not e["squashed"]:
            continue
        exact = 1 if q_sq and q_sq == e["squashed"] else 0
        contain = 1 if _contained(q_sq, e["squashed"]) else 0
        tri = _jaccard_trigram(q_sq, e["squashed"])
        tok = _token_set_ratio(q_tok, e["tokens"])
        scored.append((e, {"exact": exact, "containment": contain,
                           "trigram": round(tri, 4), "token_set": round(tok, 4)},
                       (exact, contain, tri, tok)))
    scored.sort(key=lambda x: x[2], reverse=True)
    return [(e, s) for e, s, _ in scored[:k]]


if __name__ == "__main__":
    ents = load_nomenclature()
    print(f"loaded {len(ents)} entries, {len(set(e['name'] for e in ents))} unique names, "
          f"{len(set(e['category'] for e in ents))} categories")
    for t in ["СКИЦА № 15-158202", "С К И Ц А", "НАКЛОНЕН ПОКРИВ", "ЧЕЛЕН ЛИСТ", "НОТАРИАЛЕН АКТ"]:
        e, s, b = match_title(t, ents)
        print(f"  {t!r:34} -> {b:9} {e['name'] if e else None!r} {s}")
