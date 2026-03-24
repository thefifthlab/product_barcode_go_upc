from odoo import api, fields, models
from odoo.exceptions import ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # ────────────────────────────────────────────────────────────────
    # Fields
    # ────────────────────────────────────────────────────────────────
    vendor_number = fields.Char(
        string="Vendor/Customer Number",  # fallback label (will be overridden by JS)
        copy=False,
        index=True,                       # important for performance & uniqueness check
        tracking=True,
        readonly=False,                   # allow manual edit in special cases
        # If you want it mostly readonly after creation, use:
        # states={'draft': [('readonly', False)]} but partners don't have state
    )

    # Optional: if you later decide to split customer_number and vendor_number
    # customer_number = fields.Char(string="Customer Number", copy=False, index=True)

    # Example unrelated field from your snippet (keep if needed)
    # barcode_line_ids = fields.One2many(
    #     'barcode.import.line', 'import_id', string="Barcode Lines"
    # )

    # ────────────────────────────────────────────────────────────────
    # SQL Constraints
    # ────────────────────────────────────────────────────────────────
    _sql_constraints = [
        (
            'vendor_number_unique',
            'UNIQUE(vendor_number)',
            'This Vendor/Customer Number is already used by another contact.'
        ),
    ]

    # ────────────────────────────────────────────────────────────────
    # Business Logic – Auto-generate vendor_number for suppliers
    # ────────────────────────────────────────────────────────────────
    @api.model_create_multi
    def create(self, vals_list):
        """
        Auto-assign vendor_number using sequence ONLY when creating a Vendor
        (supplier_rank > 0).
        """
        for vals in vals_list:
            # Only generate if no number provided AND it's marked as supplier
            if not vals.get('vendor_number') and vals.get('supplier_rank', 0) > 0:
                sequence = self.env['ir.sequence'].next_by_code('res.partner.vendor')
                vals['vendor_number'] = sequence or '/'

        return super(ResPartner, self).create(vals_list)

    def write(self, vals):
        """
        If someone turns a regular partner into a Vendor afterwards,
        assign a vendor_number if missing.
        """
        res = super(ResPartner, self).write(vals)

        # Only act if supplier_rank was modified and is now > 0
        if 'supplier_rank' in vals and vals['supplier_rank'] > 0:
            for partner in self:
                if not partner.vendor_number:
                    sequence = self.env['ir.sequence'].next_by_code('res.partner.vendor')
                    partner.vendor_number = sequence or '/'

        return res

    # ────────────────────────────────────────────────────────────────
    # Optional: Prevent duplicate numbers even across companies (if multi-company)
    # ────────────────────────────────────────────────────────────────
    @api.constrains('vendor_number')
    def _check_vendor_number_unique(self):
        for partner in self.filtered(lambda p: p.vendor_number):
            domain = [
                ('vendor_number', '=', partner.vendor_number),
                ('id', '!=', partner.id),
                # Optional: remove if you want global uniqueness even across companies
                # ('company_id', 'in', [False, partner.company_id.id]),
            ]
            if self.env['res.partner'].search_count(domain):
                raise ValidationError(
                    f"The number '{partner.vendor_number}' is already used "
                    f"by another contact."
                )

    # ────────────────────────────────────────────────────────────────
    # Important: Do NOT implement dynamic label here with _get_view
    # → Use JavaScript patch (as recommended earlier) for reactive label change
    # ────────────────────────────────────────────────────────────────