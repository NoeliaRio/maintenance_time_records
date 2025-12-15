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
    issue_date = fields.Datetime(
        string="Fecha de emisión de la orden",
        readonly=True,
        default=lambda self: fields.Datetime.now()
    )
    date_limit = fields.Date(
        string="Fecha límite para ejecución",
        compute="_compute_date_limit",
        store=True
    )
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
    time_record_ids = fields.One2many(
        'maintenance.time_records',
        'maintenance_request_id',
        string="Registros de tiempo"
    )
    time_state = fields.Selection(
        [
            ('idle', 'Idle'),
            ('active', 'Active'),
            ('pause', 'Pause'),
            ('done', 'Done')
        ],
        string='Timer State',
        default='idle'
    )
    total_active_duration_hours = fields.Float(
        string='Tiempo activo (horas)',
        compute='_compute_total_active_duration',
        store=True
    )
    total_active_duration_display = fields.Char(
        string='Tiempo activo',
        compute='_compute_total_active_duration',
        store=False
    )
    is_stage_repair_or_scrap = fields.Boolean(
        string='¿Reparado o Desechar?',
        compute='_compute_is_stage_repair_or_scrap',
        store=False
    )

    @api.depends('stage_id')
    def _compute_is_revision(self):
        for record in self:
            record.is_revision = record.stage_id.name == 'Revisión'

    @api.depends('stage_id')
    def _compute_is_finish(self):
        restricted_stages = ['Finalizado', 'Cancelado']
        for record in self:
            record.is_finish = record.stage_id.name in restricted_stages

    @api.depends('stage_id')
    def _compute_is_stage_repair_or_scrap(self):
        stage_repaired = self.env.ref('maintenance.stage_3', raise_if_not_found=False)
        stage_scrap = self.env.ref('maintenance.stage_4', raise_if_not_found=False)
        target_ids = {s.id for s in (stage_repaired, stage_scrap) if s}
        for record in self:
            record.is_stage_repair_or_scrap = record.stage_id.id in target_ids

    @api.model
    def create(self, vals):
        if vals.get('code', '/') == '/':
            vals['code'] = self.env['ir.sequence'].next_by_code('maintenance.request.default') or '/'
        vals.setdefault('issue_date', fields.Datetime.now())
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
        self._ensure_not_final_stage_for_cancel()
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

    def _ensure_not_final_stage_for_cancel(self):
        final_stage_xmlids = ['maintenance.stage_3', 'maintenance.stage_4']
        final_stage_ids = []
        for xmlid in final_stage_xmlids:
            stage = self.env.ref(xmlid, raise_if_not_found=False)
            if stage:
                final_stage_ids.append(stage.id)
        for request in self:
            if final_stage_ids and request.stage_id.id in final_stage_ids:
                raise ValidationError(
                    _("No se puede cancelar una orden que ya está en una etapa final: '%s'.")
                    % request.stage_id.display_name
                )

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
            stage_repaired = self.env.ref('maintenance.stage_3', raise_if_not_found=False)
            stage_scrap = self.env.ref('maintenance.stage_4', raise_if_not_found=False)
            if stage_repaired and new_stage.id == stage_repaired.id:
                vals.setdefault('check_date_time', fields.Datetime.now())
            if stage_scrap and new_stage.id == stage_scrap.id:
                vals.setdefault('cancellation_date_time', fields.Datetime.now())

        return super(MaintenanceRequest, self).write(vals)

    @api.depends('schedule_date')
    def _compute_date_limit(self):
        for request in self:
            request.date_limit = False
            if request.schedule_date:
                sched_date = request.schedule_date
                sched_as_date = sched_date.date() if isinstance(sched_date, datetime) else sched_date
                first_of_next_month = (sched_as_date.replace(day=28) + timedelta(days=4)).replace(day=1)
                last_day = first_of_next_month - timedelta(days=1)
                request.date_limit = last_day

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

    def _close_open_time_records(self):
        """Cerrar cualquier registro de tiempo sin fin asociado a la solicitud."""
        now = fields.Datetime.now()
        for request in self:
            open_records = request.time_record_ids.filtered(lambda r: not r.end_datetime)
            if open_records:
                open_records.write({'end_datetime': now})

    def action_start_time(self):
        self.ensure_one()
        now = fields.Datetime.now()
        self._close_open_time_records()
        stage_in_progress = self.env.ref('maintenance.stage_1', raise_if_not_found=False)
        self.env['maintenance.time_records'].create({
            'maintenance_request_id': self.id,
            'time_type': 'active',
            'start_datetime': now,
            'name': f"Tiempo activo - {self.name or self.code or ''}",
        })
        if not self.start_date:
            self.start_date = now
        self.time_state = 'active'
        if stage_in_progress and self.stage_id != stage_in_progress:
            self.stage_id = stage_in_progress.id

    def action_finish_time(self):
        self.ensure_one()
        self._close_open_time_records()
        now = fields.Datetime.now()
        if not self.end_date:
            self.end_date = now
        self.time_state = 'done'
        stage_revision = self.env.ref('maintenance_time_records.maintenance_stage_revision', raise_if_not_found=False)
        if stage_revision and self.stage_id != stage_revision:
            # allow changing to revision when finishing time tracking
            self.with_context(allow_stage_change=True).stage_id = stage_revision.id

    def action_continue_time(self):
        self.ensure_one()
        now = fields.Datetime.now()
        self._close_open_time_records()
        self.env['maintenance.time_records'].create({
            'maintenance_request_id': self.id,
            'time_type': 'active',
            'start_datetime': now,
            'name': f"Tiempo activo - {self.name or self.code or ''}",
        })
        self.time_state = 'active'

    def action_pause_time(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.pause.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_maintenance_request_id': self.id,
            },
        }

    @api.depends('time_record_ids.time_type', 'time_record_ids.start_datetime', 'time_record_ids.end_datetime')
    def _compute_total_active_duration(self):
        for request in self:
            total_seconds = 0
            active_records = request.time_record_ids.filtered(lambda r: r.time_type == 'active')
            for rec in active_records:
                if rec.start_datetime:
                    end_time = rec.end_datetime or fields.Datetime.now()
                    delta_seconds = max((end_time - rec.start_datetime).total_seconds(), 0)
                    total_seconds += delta_seconds
            hours = int(total_seconds // 3600)
            minutes = int((total_seconds % 3600) // 60)
            seconds = int(total_seconds % 60)
            hours_float = total_seconds / 3600.0 if total_seconds else 0.0
            request.total_active_duration_hours = round(hours_float, 2)
            request.duration = round(hours_float, 2)
            # Mostrar hh:mm:ss
            request.total_active_duration_display = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
