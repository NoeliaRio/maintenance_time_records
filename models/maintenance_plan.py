from odoo import models, fields, api
import logging
import ast

_logger = logging.getLogger(__name__)


class MaintenancePlan(models.Model):
    _inherit = 'maintenance.plan'

    note = fields.Text(string="Instrucciones")
    code = fields.Char(string='Código', readonly=True, copy=False, default='/')
    instruction_pdf = fields.Binary(string="Instructivo PDF", help="Cargar el PDF del instructivo de mantenimiento.")

    @api.model
    def create(self, vals):
        if vals.get('code', '/') == '/':
            vals['code'] = self.env['ir.sequence'].next_by_code('maintenance.plan.default') or '/'
        return super(MaintenancePlan, self).create(vals)

    def button_manual_request_generation(self):
        messages = []
        for plan in self:
            if plan.equipment_id:
                equipment = plan.equipment_id
                equipment._create_new_request(plan)
                messages.append(f"Solicitud manual generada para el plan de mantenimiento ID: {plan.id} con equipo ID: {equipment.id}.")
            else:
                messages.append(f"No se pudo generar solicitud manual para el plan ID {plan.id} porque no tiene equipo asociado.")
        return messages

    def action_view_requests(self):
        """Abrir solicitudes vinculadas usando la vista Kanban personalizada."""
        action = None
        try:
            action = super().action_view_requests()
        except AttributeError:
            action = None

        if not action:
            try:
                action = self.env["ir.actions.actions"]._for_xml_id("maintenance.action_maintenance_request")
            except ValueError:
                action = self.env["ir.actions.actions"]._for_xml_id(
                    "maintenance_time_records.action_maintenance_request_kanban_technical"
                )

        if isinstance(action, dict):
            action_dict = action
        else:
            # Cuando se obtuvo un recordset de ir.actions.act_window
            action_dict = action.read()[0] if action else {}

        kanban_view = self.env.ref('maintenance_time_records.view_maintenance_kanban_technical', raise_if_not_found=False)
        if kanban_view:
            existing_views = action_dict.get('views') or []
            # Colocar el kanban personalizado como primera vista y preservar las demás sin duplicar kanban
            filtered_views = [(vid, vtype) for vid, vtype in existing_views if vtype != 'kanban']
            action_dict['views'] = [(kanban_view.id, 'kanban')] + filtered_views
            view_mode_parts = ['kanban'] + [vtype for _, vtype in filtered_views]
            action_dict['view_mode'] = ','.join(dict.fromkeys(view_mode_parts))  # quita duplicados conservando orden
            action_dict['view_id'] = kanban_view.id

        domain = [('maintenance_plan_id', 'in', self.ids)]
        action_dict['domain'] = domain

        context = action_dict.get('context', '{}')
        if isinstance(context, str):
            try:
                context = ast.literal_eval(context)
            except Exception:
                context = {}
        context.update({
            'default_maintenance_plan_id': self.ids[0] if len(self) == 1 else False,
            'search_default_maintenance_plan_id': self.ids[0] if len(self) == 1 else False,
        })
        action_dict['context'] = context
        return action_dict
