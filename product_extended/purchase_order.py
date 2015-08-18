# -*- encoding: utf-8 -*-
##############################################################################
#
#    Avanzosc - Avanced Open Source Consulting
#    Copyright (C) 2011 - 2012 Avanzosc <http://www.avanzosc.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see http://www.gnu.org/licenses/.
#
##############################################################################

import time
from openerp.osv import orm, fields
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

class purchase_order(orm.Model):
    _inherit = "purchase.order"

    def wkf_confirm_order(self, cr, uid, ids, context=None):
        supplierinfo_obj = self.pool['product.supplierinfo']
        res = super(purchase_order, self).wkf_confirm_order(cr, uid, ids, context)
        for o in self.browse(cr, uid, ids, context):
            for line in o.order_line:
                if line.product_id:
                    vals = {
                        'last_purchase_date': time.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        'last_supplier_id': line.partner_id.id
                    }
                    self.pool['product.product'].write(cr, uid, [line.product_id.id], vals, context)
                    supplierinfo_ids = supplierinfo_obj.search(cr, uid, [('product_id', '=', line.product_id.id), ('name', '=', line.partner_id.id)], context=context)
                    if not supplierinfo_ids:
                        supplierinfo_obj.create(cr, uid, {
                            'name': line.partner_id.id,
                            'product_name': line.name,
                            'product_id': line.product_id.id,
                            'min_qty': 1,
                            'product_code': line.product_id.default_code,
                            'sequence': 10
                        }, context)
        return res
