{
    'name': 'GO-UPC Barcode Product Lookup',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Create products automatically by scanning barcodes using GO-UPC API',
    'depends': ['base', 'stock', 'product','purchase'],

    'data': [
        'security/ir.model.access.csv',
        'wizard/barcode_lookup_wizard_views.xml',
        'views/res_config_settings_views.xml',
        # 'views/barcode_import_views.xml',
        'data/ir_config_parameter.xml',
        'views/res_partner_views.xml',
        'data/sequences.xml',

    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}