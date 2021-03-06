# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2010-2012 Associazione OpenERP Italia
#    (<http://www.openerp-italia.org>).
#    Copyright (C) 2014-2018 Didotech srl
#    (<http://www.didotech.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from tools.translate import _

from datetime import date, datetime

from openerp.osv import orm, fields
from tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT


class stock_picking(orm.Model):
    _inherit = "stock.picking"

    def _get_invoiced_state(self, cr, uid, ids, field_name, arg, context):
        context = context or self.pool['res.users'].context_get(cr, uid)
        res = dict.fromkeys(ids, 0.0)
        for picking in self.browse(cr, 1, ids, context=context):
            res[picking.id] = ''
            order = picking.sale_id
            if order:
                # res[picking.id] = u'{payment_term}'.format(
                #     payment_term=order.payment_term and order.payment_term.name or '')
                for invoice in order.invoice_ids:
                    res[picking.id] = dict(self.pool['account.invoice'].fields_get(cr, uid, context=context)['state']['selection'])[invoice.state]
        return res

    def _credit_limit(self, cr, uid, ids, field_name, arg, context):
        context = context or self.pool['res.users'].context_get(cr, uid)
        res = dict.fromkeys(ids, 0.0)
        for picking in self.browse(cr, uid, ids, context=context):
            res[picking.id] = False
            partner = picking.address_id.partner_id
            if partner:
                # We sum from all the sale orders that are aproved, the sale order lines that are not yet invoiced
                invoice_obj = self.pool['account.invoice']
                invoice_ids = invoice_obj.search(cr, uid,
                                                 [('partner_id', '=', partner.id), ('state', 'in', ['draft', 'open'])],
                                                 context=context)
                invoices_amount = 0.0
                for invoice in invoice_obj.browse(cr, uid, invoice_ids, context=context):
                    invoices_amount += invoice.amount_total
                available_credit = partner.credit_limit - invoices_amount
                res[picking.id] = available_credit
        return res

    def _get_day(self, cr, uid, ids, name, args, context=None):
        context = context or self.pool['res.users'].context_get(cr, uid)
        res = {}
        for picking in self.browse(cr, uid, ids, context=context):
            res[picking.id] = {
                'week_nbr': False,
            }
            if not picking.minimum_planned_date:
                continue

            start_date = datetime.strptime(picking.minimum_planned_date, DEFAULT_SERVER_DATE_FORMAT)
            start_date = date(start_date.year, start_date.month, start_date.day)

            # mese in italiano start_date.strftime('%B').capitalize()
            res[picking.id] = {
                'week_nbr': start_date.isocalendar()[1]
            }

        return res

    def _get_order_type(self, cr, uid, ids, name, args, context=None):
        context = context or self.pool['res.users'].context_get(cr, uid)
        res = {}
        for picking in self.browse(cr, uid, ids, context=context):
            if picking.type == 'internal':
                order_type = 'internal'
            else:
                order_type = 'client'
            res[picking.id] = order_type
        return res

    def _get_order_board_state(self, cr, uid, ids, name, args, context=None):
        context = context or self.pool['res.users'].context_get(cr, uid)
        res = {}
        for picking in self.browse(cr, uid, ids, context=context):
            res[picking.id] = {
                'order_sent': False,
                'order_ready': False
            }
            if picking.state == 'done':
                res[picking.id]['order_ready'] = True
        return res

    def _get_picking_sale(self, cr, uid, ids, context=None):
        context = context or self.pool['res.users'].context_get(cr, uid)
        result = {}
        stock_picking_model = self.pool['stock.picking']
        picking_ids = stock_picking_model.search(cr, uid, [('sale_id', 'in', ids)], context=context)
        for picking in stock_picking_model.browse(cr, uid, picking_ids, context):
            result[picking.id] = True
        return result.keys()

    def _get_picking_partner_address(self, cr, uid, ids, context=None):
        context = context or self.pool['res.users'].context_get(cr, uid)
        result = {}
        stock_picking_model = self.pool['stock.picking']
        picking_ids = stock_picking_model.search(cr, uid, [('address_delivery_id', 'in', ids)], context=context)
        for picking in stock_picking_model.browse(cr, uid, picking_ids, context):
            result[picking.id] = True
        return result.keys()

    def _get_picking_partner(self, cr, uid, ids, context=None):
        context = context or self.pool['res.users'].context_get(cr, uid)
        result = {}
        stock_picking_model = self.pool['stock.picking']
        picking_ids = stock_picking_model.search(cr, uid, [('customer_id', 'in', ids)], context=context)
        for picking in stock_picking_model.browse(cr, uid, picking_ids, context):
            result[picking.id] = True
        return result.keys()

    def _name_get_fnc(self, cr, uid, ids, prop, unknow_none, context=None):
        res = self.name_get(cr, uid, ids, context=context)
        return dict(res)

    def _is_goods_ready(self, cr, uid, ids, field_name, arg, context=None):
        result = {}
        for pick in self.browse(cr, uid, ids, context):
            moves_ready = False
            for m in pick.move_lines:
                if m.goods_ready:
                    moves_ready = True
                    break
            result[pick.id] = moves_ready
        return result

    def _filter_goods_ready(self, cr, uid, obj, field_name, args, context=None):
        all_pickings_ids = self.search(cr, uid, [], context=context)
        goods_ready_dict = self._is_goods_ready(cr=cr, uid=uid, ids=all_pickings_ids, field_name=field_name, arg=args, context=context)
        res = [key for (key, value) in goods_ready_dict.iteritems() if value]
        where = [('id', 'in', res)]
        return where

    _columns = {
        'complete_name': fields.function(_name_get_fnc, method=True, type="char", string='Name'),
        'goods_ready': fields.function(_is_goods_ready, type="boolean", string="Have Posa", fnct_search=_filter_goods_ready),
        'carriage_condition_id': fields.many2one(
            'stock.picking.carriage_condition', 'Carriage condition'),
        'goods_description_id': fields.many2one(
            'stock.picking.goods_description', 'Description of goods'),
        'transportation_condition_id': fields.many2one(
            'stock.picking.transportation_condition', 'Transportation condition'),
        # address_id is overridden because it's used 2binvoiced
        # n.b.: partner_id is only a related, so not useful for the workflow
        'address_id': fields.many2one(
            'res.partner.address', 'Partner', help="Partner to be invoiced"
        ),
        'address_delivery_id': fields.many2one(
            'res.partner.address', 'Address', help='Delivery address of \
            partner'
        ),
        'invoice_state': fields.selection([
            ("invoiced", "Invoiced"),
            ("2binvoiced", "To Be Invoiced"),
            ("none", "Not Applicable")], "Invoice Control",
            select=True, required=True, readonly=False),
        'client_order_ref': fields.related(
            'sale_id', 'client_order_ref', type='char',
            string='Customer Reference'),
        'credit_limit': fields.function(_credit_limit, string="Remaining Credit Limit", type='float', readonly=True,
                                        method=True),
        'visible_credit_limit': fields.related('company_id', 'check_credit_limit', type='boolean',
                                               string=_('Fido Residuo Visibile'), store=False, readonly=True),
        # 'weight': fields.float('Gross weight', digits_compute=dp.get_precision('Stock Weight'), help="The gross weight in Kg."),
        # 'weight_net': fields.float('Net weight', digits_compute=dp.get_precision('Stock Weight'), help="The net weight in Kg."),
        'customer_id': fields.related('sale_id', 'partner_id', type='many2one', relation='res.partner',
                                      string='Customer', readonly=True, store={
                                        'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['sale_id'], 6000),
                                        'sale.order': (_get_picking_sale, ['partner_id'], 6000),
                                        }),
        'order_type': fields.function(_get_order_type, string="Order Type", type="selection", selection=[
            ('client', 'Client'),
            ('internal', 'Internal'),
        ], readonly=True),
        'order_sent': fields.function(_get_order_board_state, type='boolean', multi='order_state', string='Order Sent'),
        'order_ready': fields.function(_get_order_board_state, type='boolean', multi='order_state', string='Order Ready'),
        'creation_date': fields.related('sale_id', 'create_date', type='date', string='Inserted on', store=False,
                                        readonly=True),
        'street': fields.related('address_delivery_id', 'street', type='char', string='Street', store=False),
        'city': fields.related('address_delivery_id', 'city', type='char', string='City', store=False),
        'province': fields.related('address_delivery_id', 'province', type='many2one', relation='res.province',
                                   string='Province', readonly=True, store={
                                        'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['address_delivery_id'], 6000),
                                        'res.partner.address': (_get_picking_partner_address, ['province'], 6000),
                                        }),

        'region': fields.related('address_delivery_id', 'region', type='many2one', relation='res.region', string='Region',
                                 readonly=True, store={
                                        'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['address_delivery_id'], 6000),
                                        'res.partner.address': (_get_picking_partner_address, ['province'], 6000),
                                        }),
        'agent': fields.related('customer_id', 'section_id', type='many2one', relation='crm.case.section',
                                string='Agent', readonly=True, store={
                                        'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['customer_id'], 6000),
                                        'res.partner': (_get_picking_partner, ['section_id'], 6000),
                                        }),
        'sale_user_id': fields.related('sale_id', 'user_id', type='many2one', relation='res.users',
                                string='Sale User', readonly=True, store={
                'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['sale_id'], 6000),
            }),
        'board_date': fields.date('Order Board Delivery date'),
        'amount_total': fields.related('sale_id', 'amount_untaxed', type='float', string='Total Amount (VAT Excluded)', readonly=True,
                                       store={
                                            'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['sale_id', 'state'], 5000),
                                            'sale.order': (_get_picking_sale, ['amount_untaxed', 'state'], 6000),
                                        }),
        'payment_term_id': fields.related('sale_id', 'payment_term', type='many2one', relation='account.payment.term', string="Payment Term"),
        'week_nbr': fields.function(_get_day, method=True, multi='day_of_week', type="integer", string="Week Number",
                                    store={
                                        'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['sale_id', 'max_date', 'state'], 5000),
                                        'sale.order': (_get_picking_sale, ['minimum_planned_date', 'state'], 6000),
                                        }),

        'minimum_planned_date': fields.related('sale_id', 'minimum_planned_date', type='date', string='Expected Date',
                                               store={
                                                   'stock.picking': (lambda self, cr, uid, ids, c={}: ids, ['sale_id', 'max_date'], 500),
                                                   'sale.order': (_get_picking_sale, ['minimum_planned_date', 'state'], 600),
                                               }),
        'internal_note': fields.text('Internal Note'),
        'invoiced_state': fields.function(_get_invoiced_state, string="Invoice State", type='char'),
    }

    def check_limit(self, cr, uid, ids, context=None):
        context = context or self.pool['res.users'].context_get(cr, uid)
        for picking in self.browse(cr, uid, ids, context=context):
            if picking.type == 'out':
                if picking.credit_limit < 0 and picking.company_id and picking.company_id.check_credit_limit:
                    title = _(u'Credit Over Limit')
                    msg = _(u'Is not possible to confirm because customer exceed the credit limit.')
                    raise orm.except_orm(_(title), _(msg))
                    return False
                if picking.company_id and picking.company_id.check_overdue and self.pool[
                    'sale.order'].partner_overdue_check(cr, uid, picking.company_id, picking.address_id.partner_id,
                                                        context):
                    title = _(u'Overdue Limit')
                    msg = _(u'Is not possible to confirm because customer have a overdue payment.')
                    raise orm.except_orm(_(title), _(msg))
                    return False
        return True

    def action_process(self, cr, uid, ids, context=None):
        context = context or self.pool['res.users'].context_get(cr, uid)
        if self.check_limit(cr, uid, ids, context):
            return super(stock_picking, self).action_process(cr, uid, ids, context=context)
        else:
            return False

    def print_picking(self, cr, uid, ids, context):
        return self.pool['account.invoice'].print_report(cr, uid, ids, 'delivery.report_shipping', context)

    def onchange_stock_journal(self, cr, uid, ids, stock_journal_id=None, state=None, context=None):
        context = context or self.pool['res.users'].context_get(cr, uid)
        if state != 'draft':
            return {'value': {}}

        stock_journal_obj = self.pool['stock.journal']
        default_invoice_state = False
        if stock_journal_id:
            default_invoice_state = stock_journal_obj.browse(
                cr, uid, stock_journal_id, context).default_invoice_state

        return {'value': {'invoice_state': default_invoice_state or 'none'}}

    def onchange_partner_in(self, cr, uid, ids, address_id=None, context=None):
        context = context or self.pool['res.users'].context_get(cr, uid)
        partner_address_obj = self.pool['res.partner.address']
        delivery_ids = []
        partner_id = None
        if address_id:
            partner_id = partner_address_obj.browse(
                cr, uid, address_id, context).partner_id
        if partner_id:
            delivery_ids = partner_address_obj.search(
                cr, uid, [('partner_id', '=', partner_id.id), (
                    'default_delivery_partner_address', '=', True)],
                context=context
            )

            if not delivery_ids:
                delivery_ids = partner_address_obj.search(
                    cr, uid, [('partner_id', '=', partner_id.id), (
                        'type', '=', 'delivery')],
                    context=context
                )
                if not delivery_ids:
                    delivery_ids = partner_address_obj.search(
                        cr, uid, [('partner_id', '=', partner_id.id)],
                        context=context
                    )

        if delivery_ids:
            return {'value': {'address_delivery_id': delivery_ids[0]}}
        else:
            return {'value': {}}

    def search(self, cr, uid, args, offset=0, limit=0, order=None, context=None, count=False):
        context = context or self.pool['res.users'].context_get(cr, uid)
        new_args = []

        order = order or context.get('order', None)
        for arg in args:
            # if arg and len(arg)==3 and arg[0] in field_to_sql.keys() and arg[1]=='ilike':
            if arg and len(arg) == 3 and arg[1] == 'ilike':
                values = arg[2].split(',')
                if values > 1:
                    new_args += ['|' for x in range(len(values) - 1)] + [(arg[0], arg[1], value.strip()) for value in values]
            else:
                new_args.append(arg)

        return super(stock_picking, self).search(cr, uid, new_args, offset=offset, limit=limit, order=order,
                                                 context=context, count=count)

    def write(self, cr, uid, ids, vals, context=None):
        if vals.get('minimum_planned_date', False):
            text = _(u'has change delivery date to {date}').format(date=vals.get('minimum_planned_date', False))
            self.message_append(cr, uid, ids, text, body_text=text, context=context)
        res = super(stock_picking, self).write(cr, uid, ids, vals, context)
        return res

    def create(self, cr, uid, vals, context=None):
        context = context or self.pool['res.users'].context_get(cr, uid)
        if ('name' not in vals) or (vals.get('name') == '/'):
            if 'type' in vals.keys() and vals['type'] == 'out':
                vals['name'] = self.pool['ir.sequence'].next_by_code(cr, uid, 'stock.picking.out')
            elif 'type' in vals.keys() and vals['type'] == 'internal':
                vals['name'] = self.pool['ir.sequence'].next_by_code(cr, uid, 'stock.picking.internal')
            else:
                vals['name'] = self.pool['ir.sequence'].next_by_code(cr, uid, 'stock.picking.in')
        ids = super(stock_picking, self).create(cr, uid, vals, context)

        if vals.get('carriage_condition_id', False) or vals.get('goods_description_id', False):
            picking = self.browse(cr, uid, ids, context)
            partner_vals = {}
            if not picking.partner_id.carriage_condition_id:
                partner_vals['carriage_condition_id'] = vals.get('carriage_condition_id')
            if not picking.partner_id.goods_description_id:
                partner_vals['goods_description_id'] = vals.get('goods_description_id')
            if not picking.partner_id.property_delivery_carrier:
                partner_vals['property_delivery_carrier'] = vals.get('carrier_id')
            if partner_vals:
                self.pool['res.partner'].write(cr, uid, [picking.partner_id.id], partner_vals, context)
        return ids

    def _prepare_invoice_line(self, cr, uid, group, picking, move_line, invoice_id, invoice_vals, context=None):
        invoice_line_vals = super(stock_picking, self)._prepare_invoice_line(cr, uid, group, picking, move_line,
                                                                             invoice_id,
                                                                             invoice_vals, context=context)
        """ Update dict with correct shipped qty
        """
        invoice_line_vals['quantity'] = move_line.product_qty or move_line.product_uos_qty
        if picking.company_id.note_on_invoice_line:
            invoice_line_vals.update({'note': move_line.note})
        return invoice_line_vals

    def _prepare_invoice(self, cr, uid, picking, partner, inv_type, journal_id, context=None):
        invoice_vals = super(stock_picking, self)._prepare_invoice(cr, uid, picking, partner, inv_type, journal_id,
                                                                   context)
        invoice_vals.update({
            'carriage_condition_id': picking.carriage_condition_id and picking.carriage_condition_id.id or False,
            'goods_description_id': picking.goods_description_id and picking.goods_description_id.id or False,
            'transportation_condition_id': picking.transportation_condition_id and picking.transportation_condition_id.id or False,
        })
        return invoice_vals

    def _invoice_hook(self, cr, uid, picking, invoice_id):
        res = super(stock_picking, self)._invoice_hook(cr, uid, picking, invoice_id)
        if picking.sale_id:
            for order_line in picking.sale_id.order_line:
                if not order_line.invoiced:
                    break
            else:
                sale_order = picking.sale_id
                if sale_order.state == 'manual':
                    sale_order.write({'state': 'progress'})
        return res

    def localtime(self, cr, uid, ids, date_time, context=None):
        return fields.datetime.context_timestamp(
            cr,
            uid,
            datetime.strptime(date_time, DEFAULT_SERVER_DATETIME_FORMAT),
            context=context
        ).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
