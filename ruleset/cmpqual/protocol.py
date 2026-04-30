# Copyright (c) 2026 FRC Team 6907, The G.O.A.T
# Licensed under the MIT License.

from __future__ import annotations

from typing import Protocol
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from real.event import Event
    from real.team import Team


class EmptyEventPoints:
    event: Event

    def __init__(self, event: Event):
        self.event = event

    # CMP Eligibility Points Calculation

    def get_qualification_points(self, team: Team) -> int:
        return 0

    def get_alliance_selection_points(self, team: Team) -> int:
        return 0

    def get_playoff_round_points(self, team: Team) -> int:
        return 0

    def get_team_age_points(self, team: Team) -> int:
        return 0

    def get_award_points(self, team: Team) -> int:
        return 0


class CMPQualRule(Protocol):
    event: Event

    def __init__(self, event: Event): ...

    # CMP Eligibility Points Calculation

    def get_qualification_points(self, team: Team) -> int: ...

    def get_alliance_selection_points(self, team: Team) -> int: ...

    def get_playoff_round_points(self, team: Team) -> int: ...

    def get_team_age_points(self, team: Team) -> int: ...

    def get_award_points(self, team: Team) -> int: ...

    def get_total_points(self, team: Team) -> int: ...

    # CMP Qualification Succession

    def get_direct_qualification_succession(self) -> list[Team]: ...
