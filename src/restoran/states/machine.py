"""Hafif durum makinesi çekirdeği.

Her aktör tipi için bir TransitionTable tanımlanır; motor event'leri besler,
durum değişimlerinde StateChange üretir. Kurallar (geçişler) config'den de
genişletilebilir; kodda olanlar v1'in referans akışıdır.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from ..contracts.events import PosEvent, VisionEvent


def utcnow_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


# Event kaynaklarından türetilen sinyal adları (payload'ın normalize hali)
SignalT = str


@dataclass(frozen=True)
class StateChange:
    actor_type: str
    actor_id: str
    old: str
    new: str
    at_ms: int
    signal: SignalT
    evidence: dict = field(default_factory=dict)


@dataclass
class ActorState:
    actor_type: str
    actor_id: str
    state: str
    since_ms: int
    attributes: dict = field(default_factory=dict)


class StateMachine:
    """signal -> (guard, hedef durum) eşlemeli geçiş motoru."""

    def __init__(self, name: str, initial: str,
                 transitions: dict[tuple[str, str | None], dict[str, str]],):
        self.name = name
        self.initial = initial
        # {(state, signal): {to, guard?}} — guard fonksiyonu attributes üzerinde çalışır
        self._t = transitions
        self._actors: dict[str, ActorState] = {}

    def get(self, actor_id: str) -> ActorState:
        if actor_id not in self._actors:
            self._actors[actor_id] = ActorState(
                actor_type=self.name, actor_id=actor_id,
                state=self.initial, since_ms=utcnow_ms())
        return self._actors[actor_id]

    def apply(self, actor_id: str, signal: SignalT, at_ms: int,
              evidence: dict | None = None) -> StateChange | None:
        actor = self.get(actor_id)
        key = (actor.state, signal)
        any_key = (actor.state, "*")
        rule = self._t.get(key) or self._t.get(any_key)
        if not rule:
            return None
        new = rule["to"]
        if new == actor.state:
            return None
        old = actor.state
        actor.state = new
        actor.since_ms = at_ms
        return StateChange(self.name, actor_id, old, new, at_ms, signal,
                           evidence or {})

    @property
    def actors(self) -> dict[str, ActorState]:
        return self._actors
