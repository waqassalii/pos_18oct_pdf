from odoo import fields, models, api


class CategoryTargetWizard(models.TransientModel):
    """ Wizard allowing to grant a badge to a user"""
    _name = 'category.target.wizard'
    _description = 'category.target wizard'

    date = fields.Date('Date')

    def print_pdf_report(self):
        data={
            'model': 'category.target.wizard',
            'form': self.read()[0]
        }
        # print('date ==',data)
        today = fields.Datetime.today()
        today_orders = self.env['pos.order'].search([('date_order', '>=', today)])
        all_order_line = today_orders.mapped('lines')
        all_line_products = all_order_line.mapped('product_id')
        categories = self.env['category.target'].search([])
        order_list = []
        for categ in categories:
            categ_subtotal = 0
            categ_dict = {
                            'categ_name': categ.category_id.name,
                            'categ_value': categ.value,
                        }
            pos_category = self.env['pos.category'].search([('id', '=', categ.category_id.id)])
            all_required_products = all_line_products.search([('pos_categ_id', '=', pos_category.id)])
            for required_product in all_required_products:
                pos_order_lines = all_order_line.filtered(lambda x:x.product_id.id == required_product.id)
                for line in pos_order_lines:
                    categ_subtotal += line.price_subtotal
                categ_dict.update({
                    'subtotal' : categ_subtotal
                })
            order_list.append(categ_dict)
        data['pos'] = order_list
        return self.env.ref('category_target.report_category_target_id').report_action(self, data=data)

        # order_list = []
        # pos_orders = self.env['pos.order.line'].search([])
        # for order in pos_orders:
        #     order_list.append({
        #         'product_id': order.product_id.name,
        #         'categ_id': order.product_id.categ_id.name,
        #         'qty': order.qty,
        #     })
        # data['pos'] = order_list
        # return self.env.ref('category_target.report_category_target_id').report_action(self, data=data)


