{
    'name': 'Maintenance Time Records',
    'version': '16.0.1.0.0',
    'summary': 'Registros de tiempos de mantenimiento basados en partes de horas',
    'category': 'Maintenance',
    'author': 'Noelia Rio',
    'license': 'LGPL-3',
    'depends': [
        'maintenance',
        'analytic',
        'maintenance_plan',
        'mass_mailing'
        #'maintenance_plan_activity'  
    ],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/maintenance_stage_data.xml',
        'data/maintenance_pause_cause_data.xml',
        'views/view_maintenance_plan_form.xml',
        'views/view_maintenance_request_form.xml',
        'views/view_maintenance_kanban_technical.xml',
        'views/maintenance_time_records_views.xml'
    ],
    'installable': True,
    'application': False,
}
