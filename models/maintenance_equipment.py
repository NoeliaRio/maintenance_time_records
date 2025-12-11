from odoo import models, fields, api
import qrcode
import base64
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    qr_code_image = fields.Binary(string="QR Code", attachment=True, readonly=True)
    reception_date = fields.Date(string="Fecha de recepción")
    warranty_expiration_date = fields.Date(string="Fecha de vencimiento de garantía")
    manual_pdf = fields.Binary(string="Manual PDF (Editable)", help="Cargar el PDF del manual de mantenimiento.", store=True)
    manual_pdf_view = fields.Binary(
        string="Manual PDF",
        compute="_compute_manual_pdf_view",
        store=True
    )
    status = fields.Selection(
        [('aprobado', 'Aprobado'), ('desaprobado', 'Desaprobado')],
        string='Estado Aprobación',
        compute='_compute_status',
        store=True
    )

    def recalc_equipment_computed_fields(self):
        equipments = self.search([])

        for eq in equipments:
            eq._compute_status()

        return True

    @api.depends("manual_pdf")
    def _compute_manual_pdf_view(self):
        for record in self:
            record.manual_pdf_view = record.manual_pdf

    def _create_new_request(self, mtn_plan):
        horizon_date = fields.Date.today() + mtn_plan.get_relativedelta(
            mtn_plan.maintenance_plan_horizon, mtn_plan.planning_step or "year"
        )
        start_maintenance_date_plan = mtn_plan.start_maintenance_date
        furthest_maintenance_request = self.env["maintenance.request"].search(
            [
                ("maintenance_plan_id", "=", mtn_plan.id),
                ("request_date", ">=", start_maintenance_date_plan),
            ],
            order="request_date desc",
            limit=1,
        )
        if furthest_maintenance_request:
            next_maintenance_date = (
                furthest_maintenance_request.request_date
                + mtn_plan.get_relativedelta(
                    mtn_plan.interval, mtn_plan.interval_step or "year"
                )
            )
        else:
            next_maintenance_date = mtn_plan.next_maintenance_date

        skip_notify_follower = mtn_plan.skip_notify_follower_on_requests
        request_model = self.env["maintenance.request"].with_context(
            mail_activity_quick_update=skip_notify_follower,
            mail_auto_subscribe_no_notify=skip_notify_follower,
        )
        requests = request_model

        while next_maintenance_date <= horizon_date:
            if next_maintenance_date >= fields.Date.today():
                equipment_name = self.name or "Equipo"
                frequency_name = self._get_frequency_name(mtn_plan.interval, mtn_plan.interval_step)
                request_name = f"{equipment_name} ({frequency_name})"

                vals = self._prepare_requests_from_plan(mtn_plan, next_maintenance_date)
                vals.update({
                    'maintenance_plan_id': mtn_plan.id,
                    'name': request_name
                })
                _logger.debug(
                    "Creando solicitud con maintenance_plan_id: %s para la fecha: %s y nombre: %s",
                    mtn_plan.id, next_maintenance_date, request_name
                )
                requests |= request_model.create(vals)

            next_maintenance_date = next_maintenance_date + mtn_plan.get_relativedelta(
                mtn_plan.interval, mtn_plan.interval_step or "year"
            )

        return requests

    @api.depends('maintenance_ids.stage_id', 'maintenance_ids.request_date', 'maintenance_ids.maintenance_type', 'maintenance_plan_ids')
    def _compute_status(self):
        for equipment in self:
            open_corrective_request = equipment.maintenance_ids.filtered(
                lambda r: r.maintenance_type == 'corrective' and r.stage_id.name in ['Nueva solicitud', 'En progreso', 'Revisión']
            )
            if open_corrective_request:
                equipment.status = 'desaprobado'

            elif not equipment.maintenance_plan_ids:
                equipment.status = 'aprobado'

            else:
                previous_requests = equipment.maintenance_ids.filtered(
                    lambda r: r.request_date and r.request_date < fields.Date.today()
                ).sorted(key='request_date', reverse=True)

                if previous_requests:
                    last_request = previous_requests[0]
                    if last_request.stage_id and last_request.stage_id.name in ['Reparado', 'Finalizado', 'Done']:
                        equipment.status = 'aprobado'
                    else:
                        equipment.status = 'desaprobado'

    def generate_qr_code(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            qr_url = f'{base_url}/web#id={record.id}&model=maintenance.equipment&view_type=form'
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_url)
            qr.make(fit=True)

            img = qr.make_image(fill='black', back_color='white')
            img = img.convert('RGB')
            qr_width, qr_height = img.size

            draw = ImageDraw.Draw(img)
            text = record.name

            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)

            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]

            final_width = max(qr_width, text_width)

            new_height = qr_height + text_height + 20
            new_img = Image.new('RGB', (final_width, new_height), 'white')

            qr_position = ((final_width - qr_width) // 2, 0)
            new_img.paste(img, qr_position)

            text_position = ((final_width - text_width) // 2, qr_height + 10)
            draw = ImageDraw.Draw(new_img)
            draw.text(text_position, text, fill='black', font=font)

            buffer = BytesIO()
            new_img.save(buffer, format="PNG")
            img_str = base64.b64encode(buffer.getvalue())
            record.qr_code_image = img_str

    def action_generate_qr_code(self):
        self.generate_qr_code()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'maintenance.equipment',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'self',
        }

    def _get_frequency_name(self, interval, interval_step):
        frequency_descriptions = {
            1: "Mensual",
            2: "Bimensual",
            3: "Trimensual",
            4: "Cuatrimensual",
            6: "Semestral",
            12: "Anual"
            }
        if interval_step == "month":
            return frequency_descriptions.get(interval, f"{interval} meses")
        return f"{interval} {interval_step}"

    def _create_next_request(self, mtn_plan, current_request_date):
        for equipment in self:
            if not mtn_plan.next_maintenance_date:
                raise ValueError("La fecha de mantenimiento no está definida correctamente.")

            if mtn_plan.interval and mtn_plan.interval > 0:
                next_maintenance_date = current_request_date + relativedelta(months=mtn_plan.interval)
            else:
                raise ValueError("El intervalo de mantenimiento no es válido.")

            equipment_name = equipment.name or "Equipo"
            frequency_name = self._get_frequency_name(mtn_plan.interval, mtn_plan.interval_step)
            request_name = f"{equipment_name} ({frequency_name})"

            vals = {
                'maintenance_plan_id': mtn_plan.id,
                'name': request_name,
                'request_date': next_maintenance_date,
                'schedule_date': next_maintenance_date,
                'maintenance_type': 'preventive',
                'equipment_id': equipment.id,
                'user_id': equipment.technician_user_id.id if equipment.technician_user_id else False
            }

            self.env['maintenance.request'].create(vals)

            mtn_plan.next_maintenance_date = next_maintenance_date
            mtn_plan.start_maintenance_date = next_maintenance_date

        return True
