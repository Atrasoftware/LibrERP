# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import orm, fields


class res_users(orm.Model):
    _name = 'res.users'
    _inherit = 'res.users'

    def search(self, cr, uid, args, offset=0, limit=0, order=None, context=None, count=False):
        context = context or self.pool['res.users'].context_get(cr, uid)
        res_users_ids = super(res_users, self).search(cr, uid, args, offset=offset, limit=limit, order=order, context=context, count=count)
        group_in = context.get('group_in', False)
        group_obj = self.pool['res.groups']
        if group_in:
            for res_user_id in res_users_ids:
                if not group_obj.user_in_group(cr, uid, res_user_id, group_in, context=context):
                    res_users_ids.remove(res_user_id)
        return res_users_ids


class groups(orm.Model):
    _name = 'res.groups'
    _inherit = 'res.groups'
    
    def id_from_xml_id(self, cr, uid, xml_id, context=None):
        context = context or self.pool['res.users'].context_get(cr, uid)
        group_obj = self.pool['res.groups']
        group_all_ids = group_obj.search(cr, uid, [], context=context)
        group_xml_ids = group_obj.get_xml_id(cr, uid, group_all_ids, context=context)
        
        for key in group_xml_ids.keys():
            xml_id_it = group_xml_ids[key]
            if xml_id_it == xml_id:
                return key
        return False
        
    def user_in_group(self, cr, uid, user_id, group_xml_id, context=None):
        context = context or self.pool['res.users'].context_get(cr, uid)
        user_obj = self.pool['res.users']
        user = user_obj.browse(cr, uid, user_id, context=context)
        if isinstance(user, list):
            user = user[0]
        
        group_id = self.id_from_xml_id(cr, uid, group_xml_id, context=context)
        for group in user.groups_id:
            if group.id == group_id:
                return True
        return False

