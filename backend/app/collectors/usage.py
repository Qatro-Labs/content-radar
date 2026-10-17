from collections import defaultdict
from dataclasses import dataclass

from app.schemas.cost import Provider


@dataclass
class UsageCount:
    calls: int = 0
    units: int = 0


class UsageMeter:
    """Cuenta las llamadas de los collectors a APIs externas (CLAUDE.md §4).

    El collector solo cuenta; el job lo persiste con `services.costs.record_meter`.
    """

    def __init__(self) -> None:
        self.counts: defaultdict[tuple[Provider, str], UsageCount] = defaultdict(UsageCount)

    def add(self, provider: Provider, operation: str, units: int = 1) -> None:
        count = self.counts[(provider, operation)]
        count.calls += 1
        count.units += units
