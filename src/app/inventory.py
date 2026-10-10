"""A transparent daily replenishment rule, separate from machine learning."""

import math


import math


def replenishment_plan(
    forecast_units,
    stock_on_hand,
    incoming_units=0,
    safety_units=0,
):
    """Calculate the recommended replenishment order for an automotive part."""
    print(forecast_units, stock_on_hand, incoming_units, safety_units)
    forecast_units = max(0, forecast_units)
    stock_on_hand = max(0, stock_on_hand)
    incoming_units = max(0, incoming_units)
    safety_units = max(0, safety_units)

    target_stock = math.ceil(forecast_units + safety_units)
    print(target_stock)
    available_stock = stock_on_hand + incoming_units
    print(available_stock)
    suggested_order = max(0, target_stock - available_stock)

    return {
        "forecast_units": forecast_units,
        "target_stock": target_stock,
        "available_stock": available_stock,
        "suggested_order": suggested_order,
        "safety_units": safety_units,
    }

