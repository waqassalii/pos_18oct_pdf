odoo.define('pos_fbr_connector.screens', function(require) {
    "use strict";
    var pos_models = require('point_of_sale.models');
    var pos_screens = require('point_of_sale.screens');
    var web_rpc = require('web.rpc');
    pos_models.load_fields("pos.order", ['invoice_no','is_registered']);

    var pos_s_order = pos_models.Order.prototype;
    pos_models.Order = pos_models.Order.extend({
    	initialize: function(attributes, options) {
            pos_s_order.initialize.apply(this, arguments);
            this.invoice_no = false;
            this.is_registered = false
        },
        set_inv_no: function(invoice_no) {
        	this.invoice_no = invoice_no || null;
        },
        get_inv_no: function() {
            return this.invoice_no
        },
        set_is_registered: function(is_registered) {
        	this.is_registered = is_registered || null;
        },
        get_is_registered: function() {
            return this.is_registered
        },
        set_qr_code: function(qr_image) {
            this.qr_image = qr_image || null;
        },
        get_qr_code: function() {
            return this.qr_image
        },
        export_as_JSON: function() {
            var vals = pos_s_order.export_as_JSON.apply(this, arguments);
            vals['invoice_no'] = this.get_inv_no();
            vals['is_registered'] = this.get_is_registered();
            return vals
        },
    });
    pos_screens.PaymentScreenWidget.include({
    	validate_order: function(force_validation) {
    		var self = this;
            if (this.order_is_valid(force_validation)) {
                var pos_order = this.pos.get_order();
                web_rpc.query({
                    model: 'pos.order',
                    method: 'data_to_fbr',
                    args: [[pos_order.uid],[pos_order.export_as_JSON()]],
                })
                .then(function(data){
                	if(data && data[0]){
                		pos_order.set_inv_no(data[0]);
                    	pos_order.set_is_registered(true);
                    	pos_order.set_qr_code(data[1]);
                	}
                	self.finalize_validation();
                });
            	
            }
        },
    });
    
    pos_screens.ReceiptScreenWidget.include({
            get_receipt_render_env: function() {
                var order = this.pos.get_order();
                return {
                    widget: this,
                    pos: this.pos,
                    order: order,
                    qr_image:order.get_qr_code(),
                    inv_num :order.get_inv_no(),
                    receipt: order.export_for_printing(),
                    orderlines: order.get_orderlines(),
                    paymentlines: order.get_paymentlines(),
                };
            },
    });
 
    
    
});