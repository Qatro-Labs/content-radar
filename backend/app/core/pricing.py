"""Precios de data/pricing.yaml para el coste de operación (CLAUDE.md §4)."""

from datetime import date
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel

from app.schemas.cost import Provider

PRICING_FILE = Path(__file__).resolve().parents[3] / "data" / "pricing.yaml"


class VariablePrice(BaseModel):
    unit: str
    # Ausente o null = precio desconocido. El coste queda en null, nunca en 0 (CLAUDE.md §2.3).
    price_per_unit: Decimal | None = None
    # Un LLM cobra distinto la entrada y la salida: `units` son los tokens de entrada.
    input_price_per_unit: Decimal | None = None
    output_price_per_unit: Decimal | None = None
    free_credit_monthly: Decimal | None = None

    def cost(self, units: Decimal, *, output_units: Decimal = Decimal(0)) -> Decimal | None:
        if self.price_per_unit is not None:
            return units * self.price_per_unit
        if self.input_price_per_unit is None or self.output_price_per_unit is None:
            return None
        return units * self.input_price_per_unit + output_units * self.output_price_per_unit


class FixedItem(BaseModel):
    monthly: Decimal


class Pricing(BaseModel):
    currency: str
    checked_at: date
    variable: dict[Provider, VariablePrice]
    fixed_monthly: dict[str, dict[str, FixedItem]]

    def fixed_total(self, profile: str) -> Decimal:
        return sum((item.monthly for item in self.fixed_monthly[profile].values()), Decimal(0))


def load_pricing(path: Path) -> Pricing:
    return Pricing.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


@lru_cache
def get_pricing() -> Pricing:
    return load_pricing(PRICING_FILE)
