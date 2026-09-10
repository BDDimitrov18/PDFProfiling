"""Experimental narrow archive-boundary verifier, independent of labels.

A negative decision authorizes only a named, visibly supported correction.
Every other seam is preserved. This is not a standalone document detector.
"""
from model_options import validate_query_fields

SCHEMA = {'left_heading': str, 'right_heading': str, 'left_kind': str,
          'right_kind': str, 'link_evidence': str, 'correction': str,
          'confidence': 'confidence'}
KINDS = {'letter', 'postal_receipt', 'review_sheet', 'contract', 'contract_terms',
         'contents', 'explanatory_note', 'closing_only', 'other'}
RULES = {'none', 'review_series', 'postal_attachment', 'terms_attachment',
         'toc_section', 'closing_continuation'}


def prompt(variant, left, right):
    if variant != 'typed_v3' or type(left) is not int or right != left + 1 or left < 1:
        raise ValueError('Expected typed_v3 and adjacent pages')
    return f'''Inspect these two scanned Bulgarian construction archive pages,
page {left} then page {right}. Verify ONLY the five narrow continuation cases
listed below. Do not decide whether the pages belong to the same overall project.
Separately filed certificates, insurance policies, permits, letters, distribution
lists (РАЗПИСЕН ЛИСТ), covers, explanatory notes, bills of quantities and coordinate
tables may be separate documents even when one refers to another as an attachment.
A generic attachment/section relationship is NOT a correction.

Read literal headings first. Choose left_kind and right_kind from:
letter, postal_receipt, review_sheet, contract, contract_terms, contents,
explanatory_note, closing_only, other. Use other when not visibly identifiable.

Choose correction from these exact cases, otherwise none:
1. review_series: BOTH pages are municipal project review sheets with the repeated
   Обект / Част / становище or забележки / дата за връщане fields. Same visible
   project, different discipline/reviewer/date is still one review series. Do not
   apply at the FIRST review sheet after a different kind of page. Do not infer a
   changed project from illegible handwriting.
2. postal_attachment: RIGHT page is a postal delivery/return receipt headed
   ИЗВЕСТИЕ ЗА ДОСТАВЯНЕ or ОБРАТНА РАЗПИСКА. LEFT is its letter with a visible
   matching reference, OR is another postal receipt from the same dispatch group.
   РАЗПИСЕН ЛИСТ is a distribution list, NOT a postal receipt for this rule.
3. terms_attachment: RIGHT is ТЪРГОВСКИ УСЛОВИЯ for the contract on LEFT, with
   matching issuer or an explicit preceding appendix reference. A longer heading
   beginning Търговски условия is allowed. A new contract is not contract terms.
4. toc_section: LEFT is a contents/index page explicitly listing the explanatory
   note on RIGHT, with matching project discipline. A project COVER is not a
   contents page. Do not merge arbitrary explanatory notes or calculations.
5. closing_continuation: RIGHT contains ONLY closing signatures, stamps, notarial
   certification or approval for the instrument on LEFT, with directly matching
   text/parties or continued sentence. No new substantive heading or document body.
   A signed complete one-page letter/certificate is never closing_only.

link_evidence must briefly identify visible text or form fields supporting the
chosen correction. Do not invent document numbers, names or addresses. If the
required relationship is unreadable, contradictory or uncertain, choose none.
Return JSON: {{"left_heading":"literal heading or empty", "right_heading":"literal heading or empty",
"left_kind":"one kind", "right_kind":"one kind", "link_evidence":"brief visible evidence",
"correction":"one case or none", "confidence":0-100}}.
'''


def decision(data):
    validate_query_fields(data, SCHEMA)
    if data['left_kind'] not in KINDS or data['right_kind'] not in KINDS or data['correction'] not in RULES:
        raise ValueError('Unknown archive evidence category')
    left, right, rule = data['left_kind'], data['right_kind'], data['correction']
    matches = {
        'none': True,
        'review_series': left == right == 'review_sheet',
        'postal_attachment': left in {'letter', 'postal_receipt'} and right == 'postal_receipt',
        'terms_attachment': left == 'contract' and right == 'contract_terms',
        'toc_section': left == 'contents' and right == 'explanatory_note',
        'closing_continuation': right == 'closing_only',
    }
    # Contradictory evidence cannot authorize a veto; retain it in the record.
    veto = rule != 'none' and matches[rule] and data['confidence'] >= 90 and bool(data['link_evidence'].strip())
    return {**data, 'new_document': not veto, 'relationship': 'continuation' if veto else 'independent',
            'evidence': data['link_evidence'], 'guard_passed': matches[rule]}
