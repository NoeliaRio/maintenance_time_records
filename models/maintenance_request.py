from datetime import date, datetime, timedelta
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    code = fields.Char(string='Código', readonly=True, copy=False, default='/')
    hours_equipment_use = fields.Integer(string="Horas de uso del equipo")
    cancellation_date_time = fields.Datetime(string="Fecha y horario de cancelación")
    check_date_time = fields.Datetime(string="Fecha y horario de revisión")
    start_date = fields.Datetime(string="Fecha y horario de inicio de ejecución")
    end_date = fields.Datetime(string="Fecha y horario de fin de ejecución")
    issue_date = fields.Date(string="Fecha de emisión de la orden")
    date_limit = fields.Date(string="Fecha límite para ejecución")
    instruction_pdf = fields.Binary(related='maintenance_plan_id.instruction_pdf', readonly=True)
    note = fields.Text(string="Instrucciones", related='maintenance_plan_id.note')
    description = fields.Text(string="Notas")
    is_previous_month = fields.Boolean(
        compute='_compute_is_previous_month_and_current',
        store=True,
        default=False,
        string="Es del mes anterior"
    )
    is_current_month = fields.Boolean(
        compute='_compute_is_previous_month_and_current',
        store=True,
        default=False,
        string="Es del mes actual"
    )
    stage_id = fields.Many2one(
        'maintenance.stage',
        string="Etapa",
        group_expand='_read_group_stage_ids',
    )
    is_revision = fields.Boolean(
        string="¿En Revisión?",
        compute='_compute_is_revision',
        default=False,
        store=True)
    is_finish = fields.Boolean(
        string="¿Fin?",
        compute='_compute_is_finish',
        default=False,
        store=True)

    @api.depends('stage_id')
    def _compute_is_revision(self):
        for record in self:
            record.is_revision = record.stage_id.name == 'Revisión'

    @api.depends('stage_id')
    def _compute_is_finish(self):
        restricted_stages = ['Finalizado', 'Cancelado']
        for record in self:
            record.is_finish = record.stage_id.name in restricted_stages

    @api.model
    def create(self, vals):
        if vals.get('code', '/') == '/':
            vals['code'] = self.env['ir.sequence'].next_by_code('maintenance.request.default') or '/'
        return super(MaintenanceRequest, self).create(vals)

    @api.constrains("stage_id")
    def _check_stage_permissions(self):
        done = 'Finalizado'
        cancelled = 'Cancelado'
        stage_done = self.env['maintenance.stage'].search([('name', '=', done)], limit=1)
        stage_cancelled = self.env['maintenance.stage'].search([('name', '=', cancelled)], limit=1)
        for request in self:
            if request.stage_id in (stage_done, stage_cancelled):
                if not self.env.user.has_group('maintenance_time_records.group_maintenance_technical_admin'):
                    raise ValidationError(_("No tiene los permisos necesarios para esta acción."))

    def update_existing_request_names(self):
        requests = self.search([("name", "!=", False)])
        count = 0
        for request in requests:
            plan = request.maintenance_plan_id
            equipment = request.equipment_id
            if plan and equipment:
                frequency_name = equipment._get_frequency_name(plan.interval, plan.interval_step)
                request.name = f"{equipment.name} ({frequency_name})"
                count += 1
        return f"{count} registros de mantenimiento actualizados."

    def button_open_view_finish_custom(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.request.finish.confirmation',
            'view_mode': 'form',
            'view_id': self.env.ref('maintenance_time_records.view_maintenance_finish_confirmation_form').id,
            'target': 'new',
            'context': {
                'active_id': self.id,
                'equipment_id': self.equipment_id.id,
                'maintenance_plan_id': self.maintenance_plan_id.id,
                'allow_stage_change': True,
            },
        }

    def button_open_view_cancelled_custom(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.request.finish.confirmation',
            'view_mode': 'form',
            'view_id': self.env.ref('maintenance_time_records.view_maintenance_cancelled_confirmation_form').id,
            'target': 'new',
            'context': {
                'active_id': self.id,
                'equipment_id': self.equipment_id.id,
                'maintenance_plan_id': self.maintenance_plan_id.id,
                'allow_stage_change': True,
            },
        }

    def write(self, vals):
        if 'schedule_date' in vals or 'stage_id' in vals:
            self._compute_is_previous_month_and_current()

        if 'stage_id' in vals:
            for request in self:
                if request.is_finish:
                    raise ValidationError(
                        _("No se puede mover esta solicitud porque está en una etapa restringida: '%s'.")
                        % request.stage_id.name
                    )

            stage_done = self.env.ref('maintenance.stage_3', raise_if_not_found=False)
            stage_cancelled = self.env.ref('maintenance.stage_4', raise_if_not_found=False)
            restricted_xmlids = {'maintenance.stage_3', 'maintenance.stage_4'}
            new_stage = self.env['maintenance.stage'].browse(vals['stage_id'])
            if not new_stage.exists():
                raise ValidationError("La etapa especificada no existe.")

            restricted_stage_ids = {stage.id for stage in (stage_done, stage_cancelled) if stage}
            restricted_stage_names = ['Finalizado', 'Cancelado', 'Done', 'Cancelled', 'Reparado', 'Desechar']

            is_restricted = (
                new_stage.id in restricted_stage_ids
                or new_stage.get_external_id().get(new_stage.id) in restricted_xmlids
                or new_stage.name in restricted_stage_names
            )

            if is_restricted and not self.env.context.get('allow_stage_change'):
                raise ValidationError(
                    "No se puede mover esta solicitud al estado '%s' desde el tablero Kanban. "
                    "Por favor, utilice el botón correspondiente." % new_stage.name
                )
            self = self.sudo()
            self.activity_update()

        return super(MaintenanceRequest, self).write(vals)

    @api.depends('schedule_date', 'stage_id.name')
    def _compute_is_previous_month_and_current(self):
        today = fields.Date.today()
        first_day_of_current_month = today.replace(day=1)
        first_day_of_previous_month = (first_day_of_current_month - timedelta(days=1)).replace(day=1)
        last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
        last_day_of_current_month = (first_day_of_current_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        valid_stages = ['new request', 'nueva solicitud', 'in progress', 'en progreso']

        for record in self:
            if record.schedule_date:
                schedule_date_as_date = (
                    record.schedule_date.date() if isinstance(record.schedule_date, datetime) else record.schedule_date
                )
                stage_name = record.stage_id.name.strip().lower() if record.stage_id and record.stage_id.name else ''
                if first_day_of_previous_month <= schedule_date_as_date <= last_day_of_previous_month:
                    record.is_previous_month = stage_name in valid_stages
                else:
                    record.is_previous_month = False
                if first_day_of_current_month <= schedule_date_as_date <= last_day_of_current_month:
                    record.is_current_month = True
                else:
                    record.is_current_month = False
            else:
                record.is_previous_month = False
                record.is_current_month = False

    def _recalculate_is_previous_and_current_month(self):
        all_requests = self.search([])
        all_requests._compute_is_previous_month_and_current()
        return True
