"""domain_rules.py — POST-PROCESSING domain-rule layer for boundary candidates.

STAGED / NOT WIRED. Like the Fix-11 functions, this module is PURE logic and is NOT imported
into split.py's live detection path. Design + unit tests ONLY; no eval, no wiring, until each
rule has pre-registered probe expectations (see RESULTS.md ROUND 6 + RULES.md).

It takes the detector's boundary CANDIDATES + per-page info and POST-PROCESSES them rule by
rule, returning adjusted boundaries + a per-rule AUDIT TRAIL (every suppression / merge /
normalisation / prior is logged with the rule id and reason — the layer is auditable rule-by-rule).

================================ VERBATIM GROUND-TRUTH RULES ================================
(Hand-extracted by human + colleague by manually splitting THIS dataset. PRESERVED EXACTLY.)

 1. Нотариален акт ends ONLY at the notary's signature.
 2. Удостоверение за наследници: starts with that title → lists heirs → ALWAYS ends with a
    длъжностно лице (official).
 3. Titles "изходни точки", "списък с подробни точки", "Координатен регистър" all normalize to
    type = Координатен регистър.
 4. Обяснителна записка ALWAYS ends with "Проектант" or "Съставил".
 5. Разрешение за строеж is always 2 pages — but sometimes only 1 page is scanned.
 6. Consecutive "Известие за доставяне" merge into one document, categorized as "обратна разписка".
 7. EVN documents carry "Търговски условия" as SECTION headings (not boundaries).
 8. After a Заглавна страница titled "Инвестиционен проект", a doc titled "съдържание" may follow
    — DO NOT split between them.
=============================================================================================

RULE KINDS (implemented distinctly):
  (A) CLOSURE rules 1, 2, 4 — a document of the named type is NOT complete (no boundary emitted
      after it) until its CLOSING MARKER is read on a page (notary signature / длъжностно лице /
      "Проектант"|"Съставил"). A section/title boundary candidate appearing BEFORE the closure
      marker is intra-document → suppressed. These READ a marker string (a reliable channel);
      they do NOT judge content. If the marker is NEVER read (e.g. a dropped scan page), the rule
      ABSTAINS — it suppresses nothing. It must never manufacture a merge from a missing page.
  (B) NORMALISE / MERGE / ADJACENCY rules 3, 6, 7, 8 — type-collapse (3), merge-consecutive (6),
      section-not-boundary (7 — EVN issuer-specific), do-not-split-adjacent-pair (8).
  SOFT PRIOR rule 5 (and ALL structural-expectation logic) — NEVER a hard override. May nudge
      confidence toward a 2-page span, but MUST tolerate a 1-page scan and MUST NEVER force a
      split or merge on page-count alone. ⚠ Rigid structural (page-count) rules MANUFACTURE
      errors when scans drop pages — rule 5 only annotates / weakly nudges, never adds/removes.

OVERFIT GUARD: these rules were extracted FROM this 20-file test set's mistakes, so a rule that
"fixes" a case risks relabelling THAT case rather than generalising. When this layer eventually
evals it gets the full probe + STRATIFIED full-tests; any rule that helps dev/probe but not
held-out structure is a candidate over-fit and is FLAGGED, not kept silently. See RULES.md.
"""
from dataclasses import dataclass, field
from typing import Optional, List, Dict, FrozenSet, Tuple
import re

# --- nomenclature codes (номенклатура_цяла.xls) for rule-referenced types that HAVE entries ---
NOMENCLATURE_CODES: Dict[str, int] = {
    "Обяснителна записка": 1001,
    "Координатен регистър": 8014,
    "Удостоверение за наследници": 19061,
    "Разрешение за строеж (РС)": 19019,
    "Обратна разписка": 19005,
    "Заглавна страница": 1010,
}
# Types the rules ADD — ABSENT from the nomenclature table (this is knowledge the rules contribute):
RULE_ADDED_TYPES = ["Нотариален акт", "Известие за доставяне", "съдържание", "Търговски условия"]

# --- closure markers (set on a PageInfo when the reliable marker string is read on that page) ---
MARKER_NOTARY = "notary_signature"      # rule 1 — notary's signature
MARKER_OFFICIAL = "official_signoff"    # rule 2 — длъжностно лице (official)
MARKER_PROEKTANT = "proektant"          # rule 4 — "Проектант"
MARKER_SASTAVIL = "sastavil"            # rule 4 — "Съставил"

# rule 3 — title synonyms that normalise to type "Координатен регистър" (code 8014)
_COORD_SYNONYMS = ("изходни точки", "списък с подробни точки", "координатен регистър")


@dataclass
class PageInfo:
    """What the layer reads off ONE page (1-indexed). title/issuer/markers are supplied upstream
    (transcribe-first; the layer never judges, it reads strings)."""
    page: int
    title: Optional[str] = None
    issuer: Optional[str] = None                       # e.g. "EVN ..." for rule 7
    markers: FrozenSet[str] = field(default_factory=frozenset)


