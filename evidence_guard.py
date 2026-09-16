"""Candidate terminal guard: a first coordinate table alone cannot force a cut.

Applied after V15 so upstream queries and anchors remain unchanged. This candidate
is not the best-v15 release. Promotion requires full regression validation.
"""

POLICY_VERSION = 'coordinate_override_abstention_v1'
LATER_RULES = ('fact_recovery', 'plot_rule', 'structural_rule', 'thermal_rule',
               'anchor_rule', 'filing_unit_rule', 'identity_rule', 'sequence_rule',
               'artifact_rule')


def apply(decisions):
    result = {page: dict(d) for page, d in decisions.items()}
    changes = []
    for page, d in decisions.items():
        if (d.get('new_document') is not True
                or d.get('feature_recovery') != 'first_coordinates'
                or d.get('right_kind') != 'coordinate_table'
                or d.get('model_new_document') is not False
                or d.get('model_relationship') not in ('continuation', 'attachment')
                or d.get('confidence', 0) < 90
                or any(d.get(rule) for rule in LATER_RULES)):
            continue
        result[page].update(new_document=False, relationship=d['model_relationship'],
                            evidence_guard=POLICY_VERSION)
        changes.append(dict(right_page=page, before=True, after=False,
                            rule=POLICY_VERSION, original_override=d['feature_recovery'],
                            model_relationship=d['model_relationship'],
                            evidence=d.get('evidence', '')))
    return result, changes
