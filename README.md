# Maintenance Time Records (Odoo 16)
Módulo de  Odoo para registrar tiempo en Mantenimiento

## Requisitos
- Odoo 16
- Dependencias: `maintenance`, `analytic`, `maintenance_plan`, `mass_mailing`

## Instalación
1. Copiar el módulo a la carpeta de addons.
2. Actualizar la lista de apps.
3. Instalar o actualizar con `-u maintenance_time_records`.

## Funcionalidades clave
- Bloqueo de cancelación en etapas finales (Reparado/Desechar) y botón de cancelar oculto en esas etapas.
- Cálculo de `duration` y horas activas a partir de registros de tiempo tipo “active”.
- Fechas automáticas: `issue_date` al crear la solicitud y `date_limit` como último día del mes de `schedule_date`.
- Vista Kanban técnica personalizada; el smart button desde el plan abre esta vista filtrada por plan.
- Gestión de tiempos: iniciar/pausar/continuar/finalizar, con wizard de pausa y duración mostrada en hh:mm:ss.
- Ícono personalizado en `static/description/icon.png`.

## Permisos
- `group_maintenance_technical_admin`: edición completa (incluye secciones duplicadas para edición).
- `maintenance.group_equipment_manager`: acceso de lectura en secciones duplicadas (Otros datos y Registros de tiempo).

## Uso rápido
- Desde una solicitud: usar los botones Inicio/Pausa/Continuar/Finalizar tiempo para generar registros; `duration` se actualiza con tiempos activos.
- `date_limit` se rellena automáticamente al cambiar `schedule_date`.
- En etapas Reparado/Desechar, no se puede cancelar y el botón se oculta.
- Desde un plan de mantenimiento, el botón de mantenimiento abre la Kanban técnica personalizada filtrada por ese plan.

## Notas de prueba
- Tras actualizar: `-u maintenance_time_records`.
- Verificar que `date_limit` se calcula al ajustar `schedule_date`.
- Probar visibilidad de botones y bloqueo de cancelación en etapas finales.
- Confirmar que la Kanban abre la vista personalizada desde el smart button del plan.
