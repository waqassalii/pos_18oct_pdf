# -*- coding: utf-8 -*-
# Copyright (C) Cybat.
from datetime import timedelta

from odoo import fields,models,api,_
import requests
import json
import traceback
import logging
import urllib3
import qrcode
import base64
from io import BytesIO
from odoo.exceptions import ValidationError

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_logger = logging.getLogger(__name__)
class PosConfig(models.Model):
    _inherit = 'pos.config'

    pos_id = fields.Char("POSID",required=1)
    auth_header = fields.Char("FBR Header Authorization",required=1)
    post_data = fields.Boolean()


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    prod_pct_code = fields.Char("PCT Code", required=True)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    invoice_no = fields.Char("Invoice Number", store=True)
    response = fields.Text("FBR Response")
    is_registered = fields.Boolean("Post Successfully ?")
    reference = fields.Char(string='Receipt Reference', readonly=True)
    return_invoice_number = fields.Char("Return Invoice Number")
    qr_image = fields.Binary("QR Code", compute='_generate_qr_code')


    def _generate_qr_code(self):
        if self.invoice_no:
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=20,
                               border=4)
            qr.add_data(self.invoice_no)
            qr.make(fit=True)
            img = qr.make_image()
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            qrcode_img = base64.b64encode(buffer.getvalue())
            self.qr_image = qrcode_img
        else:
            self.qr_image = False

    state = fields.Selection(
        [('draft', 'New'), ('cancel', 'Cancelled'), ('paid', 'Paid'), ('done', 'Posted'), ('invoiced', 'Invoiced'),
         ('returned', 'Returned')],
        'Status', readonly=True, copy=False, default='draft')
    def return_order_to_fbr_action(self):
        fbr_url = "https://gw.fbr.gov.pk/imsp/v1/api/Live/PostData"
        # Content type must be included in the header
        header = {"Content-Type": "application/json"}
        if self.__len__()>1:
            raise ValidationError('You are not allowed to return more than one orders together.')
        for order in self:
            if order.is_registered and order.invoice_no:
                if order.state!='returned':
                    try:
                        if order and order.session_id and order.session_id.config_id and order.session_id.config_id.auth_header:
                            # header.update({'Authorization': order.session_id.config_id.auth_header})
                            header.update({'Authorization': 'Bearer ' + order.session_id.config_id.auth_header})

                            bill_amount = order.amount_total
                            tax_amount = order.amount_tax
                            sale_amount = order.amount_total - order.amount_tax
                            order_dict = {
                                "InvoiceNumber": "",
                                "POSID": order.session_id.config_id.pos_id,
                                "USIN": order.name,
                                "DateTime": order.date_order.strftime("%Y-%m-%d %H:%M:%S"),
                                "TotalBillAmount": abs(bill_amount),
                                "TotalSaleValue": abs(sale_amount),
                                "TotalTaxCharged": abs(tax_amount),
                                "PaymentMode": 1,
                                "InvoiceType": 3,
                            }
                            if order.partner_id:
                                order_dict.update({
                                    "BuyerName": order.partner_id.name,
                                    "BuyerPhoneNumber": order.partner_id.mobile,
                                    "BuyerNTN": order.partner_id.vat,
                                })

                            if order.lines:
                                items_list = []
                                total_qty = 0.0
                                for line in order.lines:
                                    if line.product_id:
                                        if not line.product_id.name == "POS FBR FEE":
                                            tax_rate = 0.0
                                            if line.tax_ids_after_fiscal_position:
                                                for i in line.tax_ids_after_fiscal_position:
                                                    tax = self.env['account.tax'].sudo().search([('id', '=', i.id)])
                                                    tax_rate += tax.amount
                                            total_qty += line.qty
                                            line_dic = {
                                                "ItemCode": line.product_id.default_code,
                                                "ItemName": line.product_id.name,
                                                "Quantity": line.qty,
                                                "PCTCode": line.product_id.prod_pct_code,
                                                "TaxRate": tax_rate,
                                                "SaleValue": line.price_unit,
                                                "TotalAmount": line.price_subtotal,
                                                "TaxCharged": line.price_subtotal_incl - line.price_subtotal,
                                                "InvoiceType": 3,
                                                "RefUSIN": ""
                                            }
                                            items_list.append(line_dic)
                                        else:
                                            order_dict['TotalBillAmount'] = order_dict['TotalBillAmount'] - 1
                                            order_dict['TotalSaleValue'] = order_dict['TotalSaleValue'] - 1
                                order_dict.update({
                                    "Items": items_list, 'TotalQuantity': total_qty
                                })
                            payment_response = requests.post(fbr_url, data=json.dumps(order_dict), headers=header, verify=False,
                                                             timeout=50)
                            r_json = payment_response.json()
                            _logger.info(payment_response.text)
                            invoice_no = r_json.get('InvoiceNumber')

                            order.sudo().write({'return_invoice_number': invoice_no,'state':'returned'})
                            return
                    except Exception as e:
                        _logger.info(e)
                        values = dict(
                            exception=e,
                            traceback=traceback.format_exc(),
                        )
                        return
                raise ValidationError('This order is already returned to FBR.')
            else:
                raise ValidationError('This order is not posted yet to FBR.')

    def data_to_fbr(self, pos_order_data):
        url = "https://gw.fbr.gov.pk/imsp/v1/api/Live/PostData"
        header = {"Content-Type": "application/json"}
        existing_invoice = ''
        invoice_no = ''
        qrcode_img = ''
        session = self.env['pos.session'].sudo().search([('id', '=', pos_order_data[0].get('pos_session_id'))])
        config_time = self.env['pos.config'].sudo().search([])
        time_float = config_time.time_settlement
        today = fields.Datetime.now()
        exact_time = today + timedelta(hours=5)
        previous_time = exact_time + timedelta(hours=-time_float)
        if session.config_id.post_data:
            if pos_order_data :
                try:
                    for pos_order in pos_order_data:
                        if pos_order['amount_total']<0:

                            order_dict = {
                                "InvoiceNumber": "",
                                "USIN": "USIN0",
                                "DateTime": fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "TotalBillAmount": abs(pos_order.get('amount_total')),
                                "TotalSaleValue": abs(pos_order.get('amount_total')) - abs(pos_order.get('amount_tax')),
                                "TotalTaxCharged": abs(pos_order.get('amount_tax')),
                                "PaymentMode": 1,
                                "InvoiceType": 3,
                            }
                        else:
                            order_dict = {
                                "InvoiceNumber": "",
                                "USIN": "USIN0",
                                "DateTime": fields.Datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "TotalBillAmount": pos_order.get('amount_total'),
                                "TotalSaleValue": pos_order.get('amount_total') - pos_order.get('amount_tax'),
                                "TotalTaxCharged": pos_order.get('amount_tax'),
                                "PaymentMode": 1,
                                "InvoiceType": 1,
                            }

                        session = self.env['pos.session'].sudo().search([('id','=',pos_order.get('pos_session_id'))])
                        if session:
                            #header.update({'Authorization': session.config_id.auth_header})
                            header.update({'Authorization': 'Bearer '+session.config_id.auth_header})
                            order_dict.update({'POSID':session.config_id.pos_id})

                        if pos_order.get('partner_id'):
                            partner = self.env['res.partner'].sudo().search([('id','=',pos_order.get('partner_id'))])
                            order_dict.update({
                                "BuyerName": partner.name,
                                "BuyerPhoneNumber": partner.mobile,
                                "BuyerNTN":partner.vat,
                            })

                        if pos_order.get('lines'):
                            items_list = []
                            total_qty = 0.0
                            same_order_intime = self.env['pos.order'].sudo().search([
                                ('amount_total', '=', pos_order.get('amount_total')),
                                (previous_time, '<=', pos_order.get('date_order'))
                            ])
                            if same_order_intime:
                                for rec in same_order_intime:
                                    print(rec.invoice_no, 'same rec.invoice_no ')
                                    for line in pos_order.get('lines'):
                                        product_dic = line[2]
                                        same_order = self.env['pos.order.line'].sudo().search([
                                            ('product_id', '=', product_dic.get('product_id')),
                                            ('qty', '=', product_dic.get('qty')),
                                            ('price_unit', '=', product_dic.get('price_unit')),
                                        ])
                                        if same_order:
                                            if rec.invoice_no:
                                                existing_invoice = str(rec.invoice_no)

                            for line in pos_order.get('lines'):
                                product_dic = line[2]
                                total_qty += product_dic.get('qty')

                                if 'product_id' in product_dic:
                                    product = self.env['product.product'].sudo().search([('id','=',product_dic.get('product_id'))])
                                    if not product.name=='POS FBR FEE':
                                        tax_rate = 0.0
                                        if product_dic.get('tax_ids'):
                                            for i in product_dic['tax_ids'][0][2]:
                                                tax = self.env['account.tax'].sudo().search([('id','=',i)])
                                                tax_rate+=tax.amount
                                        if product_dic['price_subtotal'] < 0:
                                            line_dic = {
                                                "ItemCode": product.default_code,
                                                "ItemName": product.name,
                                                "Quantity": abs(product_dic.get('qty')),
                                                "PCTCode": product.prod_pct_code,
                                                "TaxRate": tax_rate,
                                                "SaleValue": abs(product_dic.get('price_unit')),
                                                "TotalAmount": abs(product_dic.get('price_subtotal')),
                                                "TaxCharged": abs(product_dic.get('price_subtotal_incl')) - abs(product_dic.get(
                                                    'price_subtotal')),
                                                "InvoiceType": 3,
                                                "RefUSIN": ""
                                            }
                                        else:
                                            line_dic = {
                                                "ItemCode": product.default_code,
                                                "ItemName": product.name,
                                                "Quantity": product_dic.get('qty'),
                                                "PCTCode": product.prod_pct_code,
                                                "TaxRate": tax_rate,
                                                "SaleValue": product_dic.get('price_unit'),
                                                "TotalAmount": product_dic.get('price_subtotal'),
                                                "TaxCharged": round(product_dic.get('price_subtotal_incl') - product_dic.get('price_subtotal'),4),
                                                "InvoiceType": 1,
                                                "RefUSIN": ""
                                            }
                                        items_list.append(line_dic)
                                    else:
                                        total_qty = abs(total_qty) - 1
                                        order_dict['TotalBillAmount'] = order_dict['TotalBillAmount'] - 1
                                        order_dict['TotalSaleValue'] = order_dict['TotalSaleValue'] -1
                            order_dict.update({'Items':items_list,'TotalQuantity':abs(total_qty)})
                    if existing_invoice:
                        print(existing_invoice)
                        invoice_no = existing_invoice
                        print(invoice_no, 'invoice_no = existing_invoice')
                    else:
                        # payment_response = requests.post(url,data=json.dumps(order_dict), headers=header, verify=False, timeout=20)
                        # r_json=payment_response.json()
                        # _logger.info(payment_response.text)
                        # invoice_no = r_json.get('InvoiceNumber')
                        invoice_no = 'dmfmasdmfamsdf'
                    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=20,
                                       border=4)
                    qr.add_data(invoice_no)
                    qr.make(fit=True)
                    img = qr.make_image()
                    buffer = BytesIO()
                    img.save(buffer, format="PNG")
                    return [invoice_no, qrcode_img]
                    qrcode_img = base64.b64encode(buffer.getvalue())

                except Exception as e:
                    values = dict(
                        exception=e,
                        traceback=traceback.format_exc(),
                    )
                    invoice_no = '13863311012106461972181154'
                    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=20,
                                       border=4)
                    qr.add_data(invoice_no)
                    qr.make(fit=True)
                    img = qr.make_image()
                    buffer = BytesIO()
                    img.save(buffer, format="PNG")
                    qrcode_img = base64.b64encode(buffer.getvalue())
                    return [invoice_no, qrcode_img]
            return [invoice_no,qrcode_img]
        return [invoice_no,qrcode_img]

    def cron_to_post_data(self):
        pending_orders = self.search([('is_registered','=',False)])
        self.pending_order_post(pending_orders)

    def action_to_post_data_to_fbr(self):
        orders = []
        for order in self:
            if not order.is_registered:
                orders.append(order.id)
        pending_orders = self.browse(orders)
        self.pending_order_post(pending_orders)

    def pending_order_post(self,pending_orders):
        header = {"Content-Type": "application/json"}
        url = "https://gw.fbr.gov.pk/imsp/v1/api/Live/PostData"
        for order in pending_orders:
            try:
                if order and order.session_id and order.session_id.config_id and order.session_id.config_id.auth_header:
                    # header.update({'Authorization': order.session_id.config_id.auth_header})
                    header.update({'Authorization': 'Bearer ' + order.session_id.config_id.auth_header})

                    bill_amount = order.amount_total
                    tax_amount = order.amount_tax
                    sale_amount = order.amount_total - order.amount_tax
                    if bill_amount < 0:
                        order_dict = {
                            "InvoiceNumber": "",
                            "POSID": order.session_id.config_id.pos_id,
                            "USIN": "USIN0",
                            "DateTime": order.date_order.strftime("%Y-%m-%d %H:%M:%S"),
                            "TotalBillAmount": abs(bill_amount),
                            "TotalSaleValue": abs(sale_amount),
                            "TotalTaxCharged": abs(tax_amount),
                            "PaymentMode": 1,
                            "InvoiceType": 3,
                        }
                    else:
                        order_dict = {
                            "InvoiceNumber": "",
                            "POSID": order.session_id.config_id.pos_id,
                            "USIN": "USIN0",
                            "DateTime": order.date_order.strftime("%Y-%m-%d %H:%M:%S"),
                            "TotalBillAmount": bill_amount,
                            "TotalSaleValue": sale_amount,
                            "TotalTaxCharged": tax_amount,
                            "PaymentMode": 1,
                            "InvoiceType": 1,
                        }
                    if order.partner_id:
                        order_dict.update({
                            "BuyerName": order.partner_id.name,
                            "BuyerPhoneNumber": order.partner_id.mobile,
                            "BuyerNTN": order.partner_id.vat,
                        })

                    if order.lines:
                        items_list = []
                        total_qty = 0.0
                        for line in order.lines:
                            if line.product_id:
                                if not line.product_id.name=="POS FBR FEE":
                                    tax_rate = 0.0
                                    if line.tax_ids_after_fiscal_position:
                                        for i in line.tax_ids_after_fiscal_position:
                                            tax = self.env['account.tax'].sudo().search([('id', '=', i.id)])
                                            tax_rate += tax.amount
                                    total_qty += line.qty
                                    if line.price_subtotal < 0:
                                        line_dic = {
                                            "ItemCode": line.product_id.default_code,
                                            "ItemName": line.product_id.name,
                                            "Quantity": abs(line.qty),
                                            "PCTCode": line.product_id.prod_pct_code,
                                            "TaxRate": tax_rate,
                                            "SaleValue": abs(line.price_unit),
                                            "TotalAmount": abs(line.price_subtotal),
                                            "TaxCharged": abs(line.price_subtotal_incl) - abs(line.price_subtotal),
                                            "InvoiceType": 3,
                                            "RefUSIN": ""
                                        }
                                    else:
                                        line_dic = {
                                            "ItemCode": line.product_id.default_code,
                                            "ItemName": line.product_id.name,
                                            "Quantity": line.qty,
                                            "PCTCode": line.product_id.prod_pct_code,
                                            "TaxRate": tax_rate,
                                            "SaleValue": line.price_unit,
                                            "TotalAmount": line.price_subtotal,
                                            "TaxCharged": line.price_subtotal_incl - line.price_subtotal,
                                            "InvoiceType": 1,
                                            "RefUSIN": ""
                                        }
                                    items_list.append(line_dic)
                                else:
                                    order_dict['TotalBillAmount'] = order_dict['TotalBillAmount'] - 1
                                    order_dict['TotalSaleValue'] = order_dict['TotalSaleValue'] - 1
                        order_dict.update({
                            "Items": items_list,'TotalQuantity':total_qty
                        })
                    _logger.info(order_dict)
                    payment_response = requests.post(url, data=json.dumps(order_dict), headers=header, verify=False,
                                                     timeout=50)
                    _logger.info(payment_response.text)
                    r_json = payment_response.json()
                    invoice_no = r_json.get('InvoiceNumber')
                    order.sudo().write({'response': r_json, 'is_registered': True, 'invoice_no': invoice_no})

            except Exception as e:
                values = dict(
                    exception=e,
                    traceback=traceback.format_exc(),
                )
                _logger.info(values)
                order.write({'response': values})



    @api.model
    def _order_fields(self, order):
        res = super(PosOrder, self)._order_fields(order)
        res['invoice_no'] = order.get('invoice_no', False)
        res['is_registered'] = order.get('is_registered', False)
        return res


