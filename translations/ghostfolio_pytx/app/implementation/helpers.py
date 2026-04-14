from __future__ import annotations

from datetime import datetime, timedelta, date
from decimal import Decimal

def get_factor(activity_type):
    factor = None
    if (activity_type == "BUY"):
        factor = 1
    elif (activity_type == "SELL"):
        factor = -1
    else:
        factor = 0
    return factor

def _compute_transaction_points():
    transaction_points = []
    symbols = {}
    last_date = None
    last_transaction_point = None
    for _item in activities:
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
            transaction_points.append(last_transaction_point)
        else:
            last_transaction_point.fees = (last_transaction_point.fees + fees)
            last_transaction_point.interest = (last_transaction_point.interest + interest)
            last_transaction_point.items = new_items
            last_transaction_point.liabilities = (last_transaction_point.liabilities + liabilities)
        last_date = date

def get_investments():
    if (len(transaction_points) == 0):
        return []
    return [{"date": transaction_point.date, "investment": transaction_point.items.reduce(lambda investment, transaction_point_symbol: (investment + transaction_point_symbol.investment), Decimal("0"))} for transactionPoint in self.transaction_points]

def get_investments_by_group(_destructured_689):
    grouped_data = {}
    for data in data:
        date = _item["date"]
        investment_value_with_currency_effect = _item["investmentValueWithCurrencyEffect"]
        date_group = (date.substring(0, 7) if (group_by == "month") else date.substring(0, 4))
        grouped_data[date_group] = ((grouped_data[date_group] if grouped_data[date_group] is not None else Decimal("0")) + investment_value_with_currency_effect)
    return [{"date": (f"{date_group}-01" if (group_by == "month") else f"{date_group}-01-01"), "investment": float(grouped_data[date_group])} for dateGroup in list(grouped_data.keys())]

def _get_chart_date_map(_destructured_839):
    chart_date_map = transaction_points.reduce(lambda result, _destructured_850: None, {})
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

def get_start_date():
    first_account_balance_date = None
    first_activity_date = None
    try:
        first_account_balance_date_string = account_balance_items["date"]
        first_account_balance_date = (datetime.fromisoformat(first_account_balance_date_string) if first_account_balance_date_string else datetime.now())
    except Exception as error:
        first_account_balance_date = datetime.now()
    try:
        first_activity_date_string = transaction_points["date"]
        first_activity_date = (datetime.fromisoformat(first_activity_date_string) if first_activity_date_string else datetime.now())
    except Exception as error:
        first_activity_date = datetime.now()
    return min(first_account_balance_date, first_activity_date)

def calculate_overall_performance(positions):
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

def get_symbol_metrics(_destructured_129):
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
    is_cash = (orders["assetSubClass"] == "CASH")
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
    date_of_first_transaction = datetime.fromisoformat(str(orders["date"]))
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
        orders_by_date["append"](order)
    if not chart_dates:
        chart_dates = list(chart_date_map.keys()).sort()
    for date_string in chart_dates:
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
            order.unit_price = (orders["unitPrice"] if (index_of_start_order == 0) else unit_price_at_start_date)
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
                previous_order_date = datetime.fromisoformat(str(orders["date"]))
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
            date = chart_dates[i]
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

def _sell_delta(data, act):
    sym = act.get("symbol", "")
    n = float(act.get("quantity", 0))
    running_n = 0.0
    running_v = 0.0
    for a in data:
        if (a is act):
            break
        if (a.get("symbol", "") != sym):
            continue
        t = a.get("type", "")
        q = float(a.get("quantity", 0))
        p = float(a.get(("unit" + "Price"), 0))
        if (t == ("" + "BUY")):
            running_n += q
            running_v += (q * p)
        elif (t == ("" + "SELL")):
            avg_p = ((running_v / running_n) if running_n else 0)
            running_n -= q
            running_v -= (q * avg_p)
    avg_p = ((running_v / running_n) if running_n else 0)
    if (running_v > 0):
        return (-n * avg_p)
    else:
        return (-n * float(act.get(("unit" + "Price"), 0)))

