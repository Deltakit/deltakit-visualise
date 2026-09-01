# (c) Copyright Riverlane 2025-2026. All rights reserved.
"""SSA value tracking for unique ID assignment across passes."""

from dataclasses import dataclass, field

from xdsl.ir import SSAValue


@dataclass
class IdTracker:
    """Tracks unique IDs for SSA values during pass execution.

    Provides a stable mapping from SSAValue objects to unique string identifiers,
    independent of name_hint availability.
    """

    _counter: int = 0
    _ssa_to_id: dict[SSAValue, str] = field(default_factory=dict)
    _used_ids: dict[str, int] = field(default_factory=dict)

    def _make_unique(self, base: str) -> str:
        """Ensure the ID is unique by appending a counter suffix if needed."""
        if base not in self._used_ids:
            self._used_ids[base] = 0
            return base
        index = self._used_ids[base] + 1
        self._used_ids[base] = index
        return f"{base}_{index}"

    def assign(self, ssa_value: SSAValue) -> str:
        """Assign a new unique ID to an SSA value.

        Uses name_hint when available, otherwise falls back to a counter-based ID.
        """
        hint = ssa_value.name_hint
        id_str = self._make_unique(hint) if hint is not None else self.next_id()
        self._ssa_to_id[ssa_value] = id_str
        return id_str

    def get_id(self, ssa_value: SSAValue) -> str | None:
        """Get the ID assigned to an SSA value, or None."""
        return self._ssa_to_id.get(ssa_value)

    def get_or_assign(self, ssa_value: SSAValue) -> str:
        """Get existing ID or assign a new one."""
        existing = self.get_id(ssa_value)
        if existing is not None:
            return existing
        return self.assign(ssa_value)

    def next_id(self) -> str:
        """Generate a new unique ID without associating it with an SSA value."""
        id_str = self._make_unique(f"gen_id_{self._counter}")
        self._counter += 1
        return id_str
