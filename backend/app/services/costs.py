"""Registro de consumo de APIs externas y coste de operación (CLAUDE.md §4)."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.usage import UsageMeter
from app.core.pricing import Pricing, get_pricing
from app.models import UsageEvent
from app.schemas.cost import (
    CostPeriod,
    MeasuredCost,
    MonthlyProjection,
    OperatingCost,
    Provider,
    ProviderCost,
)

MONTH_DAYS = 30
# La proyección escala lo medido a 30 días. Con menos de un día observado, una sola ejecución
# se multiplicaría por cientos: se toma un día como mínimo.
MIN_PROJECTION_DAYS = 1.0
SECONDS_PER_DAY = 86400
USD_DECIMALS = 6


def _new_event(
    provider: Provider,
    operation: str,
    units: int | float | Decimal,
    *,
    calls: int = 1,
    pipeline_run_id: int | None = None,
    details: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
) -> UsageEvent:
    price = get_pricing().variable[provider]
    amount = Decimal(str(units))
    return UsageEvent(
        occurred_at=occurred_at or datetime.now(UTC),
        provider=provider.value,
        operation=operation,
        calls=calls,
        units=amount,
        unit=price.unit,
        cost_usd=price.cost(amount),
        pipeline_run_id=pipeline_run_id,
        details=details,
    )


async def record_usage(
    session: AsyncSession,
    provider: Provider,
    operation: str,
    units: int | float | Decimal,
    *,
    calls: int = 1,
    pipeline_run_id: int | None = None,
    details: dict[str, Any] | None = None,
    occurred_at: datetime | None = None,
) -> UsageEvent:
    """Guarda un consumo con su coste según pricing.yaml (null si el precio es desconocido)."""
    event = _new_event(
        provider,
        operation,
        units,
        calls=calls,
        pipeline_run_id=pipeline_run_id,
        details=details,
        occurred_at=occurred_at,
    )
    session.add(event)
    await session.commit()
    return event


async def record_meter(
    session: AsyncSession, meter: UsageMeter, *, pipeline_run_id: int | None = None
) -> int:
    """Persiste lo contado por los collectors: una fila por proveedor y operación."""
    events = [
        _new_event(provider, operation, c.units, calls=c.calls, pipeline_run_id=pipeline_run_id)
        for (provider, operation), c in meter.counts.items()
    ]
    session.add_all(events)
    await session.commit()
    return len(events)


@dataclass
class ProviderTotal:
    provider: Provider
    unit: str
    units: Decimal
    calls: int
    cost_usd: Decimal | None
    unknown_price_events: int
    first_at: datetime


async def _provider_totals(
    session: AsyncSession, start: datetime, end: datetime
) -> list[ProviderTotal]:
    stmt = (
        select(
            UsageEvent.provider,
            UsageEvent.unit,
            func.sum(UsageEvent.units),
            func.sum(UsageEvent.calls),
            # SUM ignora los null: si ningún evento tiene precio, el resultado es null, no 0.
            func.sum(UsageEvent.cost_usd),
            func.count().filter(UsageEvent.cost_usd.is_(None)),
            func.min(UsageEvent.occurred_at),
        )
        .where(UsageEvent.occurred_at >= start, UsageEvent.occurred_at <= end)
        .group_by(UsageEvent.provider, UsageEvent.unit)
        .order_by(UsageEvent.provider)
    )
    rows = (await session.execute(stmt)).all()
    return [ProviderTotal(Provider(row[0]), *row[1:]) for row in rows]


def observed_days(first_at: datetime | None, now: datetime) -> float | None:
    if first_at is None:
        return None
    return max((now - first_at).total_seconds() / SECONDS_PER_DAY, MIN_PROJECTION_DAYS)


def project_variable(
    totals: list[ProviderTotal], days: float | None, pricing: Pricing
) -> Decimal | None:
    """Coste variable mensual estimado: lo medido escalado a 30 días, menos el crédito gratis."""
    known = [(t.provider, t.cost_usd) for t in totals if t.cost_usd is not None]
    if days is None or not known:
        return None
    scale = Decimal(MONTH_DAYS) / Decimal(str(days))
    projected = Decimal(0)
    for provider, cost in known:
        credit = pricing.variable[provider].free_credit_monthly or Decimal(0)
        projected += max(cost * scale - credit, Decimal(0))
    return projected


def _usd(value: Decimal | None) -> float | None:
    return None if value is None else round(float(value), USD_DECIMALS)


def _projection(
    pricing: Pricing, profile: str, variable: Decimal | None, days: float | None
) -> MonthlyProjection:
    fixed = pricing.fixed_total(profile)
    return MonthlyProjection(
        fixed_usd=float(fixed),
        variable_usd=_usd(variable),
        total_usd=None if variable is None else _usd(fixed + variable),
        based_on_days=None if days is None else round(days, 2),
    )


def _limitations(totals: list[ProviderTotal], days: float | None, pricing: Pricing) -> list[str]:
    if days is None:
        return ["Sin consumo registrado en el periodo: no hay coste variable que medir."]
    notes = [f"La proyección mensual es una estimación: escala {days:.1f} días de consumo a 30."]
    credited = [t.provider for t in totals if pricing.variable[t.provider].free_credit_monthly]
    if credited:
        notes.append(f"La proyección descuenta el crédito mensual gratis de: {', '.join(credited)}")
    unknown = sum(t.unknown_price_events for t in totals)
    if unknown:
        notes.append(f"Consumos sin precio conocido (no suman al coste): {unknown}.")
    return notes


async def operating_cost(
    session: AsyncSession, period: CostPeriod, *, now: datetime
) -> OperatingCost:
    pricing = get_pricing()
    start = now - timedelta(days=period.days)
    totals = await _provider_totals(session, start, now)
    days = observed_days(min((t.first_at for t in totals), default=None), now)
    variable = project_variable(totals, days, pricing)
    known_costs = [t.cost_usd for t in totals if t.cost_usd is not None]

    return OperatingCost(
        period=period,
        currency=pricing.currency,
        pricing_checked_at=pricing.checked_at,
        measured_since=await session.scalar(select(func.min(UsageEvent.occurred_at))),
        measured=MeasuredCost(
            window_start=start,
            window_end=now,
            total_usd=_usd(sum(known_costs, Decimal(0))) if known_costs else None,
            unknown_price_events=sum(t.unknown_price_events for t in totals),
            providers=[
                ProviderCost(
                    provider=t.provider,
                    unit=t.unit,
                    units=float(t.units),
                    calls=t.calls,
                    cost_usd=_usd(t.cost_usd),
                    unknown_price_events=t.unknown_price_events,
                )
                for t in totals
            ],
        ),
        projection={
            profile: _projection(pricing, profile, variable, days)
            for profile in pricing.fixed_monthly
        },
        limitations=_limitations(totals, days, pricing),
    )
