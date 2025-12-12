from odoo import models, fields
from odoo.exceptions import ValidationError


class MaintenanceRequestFinishConfirmation(models.TransientModel):
    _name = 'maintenance.request.finish.confirmation'
    _description = 'Confirmación para finalizar la solicitud de mantenimiento'

    def action_confirm_finish(self):
        maintenance_request = self.env['maintenance.request'].browse(self.env.context.get('active_id'))
        equipment = self.env['maintenance.equipment'].browse(self.env.context.get('equipment_id'))
        maintenance_plan = self.env['maintenance.plan'].browse(self.env.context.get('maintenance_plan_id'))
        if maintenance_request:
            stage_finished = self.env.ref('maintenance.stage_3', raise_if_not_found=False)
            if not stage_finished:
                stage_finished = self.env["maintenance.stage"].search(
                    ['|', '|', ('name', '=', 'Finalizado'), ('name', '=', 'Done'), ('name', '=', 'Reparado')],
                    limit=1
                )
            if not stage_finished:
                raise ValidationError("No se encontró la etapa 'Finalizado/Reparado/Done'. Revise la configuración de etapas.")

            current_request_date = maintenance_request.schedule_date
            maintenance_request.stage_id = stage_finished.id
            maintenance_request.check_date_time = fields.Datetime.now()

            if maintenance_plan:
                equipment._create_next_request(maintenance_plan, current_request_date)
        return {'type': 'ir.actions.act_window_close'}

    def action_confirm_cancelled(self):
        maintenance_request = self.env['maintenance.request'].browse(self.env.context.get('active_id'))
        equipment = self.env['maintenance.equipment'].browse(self.env.context.get('equipment_id'))
        maintenance_plan = self.env['maintenance.plan'].browse(self.env.context.get('maintenance_plan_id'))
        if maintenance_request:
            stage_cancelled = self.env.ref('maintenance.stage_4', raise_if_not_found=False)
            if not stage_cancelled:
                stage_cancelled = self.env["maintenance.stage"].search(
                    ['|', '|', ('name', '=', 'Cancelado'), ('name', '=', 'Cancelled'), ('name', '=', 'Desechar')],
                    limit=1
                )
            if not stage_cancelled:
                raise ValidationError("No se encontró la etapa 'Cancelado/Desechar/Cancelled'. Revise la configuración de etapas.")

            current_request_date = maintenance_request.schedule_date
            maintenance_request.stage_id = stage_cancelled.id
            maintenance_request.cancellation_date_time = fields.Datetime.now()

            if maintenance_plan:
                equipment._create_next_request(maintenance_plan, current_request_date)
        return {'type': 'ir.actions.act_window_close'}
