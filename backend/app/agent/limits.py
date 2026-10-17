"""Límites del agente del Radar (plan data-radar-agent, D3).

En memoria: la API corre en una sola réplica (backend/Dockerfile) y perderlos al reiniciar no
importa. El endpoint es público y gasta la clave del LLM.
"""

from collections import defaultdict, deque
from datetime import datetime, timedelta
from enum import StrEnum

MAX_STEPS = 8
# Lo que se lee de un vistazo en la barra del agente (DESIGN.md §7); el corte duro está en D13.
MAX_ANSWER_WORDS = 120
MAX_OUTPUT_TOKENS = 1500
PER_IP_PER_HOUR = 20
GLOBAL_PER_DAY = 300
IP_WINDOW = timedelta(hours=1)
GLOBAL_WINDOW = timedelta(days=1)


class LimitResult(StrEnum):
    OK = "ok"
    IP = "ip"
    GLOBAL = "global"


def _drop_older(times: deque[datetime], since: datetime) -> None:
    while times and times[0] <= since:
        times.popleft()


class RateLimiter:
    """Ventanas deslizantes; solo cuentan las preguntas aceptadas."""

    def __init__(self, *, per_ip_per_hour: int, global_per_day: int) -> None:
        self._per_ip_per_hour = per_ip_per_hour
        self._global_per_day = global_per_day
        self._by_ip: defaultdict[str, deque[datetime]] = defaultdict(deque)
        self._all: deque[datetime] = deque()

    def check(self, ip: str, now: datetime) -> LimitResult:
        _drop_older(self._all, now - GLOBAL_WINDOW)
        if len(self._all) >= self._global_per_day:
            return LimitResult.GLOBAL
        ip_times = self._by_ip[ip]
        _drop_older(ip_times, now - IP_WINDOW)
        if len(ip_times) >= self._per_ip_per_hour:
            return LimitResult.IP
        ip_times.append(now)
        self._all.append(now)
        return LimitResult.OK
