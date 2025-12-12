from odoo import models, fields


class MaintenancePauseCause(models.Model):
    _name = 'maintenance.pause.cause'
    _description = 'Causa de pausa en mantenimiento'

    name = fields.Char(string='Causa de la pausa', required=True)
    description = fields.Text(string='Descripción')
    active = fields.Boolean(string="Activo", default=True)

    def toggle_active(self):
        for record in self:
            record.active = not record.active
