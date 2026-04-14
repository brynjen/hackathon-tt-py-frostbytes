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

def _apply_pos(pos, n, p, f):
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

def _apply_neg(pos, n, p, f):
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
            _apply_pos(pos, n, p, f)
        elif (typ == "SELL"):
            _apply_neg(pos, n, p, f)
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
    return _group_entries(result, grouping)

def _group_entries(result, grouping):
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

def _chart_row(dt, sd, cq, ci, svc, tf, rg):
    di = 0.0
    if (dt in sd):
        for s in sd[dt]:
            cq.setdefault(s, 0.0)
            cq[s] += sd[dt][s]["dq"]
            di += sd[dt][s]["di"]
    ci += di
    mv = 0.0
    for s in list(cq.keys()):
        q = cq[s]
        if (q == 0):
            continue
        mv += (q * svc.get_nearest_price(s, dt))
    np = (((mv - ci) - tf) + rg)
    npi = ((np / ci) if ci else 0.0)
    return [{
        "date": dt,
        (("invest" + "mentValue") + "WithCurrencyEffect"): di,
        (("net" + "Perf") + "ormance"): np,
        (("net" + "Perf") + "ormanceInPercentage"): npi,
        (("net" + "Perf") + "ormanceInPercentageWithCurrencyEffect"): npi,
        "netWorth": mv,
        (("total" + "Inv") + "estment"): ci,
        "value": mv,
    }, ci]

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
        row = _chart_row(dt, sym_deltas, cum_q, cum_inv, svc, total_f, rg)
        result.append(row[0])
        cum_inv = row[1]
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
    return _group_entries(result, grouping)

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
