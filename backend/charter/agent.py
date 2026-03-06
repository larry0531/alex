"""
Chart Maker Agent - creates visualization data for portfolio analysis.
"""

import os
import logging
from typing import Dict, Any

from agents.extensions.models.litellm_model import LitellmModel
from shared.portfolio import calculate_portfolio_value, aggregate_allocations, _safe_float

from templates import CHARTER_INSTRUCTIONS, create_charter_task

logger = logging.getLogger()


def analyze_portfolio(portfolio_data: Dict[str, Any]) -> str:
    """
    Analyze the portfolio to understand its composition and calculate key metrics.
    Returns detailed breakdown of positions, accounts, and calculated allocations.
    """
    result = []
    total_value = calculate_portfolio_value(portfolio_data)
    position_values = {}
    account_totals = {}

    # Calculate position values and totals per account
    for account in portfolio_data.get("accounts", []):
        account_name = account.get("name", "Unknown")
        account_type = account.get("type", "unknown")
        cash = _safe_float(account.get("cash_balance"))

        if account_name not in account_totals:
            account_totals[account_name] = {"value": 0, "type": account_type, "positions": []}

        account_totals[account_name]["value"] += cash

        for position in account.get("positions", []):
            symbol = position.get("symbol")
            quantity = _safe_float(position.get("quantity"))
            instrument = position.get("instrument", {})
            price = _safe_float(instrument.get("current_price"))
            if price == 0.0:
                logger.warning(f"Charter: No price for {symbol}, skipping value")
                continue
            value = quantity * price

            position_values[symbol] = position_values.get(symbol, 0) + value
            account_totals[account_name]["value"] += value
            account_totals[account_name]["positions"].append(
                {"symbol": symbol, "value": value, "instrument": instrument}
            )

    # Build analysis summary
    result.append("Portfolio Analysis:")
    result.append(f"Total Value: ${total_value:,.2f}")
    result.append(f"Number of Accounts: {len(account_totals)}")
    result.append(f"Number of Positions: {len(position_values)}")

    result.append("\nAccount Breakdown:")
    for name, data in account_totals.items():
        pct = (data["value"] / total_value * 100) if total_value > 0 else 0
        result.append(f"  {name} ({data['type']}): ${data['value']:,.2f} ({pct:.1f}%)")

    result.append("\nTop Holdings by Value:")
    sorted_positions = sorted(position_values.items(), key=lambda x: x[1], reverse=True)[:10]
    for symbol, value in sorted_positions:
        pct = (value / total_value * 100) if total_value > 0 else 0
        result.append(f"  {symbol}: ${value:,.2f} ({pct:.1f}%)")

    # Use shared allocation aggregation
    allocations = aggregate_allocations(portfolio_data)
    asset_classes = allocations["asset_classes"]
    regions = allocations["regions"]
    sectors = allocations["sectors"]

    result.append("\nCalculated Allocations:")

    result.append("\nAsset Classes:")
    for asset_class, value in sorted(asset_classes.items(), key=lambda x: x[1], reverse=True):
        result.append(f"  {asset_class}: ${value:,.2f}")

    result.append("\nGeographic Regions:")
    for region, value in sorted(regions.items(), key=lambda x: x[1], reverse=True):
        result.append(f"  {region}: ${value:,.2f}")

    result.append("\nSectors:")
    for sector, value in sorted(sectors.items(), key=lambda x: x[1], reverse=True)[:10]:
        result.append(f"  {sector}: ${value:,.2f}")

    return "\n".join(result)


def create_agent(job_id: str, portfolio_data: Dict[str, Any], db=None):
    """Create the charter agent without tools - will output JSON directly."""
    
    # Get model configuration
    model_id = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-7-sonnet-20250219-v1:0")
    # Set region for LiteLLM Bedrock calls
    bedrock_region = os.getenv("BEDROCK_REGION", "us-west-2")
    os.environ["AWS_REGION_NAME"] = bedrock_region
    
    logger.info(f"Charter: Creating agent with model_id={model_id}, region={bedrock_region}")
    logger.info(f"Charter: Job ID: {job_id}")
    
    model = LitellmModel(model=f"bedrock/{model_id}")
    
    # Analyze the portfolio upfront
    portfolio_analysis = analyze_portfolio(portfolio_data)
    logger.info(f"Charter: Portfolio analysis generated, length: {len(portfolio_analysis)}")
    
    # Create the task using template
    task = create_charter_task(portfolio_analysis, portfolio_data)
    
    logger.info(f"Charter: Task created, length: {len(task)} characters")
    
    # Return model and task (no tools or context needed)
    return model, task