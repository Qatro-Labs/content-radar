from typing import Protocol

from app.models import Source
from app.schemas.signal import ContentSignal


class SignalCollector(Protocol):
    """Interfaz común de todos los conectores (CLAUDE.md §5).

    Recibe una fuente dada de alta y devuelve señales normalizadas. No escribe en la DB:
    la persistencia la hace `services.signals.store_signals`.
    """

    async def collect(self, source: Source, *, backfill_days: int = 14) -> list[ContentSignal]: ...
