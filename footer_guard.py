"""Terminal appendix continuity, corroborated by two footer OCR layouts."""
import re

POLICY_VERSION = 'numbered_appendix_back_reference_v1'
PROTECTED = ('fact_recovery', 'plot_rule', 'structural_rule', 'thermal_rule',
             'anchor_rule', 'filing_unit_rule', 'identity_rule', 'sequence_rule', 'artifact_rule')
BACK_REFERENCE = re.compile(r'^\s*(?:приложение|appendix|annex)\b.{0,50}\b(?:към|to)\b', re.I | re.S)
PREFIX = r'(?:page|стр|str|[cс][tmт][prр]|crp|cmp)\.?'
NUMBERING = re.compile(r'(?<!\w)' + PREFIX + r'\s*(\d{1,4})\s*(?:of|от|ot|oт)\s*(\d{1,4})(?!\d)', re.I)


def extract(text):
    return sorted({(int(a), int(b)) for a, b in NUMBERING.findall(text)
                   if 1 <= int(a) <= int(b) <= 9999 and int(b) > 1})


def consensus(readings):
    if len(readings) != 2 or any(r['error'] for r in readings):
        return None
    parsed = [extract(r['text']) for r in readings]
    return parsed[0][0] if len(parsed[0]) == 1 and parsed[0] == parsed[1] else None


def eligible(decision):
    return (decision.get('new_document') is True
            and not any(decision.get(k) for k in PROTECTED)
            and bool(BACK_REFERENCE.search(decision.get('right_heading', ''))))


def apply(decisions, ocr):
    result = {p: dict(d) for p, d in decisions.items()}
    changes = []
    for page, d in decisions.items():
        if not eligible(d):
            continue
        left, right = ocr.get(int(page) - 1), ocr.get(int(page))
        if not left or not right or any(r.get('status') != 'complete' for r in (left, right)):
            continue
        a, b = (consensus(r['readings']) for r in (left, right))
        if not a or not b or b[0] != a[0] + 1 or b[1] != a[1]:
            continue
        result[page].update(new_document=False, relationship='attachment', footer_guard=POLICY_VERSION)
        changes.append(dict(right_page=int(page), before=True, after=False, rule=POLICY_VERSION,
                            left_numbering=list(a), right_numbering=list(b), right_heading=d['right_heading']))
    return result, changes