@dataclass
class Boundary:
    """A candidate document-START at `page` (1-indexed), from the detector. doc_type is filled /
    normalised by the rules. conf is only ever nudged by the soft prior (rule 5)."""
    page: int
    conf: float = 0.90
    doc_type: Optional[str] = None


@dataclass
class AuditEntry:
    rule: str            # e.g. "R1-closure-notarial"
    action: str          # suppress | merge | normalize | prior | abstain
    page: Optional[int]
    detail: str


def _norm(s: Optional[str]) -> Optional[str]:
    """lower + collapse whitespace; for robust title/marker comparison. (Deliberately simple —
    upstream transcription is the reliable channel; this is not a fuzzy matcher.)"""
    if s is None:
        return None
    return " ".join(s.strip().lower().split())


def _title_is(title: Optional[str], key: str) -> bool:
    """True when `key` (normalised) appears in `title` (normalised). Containment, so a long
    transcribed heading ('НОТАРИАЛЕН АКТ за покупко-продажба…') still matches its type key."""
    t = _norm(title)
    return t is not None and _norm(key) in t


def _title_of(pages: Dict[int, PageInfo], page: int) -> Optional[str]:
    pi = pages.get(page)
    return pi.title if pi else None


# ===========================================================================================
# Rule 3 — NORMALISE titles → type (must run first: closure/merge rules key on type)
# ===========================================================================================
def rule3_normalize_types(pages: Dict[int, PageInfo], bnds: List[Boundary], audit: List[AuditEntry]) -> List[Boundary]:
    for b in bnds:
        title = _title_of(pages, b.page)
        t = _norm(title)
        if t is not None and any(syn in t for syn in _COORD_SYNONYMS):
            if b.doc_type != "Координатен регистър":
                b.doc_type = "Координатен регистър"
                audit.append(AuditEntry("R3-normalize", "normalize", b.page,
                    f"title {title!r} → type 'Координатен регистър' (code 8014)"))
        elif b.doc_type is None and title:
            b.doc_type = title.strip()
    return bnds


# ===========================================================================================
# (A) CLOSURE rules 1, 2, 4 — generic engine. Suppress intra-document candidates that appear
#     BEFORE the named type's closure marker. ABSTAIN if the marker is never read.
# ===========================================================================================
def _apply_closure(pages: Dict[int, PageInfo], bnds: List[Boundary], audit: List[AuditEntry],
                   type_key: str, marker_set: FrozenSet[str], rule_id: str) -> List[Boundary]:
    keep = list(bnds)
    page_nums = sorted(pages)
    for b in bnds:
        if not _title_is(_title_of(pages, b.page), type_key):
            continue
        # first page at/after the start that carries the closure marker
        closure = next((p for p in page_nums if p >= b.page and (pages[p].markers & marker_set)), None)
        if closure is None:
            audit.append(AuditEntry(rule_id, "abstain", b.page,
                f"{type_key}: closure marker {sorted(marker_set)} never read at/after p{b.page} "
                f"(possible dropped scan) → abstain, suppress nothing"))
            continue
        for other in list(keep):
            if other is b:
                continue
            if b.page < other.page <= closure:
                keep.remove(other)
                audit.append(AuditEntry(rule_id, "suppress", other.page,
                    f"intra-document: candidate p{other.page} precedes the {type_key} closure "
                    f"marker on p{closure} → suppressed (doc starts p{b.page})"))
    return keep


def rule1_closure_notarial(pages, bnds, audit):
    """Нотариален акт ends ONLY at the notary's signature."""
    return _apply_closure(pages, bnds, audit, "нотариален акт", frozenset({MARKER_NOTARY}), "R1-closure-notarial")


def rule2_closure_naslednici(pages, bnds, audit):
    """Удостоверение за наследници ALWAYS ends with a длъжностно лице (official)."""
    return _apply_closure(pages, bnds, audit, "удостоверение за наследници", frozenset({MARKER_OFFICIAL}), "R2-closure-naslednici")


def rule4_closure_obyasnitelna(pages, bnds, audit):
    """Обяснителна записка ALWAYS ends with 'Проектант' or 'Съставил'."""
    return _apply_closure(pages, bnds, audit, "обяснителна записка", frozenset({MARKER_PROEKTANT, MARKER_SASTAVIL}), "R4-closure-obysn")


# ===========================================================================================
# (B) MERGE / SECTION / ADJACENCY rules 6, 7, 8
# ===========================================================================================
def rule6_merge_izvestie(pages: Dict[int, PageInfo], bnds: List[Boundary], audit: List[AuditEntry]) -> List[Boundary]:
    """Consecutive 'Известие за доставяне' merge into ONE document → type 'Обратна разписка' (19005)."""
    ordered = sorted(bnds, key=lambda b: b.page)
    out: List[Boundary] = []
    i, n = 0, len(ordered)
    while i < n:
        b = ordered[i]
        if _title_is(_title_of(pages, b.page), "известие за доставяне"):
            j = i
            while j + 1 < n and _title_is(_title_of(pages, ordered[j + 1].page), "известие за доставяне"):
                j += 1
            b.doc_type = "Обратна разписка"
            out.append(b)
            for k in range(i + 1, j + 1):
                audit.append(AuditEntry("R6-merge", "merge", ordered[k].page,
                    f"consecutive 'Известие за доставяне' p{ordered[k].page} merged into doc "
                    f"starting p{b.page}; type → 'Обратна разписка' (code 19005)"))
            i = j + 1
        else:
            out.append(b)
            i += 1
    return out


