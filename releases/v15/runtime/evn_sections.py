"""Experimental, issuer-specific suppression of proposed document starts.

Historical human rule 7 (``6bc669b:RULES.md``) says that EVN's
``Търговски условия`` heading denotes a section. This module only interprets
literal page transcriptions; it neither locates starts nor runs inference.
Its effect on accuracy and its scope beyond the historical corpus are unmeasured.
It is intentionally separate from the production detector. Callers must preserve
the original first page and apply this candidate only to already proposed cuts.
"""
from __future__ import annotations

import json
import re
import unicodedata


# Do not fuzzy-match spelling, transliterate mixed scripts, or search body text.
_ISSUER_TOKEN = re.compile(r"(?<!\w)(?:evn|евн)(?!\w)")
_SECTION_NUMBER = r"(?:[0-9]+(?:\.[0-9]+)*[.)]|[ivxlcdm]+[.)]|\([0-9]+\))"
_TITLE = re.compile(rf"(?:{_SECTION_NUMBER}\s*)?търговски условия[.:]?")


def transcription_prompt(page_num: int) -> str:
    """Request visible strings without suggesting a title, issuer, or decision."""
    if type(page_num) is not int or page_num < 1:
        raise ValueError("page_num must be a positive integer")
    return (
        f"Read page {page_num}. Transcribe its main/top heading and the issuing "
        "organization's name as visibly printed in the page header or letterhead. "
        "Copy the original language and wording literally, including any heading "
        "number. Do not translate, summarize, complete missing text, or infer an "
        "organization from organizations mentioned in the body. Do not copy body "
        "paragraphs into the heading. Use an empty string for either field if it "
        "is absent or unreadable. Return exactly one JSON object with only two "
        "string fields: {\"title\": \"\", \"issuer\": \"\"}. "
        "Do not include Markdown fences, commentary, or additional fields."
    )


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _abstain(reason: str, title: str = "", issuer: str = "") -> dict:
    return {"status": "abstain", "title": title, "issuer": issuer, "reason": reason}


def parse_evidence(raw: str) -> dict:
    """Parse the strict transcription schema; uncertain evidence preserves cuts.

    Literal strings are retained for auditing. JSON fences, prose, duplicate or
    extra keys, non-string values, and missing/blank fields are not repaired.
    """
    if type(raw) is not str:
        return _abstain("transcription is not a string")
    try:
        evidence = json.loads(raw, object_pairs_hook=_unique_object)
    except (ValueError, RecursionError):
        return _abstain("invalid or ambiguous JSON")
    if type(evidence) is not dict or set(evidence) != {"title", "issuer"}:
        return _abstain("expected exactly title and issuer fields")
    title, issuer = evidence["title"], evidence["issuer"]
    if type(title) is not str or type(issuer) is not str:
        return _abstain("title and issuer must be strings")
    if not title.strip() or not issuer.strip():
        return _abstain("title or issuer is absent or unreadable", title, issuer)
    return {"status": "ok", "title": title, "issuer": issuer,
            "reason": "literal title and issuer transcribed"}


def _normalize(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def should_suppress(evidence: dict) -> bool:
    """Match the whole heading and an exact issuer token; otherwise keep the cut.

    Accepted normalization is limited to Unicode canonical composition, case,
    whitespace, a leading numbered-section marker, and a final period or colon.
    A longer title merely mentioning trade terms does not match. The issuer can
    include a legal name around the separate Latin EVN or Cyrillic ЕВН token.
    """
    if not isinstance(evidence, dict) or evidence.get("status") != "ok":
        return False
    title, issuer = evidence.get("title"), evidence.get("issuer")
    if type(title) is not str or type(issuer) is not str:
        return False
    return bool(_TITLE.fullmatch(_normalize(title))
                and _ISSUER_TOKEN.search(_normalize(issuer)))
