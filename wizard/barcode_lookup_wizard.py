import base64
import requests
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class BarcodeLookupWizard(models.TransientModel):
    _name = 'barcode.lookup.wizard'
    _description = 'GO-UPC Barcode Lookup'

    barcode = fields.Char(string="Barcode", required=True)
    product_name = fields.Char(string="Product Name")
    description_sale = fields.Text(string="Description")
    image_1920_preview = fields.Binary(string="Image")
    categ_name = fields.Char(string="Category")
    brand_name = fields.Char(string="Brand")
    found = fields.Boolean(default=False)

    def action_lookup_barcode(self):
        self.ensure_one()
        params = self.env['ir.config_parameter'].sudo()
        api_key = params.get_param('product_barcode_go_upc.api_key')
        timeout = int(params.get_param('product_barcode_go_upc.timeout', 15))

        if not api_key:
            raise UserError(_("Please configure your GO-UPC API Key in Inventory Settings."))

        url = f"https://go-upc.com/api/v1/code/{self.barcode}"
        headers = {"Authorization": f"Bearer {api_key}"}

        try:
            res = requests.get(url, headers=headers, timeout=timeout)
            if res.status_code == 404:
                self.found = False
                return {'warning': {'title': _("Not Found"), 'message': _("No product found for this barcode.")}}

            res.raise_for_status()
            data = res.json().get('product', {})

            self.write({
                'product_name': data.get('name'),
                'description_sale': data.get('description'),
                'brand_name': data.get('brand'),
                'categ_name': data.get('category'),
                'found': True,
            })

            if data.get('imageUrl'):
                img_res = requests.get(data['imageUrl'], timeout=10)
                if img_res.ok:
                    self.image_1920_preview = base64.b64encode(img_res.content)

        except Exception as e:
            raise UserError(_("Error connecting to GO-UPC: %s") % str(e))

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_create_product(self):
        self.ensure_one()
        if not self.found:
            raise ValidationError(_("Perform a search first."))

        # Check if product exists already
        existing = self.env['product.product'].search([('barcode', '=', self.barcode)], limit=1)
        if existing:
            raise ValidationError(_("A product with this barcode already exists: %s") % existing.display_name)

        # Handle Category
        categ = self.env['product.category'].search([('name', '=ilike', self.categ_name)], limit=1)
        if not categ and self.categ_name:
            categ = self.env['product.category'].create({'name': self.categ_name})

        product = self.env['product.product'].create({
            'name': self.product_name,
            'barcode': self.barcode,
            'description_sale': self.description_sale,
            'image_1920': self.image_1920_preview,
            'categ_id': categ.id if categ else self.env.ref('product.product_category_all').id,
            'type': 'consu',  # Default to consumable/storable as needed
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'view_mode': 'form',
            'res_id': product.id,
            'target': 'current',
        }