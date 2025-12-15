from odoo import api, SUPERUSER_ID


def _restrict_equipment_manager_rule(cr):
    """Limit default maintenance equipment manager rule to own requests."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    rule = env.ref('maintenance.equipment_request_rule_admin_user', raise_if_not_found=False)
    if rule:
        desired_domain = "['|', '|', ('owner_user_id', '=', user.id), ('message_partner_ids', 'in', [user.partner_id.id]), ('user_id', '=', user.id)]"
        if rule.domain_force != desired_domain:
            rule.domain_force = desired_domain


def post_init_hook(cr, registry):
    _restrict_equipment_manager_rule(cr)