def _is_evn(pi: Optional[PageInfo]) -> bool:
    return pi is not None and pi.issuer is not None and "evn" in pi.issuer.lower()


def rule7_evn_trade_terms(pages: Dict[int, PageInfo], bnds: List[Boundary], audit: List[AuditEntry]) -> List[Boundary]:
    """ISSUER-SPECIFIC (EVN): 'Търговски условия' is a SECTION heading, not a boundary."""
    out = []
    for b in bnds:
        pi = pages.get(b.page)
        if _title_is(_title_of(pages, b.page), "търговски условия") and _is_evn(pi):
            audit.append(AuditEntry("R7-section", "suppress", b.page,
                "EVN 'Търговски условия' is a section heading, not a document start → suppressed "
                "(ISSUER-SPECIFIC: EVN only)"))
            continue
        out.append(b)
    return out


def rule8_invest_sadarzhanie(pages: Dict[int, PageInfo], bnds: List[Boundary], audit: List[AuditEntry]) -> List[Boundary]:
    """After a Заглавна страница titled 'Инвестиционен проект', a 'съдържание' doc may follow —
    DO NOT split between them."""
    starts = sorted(b.page for b in bnds)
    drop = set()
    for b in bnds:
        if not _title_is(_title_of(pages, b.page), "инвестиционен проект"):
            continue
        nxt = next((s for s in starts if s > b.page), None)
        if nxt is not None and _title_is(_title_of(pages, nxt), "съдържание"):
            drop.add(nxt)
            audit.append(AuditEntry("R8-adjacent", "suppress", nxt,
                f"'съдържание' p{nxt} immediately follows Заглавна страница 'Инвестиционен проект' "
                f"p{b.page} → DO NOT split between them; boundary suppressed"))
    return [b for b in bnds if b.page not in drop]


# ===========================================================================================
# SOFT PRIOR rule 5 — NEVER a hard override.
# ===========================================================================================
def rule5_rs_twopage_prior(pages: Dict[int, PageInfo], bnds: List[Boundary], audit: List[AuditEntry],
                           prior_weight: float = 0.05) -> List[Boundary]:
    """Разрешение за строеж (РС, code 19019) is USUALLY 2 pages — but sometimes only 1 is scanned.
    SOFT PRIOR ONLY: if a candidate closes a 2-page span (a candidate exists at start+2), nudge
    THAT candidate's conf up by a small weight. NEVER adds or removes a boundary; NEVER penalises
    a 1-page scan (a candidate at start+1 is left untouched). Page-count NEVER forces a split/merge.
    ⚠ Rigid structural rules manufacture errors when scans drop pages — this only annotates/nudges."""
    pages_with_bnd = {b.page: b for b in bnds}
    for b in bnds:
        if not _title_is(_title_of(pages, b.page), "разрешение за строеж"):
            continue
        twopage = pages_with_bnd.get(b.page + 2)
        if twopage is not None:
            twopage.conf = min(1.0, twopage.conf + prior_weight)
            audit.append(AuditEntry("R5-softprior", "prior", b.page + 2,
                f"РС (code 19019) typical 2-page span: weak +{prior_weight} conf nudge on the "
                f"span-closing candidate p{b.page + 2}. SOFT only — no split/merge forced."))
        else:
            audit.append(AuditEntry("R5-softprior", "prior", b.page,
                f"РС (code 19019) at p{b.page}: typical span 2 pages but tolerating a possible "
                f"1-page scan — NO change made (page-count never forces a split/merge)."))
    return bnds


# ===========================================================================================
# Orchestrator
# ===========================================================================================
RULE_ORDER = [
    ("R3", rule3_normalize_types),      # normalise types first (closure/merge key on type)
    ("R1", rule1_closure_notarial),
    ("R2", rule2_closure_naslednici),
    ("R4", rule4_closure_obyasnitelna),
    ("R6", rule6_merge_izvestie),
    ("R7", rule7_evn_trade_terms),
    ("R8", rule8_invest_sadarzhanie),
    ("R5", rule5_rs_twopage_prior),     # soft prior last; never adds/removes
]


def apply_domain_rules(pages: List[PageInfo], boundaries: List[Boundary]) -> Tuple[List[Boundary], List[AuditEntry]]:
    """Post-process detector boundary CANDIDATES through the domain rules in order.
    Returns (adjusted boundaries sorted by page, audit trail). Inputs are not mutated."""
    pages_by_num = {p.page: p for p in pages}
    bnds = [Boundary(b.page, b.conf, b.doc_type) for b in boundaries]  # defensive copy
    audit: List[AuditEntry] = []
    for _id, fn in RULE_ORDER:
        bnds = fn(pages_by_num, bnds, audit)
    return sorted(bnds, key=lambda b: b.page), audit