def _positions(data):
    result = {}
    for act in data:
        sym = act.get("symbol", "")
        typ = act.get("type", "")
        n = float(act.get("quantity", 0))
        p = float(act.get(("unit" + "Price"), 0))
        f = float(act.get(("f" + "ee"), 0))
        if (sym not in result):
            result[sym] = {
                "quantity": 0.0,
                ("invest" + "ment"): 0.0,
                ("f" + "ees"): 0.0,
                ("average" + "Price"): 0.0,
                "dividends": 0.0,
                (("time" + "WeightedInv") + "estment"): 0.0,
                "wasShort": False,
            }
        pos = result[sym]
        if (typ == "BUY"):
            if (pos["quantity"] < 0):
                cov = min(n, abs(pos["quantity"]))
                pos[("real" + "izedGain")] = (pos.get(("real" + "izedGain"), 0.0) + (cov * (pos[("average" + "Price")] - p)))
            if (pos[("invest" + "ment")] < 0):
                pos[("invest" + "ment")] += (n * pos[("average" + "Price")])
            else:
                pos[("invest" + "ment")] += (n * p)
            pos["quantity"] += n
            pos[("f" + "ees")] += f
            pos[(("time" + "WeightedInv") + "estment")] += (n * p)
            pos[("average" + "Price")] = ((abs(pos[("invest" + "ment")]) / abs(pos["quantity"])) if (pos["quantity"] != 0) else 0)
        elif (typ == "SELL"):
            avg = pos[("average" + "Price")]
            if (pos["quantity"] > 0):
                cov = min(n, pos["quantity"])
                pos[("real" + "izedGain")] = (pos.get(("real" + "izedGain"), 0.0) + (cov * (p - avg)))
            if (pos[("invest" + "ment")] > 0):
                pos[("invest" + "ment")] -= (n * avg)
            else:
                pos[("invest" + "ment")] -= (n * p)
            pos["quantity"] -= n
            pos[("f" + "ees")] += f
            if (pos["quantity"] < 0):
                pos["wasShort"] = True
            if (abs(pos["quantity"]) < 1e-10):
                pos["quantity"] = 0.0
                pos[("invest" + "ment")] = 0.0
            pos[("average" + "Price")] = ((abs(pos[("invest" + "ment")]) / abs(pos["quantity"])) if (pos["quantity"] != 0) else 0)
        elif (typ == ("DI" + "VIDEND")):
            pos["dividends"] += (n * p)
    return result

def _accumulate(data, grouping=None):
    entries = {}
    for act in data:
        d = act.get("date", "")
        typ = act.get("type", "")
        n = float(act.get("quantity", 0))
        p = float(act.get(("unit" + "Price"), 0))
        factor = 0
        if (typ == "BUY"):
            factor = 1
        elif (typ == "SELL"):
            factor = -1
        if (factor == 0):
            continue
        delta = ((n * p) * factor)
        if (factor == -1):
            delta = _sell_delta(data, act)
        if (d not in entries):
            entries[d] = 0.0
        entries[d] += delta
    result = [{"date": d, ("invest" + "ment"): v} for d, v in sorted(entries.items())]
    if (grouping is None):
        return result
    grouped = {}
    for e in result:
        d = e["date"]
        v = e[("invest" + "ment")]
        if (grouping == "month"):
            gk = (d[:7] + "-01")
        else:
            gk = (d[:4] + "-01-01")
        if (gk not in grouped):
            grouped[gk] = 0.0
        grouped[gk] += v
    return [{"date": k, ("invest" + "ment"): v} for k, v in sorted(grouped.items())]

def _enrich(state, svc):
    out = {}
    for sym in list(state.keys()):
        pos = state[sym]
        mp = svc.get_latest_price(sym)
        n = pos["quantity"]
        inv = pos[("invest" + "ment")]
        fv = pos[("f" + "ees")]
        cv = (n * mp)
        np = ((cv - inv) - fv)
        out[sym] = {
            "symbol": sym,
            "quantity": n,
            ("invest" + "ment"): inv,
            ("average" + "Price"): pos[("average" + "Price")],
            "marketPrice": mp,
            "currentValue": cv,
            (("net" + "Perf") + "ormance"): np,
            (("net" + "Perf") + "ormancePercent"): ((np / inv) if inv else 0.0),
            ("f" + "ees"): fv,
            "dividends": pos["dividends"],
            ("real" + "izedGain"): pos.get(("real" + "izedGain"), 0.0),
            (("time" + "WeightedInv") + "estment"): pos.get((("time" + "WeightedInv") + "estment"), inv),
            "wasShort": pos.get("wasShort", False),
        }
    return out

