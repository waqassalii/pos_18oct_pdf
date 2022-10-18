# -*- coding: utf-8 -*-
# from odoo import http


# class CategoryTarget(http.Controller):
#     @http.route('/category_target/category_target/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/category_target/category_target/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('category_target.listing', {
#             'root': '/category_target/category_target',
#             'objects': http.request.env['category_target.category_target'].search([]),
#         })

#     @http.route('/category_target/category_target/objects/<model("category_target.category_target"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('category_target.object', {
#             'object': obj
#         })
