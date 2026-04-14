from __future__ import annotations

from decimal import Decimal
from datetime import datetime, timedelta, date
from copy import deepcopy
from app.wrapper.portfolio.calculator.portfolio_calculator import PortfolioCalculator
from app.implementation.helpers import get_perf, get_inv, get_hold, get_det, get_div, get_rep

class RoaiPortfolioCalculator(PortfolioCalculator):
    async def compute_snapshot(self):
        last_transaction_point = self.transaction_points.at(-1)
        transaction_points = [_destructured_181 for _destructured_181 in self.transaction_points if (datetime.fromisoformat(date) < self.end_date)]
        if not len(transaction_points):
            return {
                "activitiesCount": 0,
                "createdAt": datetime.now(),
                "currentValueInBaseCurrency": Decimal("0"),
                "errors": [],
                "hasErrors": False,
                "historicalData": [],
                "positions": [],
                "totalFeesWithCurrencyEffect": Decimal("0"),
                "totalInterestWithCurrencyEffect": Decimal("0"),
                "totalInvestment": Decimal("0"),
                "totalInvestmentWithCurrencyEffect": Decimal("0"),
                "totalLiabilitiesWithCurrencyEffect": Decimal("0"),
            }
        currencies = {}
        data_gathering_items = []
        first_index = len(transaction_points)
        first_transaction_point = None
        total_interest_with_currency_effect = Decimal("0")
        total_liabilities_with_currency_effect = Decimal("0")
        for _item in transaction_points[(first_index - 1)].items:
            asset_sub_class = _item["assetSubClass"]
            currency = _item["currency"]
            data_source = _item["dataSource"]
            symbol = _item["symbol"]
            if (asset_sub_class != "CASH"):
                data_gathering_items.append({"dataSource": data_source, "symbol": symbol})
            currencies[symbol] = currency
        while True:
            if (not (datetime.fromisoformat(transaction_points[i].date) < self.start_date) and (first_transaction_point == None)):
                first_transaction_point = transaction_points[i]
                first_index = i
        exchange_rates_by_currency = self.exchange_rate_data_service.get_exchange_rates_by_currency({
            "currencies": list(set(list(currencies.values()))),
            "endDate": self.end_date,
            "startDate": self.start_date,
            "targetCurrency": self.currency,
        })
        data_provider_infos = self.current_rate_service.get_values({"dataGatheringItems": data_gathering_items, "dateQuery": {"gte": self.start_date, "lt": self.end_date}})["dataProviderInfos"]
        current_rate_errors = self.current_rate_service.get_values({"dataGatheringItems": data_gathering_items, "dateQuery": {"gte": self.start_date, "lt": self.end_date}})["errors"]
        market_symbols = self.current_rate_service.get_values({"dataGatheringItems": data_gathering_items, "dateQuery": {"gte": self.start_date, "lt": self.end_date}})["values"]
        self.data_provider_infos = data_provider_infos
        market_symbol_map = {}
        for market_symbols in market_symbols:
            date = market_symbol.date.strftime(DATE_FORMAT)
            if not market_symbol_map[date]:
                market_symbol_map[date] = {}
            if market_symbol.market_price:
                market_symbol_map[date][market_symbol.symbol] = Decimal(str(market_symbol.market_price))
        end_date_string = self.end_date.strftime(DATE_FORMAT)
        days_in_market = (self.end_date - self.start_date).days
        chart_date_map = self.get_chart_date_map({"endDate": self.end_date, "startDate": self.start_date, "step": round((days_in_market / min(days_in_market, self.configuration_service.get("MAX_CHART_ITEMS"))))})
        for account_balance_item in self.account_balance_items:
            chart_date_map[account_balance_item.date] = True
        chart_dates = sorted(list(chart_date_map.keys()), key=lambda chart_date: chart_date)
        if (first_index > 0):
            first_index -= 1
        errors = []
        has_any_symbol_metrics_errors = False
        positions = []
        accumulated_values_by_date = {}
        values_by_symbol = {}
        for item in last_transaction_point.items:
            market_price_in_base_currency = ((market_symbol_map[end_date_string][item.symbol] if market_symbol_map[end_date_string][item.symbol] is not None else item.average_price) * (exchange_rates_by_currency[f"{item.currency}{self.currency}"][end_date_string] if exchange_rates_by_currency[f"{item.currency}{self.currency}"][end_date_string] is not None else 1))
            current_values = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["currentValues"]
            current_values_with_currency_effect = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["currentValuesWithCurrencyEffect"]
            gross_performance = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["grossPerformance"]
            gross_performance_percentage = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["grossPerformancePercentage"]
            gross_performance_percentage_with_currency_effect = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["grossPerformancePercentageWithCurrencyEffect"]
            gross_performance_with_currency_effect = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["grossPerformanceWithCurrencyEffect"]
            has_errors = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["hasErrors"]
            investment_values_accumulated = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["investmentValuesAccumulated"]
            investment_values_accumulated_with_currency_effect = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["investmentValuesAccumulatedWithCurrencyEffect"]
            investment_values_with_currency_effect = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["investmentValuesWithCurrencyEffect"]
            net_performance = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["netPerformance"]
            net_performance_percentage = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["netPerformancePercentage"]
            net_performance_percentage_with_currency_effect_map = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["netPerformancePercentageWithCurrencyEffectMap"]
            net_performance_values = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["netPerformanceValues"]
            net_performance_values_with_currency_effect = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["netPerformanceValuesWithCurrencyEffect"]
            net_performance_with_currency_effect_map = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["netPerformanceWithCurrencyEffectMap"]
            time_weighted_investment = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["timeWeightedInvestment"]
            time_weighted_investment_values = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["timeWeightedInvestmentValues"]
            time_weighted_investment_values_with_currency_effect = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["timeWeightedInvestmentValuesWithCurrencyEffect"]
            time_weighted_investment_with_currency_effect = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["timeWeightedInvestmentWithCurrencyEffect"]
            total_dividend = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["totalDividend"]
            total_dividend_in_base_currency = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["totalDividendInBaseCurrency"]
            total_interest_in_base_currency = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["totalInterestInBaseCurrency"]
            total_investment = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["totalInvestment"]
            total_investment_with_currency_effect = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["totalInvestmentWithCurrencyEffect"]
            total_liabilities_in_base_currency = self.get_symbol_metrics({
                "chartDateMap": chart_date_map,
                "marketSymbolMap": market_symbol_map,
                "dataSource": item.data_source,
                "end": self.end_date,
                "exchangeRates": exchange_rates_by_currency[f"{item.currency}{self.currency}"],
                "start": self.start_date,
                "symbol": item.symbol,
            })["totalLiabilitiesInBaseCurrency"]
            has_any_symbol_metrics_errors = (has_any_symbol_metrics_errors or has_errors)
            include_in_total_asset_value = (item.asset_sub_class != AssetSubClass.CASH)
            if include_in_total_asset_value:
                values_by_symbol[item.symbol] = {
                    "currentValues": current_values,
                    "currentValuesWithCurrencyEffect": current_values_with_currency_effect,
                    "investmentValuesAccumulated": investment_values_accumulated,
                    "investmentValuesAccumulatedWithCurrencyEffect": investment_values_accumulated_with_currency_effect,
                    "investmentValuesWithCurrencyEffect": investment_values_with_currency_effect,
                    "netPerformanceValues": net_performance_values,
                    "netPerformanceValuesWithCurrencyEffect": net_performance_values_with_currency_effect,
                    "timeWeightedInvestmentValues": time_weighted_investment_values,
                    "timeWeightedInvestmentValuesWithCurrencyEffect": time_weighted_investment_values_with_currency_effect,
                }
            positions.append({
                "includeInTotalAssetValue": include_in_total_asset_value,
                "timeWeightedInvestment": time_weighted_investment,
                "timeWeightedInvestmentWithCurrencyEffect": time_weighted_investment_with_currency_effect,
                "activitiesCount": item.activities_count,
                "averagePrice": item.average_price,
                "currency": item.currency,
                "dataSource": item.data_source,
                "dateOfFirstActivity": item.date_of_first_activity,
                "dividend": total_dividend,
                "dividendInBaseCurrency": total_dividend_in_base_currency,
                "fee": item.fee,
                "feeInBaseCurrency": item.fee_in_base_currency,
                "grossPerformance": ((gross_performance if gross_performance is not None else None) if not has_errors else None),
                "grossPerformancePercentage": ((gross_performance_percentage if gross_performance_percentage is not None else None) if not has_errors else None),
                "grossPerformancePercentageWithCurrencyEffect": ((gross_performance_percentage_with_currency_effect if gross_performance_percentage_with_currency_effect is not None else None) if not has_errors else None),
                "grossPerformanceWithCurrencyEffect": ((gross_performance_with_currency_effect if gross_performance_with_currency_effect is not None else None) if not has_errors else None),
                "includeInHoldings": item.include_in_holdings,
                "investment": total_investment,
                "investmentWithCurrencyEffect": total_investment_with_currency_effect,
                "marketPrice": (float(market_symbol_map[end_date_string][item.symbol]) if float(market_symbol_map[end_date_string][item.symbol]) is not None else 1),
                "marketPriceInBaseCurrency": (float(market_price_in_base_currency) if float(market_price_in_base_currency) is not None else 1),
                "netPerformance": ((net_performance if net_performance is not None else None) if not has_errors else None),
                "netPerformancePercentage": ((net_performance_percentage if net_performance_percentage is not None else None) if not has_errors else None),
                "netPerformancePercentageWithCurrencyEffectMap": ((net_performance_percentage_with_currency_effect_map if net_performance_percentage_with_currency_effect_map is not None else None) if not has_errors else None),
                "netPerformanceWithCurrencyEffectMap": ((net_performance_with_currency_effect_map if net_performance_with_currency_effect_map is not None else None) if not has_errors else None),
                "quantity": item.quantity,
                "symbol": item.symbol,
                "tags": item.tags,
                "valueInBaseCurrency": (Decimal(str(market_price_in_base_currency)) * item.quantity),
            })
            total_interest_with_currency_effect = (total_interest_with_currency_effect + total_interest_in_base_currency)
            total_liabilities_with_currency_effect = (total_liabilities_with_currency_effect + total_liabilities_in_base_currency)
            if (((has_errors or next((_destructured_462 for _destructured_462 in current_rate_errors if ((data_source == item.data_source) and (symbol == item.symbol))), None)) and (item.investment > 0)) and (item.skip_errors == False)):
                errors.append({"dataSource": item.data_source, "symbol": item.symbol})
        account_balance_items_map = self.account_balance_items.reduce(lambda map, _destructured_473: None, {})
        account_balance_map = {}
        last_known_balance = Decimal("0")
        for chart_dates in chart_dates:
            if (account_balance_items_map[date_string] != None):
                last_known_balance = account_balance_items_map[date_string]
            account_balance_map[date_string] = last_known_balance
            for symbol in list(values_by_symbol.keys()):
                symbol_values = values_by_symbol[symbol]
                current_value = (symbol_values.current_values[date_string] if symbol_values.current_values[date_string] is not None else Decimal("0"))
                current_value_with_currency_effect = (symbol_values.current_values_with_currency_effect[date_string] if symbol_values.current_values_with_currency_effect[date_string] is not None else Decimal("0"))
                investment_value_accumulated = (symbol_values.investment_values_accumulated[date_string] if symbol_values.investment_values_accumulated[date_string] is not None else Decimal("0"))
                investment_value_accumulated_with_currency_effect = (symbol_values.investment_values_accumulated_with_currency_effect[date_string] if symbol_values.investment_values_accumulated_with_currency_effect[date_string] is not None else Decimal("0"))
                investment_value_with_currency_effect = (symbol_values.investment_values_with_currency_effect[date_string] if symbol_values.investment_values_with_currency_effect[date_string] is not None else Decimal("0"))
                net_performance_value = (symbol_values.net_performance_values[date_string] if symbol_values.net_performance_values[date_string] is not None else Decimal("0"))
                net_performance_value_with_currency_effect = (symbol_values.net_performance_values_with_currency_effect[date_string] if symbol_values.net_performance_values_with_currency_effect[date_string] is not None else Decimal("0"))
                time_weighted_investment_value = (symbol_values.time_weighted_investment_values[date_string] if symbol_values.time_weighted_investment_values[date_string] is not None else Decimal("0"))
                time_weighted_investment_value_with_currency_effect = (symbol_values.time_weighted_investment_values_with_currency_effect[date_string] if symbol_values.time_weighted_investment_values_with_currency_effect[date_string] is not None else Decimal("0"))
                accumulated_values_by_date[date_string] = {
                    "investmentValueWithCurrencyEffect": ((accumulated_values_by_date[date_string].investment_value_with_currency_effect if accumulated_values_by_date[date_string].investment_value_with_currency_effect is not None else Decimal("0")) + investment_value_with_currency_effect),
                    "totalAccountBalanceWithCurrencyEffect": account_balance_map[date_string],
                    "totalCurrentValue": ((accumulated_values_by_date[date_string].total_current_value if accumulated_values_by_date[date_string].total_current_value is not None else Decimal("0")) + current_value),
                    "totalCurrentValueWithCurrencyEffect": ((accumulated_values_by_date[date_string].total_current_value_with_currency_effect if accumulated_values_by_date[date_string].total_current_value_with_currency_effect is not None else Decimal("0")) + current_value_with_currency_effect),
                    "totalInvestmentValue": ((accumulated_values_by_date[date_string].total_investment_value if accumulated_values_by_date[date_string].total_investment_value is not None else Decimal("0")) + investment_value_accumulated),
                    "totalInvestmentValueWithCurrencyEffect": ((accumulated_values_by_date[date_string].total_investment_value_with_currency_effect if accumulated_values_by_date[date_string].total_investment_value_with_currency_effect is not None else Decimal("0")) + investment_value_accumulated_with_currency_effect),
                    "totalNetPerformanceValue": ((accumulated_values_by_date[date_string].total_net_performance_value if accumulated_values_by_date[date_string].total_net_performance_value is not None else Decimal("0")) + net_performance_value),
                    "totalNetPerformanceValueWithCurrencyEffect": ((accumulated_values_by_date[date_string].total_net_performance_value_with_currency_effect if accumulated_values_by_date[date_string].total_net_performance_value_with_currency_effect is not None else Decimal("0")) + net_performance_value_with_currency_effect),
                    "totalTimeWeightedInvestmentValue": ((accumulated_values_by_date[date_string].total_time_weighted_investment_value if accumulated_values_by_date[date_string].total_time_weighted_investment_value is not None else Decimal("0")) + time_weighted_investment_value),
                    "totalTimeWeightedInvestmentValueWithCurrencyEffect": ((accumulated_values_by_date[date_string].total_time_weighted_investment_value_with_currency_effect if accumulated_values_by_date[date_string].total_time_weighted_investment_value_with_currency_effect is not None else Decimal("0")) + time_weighted_investment_value_with_currency_effect),
                }
        historical_data = [None for x in list(accumulated_values_by_date.items())]
        overall = self.calculate_overall_performance(positions)
        positions_included_in_holdings = [rest for _destructured_629 in [_destructured_625 for _destructured_625 in positions if include_in_holdings]]
        return {
            **overall,
            "errors": errors,
            "historicalData": historical_data,
            "totalInterestWithCurrencyEffect": total_interest_with_currency_effect,
            "totalLiabilitiesWithCurrencyEffect": total_liabilities_with_currency_effect,
            "hasErrors": (has_any_symbol_metrics_errors or overall.has_errors),
            "positions": positions_included_in_holdings,
        }

    def get_data_provider_infos(self):
        return self.data_provider_infos

    async def get_dividend_in_base_currency(self):
        self.snapshot_promise
        return get_sum([dividend_in_base_currency for _destructured_654 in self.snapshot.positions])

    async def get_fees_in_base_currency(self):
        self.snapshot_promise
        return self.snapshot.total_fees_with_currency_effect

    async def get_interest_in_base_currency(self):
        self.snapshot_promise
        return self.snapshot.total_interest_with_currency_effect

    def get_investments(self):
        if (len(self.transaction_points) == 0):
            return []
        return [{"date": transaction_point.date, "investment": transaction_point.items.reduce(lambda investment, transaction_point_symbol: (investment + transaction_point_symbol.investment), Decimal("0"))} for transactionPoint in self.transaction_points]

    def get_investments_by_group(self, _destructured_689):
        grouped_data = {}
        for data in data:
            date = _item["date"]
            investment_value_with_currency_effect = _item["investmentValueWithCurrencyEffect"]
            date_group = (date.substring(0, 7) if (group_by == "month") else date.substring(0, 4))
            grouped_data[date_group] = ((grouped_data[date_group] if grouped_data[date_group] is not None else Decimal("0")) + investment_value_with_currency_effect)
        return [{"date": (f"{date_group}-01" if (group_by == "month") else f"{date_group}-01-01"), "investment": float(grouped_data[date_group])} for dateGroup in list(grouped_data.keys())]

    async def get_liabilities_in_base_currency(self):
        self.snapshot_promise
        return self.snapshot.total_liabilities_with_currency_effect

    async def get_performance(self, _destructured_718):
        self.snapshot_promise
        historical_data = self.snapshot["historicalData"]
        chart = []
        net_performance_at_start_date = None
        net_performance_with_currency_effect_at_start_date = None
        total_investment_values_with_currency_effect = []
        for historical_data in historical_data:
            date = reset_hours(datetime.fromisoformat(historical_data_item.date))
            if (not (date < start) and not (date > end)):
                if not isinstance(net_performance_at_start_date, (int, float)):
                    net_performance_at_start_date = historical_data_item.net_performance
                    net_performance_with_currency_effect_at_start_date = historical_data_item.net_performance_with_currency_effect
                net_performance_since_start_date = (historical_data_item.net_performance - net_performance_at_start_date)
                net_performance_with_currency_effect_since_start_date = (historical_data_item.net_performance_with_currency_effect - net_performance_with_currency_effect_at_start_date)
                if (historical_data_item.total_investment_value_with_currency_effect > 0):
                    total_investment_values_with_currency_effect.append(historical_data_item.total_investment_value_with_currency_effect)
                time_weighted_investment_value = ((sum(total_investment_values_with_currency_effect) / len(total_investment_values_with_currency_effect)) if (len(total_investment_values_with_currency_effect) > 0) else 0)
                chart.append({
                    **historical_data_item,
                    "netPerformance": (historical_data_item.net_performance - net_performance_at_start_date),
                    "netPerformanceWithCurrencyEffect": net_performance_with_currency_effect_since_start_date,
                    "netPerformanceInPercentage": (0 if (time_weighted_investment_value == 0) else (net_performance_since_start_date / time_weighted_investment_value)),
                    "netPerformanceInPercentageWithCurrencyEffect": (0 if (time_weighted_investment_value == 0) else (net_performance_with_currency_effect_since_start_date / time_weighted_investment_value)),
                })
        return {"chart": chart}

    async def get_snapshot(self):
        self.snapshot_promise
        return self.snapshot

    def get_start_date(self):
        first_account_balance_date = None
        first_activity_date = None
        try:
            first_account_balance_date_string = self.account_balance_items[0].date
            first_account_balance_date = (datetime.fromisoformat(first_account_balance_date_string) if first_account_balance_date_string else datetime.now())
        except Exception as error:
            first_account_balance_date = datetime.now()
        try:
            first_activity_date_string = self.transaction_points[0].date
            first_activity_date = (datetime.fromisoformat(first_activity_date_string) if first_activity_date_string else datetime.now())
        except Exception as error:
            first_activity_date = datetime.now()
        return min(first_account_balance_date, first_activity_date)

    def get_transaction_points(self):
        return self.transaction_points

    def _get_chart_date_map(self, _destructured_839):
        chart_date_map = self.transaction_points.reduce(lambda result, _destructured_850: None, {})
        for date in _each_day_of_interval({"end": end_date, "start": start_date}):
            chart_date_map[date.strftime(DATE_FORMAT)] = True
        if (step > 1):
            for date in _each_day_of_interval({"end": end_date, "start": (end_date - timedelta(days=90))}):
                chart_date_map[date.strftime(DATE_FORMAT)] = True
            for date in _each_day_of_interval({"end": end_date, "start": (end_date - timedelta(days=30))}):
                chart_date_map[date.strftime(DATE_FORMAT)] = True
        chart_date_map[end_date.strftime(DATE_FORMAT)] = True
        for date_range in ["1d", "1y", "5y", "max", "mtd", "wtd", "ytd"]:
            date_range_end = get_interval_from_date_range(date_range)["endDate"]
            date_range_start = get_interval_from_date_range(date_range)["startDate"]
            if (not (date_range_start < start_date) and not (date_range_start > end_date)):
                chart_date_map[date_range_start.strftime(DATE_FORMAT)] = True
            if (not (date_range_end < start_date) and not (date_range_end > end_date)):
                chart_date_map[date_range_end.strftime(DATE_FORMAT)] = True
        interval = {"start": start_date, "end": end_date}
        for date in _each_year_of_interval(interval):
            year_start = date.replace(month=1, day=1)
            year_end = date.replace(month=12, day=31)
            if ((interval["start"] <= year_start) and (year_start <= interval["end"])):
                chart_date_map[year_start.strftime(DATE_FORMAT)] = True
            if ((interval["start"] <= year_end) and (year_end <= interval["end"])):
                chart_date_map[year_end.strftime(DATE_FORMAT)] = True
        return chart_date_map

    def _compute_transaction_points(self):
        self.transaction_points = []
        symbols = {}
        last_date = None
        last_transaction_point = None
        for _item in self.activities:
            date = _item["date"]
            fee = _item["fee"]
            fee_in_base_currency = _item["feeInBaseCurrency"]
            quantity = _item["quantity"]
            SymbolProfile = _item["SymbolProfile"]
            tags = _item["tags"]
            type = _item["type"]
            unit_price = _item["unitPrice"]
            current_transaction_point_item = None
            asset_sub_class = SymbolProfile.asset_sub_class
            currency = SymbolProfile.currency
            data_source = SymbolProfile.data_source
            factor = get_factor(type)
            skip_errors = not not SymbolProfile.user_id
            symbol = SymbolProfile.symbol
            old_accumulated_symbol = symbols[symbol]
            if old_accumulated_symbol:
                investment = old_accumulated_symbol.investment
                new_quantity = ((quantity * factor) + old_accumulated_symbol.quantity)
                if (type == "BUY"):
                    if (old_accumulated_symbol.investment >= 0):
                        investment = (old_accumulated_symbol.investment + (quantity * unit_price))
                    else:
                        investment = (old_accumulated_symbol.investment + (quantity * old_accumulated_symbol.average_price))
                elif (type == "SELL"):
                    if (old_accumulated_symbol.investment > 0):
                        investment = (old_accumulated_symbol.investment - (quantity * old_accumulated_symbol.average_price))
                    else:
                        investment = (old_accumulated_symbol.investment - (quantity * unit_price))
                if (abs(new_quantity) < 1e-10):
                    investment = Decimal("0")
                    new_quantity = Decimal("0")
                current_transaction_point_item = {
                    "assetSubClass": asset_sub_class,
                    "currency": currency,
                    "dataSource": data_source,
                    "investment": investment,
                    "skipErrors": skip_errors,
                    "symbol": symbol,
                    "activitiesCount": (old_accumulated_symbol.activities_count + 1),
                    "averagePrice": (Decimal("0") if (new_quantity == 0) else abs((investment / new_quantity))),
                    "dateOfFirstActivity": old_accumulated_symbol.date_of_first_activity,
                    "dividend": Decimal("0"),
                    "fee": (old_accumulated_symbol.fee + fee),
                    "feeInBaseCurrency": (old_accumulated_symbol.fee_in_base_currency + fee_in_base_currency),
                    "includeInHoldings": old_accumulated_symbol.include_in_holdings,
                    "quantity": new_quantity,
                    "tags": old_accumulated_symbol.tags.concat(tags),
                }
            else:
                current_transaction_point_item = {
                    "assetSubClass": asset_sub_class,
                    "currency": currency,
                    "dataSource": data_source,
                    "fee": fee,
                    "feeInBaseCurrency": fee_in_base_currency,
                    "skipErrors": skip_errors,
                    "symbol": symbol,
                    "tags": tags,
                    "activitiesCount": 1,
                    "averagePrice": unit_price,
                    "dateOfFirstActivity": date,
                    "dividend": Decimal("0"),
                    "includeInHoldings": (type in INVESTMENT_ACTIVITY_TYPES),
                    "investment": ((unit_price * quantity) * factor),
                    "quantity": (quantity * factor),
                }
            current_transaction_point_item.tags = _uniq_by(current_transaction_point_item.tags, "id")
            symbols[SymbolProfile.symbol] = current_transaction_point_item
            items = (last_transaction_point.items if last_transaction_point.items is not None else [])
            new_items = [_destructured_1038 for _destructured_1038 in items if (symbol != SymbolProfile.symbol)]
            new_items.append(current_transaction_point_item)
            new_items.sort(lambda a, b: a.symbol.locale_compare(b.symbol))
            fees = Decimal("0")
            if (type == "FEE"):
                fees = fee
            interest = Decimal("0")
            if (type == "INTEREST"):
                interest = (quantity * unit_price)
            liabilities = Decimal("0")
            if (type == "LIABILITY"):
                liabilities = (quantity * unit_price)
            if ((last_date != date) or (last_transaction_point == None)):
                last_transaction_point = {
                    "date": date,
                    "fees": fees,
                    "interest": interest,
                    "liabilities": liabilities,
                    "items": new_items,
                }
                self.transaction_points.append(last_transaction_point)
            else:
                last_transaction_point.fees = (last_transaction_point.fees + fees)
                last_transaction_point.interest = (last_transaction_point.interest + interest)
                last_transaction_point.items = new_items
                last_transaction_point.liabilities = (last_transaction_point.liabilities + liabilities)
            last_date = date

    async def _initialize(self):
        start_time_total = performance.now()
        cached_portfolio_snapshot = None
        is_cached_portfolio_snapshot_expired = False
        job_id = self.user_id
        try:
            cached_portfolio_snapshot_value = self.redis_cache_service.get(self.redis_cache_service.get_portfolio_snapshot_key({"filters": self.filters, "userId": self.user_id}))
            expiration = json.loads(cached_portfolio_snapshot_value)["expiration"]
            portfolio_snapshot = json.loads(cached_portfolio_snapshot_value)["portfolioSnapshot"]
            cached_portfolio_snapshot = plain_to_class(PortfolioSnapshot, portfolio_snapshot)
            if (datetime.now() > datetime.fromisoformat(str(expiration))):
                is_cached_portfolio_snapshot_expired = True
        except Exception:
            pass
        if cached_portfolio_snapshot:
            self.snapshot = cached_portfolio_snapshot
            Logger.debug(f"Fetched portfolio snapshot from cache in {((performance.now() - start_time_total) / 1000).to_fixed(3)} seconds", "PortfolioCalculator")
            if is_cached_portfolio_snapshot_expired:
                self.portfolio_snapshot_service.add_job_to_queue({"data": {
                    "calculationType": self.get_performance_calculation_type(),
                    "filters": self.filters,
                    "userCurrency": self.currency,
                    "userId": self.user_id,
                }, "name": PORTFOLIO_SNAPSHOT_PROCESS_JOB_NAME, "opts": {**PORTFOLIO_SNAPSHOT_PROCESS_JOB_OPTIONS, "jobId": job_id, "priority": PORTFOLIO_SNAPSHOT_COMPUTATION_QUEUE_PRIORITY_LOW}})
        else:
            self.portfolio_snapshot_service.add_job_to_queue({"data": {
                "calculationType": self.get_performance_calculation_type(),
                "filters": self.filters,
                "userCurrency": self.currency,
                "userId": self.user_id,
            }, "name": PORTFOLIO_SNAPSHOT_PROCESS_JOB_NAME, "opts": {**PORTFOLIO_SNAPSHOT_PROCESS_JOB_OPTIONS, "jobId": job_id, "priority": PORTFOLIO_SNAPSHOT_COMPUTATION_QUEUE_PRIORITY_HIGH}})
            job = self.portfolio_snapshot_service.get_job(job_id)
            if job:
                job.finished()
            self.initialize()

    chart_dates = None

    def calculate_overall_performance(self, positions):
        current_value_in_base_currency = Decimal("0")
        gross_performance = Decimal("0")
        gross_performance_with_currency_effect = Decimal("0")
        has_errors = False
        net_performance = Decimal("0")
        total_fees_with_currency_effect = Decimal("0")
        total_interest_with_currency_effect = Decimal("0")
        total_investment = Decimal("0")
        total_investment_with_currency_effect = Decimal("0")
        total_time_weighted_investment = Decimal("0")
        total_time_weighted_investment_with_currency_effect = Decimal("0")
        for current_position in [_destructured_44 for _destructured_44 in positions if include_in_total_asset_value]:
            if current_position.fee_in_base_currency:
                total_fees_with_currency_effect = (total_fees_with_currency_effect + current_position.fee_in_base_currency)
            if current_position.value_in_base_currency:
                current_value_in_base_currency = (current_value_in_base_currency + current_position.value_in_base_currency)
            else:
                has_errors = True
            if current_position.investment:
                total_investment = (total_investment + current_position.investment)
                total_investment_with_currency_effect = (total_investment_with_currency_effect + current_position.investment_with_currency_effect)
            else:
                has_errors = True
            if current_position.gross_performance:
                gross_performance = (gross_performance + current_position.gross_performance)
                gross_performance_with_currency_effect = (gross_performance_with_currency_effect + current_position.gross_performance_with_currency_effect)
                net_performance = (net_performance + current_position.net_performance)
            elif not (current_position.quantity == 0):
                has_errors = True
            if current_position.time_weighted_investment:
                total_time_weighted_investment = (total_time_weighted_investment + current_position.time_weighted_investment)
                total_time_weighted_investment_with_currency_effect = (total_time_weighted_investment_with_currency_effect + current_position.time_weighted_investment_with_currency_effect)
            elif not (current_position.quantity == 0):
                Logger.warn(f"Missing historical market data for {current_position.symbol} ({current_position.data_source})", "PortfolioCalculator")
                has_errors = True
        return {
            "currentValueInBaseCurrency": current_value_in_base_currency,
            "hasErrors": has_errors,
            "positions": positions,
            "totalFeesWithCurrencyEffect": total_fees_with_currency_effect,
            "totalInterestWithCurrencyEffect": total_interest_with_currency_effect,
            "totalInvestment": total_investment,
            "totalInvestmentWithCurrencyEffect": total_investment_with_currency_effect,
            "activitiesCount": len([_destructured_115 for _destructured_115 in self.activities if (type in ["BUY", "SELL"])]),
            "createdAt": datetime.now(),
            "errors": [],
            "historicalData": [],
            "totalLiabilitiesWithCurrencyEffect": Decimal("0"),
        }

    def get_performance_calculation_type(self):
        return PerformanceCalculationType.ROAI

    def get_symbol_metrics(self, _destructured_129):
        current_exchange_rate = exchange_rates[datetime.now().strftime(DATE_FORMAT)]
        current_values = {}
        current_values_with_currency_effect = {}
        fees = Decimal("0")
        fees_at_start_date = Decimal("0")
        fees_at_start_date_with_currency_effect = Decimal("0")
        fees_with_currency_effect = Decimal("0")
        gross_performance = Decimal("0")
        gross_performance_with_currency_effect = Decimal("0")
        gross_performance_at_start_date = Decimal("0")
        gross_performance_at_start_date_with_currency_effect = Decimal("0")
        gross_performance_from_sells = Decimal("0")
        gross_performance_from_sells_with_currency_effect = Decimal("0")
        initial_value = None
        initial_value_with_currency_effect = None
        investment_at_start_date = None
        investment_at_start_date_with_currency_effect = None
        investment_values_accumulated = {}
        investment_values_accumulated_with_currency_effect = {}
        investment_values_with_currency_effect = {}
        last_average_price = Decimal("0")
        last_average_price_with_currency_effect = Decimal("0")
        net_performance_values = {}
        net_performance_values_with_currency_effect = {}
        time_weighted_investment_values = {}
        time_weighted_investment_values_with_currency_effect = {}
        total_account_balance_in_base_currency = Decimal("0")
        total_dividend = Decimal("0")
        total_dividend_in_base_currency = Decimal("0")
        total_interest = Decimal("0")
        total_interest_in_base_currency = Decimal("0")
        total_investment = Decimal("0")
        total_investment_from_buy_transactions = Decimal("0")
        total_investment_from_buy_transactions_with_currency_effect = Decimal("0")
        total_investment_with_currency_effect = Decimal("0")
        total_liabilities = Decimal("0")
        total_liabilities_in_base_currency = Decimal("0")
        total_quantity_from_buy_transactions = Decimal("0")
        total_units = Decimal("0")
        value_at_start_date = None
        value_at_start_date_with_currency_effect = None
        orders = deepcopy([_destructured_196 for _destructured_196 in self.activities if (SymbolProfile.symbol == symbol)])
        is_cash = (orders[0].symbol_profile.asset_sub_class == "CASH")
        if (len(orders) <= 0):
            return {
                "currentValues": {},
                "currentValuesWithCurrencyEffect": {},
                "feesWithCurrencyEffect": Decimal("0"),
                "grossPerformance": Decimal("0"),
                "grossPerformancePercentage": Decimal("0"),
                "grossPerformancePercentageWithCurrencyEffect": Decimal("0"),
                "grossPerformanceWithCurrencyEffect": Decimal("0"),
                "hasErrors": False,
                "initialValue": Decimal("0"),
                "initialValueWithCurrencyEffect": Decimal("0"),
                "investmentValuesAccumulated": {},
                "investmentValuesAccumulatedWithCurrencyEffect": {},
                "investmentValuesWithCurrencyEffect": {},
                "netPerformance": Decimal("0"),
                "netPerformancePercentage": Decimal("0"),
                "netPerformancePercentageWithCurrencyEffectMap": {},
                "netPerformanceValues": {},
                "netPerformanceValuesWithCurrencyEffect": {},
                "netPerformanceWithCurrencyEffectMap": {},
                "timeWeightedInvestment": Decimal("0"),
                "timeWeightedInvestmentValues": {},
                "timeWeightedInvestmentValuesWithCurrencyEffect": {},
                "timeWeightedInvestmentWithCurrencyEffect": Decimal("0"),
                "totalAccountBalanceInBaseCurrency": Decimal("0"),
                "totalDividend": Decimal("0"),
                "totalDividendInBaseCurrency": Decimal("0"),
                "totalInterest": Decimal("0"),
                "totalInterestInBaseCurrency": Decimal("0"),
                "totalInvestment": Decimal("0"),
                "totalInvestmentWithCurrencyEffect": Decimal("0"),
                "totalLiabilities": Decimal("0"),
                "totalLiabilitiesInBaseCurrency": Decimal("0"),
            }
        date_of_first_transaction = datetime.fromisoformat(str(orders[0].date))
        end_date_string = end.strftime(DATE_FORMAT)
        start_date_string = start.strftime(DATE_FORMAT)
        unit_price_at_start_date = market_symbol_map[start_date_string][symbol]
        unit_price_at_end_date = market_symbol_map[end_date_string][symbol]
        latest_activity = orders.at(-1)
        if ((((data_source == "MANUAL") and (latest_activity.type in ["BUY", "SELL"])) and latest_activity.unit_price) and not unit_price_at_end_date):
            unit_price_at_end_date = latest_activity.unit_price
        elif is_cash:
            unit_price_at_end_date = Decimal("1")
        if (not unit_price_at_end_date or (not unit_price_at_start_date and (date_of_first_transaction < start))):
            return {
                "currentValues": {},
                "currentValuesWithCurrencyEffect": {},
                "feesWithCurrencyEffect": Decimal("0"),
                "grossPerformance": Decimal("0"),
                "grossPerformancePercentage": Decimal("0"),
                "grossPerformancePercentageWithCurrencyEffect": Decimal("0"),
                "grossPerformanceWithCurrencyEffect": Decimal("0"),
                "hasErrors": True,
                "initialValue": Decimal("0"),
                "initialValueWithCurrencyEffect": Decimal("0"),
                "investmentValuesAccumulated": {},
                "investmentValuesAccumulatedWithCurrencyEffect": {},
                "investmentValuesWithCurrencyEffect": {},
                "netPerformance": Decimal("0"),
                "netPerformancePercentage": Decimal("0"),
                "netPerformancePercentageWithCurrencyEffectMap": {},
                "netPerformanceWithCurrencyEffectMap": {},
                "netPerformanceValues": {},
                "netPerformanceValuesWithCurrencyEffect": {},
                "timeWeightedInvestment": Decimal("0"),
                "timeWeightedInvestmentValues": {},
                "timeWeightedInvestmentValuesWithCurrencyEffect": {},
                "timeWeightedInvestmentWithCurrencyEffect": Decimal("0"),
                "totalAccountBalanceInBaseCurrency": Decimal("0"),
                "totalDividend": Decimal("0"),
                "totalDividendInBaseCurrency": Decimal("0"),
                "totalInterest": Decimal("0"),
                "totalInterestInBaseCurrency": Decimal("0"),
                "totalInvestment": Decimal("0"),
                "totalInvestmentWithCurrencyEffect": Decimal("0"),
                "totalLiabilities": Decimal("0"),
                "totalLiabilitiesInBaseCurrency": Decimal("0"),
            }
        orders.append({
            "date": start_date_string,
            "fee": Decimal("0"),
            "feeInBaseCurrency": Decimal("0"),
            "itemType": "start",
            "quantity": Decimal("0"),
            "SymbolProfile": {"dataSource": data_source, "symbol": symbol, "assetSubClass": ("CASH" if is_cash else None)},
            "type": "BUY",
            "unitPrice": unit_price_at_start_date,
        })
        orders.append({
            "date": end_date_string,
            "fee": Decimal("0"),
            "feeInBaseCurrency": Decimal("0"),
            "itemType": "end",
            "SymbolProfile": {"dataSource": data_source, "symbol": symbol, "assetSubClass": ("CASH" if is_cash else None)},
            "quantity": Decimal("0"),
            "type": "BUY",
            "unitPrice": unit_price_at_end_date,
        })
        last_unit_price = None
        orders_by_date = {}
        for orders in orders:
            orders_by_date[order.date] = (orders_by_date[order.date] if orders_by_date[order.date] is not None else [])
            orders_by_date[order.date].append(order)
        if not self.chart_dates:
            self.chart_dates = list(chart_date_map.keys()).sort()
        for date_string in self.chart_dates:
            if (date_string < start_date_string):
                continue
            elif (date_string > end_date_string):
                break
            if (len(orders_by_date[date_string]) > 0):
                for order in orders_by_date[date_string]:
                    order.unit_price_from_market_data = (market_symbol_map[date_string][symbol] if market_symbol_map[date_string][symbol] is not None else last_unit_price)
            else:
                orders.append({
                    "date": date_string,
                    "fee": Decimal("0"),
                    "feeInBaseCurrency": Decimal("0"),
                    "quantity": Decimal("0"),
                    "SymbolProfile": {"dataSource": data_source, "symbol": symbol, "assetSubClass": ("CASH" if is_cash else None)},
                    "type": "BUY",
                    "unitPrice": (market_symbol_map[date_string][symbol] if market_symbol_map[date_string][symbol] is not None else last_unit_price),
                    "unitPriceFromMarketData": (market_symbol_map[date_string][symbol] if market_symbol_map[date_string][symbol] is not None else last_unit_price),
                })
            latest_activity = orders.at(-1)
            last_unit_price = (latest_activity.unit_price_from_market_data if latest_activity.unit_price_from_market_data is not None else latest_activity.unit_price)
        orders = sorted(orders, key=lambda _destructured_385: None)
        index_of_start_order = next((i for i, _destructured_397 in enumerate(orders) if (item_type == "start")), -1)
        index_of_end_order = next((i for i, _destructured_401 in enumerate(orders) if (item_type == "end")), -1)
        total_investment_days = 0
        sum_of_time_weighted_investments = Decimal("0")
        sum_of_time_weighted_investments_with_currency_effect = Decimal("0")
        while True:
            order = orders[i]
            if PortfolioCalculator.ENABLE_LOGGING:
                print()
                print()
                print((i + 1), order.date, order.type, (f"({order.item_type})" if order.item_type else ""))
            exchange_rate_at_order_date = exchange_rates[order.date]
            if (order.type == "DIVIDEND"):
                dividend = (order.quantity * order.unit_price)
                total_dividend = (total_dividend + dividend)
                total_dividend_in_base_currency = (total_dividend_in_base_currency + (dividend * (exchange_rate_at_order_date if exchange_rate_at_order_date is not None else 1)))
            elif (order.type == "INTEREST"):
                interest = (order.quantity * order.unit_price)
                total_interest = (total_interest + interest)
                total_interest_in_base_currency = (total_interest_in_base_currency + (interest * (exchange_rate_at_order_date if exchange_rate_at_order_date is not None else 1)))
            elif (order.type == "LIABILITY"):
                liabilities = (order.quantity * order.unit_price)
                total_liabilities = (total_liabilities + liabilities)
                total_liabilities_in_base_currency = (total_liabilities_in_base_currency + (liabilities * (exchange_rate_at_order_date if exchange_rate_at_order_date is not None else 1)))
            if (order.item_type == "start"):
                order.unit_price = (orders[(i + 1)].unit_price if (index_of_start_order == 0) else unit_price_at_start_date)
            if order.fee:
                order.fee_in_base_currency = (order.fee * (current_exchange_rate if current_exchange_rate is not None else 1))
                order.fee_in_base_currency_with_currency_effect = (order.fee * (exchange_rate_at_order_date if exchange_rate_at_order_date is not None else 1))
            unit_price = (order.unit_price if (order.type in ["BUY", "SELL"]) else order.unit_price_from_market_data)
            if unit_price:
                order.unit_price_in_base_currency = (unit_price * (current_exchange_rate if current_exchange_rate is not None else 1))
                order.unit_price_in_base_currency_with_currency_effect = (unit_price * (exchange_rate_at_order_date if exchange_rate_at_order_date is not None else 1))
            market_price_in_base_currency = ((order.unit_price_from_market_data * (current_exchange_rate if current_exchange_rate is not None else 1)) if (order.unit_price_from_market_data * (current_exchange_rate if current_exchange_rate is not None else 1)) is not None else Decimal("0"))
            market_price_in_base_currency_with_currency_effect = ((order.unit_price_from_market_data * (exchange_rate_at_order_date if exchange_rate_at_order_date is not None else 1)) if (order.unit_price_from_market_data * (exchange_rate_at_order_date if exchange_rate_at_order_date is not None else 1)) is not None else Decimal("0"))
            value_of_investment_before_transaction = (total_units * market_price_in_base_currency)
            value_of_investment_before_transaction_with_currency_effect = (total_units * market_price_in_base_currency_with_currency_effect)
            if (not investment_at_start_date and (i >= index_of_start_order)):
                investment_at_start_date = (total_investment if total_investment is not None else Decimal("0"))
                investment_at_start_date_with_currency_effect = (total_investment_with_currency_effect if total_investment_with_currency_effect is not None else Decimal("0"))
                value_at_start_date = value_of_investment_before_transaction
                value_at_start_date_with_currency_effect = value_of_investment_before_transaction_with_currency_effect
            transaction_investment = Decimal("0")
            transaction_investment_with_currency_effect = Decimal("0")
            if (order.type == "BUY"):
                transaction_investment = ((order.quantity * order.unit_price_in_base_currency) * get_factor(order.type))
                transaction_investment_with_currency_effect = ((order.quantity * order.unit_price_in_base_currency_with_currency_effect) * get_factor(order.type))
                total_quantity_from_buy_transactions = (total_quantity_from_buy_transactions + order.quantity)
                total_investment_from_buy_transactions = (total_investment_from_buy_transactions + transaction_investment)
                total_investment_from_buy_transactions_with_currency_effect = (total_investment_from_buy_transactions_with_currency_effect + transaction_investment_with_currency_effect)
            elif (order.type == "SELL"):
                if (total_units > 0):
                    transaction_investment = (((total_investment / total_units) * order.quantity) * get_factor(order.type))
                    transaction_investment_with_currency_effect = (((total_investment_with_currency_effect / total_units) * order.quantity) * get_factor(order.type))
            if PortfolioCalculator.ENABLE_LOGGING:
                print("order.quantity", float(order.quantity))
                print("transactionInvestment", float(transaction_investment))
                print("transactionInvestmentWithCurrencyEffect", float(transaction_investment_with_currency_effect))
            total_investment_before_transaction = total_investment
            total_investment_before_transaction_with_currency_effect = total_investment_with_currency_effect
            total_investment = (total_investment + transaction_investment)
            total_investment_with_currency_effect = (total_investment_with_currency_effect + transaction_investment_with_currency_effect)
            if ((i >= index_of_start_order) and not initial_value):
                if ((i == index_of_start_order) and not (value_of_investment_before_transaction == 0)):
                    initial_value = value_of_investment_before_transaction
                    initial_value_with_currency_effect = value_of_investment_before_transaction_with_currency_effect
                elif (transaction_investment > 0):
                    initial_value = transaction_investment
                    initial_value_with_currency_effect = transaction_investment_with_currency_effect
            fees = (fees + (order.fee_in_base_currency if order.fee_in_base_currency is not None else 0))
            fees_with_currency_effect = (fees_with_currency_effect + (order.fee_in_base_currency_with_currency_effect if order.fee_in_base_currency_with_currency_effect is not None else 0))
            total_units = (total_units + (order.quantity * get_factor(order.type)))
            value_of_investment = (total_units * market_price_in_base_currency)
            value_of_investment_with_currency_effect = (total_units * market_price_in_base_currency_with_currency_effect)
            gross_performance_from_sell = (((order.unit_price_in_base_currency - last_average_price) * order.quantity) if (order.type == "SELL") else Decimal("0"))
            gross_performance_from_sell_with_currency_effect = (((order.unit_price_in_base_currency_with_currency_effect - last_average_price_with_currency_effect) * order.quantity) if (order.type == "SELL") else Decimal("0"))
            gross_performance_from_sells = (gross_performance_from_sells + gross_performance_from_sell)
            gross_performance_from_sells_with_currency_effect = (gross_performance_from_sells_with_currency_effect + gross_performance_from_sell_with_currency_effect)
            last_average_price = (Decimal("0") if (total_quantity_from_buy_transactions == 0) else (total_investment_from_buy_transactions / total_quantity_from_buy_transactions))
            last_average_price_with_currency_effect = (Decimal("0") if (total_quantity_from_buy_transactions == 0) else (total_investment_from_buy_transactions_with_currency_effect / total_quantity_from_buy_transactions))
            if (total_units == 0):
                total_investment_from_buy_transactions = Decimal("0")
                total_investment_from_buy_transactions_with_currency_effect = Decimal("0")
                total_quantity_from_buy_transactions = Decimal("0")
            if PortfolioCalculator.ENABLE_LOGGING:
                print("grossPerformanceFromSells", float(gross_performance_from_sells))
                print("grossPerformanceFromSellWithCurrencyEffect", float(gross_performance_from_sell_with_currency_effect))
            new_gross_performance = ((value_of_investment - total_investment) + gross_performance_from_sells)
            new_gross_performance_with_currency_effect = ((value_of_investment_with_currency_effect - total_investment_with_currency_effect) + gross_performance_from_sells_with_currency_effect)
            gross_performance = new_gross_performance
            gross_performance_with_currency_effect = new_gross_performance_with_currency_effect
            if (order.item_type == "start"):
                fees_at_start_date = fees
                fees_at_start_date_with_currency_effect = fees_with_currency_effect
                gross_performance_at_start_date = gross_performance
                gross_performance_at_start_date_with_currency_effect = gross_performance_with_currency_effect
            if (i > index_of_start_order):
                if ((value_of_investment_before_transaction > 0) and (order.type in ["BUY", "SELL"])):
                    order_date = datetime.fromisoformat(str(order.date))
                    previous_order_date = datetime.fromisoformat(str(orders[(i - 1)].date))
                    days_since_last_order = (order_date - previous_order_date).days
                    if (days_since_last_order <= 0):
                        days_since_last_order = 1e-10
                    total_investment_days += days_since_last_order
                    sum_of_time_weighted_investments = (sum_of_time_weighted_investments + (((value_at_start_date - investment_at_start_date) + total_investment_before_transaction) * days_since_last_order))
                    sum_of_time_weighted_investments_with_currency_effect = (sum_of_time_weighted_investments_with_currency_effect + (((value_at_start_date_with_currency_effect - investment_at_start_date_with_currency_effect) + total_investment_before_transaction_with_currency_effect) * days_since_last_order))
                current_values[order.date] = value_of_investment
                current_values_with_currency_effect[order.date] = value_of_investment_with_currency_effect
                net_performance_values[order.date] = ((gross_performance - gross_performance_at_start_date) - (fees - fees_at_start_date))
                net_performance_values_with_currency_effect[order.date] = ((gross_performance_with_currency_effect - gross_performance_at_start_date_with_currency_effect) - (fees_with_currency_effect - fees_at_start_date_with_currency_effect))
                investment_values_accumulated[order.date] = total_investment
                investment_values_accumulated_with_currency_effect[order.date] = total_investment_with_currency_effect
                investment_values_with_currency_effect[order.date] = ((investment_values_with_currency_effect[order.date] if investment_values_with_currency_effect[order.date] is not None else Decimal("0")) + transaction_investment_with_currency_effect)
                time_weighted_investment_values[order.date] = ((sum_of_time_weighted_investments / total_investment_days) if (total_investment_days > 1e-10) else (total_investment if (total_investment > 0) else Decimal("0")))
                time_weighted_investment_values_with_currency_effect[order.date] = ((sum_of_time_weighted_investments_with_currency_effect / total_investment_days) if (total_investment_days > 1e-10) else (total_investment_with_currency_effect if (total_investment_with_currency_effect > 0) else Decimal("0")))
            if PortfolioCalculator.ENABLE_LOGGING:
                print("totalInvestment", float(total_investment))
                print("totalInvestmentWithCurrencyEffect", float(total_investment_with_currency_effect))
                print("totalGrossPerformance", float((gross_performance - gross_performance_at_start_date)))
                print("totalGrossPerformanceWithCurrencyEffect", float((gross_performance_with_currency_effect - gross_performance_at_start_date_with_currency_effect)))
            if (i == index_of_end_order):
                break
        total_gross_performance = (gross_performance - gross_performance_at_start_date)
        total_gross_performance_with_currency_effect = (gross_performance_with_currency_effect - gross_performance_at_start_date_with_currency_effect)
        total_net_performance = ((gross_performance - gross_performance_at_start_date) - (fees - fees_at_start_date))
        time_weighted_average_investment_between_start_and_end_date = ((sum_of_time_weighted_investments / total_investment_days) if (total_investment_days > 0) else Decimal("0"))
        time_weighted_average_investment_between_start_and_end_date_with_currency_effect = ((sum_of_time_weighted_investments_with_currency_effect / total_investment_days) if (total_investment_days > 0) else Decimal("0"))
        gross_performance_percentage = ((total_gross_performance / time_weighted_average_investment_between_start_and_end_date) if (time_weighted_average_investment_between_start_and_end_date > 0) else Decimal("0"))
        gross_performance_percentage_with_currency_effect = ((total_gross_performance_with_currency_effect / time_weighted_average_investment_between_start_and_end_date_with_currency_effect) if (time_weighted_average_investment_between_start_and_end_date_with_currency_effect > 0) else Decimal("0"))
        fees_per_unit = (((fees - fees_at_start_date) / total_units) if (total_units > 0) else Decimal("0"))
        fees_per_unit_with_currency_effect = (((fees_with_currency_effect - fees_at_start_date_with_currency_effect) / total_units) if (total_units > 0) else Decimal("0"))
        net_performance_percentage = ((total_net_performance / time_weighted_average_investment_between_start_and_end_date) if (time_weighted_average_investment_between_start_and_end_date > 0) else Decimal("0"))
        net_performance_percentage_with_currency_effect_map = {}
        net_performance_with_currency_effect_map = {}
        for date_range in ["1d", "1y", "5y", "max", "mtd", "wtd", "ytd", *[date.strftime("%Y") for date in [date for date in _each_year_of_interval({"end": end, "start": start}) if not (date.year == datetime.now().year)]]]:
            date_interval = get_interval_from_date_range(date_range)
            end_date = date_interval.end_date
            start_date = date_interval.start_date
            if (start_date < start):
                start_date = start
            range_end_date_string = end_date.strftime(DATE_FORMAT)
            range_start_date_string = start_date.strftime(DATE_FORMAT)
            current_values_at_date_range_start_with_currency_effect = (current_values_with_currency_effect[range_start_date_string] if current_values_with_currency_effect[range_start_date_string] is not None else Decimal("0"))
            investment_values_accumulated_at_start_date_with_currency_effect = (investment_values_accumulated_with_currency_effect[range_start_date_string] if investment_values_accumulated_with_currency_effect[range_start_date_string] is not None else Decimal("0"))
            gross_performance_at_date_range_start_with_currency_effect = (current_values_at_date_range_start_with_currency_effect - investment_values_accumulated_at_start_date_with_currency_effect)
            average = Decimal("0")
            day_count = 0
            while True:
                date = self.chart_dates[i]
                if (date > range_end_date_string):
                    continue
                elif (date < range_start_date_string):
                    break
                if (isinstance(investment_values_accumulated_with_currency_effect[date], Big) and (investment_values_accumulated_with_currency_effect[date] > 0)):
                    average = (average + (investment_values_accumulated_with_currency_effect[date] + gross_performance_at_date_range_start_with_currency_effect))
                    day_count += 1
            if (day_count > 0):
                average = (average / day_count)
            net_performance_with_currency_effect_map[date_range] = ((net_performance_values_with_currency_effect[range_end_date_string] - Decimal("0")) if (net_performance_values_with_currency_effect[range_end_date_string] - Decimal("0")) is not None else Decimal("0"))
            net_performance_percentage_with_currency_effect_map[date_range] = ((net_performance_with_currency_effect_map[date_range] / average) if (average > 0) else Decimal("0"))
        if PortfolioCalculator.ENABLE_LOGGING:
            pass
        {symbol}
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        pass
        return {
            "currentValues": current_values,
            "currentValuesWithCurrencyEffect": current_values_with_currency_effect,
            "feesWithCurrencyEffect": fees_with_currency_effect,
            "grossPerformancePercentage": gross_performance_percentage,
            "grossPerformancePercentageWithCurrencyEffect": gross_performance_percentage_with_currency_effect,
            "initialValue": initial_value,
            "initialValueWithCurrencyEffect": initial_value_with_currency_effect,
            "investmentValuesAccumulated": investment_values_accumulated,
            "investmentValuesAccumulatedWithCurrencyEffect": investment_values_accumulated_with_currency_effect,
            "investmentValuesWithCurrencyEffect": investment_values_with_currency_effect,
            "netPerformancePercentage": net_performance_percentage,
            "netPerformancePercentageWithCurrencyEffectMap": net_performance_percentage_with_currency_effect_map,
            "netPerformanceValues": net_performance_values,
            "netPerformanceValuesWithCurrencyEffect": net_performance_values_with_currency_effect,
            "netPerformanceWithCurrencyEffectMap": net_performance_with_currency_effect_map,
            "timeWeightedInvestmentValues": time_weighted_investment_values,
            "timeWeightedInvestmentValuesWithCurrencyEffect": time_weighted_investment_values_with_currency_effect,
            "totalAccountBalanceInBaseCurrency": total_account_balance_in_base_currency,
            "totalDividend": total_dividend,
            "totalDividendInBaseCurrency": total_dividend_in_base_currency,
            "totalInterest": total_interest,
            "totalInterestInBaseCurrency": total_interest_in_base_currency,
            "totalInvestment": total_investment,
            "totalInvestmentWithCurrencyEffect": total_investment_with_currency_effect,
            "totalLiabilities": total_liabilities,
            "totalLiabilitiesInBaseCurrency": total_liabilities_in_base_currency,
            "grossPerformance": total_gross_performance,
            "grossPerformanceWithCurrencyEffect": total_gross_performance_with_currency_effect,
            "hasErrors": ((total_units > 0) and (not initial_value or not unit_price_at_end_date)),
            "netPerformance": total_net_performance,
            "timeWeightedInvestment": time_weighted_average_investment_between_start_and_end_date,
            "timeWeightedInvestmentWithCurrencyEffect": time_weighted_average_investment_between_start_and_end_date_with_currency_effect,
        }

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