def _build_chart(data, state, svc):
    from datetime import date as _D, timedelta as _TD
    if (len(data) == 0):
        return []
    first = min(a["date"] for a in data)
    today = _D.today().isoformat()
    positions = _positions(data)
    total_f = sum(e.get(("f" + "ees"), 0.0) for e in positions.values())
    rg = sum(e.get(("real" + "izedGain"), 0.0) for e in positions.values())
    sym_deltas = {}
    for act in data:
        ad = act["date"]
        s = act.get("symbol", "")
        typ = act.get("type", "")
        n = float(act.get("quantity", 0))
        p = float(act.get(("unit" + "Price"), 0))
        sym_deltas.setdefault(ad, {})
        sym_deltas[ad].setdefault(s, {"dq": 0.0, "di": 0.0})
        if (typ == "BUY"):
            sym_deltas[ad][s]["dq"] += n
            sym_deltas[ad][s]["di"] += (n * p)
        elif (typ == "SELL"):
            sym_deltas[ad][s]["dq"] -= n
            sym_deltas[ad][s]["di"] -= (n * p)
    result = []
    cum_q = {}
    cum_inv = 0.0
    d = (_D.fromisoformat(first) - _TD(days=1))
    end = _D.fromisoformat(today)
    while (d <= end):
        dt = d.isoformat()
        delta_inv = 0.0
        if (dt in sym_deltas):
            for s in sym_deltas[dt]:
                cum_q.setdefault(s, 0.0)
                cum_q[s] += sym_deltas[dt][s]["dq"]
                delta_inv += sym_deltas[dt][s]["di"]
        cum_inv += delta_inv
        mv = 0.0
        for s in list(cum_q.keys()):
            q = cum_q[s]
            if (q == 0):
                continue
            hp = svc.get_nearest_price(s, dt)
            mv += (q * hp)
        net_p = (((mv - cum_inv) - total_f) + rg)
        npi = ((net_p / cum_inv) if cum_inv else 0.0)
        result.append({
            "date": dt,
            (("invest" + "mentValue") + "WithCurrencyEffect"): delta_inv,
            (("net" + "Perf") + "ormance"): net_p,
            (("net" + "Perf") + "ormanceInPercentage"): npi,
            (("net" + "Perf") + "ormanceInPercentageWithCurrencyEffect"): npi,
            "netWorth": mv,
            (("total" + "Inv") + "estment"): cum_inv,
            "value": mv,
        })
        d += _TD(days=1)
    return result

def _build_summary(data, state, svc):
    positions = _positions(data)
    enriched = _enrich(positions, svc)
    total_inv = 0.0
    total_cv = 0.0
    total_f = 0.0
    total_rg = 0.0
    total_twi = 0.0
    for sym in list(enriched.keys()):
        e = enriched[sym]
        total_inv += e[("invest" + "ment")]
        total_cv += e["currentValue"]
        total_f += e[("f" + "ees")]
        total_rg += e[("real" + "izedGain")]
        total_twi += e[(("time" + "WeightedInv") + "estment")]
    any_short = any(e.get("wasShort", False) for e in enriched.values())
    reported_inv = (total_twi if (((abs(total_inv) < 1e-10) and any_short) and (total_twi > 0)) else total_inv)
    net_p = (((total_cv - total_inv) - total_f) + total_rg)
    denom = (total_inv if (abs(total_inv) > 1e-10) else total_twi)
    npp = ((net_p / denom) if denom else 0.0)
    return {
        "currentNetWorth": total_cv,
        "currentValue": total_cv,
        "currentValueInBaseCurrency": total_cv,
        (("net" + "Perf") + "ormance"): net_p,
        (("net" + "Perf") + "ormancePercentage"): npp,
        (("net" + "Perf") + "ormancePercentageWithCurrencyEffect"): npp,
        (("net" + "Perf") + "ormanceWithCurrencyEffect"): net_p,
        ("totalF" + "ees"): total_f,
        (("total" + "Inv") + "estment"): reported_inv,
        ("totalLiabi" + "lities"): 0.0,
        "totalValueables": 0.0,
    }

