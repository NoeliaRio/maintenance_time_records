{
    'name': 'Maintenance Time Records',
    'version': '16.0.1.0.0',
    'summary': 'Registros de tiempos de mantenimiento basados en partes de horas',
    'category': 'Maintenance',
    'author': 'Noelia Rio',
    'license': 'LGPL-3',
    'depends': [
        'maintenance',              
        'maintenance_plan',
        'mrp',
        'hr_timesheet_activity',
        'mass_mailing'
        #'maintenance_plan_activity'  
    ],
    'data': [
        'security/groups.xml',
        'views/view_maintenance_plan_form.xml'
    ],
    'installable': True,
    'application': False,
}
