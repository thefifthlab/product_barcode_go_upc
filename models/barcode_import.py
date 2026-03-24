from odoo import api, fields, models, _
from odoo.exceptions import UserError
import requests
import base64
import logging

_logger = logging.getLogger(__name__)


class BarcodeImport(models.Model):
    _name = 'barcode.import'
    _description = 'Bulk Barcode Import'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, create_date desc'

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(
        string="Reference",
        required=True,
        default="New",
        copy=False,
        tracking=True,
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('processed', 'Processed'),
        ],
        string="Status",
        default='draft',
        required=True,
        tracking=True,
    )
    line_ids = fields.One2many(
        comodel_name='barcode.import.line',
        inverse_name='import_id',
        string="Barcodes to Process",
    )
    success_count = fields.Integer(
        string="Success",
        compute='_compute_counts',
        store=True,
    )
    not_found_count = fields.Integer(
        string="Not Found",
        compute='_compute_counts',
        store=True,
    )
    error_count = fields.Integer(
        string="Errors",
        compute='_compute_counts',
        store=True,
    )
    error_log = fields.Text(
        string="Full Error Log",
        readonly=True,
    )

    @api.depends('line_ids.status')
    def _compute_counts(self):
        for record in self:
            statuses = record.line_ids.mapped('status')
            record.success_count = statuses.count('success')
            record.not_found_count = statuses.count('not_found')
            record.error_count = statuses.count('error')

    def action_process_bulk(self):
        self.ensure_one()
        if self.state == 'processed':
            raise UserError(_("This import has already been processed."))

        successes = 0
        not_found = 0
        errors = []

        for line in self.line_ids.filtered(lambda l: l.status in ('pending', 'not_found', 'error')):
            try:
                product = self._find_or_create_product_from_barcode(line.barcode)
                if product:
                    line.write({
                        'product_id': product.id,
                        'status': 'success',
                        'message': _('Product found or created successfully'),
                    })
                    successes += 1
                else:
                    line.write({
                        'status': 'not_found',
                        'message': _('No product data found in Barcode Lookup API'),
                    })
                    not_found += 1
            except Exception as e:
                error_msg = str(e)[:500]
                line.write({
                    'status': 'error',
                    'message': error_msg,
                })
                errors.append(f"Barcode {line.barcode}: {error_msg}")

        self.state = 'processed'

        # Build user-friendly notification
        message = (
            f"Processed {len(self.line_ids)} barcodes.\n"
            f"→ {successes} created/found successfully\n"
            f"→ {not_found} not found in Barcode Lookup\n"
        )
        if errors:
            message += f"→ {len(errors)} errors occurred.\n\n"
            message += "\n".join(errors[:15])  # Show first 15
            if len(errors) > 15:
                message += f"\n... and {len(errors) - 15} more errors."

        # Save full log in case many errors
        if errors:
            self.error_log = "\n".join(errors)

        # Post summary to chatter
        self.message_post(body=message, message_type='notification')

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Bulk Import Finished'),
                'message': message,
                'type': 'success' if not errors else 'warning',
                'sticky': bool(errors),
            }
        }

    def action_retry_failed(self):
        """Reset failed/pending lines and allow re-processing"""
        self.ensure_one()
        if self.state == 'processed':
            self.state = 'draft'
        self.line_ids.filtered(lambda l: l.status in ('not_found', 'error')).write({
            'status': 'pending',
            'message': False,
            'product_id': False,
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _find_or_create_product_from_barcode(self, barcode):
        """Search for existing product or create new one from Barcode Lookup API"""
        product = self.env['product.product'].search([('barcode', '=', barcode)], limit=1)
        if product:
            return product

        data = self._fetch_barcode_lookup_data(barcode)
        if not data:
            return False

        vals = {
            'name': data.get('product_name') or f"Unknown Product - {barcode}",
            'type': 'product',
            'barcode': barcode,
            'default_code': data.get('mpn') or data.get('sku') or barcode,
            'list_price': float(data.get('pricing', {}).get('retail') or 0.0),
            'standard_price': float(data.get('pricing', {}).get('cost') or 0.0),
            'description_sale': data.get('description', ''),
            'categ_id': self.env.ref('product.product_category_all', raise_if_not_found=False).id or False,
        }

        # Optional: Try to match category (very basic – improve later if needed)
        if data.get('category'):
            try:
                cat_path = data['category'].strip()
                cat_name = cat_path.split(' > ')[-1].strip() if ' > ' in cat_path else cat_path
                category = self.env['product.category'].search([('name', '=ilike', cat_name)], limit=1)
                if category:
                    vals['categ_id'] = category.id
            except Exception:
                pass

        # Try to attach first product image (with safety checks)
        images = data.get('images', [])
        if images:
            try:
                img = images[0]
                image_url = img if isinstance(img, str) else (img.get('src') or img.get('url'))
                if image_url and image_url.startswith(('http://', 'https://')):
                    response = requests.get(image_url, timeout=6, stream=True)
                    if response.status_code == 200:
                        content_type = response.headers.get('Content-Type', '')
                        content_length = int(response.headers.get('Content-Length', 0))
                        if 'image' in content_type.lower() and content_length < 6_000_000:  # < ~6MB
                            vals['image_1920'] = base64.b64encode(response.content)
            except Exception as img_err:
                _logger.warning(f"Failed to download image for barcode {barcode}: {img_err}")

        return self.env['product.product'].sudo().create(vals)

    def _fetch_barcode_lookup_data(self, barcode):
        api_key = self.env['ir.config_parameter'].sudo().get_param('barcode.barcode_lookup_api_key')
        if not api_key:
            raise UserError(
                _("Barcode Lookup API key is not configured.\n"
                  "Please go to Settings → Technical → System Parameters "
                  "and set 'barcode.barcode_lookup_api_key'.")
            )

        url = f"https://api.barcodelookup.com/v3/products/?barcode={barcode}&key={api_key}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            products = data.get('products', [])
            if products:
                return products[0]
            return False
        except requests.exceptions.RequestException as e:
            raise UserError(_(f"Barcode Lookup API connection failed: {str(e)}"))
        except ValueError:
            raise UserError(_("Invalid JSON response from Barcode Lookup API"))


class BarcodeImportLine(models.Model):
    _name = 'barcode.import.line'
    _description = 'Barcode Import Line'
    _order = 'sequence asc, id desc'

    import_id = fields.Many2one(
        'barcode.import',
        string="Import",
        required=True,
        ondelete='cascade',
    )
    sequence = fields.Integer(
        string="Sequence",
        default=10,
        index=True,
    )
    barcode = fields.Char(
        string="Barcode",
        required=True,
    )
    product_id = fields.Many2one(
        'product.product',
        string="Product",
        readonly=True,
    )
    status = fields.Selection(
        [
            ('pending', 'Pending'),
            ('success', 'Success'),
            ('not_found', 'Not Found'),
            ('error', 'Error'),
        ],
        string="Status",
        default='pending',
        readonly=True,
    )
    message = fields.Char(
        string="Message",
        readonly=True,
    )