"""Unpromoted terminal guards; upstream V15 inference remains unchanged."""
from evidence_guard import apply as coordinate_guard
from quantity_guard import apply as quantity_guard

POLICY_VERSION = 'coordinate_and_quantity_override_abstention_v2'


def apply(decisions):
    result, changes = coordinate_guard(decisions)
    result, quantity_changes = quantity_guard(result)
    changes.extend(dict(right_page=c['page'], before=c['before'], after=c['after'],
                        rule=c['reason'], original_override='internal_structural_calculation',
                        model_relationship=decisions[c['page']]['model_relationship'],
                        evidence=decisions[c['page']].get('evidence', ''))
                   for c in quantity_changes)
    return result, changes
