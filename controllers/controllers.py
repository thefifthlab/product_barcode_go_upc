# -*- coding: utf-8 -*-
# from odoo import http


# class ProductBarcodeGoUpc(http.Controller):
#     @http.route('/product_barcode_go_upc/product_barcode_go_upc', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/product_barcode_go_upc/product_barcode_go_upc/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('product_barcode_go_upc.listing', {
#             'root': '/product_barcode_go_upc/product_barcode_go_upc',
#             'objects': http.request.env['product_barcode_go_upc.product_barcode_go_upc'].search([]),
#         })

#     @http.route('/product_barcode_go_upc/product_barcode_go_upc/objects/<model("product_barcode_go_upc.product_barcode_go_upc"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('product_barcode_go_upc.object', {
#             'object': obj
#         })

