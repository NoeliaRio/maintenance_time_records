from odoo import models, fields


class MaintenanceRequestFinishConfirmation(models.TransientModel):
    _name = 'maintenance.request.finish.confirmation'
    _description = 'Confirmación para finalizar la solicitud de mantenimiento'

    def action_confirm_finish(self):
        maintenance_request = self.env['maintenance.request'].browse(self.env.context.get('active_id'))
        equipment = self.env['maintenance.equipment'].browse(self.env.context.get('equipment_id'))
        maintenance_plan = self.env['maintenance.plan'].browse(self.env.context.get('maintenance_plan_id'))
        if maintenance_request:
            stage_finished = self.env["maintenance.stage"].search([('name', '=', 'Finalizado')], limit=1)
            current_request_date = maintenance_request.schedule_date
            if stage_finished:
                maintenance_request.stage_id = stage_finished.id
                maintenance_request.check_date_time = fields.Datetime.now()
            equipment._create_next_request(maintenance_plan, current_request_date)
        return {'type': 'ir.actions.act_window_close'}

    def action_confirm_cancelled(self):
        maintenance_request = self.env['maintenance.request'].browse(self.env.context.get('active_id'))
        equipment = self.env['maintenance.equipment'].browse(self.env.context.get('equipment_id'))
        maintenance_plan = self.env['maintenance.plan'].browse(self.env.context.get('maintenance_plan_id'))
        if maintenance_request:
            stage_cancelled = self.env["maintenance.stage"].search([('name', '=', 'Cancelado')], limit=1)
            current_request_date = maintenance_request.schedule_date
            if stage_cancelled:
                maintenance_request.stage_id = stage_cancelled.id
                maintenance_request.cancellation_date_time = fields.Datetime.now()
            equipment._create_next_request(maintenance_plan, current_request_date)
        return {'type': 'ir.actions.act_window_close'}
