"""
Shared portfolio calculation utilities used across multiple agents.

Consolidates the duplicated portfolio value calculation and allocation
aggregation logic from charter, retirement, reporter, and planner agents.
"""

import logging
from typing import Dict, Any

logger = logging.getLogger()


def _safe_float(value, default: float = 0.0) -> float:
    """Safely convert a value to float, returning default for None/empty."""
    if value is None or value == "":
        return default
    return float(value)


def calculate_portfolio_value(portfolio_data: Dict[str, Any]) -> float:
    """Calculate total portfolio value from portfolio_data dict.

    Iterates through all accounts, summing cash balances and
    position values (quantity * current_price).

    Args:
        portfolio_data: Dict with "accounts" list, each containing
            "cash_balance" and "positions" with "quantity" and "instrument".

    Returns:
        Total portfolio value as float.
    """
    total_value = 0.0

    for account in portfolio_data.get("accounts", []):
        total_value += _safe_float(account.get("cash_balance"))

        for position in account.get("positions", []):
            quantity = _safe_float(position.get("quantity"))
            instrument = position.get("instrument", {})
            price = _safe_float(instrument.get("current_price"))
            if price == 0.0:
                logger.warning(f"No price for {position.get('symbol')}, skipping value")
                continue
            total_value += quantity * price

    return total_value


def aggregate_allocations(portfolio_data: Dict[str, Any]) -> Dict[str, Dict[str, float]]:
    """Aggregate allocation breakdowns across the entire portfolio.

    Computes value-weighted allocation for asset classes, regions, and sectors
    across all positions. Also includes cash as an asset class.

    Args:
        portfolio_data: Dict with "accounts" list.

    Returns:
        Dict with keys "asset_classes", "regions", "sectors",
        each mapping category names to dollar values.
    """
    asset_classes: Dict[str, float] = {}
    regions: Dict[str, float] = {}
    sectors: Dict[str, float] = {}

    for account in portfolio_data.get("accounts", []):
        for position in account.get("positions", []):
            quantity = _safe_float(position.get("quantity"))
            instrument = position.get("instrument", {})
            price = _safe_float(instrument.get("current_price"))
            if price == 0.0:
                continue
            value = quantity * price

            for asset_class, pct in (instrument.get("allocation_asset_class") or {}).items():
                asset_classes[asset_class] = asset_classes.get(asset_class, 0) + value * (pct / 100)

            for region, pct in (instrument.get("allocation_regions") or {}).items():
                regions[region] = regions.get(region, 0) + value * (pct / 100)

            for sector, pct in (instrument.get("allocation_sectors") or {}).items():
                sectors[sector] = sectors.get(sector, 0) + value * (pct / 100)

    # Add cash to asset classes
    total_cash = sum(
        _safe_float(acc.get("cash_balance"))
        for acc in portfolio_data.get("accounts", [])
    )
    if total_cash > 0:
        asset_classes["cash"] = asset_classes.get("cash", 0) + total_cash

    return {
        "asset_classes": asset_classes,
        "regions": regions,
        "sectors": sectors,
    }
