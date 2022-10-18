# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import datetime, time, timedelta
from dateutil import relativedelta


class TimeSettlementConfig(models.Model):
    _inherit = 'pos.config'

    time_settlement = fields.Float('Time Settlement')

