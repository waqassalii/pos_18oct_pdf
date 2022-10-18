# -*- coding: utf-8 -*-
# from odoo import http


# class PosFbrInvoice(http.Controller):
#     @http.route('/pos_fbr_invoice/pos_fbr_invoice/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/pos_fbr_invoice/pos_fbr_invoice/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('pos_fbr_invoice.listing', {
#             'root': '/pos_fbr_invoice/pos_fbr_invoice',
#             'objects': http.request.env['pos_fbr_invoice.pos_fbr_invoice'].search([]),
#         })

#     @http.route('/pos_fbr_invoice/pos_fbr_invoice/objects/<model("pos_fbr_invoice.pos_fbr_invoice"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('pos_fbr_invoice.object', {
#             'object': obj
#         })
