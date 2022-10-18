# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def create(self, values):
        session = self.env['pos.session'].browse(values['session_id'])
        values = self._complete_values_from_session(session, values)
        res =  super(PosOrder, self).create(values)
        self.env['custom.pos.order'].create({'pos_id':res.id})
        return res


class CustomPosOrder(models.Model):
    _name = 'custom.pos.order'
    _inherits = {'pos.order': 'pos_id'}
    _description = 'custom_pos_order.custom_pos_order'

    pos_id = fields.Many2one('pos.order', string='POS id', auto_join=True, index=True, ondelete='cascade')
    # name = fields.Char()
