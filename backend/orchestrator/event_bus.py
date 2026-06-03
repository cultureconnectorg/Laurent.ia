"""
event_bus.py — Bus d'événements asyncio in-process pour les 20 agents.

Architecture pub/sub légère :
  - Chaque canal possède une asyncio.Queue dédiée.
  - Les abonnés (agents) consomment via une coroutine background.
  - publish() est NON-BLOQUANT (put_nowait, drop si queue pleine — l'agent est sans
    doute en surcharge, on préfère perdre un log que ralentir le streaming SSE).

Le bus est instancié UNE FOIS au startup et attaché à app.state.event_bus.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Awaitable, Callable

from .signals import Signal

logger = logging.getLogger(__name__)

MAX_QUEUE_SIZE = 1024  # Au-delà, on drop les nouveaux signaux (back-pressure protection)


class EventBus:
    """Bus pub/sub asyncio.Queue par canal."""

    def __init__(self) -> None:
        self._queues: dict[str, asyncio.Queue[Signal]] = {}
        self._subscribers: dict[str, list[Callable[[Signal], Awaitable[None]]]] = defaultdict(list)
        self._tasks: list[asyncio.Task] = []
        self._dropped: int = 0

    def _ensure_queue(self, channel: str) -> asyncio.Queue:
        if channel not in self._queues:
            self._queues[channel] = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
        return self._queues[channel]

    def subscribe(self, channel: str, handler: Callable[[Signal], Awaitable[None]]) -> None:
        """Enregistre un handler pour un canal. Le dispatcher démarre via start()."""
        self._subscribers[channel].append(handler)
        self._ensure_queue(channel)

    def publish(self, signal: Signal) -> bool:
        """
        Publie sur le canal du signal (NON-BLOQUANT).
        Retourne True si mis en queue, False si dropped (queue pleine).
        """
        q = self._ensure_queue(signal.channel)
        try:
            q.put_nowait(signal)
            return True
        except asyncio.QueueFull:
            self._dropped += 1
            logger.warning("event_bus: dropped signal on %s (queue full)", signal.channel)
            return False

    async def _dispatch_loop(self, channel: str) -> None:
        """Boucle de distribution pour un canal. Lance tous les handlers en parallèle."""
        q = self._ensure_queue(channel)
        while True:
            try:
                signal = await q.get()
            except asyncio.CancelledError:
                raise
            handlers = list(self._subscribers.get(channel, []))
            if not handlers:
                continue
            # Lance tous les handlers en parallèle, isole leurs erreurs
            results = await asyncio.gather(
                *[self._safe_invoke(h, signal) for h in handlers],
                return_exceptions=True,
            )
            for r in results:
                if isinstance(r, Exception):
                    logger.warning("event_bus: handler error on %s: %s", channel, r)

    @staticmethod
    async def _safe_invoke(handler: Callable[[Signal], Awaitable[None]], signal: Signal) -> None:
        try:
            await handler(signal)
        except Exception as e:
            logger.warning("event_bus: agent handler raised %s: %s", handler, e)

    def start(self) -> None:
        """Démarre une task dispatcher par canal enregistré."""
        for channel in list(self._subscribers.keys()):
            t = asyncio.create_task(self._dispatch_loop(channel))
            self._tasks.append(t)

    def stop(self) -> None:
        for t in self._tasks:
            t.cancel()
        self._tasks.clear()

    def stats(self) -> dict:
        return {
            "channels": {ch: q.qsize() for ch, q in self._queues.items()},
            "subscribers": {ch: len(hs) for ch, hs in self._subscribers.items()},
            "dropped": self._dropped,
        }
