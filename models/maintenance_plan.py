from odoo import models, fields, api
import logging

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
