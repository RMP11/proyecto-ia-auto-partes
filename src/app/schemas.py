"""Validate the public forecast request. Historical model inputs are computed internally."""

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.app.settings import PRODUCTS, BRANCHES


class ForecastInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    branch_id: str
    product_id: str
    forecast_date: date
    # planned_promotion: int = Field(ge=0, le=1, strict=True)
    stock_on_hand: int = Field(ge=0, le=100000, strict=True)
    incoming_units: int = Field(ge=0, le=100000, strict=True)
    safety_units: int = Field(ge=0, le=1000, strict=True)

    @field_validator("branch_id")
    @classmethod
    def known_branch(cls, value: str) -> str:
        if value not in BRANCHES:
            raise ValueError(f"La sucursal '{value}' no existe en el catálogo. Elige una sucursal válida.")
        return value

    @field_validator("product_id")
    @classmethod
    def known_product(cls, value: str) -> str:
        if value not in PRODUCTS:
            raise ValueError(f"El producto '{value}' no existe en el catálogo de repuestos.")
        return value

