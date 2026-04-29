# Copyright (c) 2026 FRC Team 6907, The G.O.A.T
# Licensed under the MIT License.

from __future__ import annotations

from typing import TYPE_CHECKING, Type
from ruleset.tournament.protocol import TournamentRule
from ruleset.tournament.simple import SimpleTournament
from ruleset.tournament.double_elim import DoubleElimTournament

if TYPE_CHECKING:
    from real.event import Event


def default_tournament_rule_class(event: Event) -> Type[TournamentRule]:
    season: int = event.season
    if season <= 2022:
        return SimpleTournament
    elif season >= 2023:
        return DoubleElimTournament
    else:
        raise ValueError(f"No default tournament rule defined for season {season}")
