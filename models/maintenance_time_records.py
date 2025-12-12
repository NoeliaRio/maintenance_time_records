from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MaintenanceTimeRecord(models.Model):
    _name = 'maintenance.time_records'
    _inherit = 'account.analytic.line'
    _description = 'Registro de tiempo de mantenimiento'
    _order = 'start_datetime desc'

    maintenance_request_id = fields.Many2one(
        'maintenance.request',
        string="Solicitud de mantenimiento",
        required=True,
        ondelete='cascade'
    )
    time_type = fields.Selection(
        [
            ('active', 'Activo'),
            ('pause', 'Pausa'),
        ],
        string='Tipo',
        default='active',
        required=True
    )
    pause_cause_id = fields.Many2one(
        'maintenance.pause.cause',
        string='Causa de la pausa'
    )
    start_datetime = fields.Datetime(
        string='Inicio',
        required=True,
        default=fields.Datetime.now
    )
    end_datetime = fields.Datetime(string='Fin')
    duration_hours = fields.Float(
        string='Duración (horas)',
        compute='_compute_duration',
        store=True
    )
    duration_display = fields.Char(
        string='Duración (mm:ss)',
        compute='_compute_duration',
        store=True
    )
    description = fields.Text(string='Descripción')
    company_id = fields.Many2one(
        'res.company',
        string='Compañía',
        default=lambda self: self.env.company,
        required=True
    )
    name = fields.Char(
        string="Descripción",
        default="Registro de tiempo",
        required=True
    )
    account_id = fields.Many2one(
        'account.analytic.account',
        string="Cuenta analítica",
        default=lambda self: self._get_default_analytic_account(),
        required=True
    )
    date = fields.Date(
        default=lambda self: fields.Date.context_today(self)
    )

    @api.model
    def _get_default_analytic_account(self):
        default_account = self.env['account.analytic.account'].search([], limit=1)
        if not default_account:
            raise ValidationError(_("No hay una cuenta analítica disponible para registrar tiempos."))
        return default_account

    @api.depends('start_datetime', 'end_datetime')
    def _compute_duration(self):
        for record in self:
            record.duration_hours = 0.0
            record.duration_display = "00:00"
            record.unit_amount = 0.0
            if record.start_datetime:
                end_time = record.end_datetime or fields.Datetime.now()
                delta = end_time - record.start_datetime
                total_seconds = max(delta.total_seconds(), 0)
                duration_hours = round(total_seconds / 3600.0, 2)
                record.duration_hours = duration_hours
                record.unit_amount = duration_hours
                minutes = int(total_seconds // 60)
                seconds = int(total_seconds % 60)
                record.duration_display = f"{minutes:02d}:{seconds:02d}"

    @api.constrains('start_datetime', 'end_datetime')
    def _check_dates(self):
        for record in self:
            if record.start_datetime and record.end_datetime and record.end_datetime < record.start_datetime:
                raise ValidationError("La fecha de fin debe ser posterior a la fecha de inicio.")

    @api.constrains('time_type', 'pause_cause_id')
    def _check_pause_cause(self):
        for record in self:
            if record.time_type == 'pause' and not record.pause_cause_id:
                raise ValidationError("Debe indicar una causa cuando el registro es de tipo pausa.")
