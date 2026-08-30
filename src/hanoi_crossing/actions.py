"""The player-relative action space: seven actions, fixed regardless of N."""

from __future__ import annotations

import enum


class Action(enum.Enum):
    """One action per turn, named relative to the acting player.

    For A, SOURCE/TARGET are poles 1a/3a; for B, 1b/3b. SHARED is pole 2 for
    both. One policy can therefore play either side.
    """

    LIFT_SOURCE = "LIFT_SOURCE"
    LIFT_SHARED = "LIFT_SHARED"
    LIFT_TARGET = "LIFT_TARGET"
    PLACE_SOURCE = "PLACE_SOURCE"
    PLACE_SHARED = "PLACE_SHARED"
    PLACE_TARGET = "PLACE_TARGET"
    SKIP = "SKIP"
