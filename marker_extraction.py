"""marker_extraction.py — TRANSCRIBE-FIRST marker extraction for the domain-rules layer
(and the sig/section + [NO-SIGNAL] identity work). STAGED / NOT WIRED into split.py's live
boundary path. Design + unit tests only; no eval until probe expectations are pre-registered.

================================  TRANSCRIBE-FIRST, NEVER JUDGE  ================================
This is THE load-bearing design constraint. Every channel works in two steps:
  (a) a dedicated post-hoc query asks the model to TRANSCRIBE VERBATIM a page region (bottom-of-page
      / stamp / signature-block / letterhead / titleblock / top-of-page heading) — it NEVER answers
      a yes/no and NEVER classifies. (Prompts below; all end "report printed text only, do not judge".)
  (b) OUR CODE detects the marker by string-matching that transcription, reusing the nomenclature
      normaliser (NFC → Latin→Cyrillic homoglyph fold → whitespace-squash). The MODEL reports printed
      text; CODE renders every verdict.
NO channel may ask "does this page have / start / end X?". That judgment framing is the proven
failure mode (confirm-pass, Fix 11 v1/v2, both one-page-checks; the p21 confabulated title is the
canonical case). If a channel is a yes/no to the model, it is WRONG by construction.
The model-side anti-confabulation guard is transcribe-first; the code-side guarantee is that a
transcription with no marker string yields NO marker (tested, incl. negative controls).
==============================================================================================
"""
import re
from nomenclature_match import normalize
from domain_rules import MARKER_NOTARY, MARKER_OFFICIAL, MARKER_PROEKTANT, MARKER_SASTAVIL

# ---------------------------------------------------------------------------
# (a) TRANSCRIPTION PROMPTS — verbatim, NEVER yes/no. The pod driver feeds these to the model.
# ---------------------------------------------------------------------------
PROMPT_CLOSURE_SIGNOFF = (
    "Transcribe VERBATIM the text in the BOTTOM portion of this page and inside any stamp, seal, or "
    "signature block (roles, names, 'Проектант'/'Съставил', notary text, official titles, registration "
    "numbers). Copy exactly what is printed. Do NOT summarise, judge, classify, or answer any question. "
    "If the bottom of the page has no such text, respond with the single word: NONE."
)
PROMPT_ISSUER = (
    "Transcribe VERBATIM the letterhead / issuer field at the TOP of this page (company or institution "
    "name and logo text). Copy exactly what is printed. Do NOT judge or classify. If absent, respond NONE."
)
PROMPT_TITLE = (
    "Transcribe VERBATIM the single top-of-page heading/title of this page, exactly as printed. "
    "Do NOT judge whether it starts a new document. If there is no heading, respond NONE."
)
PROMPT_TITLEBLOCK = (
    "Transcribe VERBATIM the identifying fields in the title block / header: document number, изх.№/вх.№, "
    "registration № (рег. №), and any sheet marker like 'лист X от Y'. Copy exactly what is printed. "
    "Do NOT judge or classify. If absent, respond NONE."
)

CHANNELS = ("closure_signoff", "issuer", "title", "titleblock_fields")
PROMPTS = {"closure_signoff": PROMPT_CLOSURE_SIGNOFF, "issuer": PROMPT_ISSUER,
           "title": PROMPT_TITLE, "titleblock_fields": PROMPT_TITLEBLOCK}

# ---------------------------------------------------------------------------
# code-side normalised keyword matching (the normaliser folds EVN -> 'еvn', squashes 'длъжностно
# лице' -> 'длъжностнолице', defeats letter-spacing — so we match THROUGH it, never on raw strings)
# ---------------------------------------------------------------------------
def _sq(text):
    return normalize(text or "")[0]

def _has(transcription_sq, keyword):
    return _sq(keyword) in transcription_sq

def _is_none(text):
    """The literal NONE sentinel the transcription prompts return (checked BEFORE normalization,
    which would homoglyph-fold 'none' -> 'nоnе')."""
    return (text or "").strip().upper() == "NONE" or not (text or "").strip()

