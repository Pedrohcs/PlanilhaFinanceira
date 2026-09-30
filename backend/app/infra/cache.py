"""Cache em memória por aba, com TTL e invalidação na escrita (`SPECS/02` §5.5, ADR-05).

Existe para respeitar a cota do Google, não para ser uma segunda fonte de
dados: toda escrita numa aba apaga a entrada dela, e `invalidar_tudo()` é o
"recarregar" de T-032. Seguro entre threads (endpoints síncronos do FastAPI
rodam num pool).
"""

import threading
import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any


class CacheAbas:
    def __init__(
        self, ttl_segundos: float, *, relogio: Callable[[], float] = time.monotonic
    ) -> None:
        self._ttl = ttl_segundos
        self._relogio = relogio
        self._entradas: dict[str, tuple[float, Any]] = {}
        # Cada invalidação avança a geração da aba. Uma leitura que começou
        # antes de uma escrita não grava o resultado (já velho) no cache.
        self._geracoes: defaultdict[str, int] = defaultdict(int)
        self._trava = threading.Lock()

    def obter[T](self, aba: str, carregar: Callable[[], T]) -> T:
        """Valor em cache da aba, ou `carregar()` se ausente ou vencido."""
        agora = self._relogio()
        with self._trava:
            entrada = self._entradas.get(aba)
            if entrada is not None and agora - entrada[0] < self._ttl:
                return entrada[1]
            geracao = self._geracoes[aba]
        # Carrega fora da trava: uma leitura lenta do Google não segura as outras.
        valor = carregar()
        with self._trava:
            if self._geracoes[aba] == geracao:
                self._entradas[aba] = (agora, valor)
        return valor

    def invalidar(self, aba: str) -> None:
        with self._trava:
            self._entradas.pop(aba, None)
            self._geracoes[aba] += 1

    def invalidar_tudo(self) -> None:
        with self._trava:
            for aba in set(self._entradas) | set(self._geracoes):
                self._geracoes[aba] += 1
            self._entradas.clear()
