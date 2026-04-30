# Copyright (c) 2026 FRC Team 6907, The G.O.A.T
# Licensed under the MIT License.

from __future__ import annotations

from typing import Optional, Type, cast

from data.frc_json import (
    FRCHTTPError,
    bypass_event_cache_file,
    bypassed_events_for_season,
)
from data.season_requests import request_season_data, SeasonRequestType
from real.event import Event
from real.team import SeasonTeam
from ruleset.cmpqual.protocol import CMPQualRule
from utils.data_util import is_json_object


class Season:
    def __init__(self, season: int):
        self.season: int = season
        self.teams: dict[int, SeasonTeam] = {}
        self.events: dict[int, list[Event]] = {}

        self.cmpQualRule: Optional[Type[CMPQualRule]] = None

        self._request_team_listing()
        self._request_event_listing()

    def _request_team_listing(self) -> None:
        teamsData = request_season_data(SeasonRequestType.TEAM_LISTING, self.season)

        for rawTeamData in teamsData:
            if not is_json_object(rawTeamData):
                continue
            typedTeamData = rawTeamData

            teamNumber = typedTeamData.get("teamNumber")
            if not isinstance(teamNumber, int):
                continue

            self.teams[teamNumber] = SeasonTeam(self.season, teamNumber)

    def _request_event_listing(self) -> None:
        eventData = request_season_data(SeasonRequestType.EVENT_LISTING, self.season)
        for rawEventData in eventData:
            if not is_json_object(rawEventData):
                continue
            typedEventData = rawEventData

            eventCode = typedEventData.get("code")
            weekNumber = typedEventData.get("weekNumber")

            if (
                not isinstance(eventCode, str)
                or not eventCode.strip()
                or not isinstance(weekNumber, int)
            ):
                continue

            if eventCode in bypassed_events_for_season(self.season):
                continue

            try:
                currentSeason = cast(Season, self)
                event = Event(self.season, eventCode)
                event.season_obj = currentSeason
            except FRCHTTPError as exc:
                if "HTTP 500" not in str(exc):
                    raise
                bypass_event_cache_file(self.season, eventCode)
                continue
            except ValueError:
                bypass_event_cache_file(self.season, eventCode)
                continue

            self.events.setdefault(weekNumber, []).append(event)

            for team in event.teams.values():
                try:
                    seasonTeam = self.get_team_from_number(team.teamNumber)
                except ValueError:
                    continue
                team.seasonTeam = seasonTeam
                seasonTeam.events.append((weekNumber, event))
                seasonTeam.eventTeams.append((weekNumber, team))

    # Getters

    def get_team_from_number(self, teamNumber: int) -> SeasonTeam:
        team = self.teams.get(teamNumber)
        if team is not None:
            return team
        raise ValueError(f"Team with number {teamNumber} not found")
