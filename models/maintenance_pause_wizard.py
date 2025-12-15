from odoo import models, fields


class MaintenancePauseWizard(models.TransientModel):
    _name = 'maintenance.pause.wizard'
    _description = 'Seleccionar causa de pausa'

    maintenance_request_id = fields.Many2one(
        'maintenance.request',
        string='Solicitud de mantenimiento',
        required=True
    )
    pause_cause_id = fields.Many2one(
        'maintenance.pause.cause',
        string='Causa de pausa',
        required=True
    )

    def action_confirm_pause(self):
        self.ensure_one()
        request = self.maintenance_request_id
        if not request:
            return {'type': 'ir.actions.act_window_close'}

        request._close_open_time_records()
        self.env['maintenance.time_records'].create({
            'maintenance_request_id': request.id,
            'time_type': 'pause',
            'pause_cause_id': self.pause_cause_id.id,
            'start_datetime': fields.Datetime.now(),
            'name': f"Pausa - {request.name or request.code or ''}",
        })
        request.time_state = 'pause'
        return {'type': 'ir.actions.act_window_close'}
