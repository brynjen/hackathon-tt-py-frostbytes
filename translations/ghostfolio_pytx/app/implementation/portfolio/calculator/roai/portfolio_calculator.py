from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timedelta, date
from copy import deepcopy
from app.wrapper.portfolio.calculator.portfolio_calculator import PortfolioCalculator
from app.implementation.helpers import get_perf, get_inv, get_hold, get_det, get_div, get_rep

class RoaiPortfolioCalculator(PortfolioCalculator):
    def get_performance(self):
        return get_perf(self.sorted_activities(), self.current_rate_service)

    def get_investments(self, group_by=None):
        return get_inv(self.sorted_activities(), group_by)

    def get_holdings(self):
        return get_hold(self.sorted_activities(), self.current_rate_service)

    def get_details(self, base_currency="USD"):
        return get_det(self.sorted_activities(), self.current_rate_service, base_currency)

    def get_dividends(self, group_by=None):
        return get_div(self.sorted_activities(), group_by)

    def evaluate_report(self):
        return get_rep(self.sorted_activities())
