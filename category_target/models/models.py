# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def unlink(self):
        print('im unlink function')
        payment = self.env['pos.payment'].search([])
        for pay in payment:
            pay.unlink()
        for rec in self:
            rec.write({'state': 'draft'})
        return super(PosOrder, self).unlink()


class CategoryTarget(models.Model):
    _name = 'category.target'
    _description = 'category_target.category_target'

    # category_id = fields.Many2one('product.category', string='Category')
    category_id = fields.Many2one('pos.category', string='Category')
    value = fields.Float()