# closure marker keyword sets (each is a list of printed strings whose presence implies the marker)
_KW_PROEKTANT = ["проектант"]
_KW_SASTAVIL = ["съставил"]
_KW_NOTARY = ["нотариус", "нотариална кантора"]          # the SIGNER's role in the signature/seal region
_KW_OFFICIAL = ["длъжностно лице"]                        # длъжностно лице (official) closing наследници
_KW_EVN = ["evn", "електроразпределение"]                # issuer EVN (normaliser folds EVN -> еvn)

_NONE_TOKENS = {"none", ""}


def match_closure_signoff(transcription: str) -> dict:
    """Pure. Detect closure markers in a transcribed bottom/signature/seal region.
    Returns {'markers': set, 'evidence': {marker: matched_kw}, 'transcription': str}.
    A transcription with no marker string yields an EMPTY marker set (anti-confabulation at code side)."""
    sq = _sq(transcription)
    markers, evidence = set(), {}
    if _is_none(transcription):
        return {"markers": set(), "evidence": {}, "transcription": transcription}
    for kw in _KW_PROEKTANT:
        if _has(sq, kw): markers.add(MARKER_PROEKTANT); evidence[MARKER_PROEKTANT] = kw
    for kw in _KW_SASTAVIL:
        if _has(sq, kw): markers.add(MARKER_SASTAVIL); evidence[MARKER_SASTAVIL] = kw
    for kw in _KW_NOTARY:
        if _has(sq, kw): markers.add(MARKER_NOTARY); evidence[MARKER_NOTARY] = kw
    for kw in _KW_OFFICIAL:
        if _has(sq, kw): markers.add(MARKER_OFFICIAL); evidence[MARKER_OFFICIAL] = kw
    return {"markers": markers, "evidence": evidence, "transcription": transcription}


def match_issuer(transcription: str) -> dict:
    """Pure. Identify the issuer from a transcribed letterhead. Returns {'issuer': str|None, 'raw': str}."""
    sq = _sq(transcription)
    issuer = None
    if any(_has(sq, kw) for kw in _KW_EVN):
        issuer = "EVN"
    return {"issuer": issuer, "raw": transcription}


def match_title(transcription: str) -> dict:
    """Pure. Return the transcribed top-of-page heading verbatim (rule 3/8 + nomenclature read it).
    No judgment — just the printed heading (or None for NONE)."""
    raw = (transcription or "").strip()
    heading = None if _is_none(raw) else raw
    return {"heading": heading}


_RX_ISSUE = re.compile(r'(изх\.?\s*№|вх\.?\s*№|рег\.?\s*№)\s*([^\n,;]+)', re.IGNORECASE)
_RX_SHEET = re.compile(r'лист\s*(\d+)\s*(?:от|/)\s*(\d+)', re.IGNORECASE)
_RX_DOCNO = re.compile(r'№\s*([0-9][0-9\-/ .]{2,})')


def match_titleblock_fields(transcription: str) -> dict:
    """Pure. Extract identifying fields for the [NO-SIGNAL] identity-change work (compare consecutive
    pages: a change of issue-number / sheet-set implies a new document). Returns a dict of raw fields."""
    t = transcription or ""
    fields = {}
    m = _RX_ISSUE.search(t)
    if m:
        fields["issue_kind"] = m.group(1).strip()
        fields["issue_number"] = m.group(2).strip()
    s = _RX_SHEET.search(t)
    if s:
        fields["sheet_x"] = int(s.group(1)); fields["sheet_of"] = int(s.group(2))
    d = _RX_DOCNO.search(t)
    if d and "issue_number" not in fields:
        fields["doc_number"] = d.group(1).strip()
    return fields


def extract_from_transcriptions(transcriptions: dict) -> dict:
    """Aggregate the 4 channel transcriptions for ONE page into a marker record that plugs straight
    into domain_rules.PageInfo (markers, issuer, title) + titleblock fields. `transcriptions` keys
    are the CHANNELS. Pure — all model I/O has already happened upstream (transcribe-first)."""
    closure = match_closure_signoff(transcriptions.get("closure_signoff", ""))
    issuer = match_issuer(transcriptions.get("issuer", ""))
    title = match_title(transcriptions.get("title", ""))
    tb = match_titleblock_fields(transcriptions.get("titleblock_fields", ""))
    return {
        "markers": closure["markers"],
        "marker_evidence": closure["evidence"],
        "issuer": issuer["issuer"],
        "issuer_raw": issuer["raw"],
        "title": title["heading"],
        "titleblock_fields": tb,
    }