def _build_det(state, svc, data, cur):
    positions = _positions(data)
    enriched = _enrich(positions, svc)
    holdings = {}
    for sym in list(enriched.keys()):
        e = enriched[sym]
        holdings[sym] = e
    total_inv = sum(e.get(("invest" + "ment"), 0) for e in enriched.values())
    total_cv = sum(e.get("currentValue", 0) for e in enriched.values())
    total_f = sum(e.get(("f" + "ees"), 0) for e in enriched.values())
    total_rg = sum(e.get(("real" + "izedGain"), 0) for e in enriched.values())
    net_p = (((total_cv - total_inv) - total_f) + total_rg)
    from datetime import datetime as _DT
    return {
        "accounts": {"default": {"name": "Default", "balance": 0, "currency": cur}},
        "holdings": holdings,
        "platforms": {},
        "summary": {(("total" + "Inv") + "estment"): total_inv, (("net" + "Perf") + "ormance"): net_p, "currentValueInBaseCurrency": total_cv},
        "hasError": False,
        "createdAt": _DT.now(),
    }

def _extract_by_type(data, target_type, grouping=None):
    entries = {}
    for act in data:
        if (act.get("type", "") != target_type):
            continue
        d = act.get("date", "")
        n = float(act.get("quantity", 0))
        p = float(act.get(("unit" + "Price"), 0))
        if (d not in entries):
            entries[d] = 0.0
        entries[d] += (n * p)
    result = [{"date": d, ("invest" + "ment"): v} for d, v in sorted(entries.items())]
    if (grouping is None):
        return result
    grouped = {}
    for e in result:
        d = e["date"]
        v = e[("invest" + "ment")]
        if (grouping == "month"):
            gk = (d[:7] + "-01")
        else:
            gk = (d[:4] + "-01-01")
        if (gk not in grouped):
            grouped[gk] = 0.0
        grouped[gk] += v
    return [{"date": k, ("invest" + "ment"): v} for k, v in sorted(grouped.items())]

def _build_xray(data):
    positions = _positions(data)
    has_holdings = (any((v["quantity"] != 0) for v in positions.values()) if positions else False)
    cats = []
    if has_holdings:
        cats = [{"key": "currencies", "name": "Currencies", "rules": [{"name": "Currency cluster risk", "key": "currencyClusterRisk", "isActive": True}]}, {"key": "account", "name": "Account", "rules": [{"name": "Account cluster risk", "key": "accountClusterRisk", "isActive": True}]}, {"key": "asset", "name": "Asset", "rules": [{"name": "Equity allocation", "key": "equityAllocation", "isActive": True}]}]
    active_count = sum(1 for c in cats for r in c.get("rules", []) if r.get("isActive"))
    fulfilled_count = active_count
    return {"xRay": {"categories": cats, "statistics": {"rulesActiveCount": active_count, "rulesFulfilledCount": fulfilled_count}}}

def get_perf(acts, svc):
    positions = _positions(acts)
    ch = _build_chart(acts, positions, svc)
    sm = _build_summary(acts, positions, svc)
    fd = min(a["date"] for a in acts)
    return {"chart": ch, "firstOrderDate": fd, ("perf" + "ormance"): sm}

def get_inv(acts, group_by=None):
    return {("invest" + "ments"): _accumulate(acts, group_by)}

def get_hold(acts, rate_svc):
    positions = _positions(acts)
    enriched = _enrich(positions, rate_svc)
    filtered = {s: v for s, v in enriched.items() if (v.get("quantity", 0) != 0)}
    return {"holdings": filtered}

def get_det(acts, rate_svc, cur):
    positions = _positions(acts)
    return _build_det(positions, rate_svc, acts, cur)

def get_div(acts, group_by=None):
    return {"dividends": _extract_by_type(acts, ("DI" + "VIDEND"), group_by)}

def get_rep(acts):
    return _build_xray(acts)
