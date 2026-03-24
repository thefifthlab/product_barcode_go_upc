from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    go_upc_api_key = fields.Char(
        string="GO-UPC API Key",
        config_parameter='product_barcode_go_upc.api_key'
    )
    go_upc_timeout = fields.Integer(
        string="API Timeout (Seconds)",
        config_parameter='product_barcode_go_upc.timeout',
        default=15
    )