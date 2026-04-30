# Copyright (c) 2026 FRC Team 6907, The G.O.A.T
# Licensed under the MIT License.

from __future__ import annotations

from enum import IntEnum
from typing import Optional, cast
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from real.event import Event
    from real.team import Team
    from real.match import Match


class AllianceColor(IntEnum):
    NONE = 0
    RED = 1
    BLUE = 2


class AllianceRole(IntEnum):
    CAPTAIN = 1
    PICK_1ST = 2
    PICK_2ND = 3
    PICK_3RD = 4
    BACKUP = 5
    BACKUP_REPLACED = 6

    STATION_1 = 7
    STATION_2 = 8
    STATION_3 = 9


class AllianceBase:
    def __init__(self, event: Event):
        self.color: AllianceColor = (
            AllianceColor.NONE
        )  # waiting for the event to assign
        self.event: Event = event
        self.teams: dict[int, Team] = {}

    def __repr__(self):
        return self.__str__()

    def assign_team(self, team: Team, allianceRole: AllianceRole):
        self.teams[allianceRole] = team

    def is_member(self, team: Team):
        return team in self.teams.values()


class AnonymousAlliance(AllianceBase):
    def __init__(self, event: Event):
        AllianceBase.__init__(self, event)
        self.match: Optional[Match] = None  # quals should have a specific match

    def __str__(self):
        return (
            f"<Alliance {self.teams[AllianceRole.STATION_1].teamNumber} "
            f"{self.teams[AllianceRole.STATION_2].teamNumber} "
            f"{self.teams[AllianceRole.STATION_3].teamNumber}>"
        )

    def register_match(self, match: Match, allianceColor: AllianceColor):
        self.match = match
        self.color = allianceColor

    def get_team_from_station(self, station: AllianceRole) -> Team:
        team = self.teams.get(station)
        if team is None:
            raise ValueError(f"Station {station} does not exist in alliance {self}")
        return team


class Alliance(AllianceBase):
    def __init__(self, event: Event):
        super().__init__(event)
        self.allianceNumber: int = 0
        self.name: Optional[str] = None
        self.playoffMatches: list[Match] = []

    def __str__(self):
        return f"<Alliance {self.allianceNumber}>"

    def register_alliance(self, allianceNumber: int):
        self.allianceNumber = allianceNumber

    def get_win_playoffs(self) -> list[Match]:
        from real.match import MatchResult

        currentAlliance = cast(Alliance, self)
        result: list[Match] = []
        for match in currentAlliance.playoffMatches:
            if match.winningAlliance is None:
                continue
            if match.get_result_by_alliance(currentAlliance) == MatchResult.WIN:
                result.append(match)
        return result

    def get_team_from_role(self, allianceRole: AllianceRole) -> Team:
        team = self.teams.get(allianceRole)
        if team is None:
            raise ValueError(
                f"Alliance role {allianceRole} does not exist in alliance {self}"
            )
        return team
