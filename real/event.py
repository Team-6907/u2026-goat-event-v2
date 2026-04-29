# Copyright (c) 2026 FRC Team 6907, The G.O.A.T
# Licensed under the MIT License.

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Type
from typing import Optional, cast
from datetime import datetime

from ruleset.cmpqual.protocol import CMPQualRule
from ruleset.tournament.protocol import TournamentType, TournamentLevel
from data.event_requests import request_event_data
from data.frc_json import EventRequestType
from real.alliance import Alliance, AllianceColor, AllianceRole
from real.match import PlayoffRound, Match
from real.team import Team
from utils.data_util import is_json_object
from utils.rule_util import default_tournament_rule_class

if TYPE_CHECKING:
    from ruleset.tournament.protocol import TournamentRule
    from real.season import Season


class Award:
    def __init__(self, name: str):
        self.name: str = name
        self.team: Optional[Team] = None
        self.person: Optional[str] = None
        self.series: int = 1
        self.awardId: int = 0
        self.cmpQualifying: bool = False
        self.cmpQualifyingReason: Optional[str] = None
        self.schoolName: Optional[str] = None
        self.fullTeamName: Optional[str] = None

    def __str__(self):
        if self.series > 1:
            return f"<Award {self.name} ({self.series})>"
        return f"<Award {self.name}>"

    def __repr__(self):
        return self.__str__()


class Event:
    def __init__(self, season: int, eventCode: str):
        self.season: int = season
        self.eventCode: str = eventCode

        self.type: TournamentType = TournamentType.NONE
        self.country: str = ""
        self.districtCode: Optional[str] = None
        self.divisionCode: Optional[str] = None
        self.name: str = ""
        self.dateStart: datetime = datetime(1970, 1, 1)
        self.dateEnd: datetime = datetime(1970, 1, 1)

        self.rankings: dict[int, Team] = {}
        self.alliances: dict[int, Alliance] = {}
        self.teams: dict[int, Team] = {}
        self.qualsMatches: dict[int, Match] = {}
        self.playoffMatches: dict[int, Match] = {}
        self.awards: dict[str, list[Award]] = {}

        self.season_obj: Optional[Season] = None

        self.tournamentRule: Optional[TournamentRule] = None
        self.cmpQualRule: Optional[CMPQualRule] = None

        self._request_teams()
        self._request_rankings()
        self._request_alliances()
        self._request_qualification_matches()
        self._request_playoff_matches()
        self._request_qualification_score_details()
        self._request_playoff_score_details()
        self._request_event_awards()

        self.add_default_tournament_rule()

    def __str__(self):
        return f"<Event {self.season} {self.eventCode}>"

    def __repr__(self):
        return self.__str__()

    # Event data request

    def request_event_data(self, requestType: EventRequestType) -> list[object]:
        return request_event_data(requestType, self.season, self.eventCode)

    def _request_teams(self) -> None:
        teamsData = self.request_event_data(EventRequestType.TEAMS)

        for rawTeamData in teamsData:
            if not is_json_object(rawTeamData):
                continue
            typedTeamData = rawTeamData

            teamNumber = typedTeamData.get("teamNumber")
            if not isinstance(teamNumber, int):
                continue

            team = Team(teamNumber, self)

            rookieYear = typedTeamData.get("rookieYear")
            if isinstance(rookieYear, int):
                team.rookieYear = rookieYear

            nameShort = typedTeamData.get("nameShort")
            nameFull = typedTeamData.get("nameFull")
            if isinstance(nameShort, str) and nameShort.strip():
                team.nameShort = nameShort
            if isinstance(nameFull, str) and nameFull.strip():
                team.nameFull = nameFull

            districtCode = typedTeamData.get("districtCode")
            if isinstance(districtCode, str):
                team.districtCode = districtCode

            self.teams[teamNumber] = team

    def _request_rankings(self) -> None:
        rankingsData = self.request_event_data(EventRequestType.RANKINGS)

        for rawRankingData in rankingsData:
            if not is_json_object(rawRankingData):
                continue
            typedRankingData = rawRankingData

            rank = typedRankingData.get("rank")
            teamNumber = typedRankingData.get("teamNumber")
            if not isinstance(rank, int) or not isinstance(teamNumber, int):
                continue

            team = self.teams.get(teamNumber)
            if team is None:
                continue

            sortOrderValues: list[int | float] = []
            for index in range(1, 7):
                sortOrderValue = typedRankingData.get(f"sortOrder{index}")
                if isinstance(sortOrderValue, (int, float)):
                    sortOrderValues.append(sortOrderValue)

            if len(sortOrderValues) > 0:
                team.sortOrder = tuple(sortOrderValues)

            team.ranking = rank
            self.rankings[rank] = team

    def _request_alliances(self) -> None:
        if len(self.alliances) > 0:
            return

        alliancesData = self.request_event_data(EventRequestType.ALLIANCES)

        for rawAllianceData in alliancesData:
            if not is_json_object(rawAllianceData):
                continue
            typedAllianceData = rawAllianceData

            allianceNumber = typedAllianceData.get("number")
            if not isinstance(allianceNumber, int):
                continue

            alliance = Alliance(self)
            alliance.register_alliance(allianceNumber)

            allianceName = typedAllianceData.get("name")
            if isinstance(allianceName, str) and allianceName.strip():
                alliance.name = allianceName

            for fieldName, allianceRole in (
                ("captain", AllianceRole.CAPTAIN),
                ("round1", AllianceRole.PICK_1ST),
                ("round2", AllianceRole.PICK_2ND),
                ("round3", AllianceRole.PICK_3RD),
                ("backup", AllianceRole.BACKUP),
                ("backupReplaced", AllianceRole.BACKUP_REPLACED),
            ):
                teamNumber = typedAllianceData.get(fieldName)
                if not isinstance(teamNumber, int):
                    continue

                team = self.get_team_from_number(teamNumber)
                team.register_alliance(alliance, allianceRole)

                alliance.assign_team(team, allianceRole)

            self.alliances[allianceNumber] = alliance

    def _request_qualification_matches(self) -> None:
        if len(self.qualsMatches) > 0:
            return

        qualificationMatchesData = self.request_event_data(
            EventRequestType.QUALIFICATION_MATCHES
        )

        stationMap: dict[str, tuple[AllianceColor, AllianceRole]] = {
            "Red1": (AllianceColor.RED, AllianceRole.STATION_1),
            "Red2": (AllianceColor.RED, AllianceRole.STATION_2),
            "Red3": (AllianceColor.RED, AllianceRole.STATION_3),
            "Blue1": (AllianceColor.BLUE, AllianceRole.STATION_1),
            "Blue2": (AllianceColor.BLUE, AllianceRole.STATION_2),
            "Blue3": (AllianceColor.BLUE, AllianceRole.STATION_3),
        }

        for rawMatchData in qualificationMatchesData:
            if not is_json_object(rawMatchData):
                continue
            typedMatchData = rawMatchData

            matchNumber = typedMatchData.get("matchNumber")
            if not isinstance(matchNumber, int):
                continue

            match = Match(self, TournamentLevel.QUALIFICATION, matchNumber)

            isReplay = typedMatchData.get("isReplay")
            if isinstance(isReplay, bool):
                match.isReplay = isReplay

            matchVideoLink = typedMatchData.get("matchVideoLink")
            if isinstance(matchVideoLink, str) and matchVideoLink.strip():
                match.matchVideoLink = matchVideoLink

            actualStartTime = typedMatchData.get("actualStartTime")
            if isinstance(actualStartTime, str) and actualStartTime.strip():
                match.actualStartTime = datetime.fromisoformat(actualStartTime)

            postResultTime = typedMatchData.get("postResultTime")
            if isinstance(postResultTime, str) and postResultTime.strip():
                match.postResultTime = datetime.fromisoformat(postResultTime)

            scoreRedFinal = typedMatchData.get("scoreRedFinal")
            if isinstance(scoreRedFinal, (int, float)):
                match.redScore = [scoreRedFinal]

            scoreBlueFinal = typedMatchData.get("scoreBlueFinal")
            if isinstance(scoreBlueFinal, (int, float)):
                match.blueScore = [scoreBlueFinal]

            teamsData = typedMatchData.get("teams")
            if isinstance(teamsData, list):
                typedTeamsData = cast(list[object], teamsData)
                for rawTeamData in typedTeamsData:
                    if not is_json_object(rawTeamData):
                        continue
                    typedTeamData = rawTeamData

                    teamNumber = typedTeamData.get("teamNumber")
                    station = typedTeamData.get("station")
                    disqualified = typedTeamData.get("dq")
                    if (
                        not isinstance(teamNumber, int)
                        or not isinstance(station, str)
                        or not isinstance(disqualified, bool)
                    ):
                        continue

                    stationInfo = stationMap.get(station)
                    if stationInfo is None:
                        continue

                    allianceColor, allianceRole = stationInfo
                    team = self.teams.get(teamNumber)
                    if team is None:
                        continue

                    match.assign_team(team, allianceRole, allianceColor, disqualified)

            self.qualsMatches[matchNumber] = match

    def _request_playoff_matches(self) -> None:
        if len(self.playoffMatches) > 0:
            return

        playoffMatchesData = self.request_event_data(EventRequestType.PLAYOFF_MATCHES)

        stationMap: dict[str, tuple[AllianceColor, AllianceRole]] = {
            "Red1": (AllianceColor.RED, AllianceRole.STATION_1),
            "Red2": (AllianceColor.RED, AllianceRole.STATION_2),
            "Red3": (AllianceColor.RED, AllianceRole.STATION_3),
            "Blue1": (AllianceColor.BLUE, AllianceRole.STATION_1),
            "Blue2": (AllianceColor.BLUE, AllianceRole.STATION_2),
            "Blue3": (AllianceColor.BLUE, AllianceRole.STATION_3),
        }

        for rawMatchData in playoffMatchesData:
            if not is_json_object(rawMatchData):
                continue
            typedMatchData = rawMatchData

            matchNumber = typedMatchData.get("matchNumber")
            if not isinstance(matchNumber, int):
                continue

            match = Match(self, TournamentLevel.PLAYOFF, matchNumber)

            isReplay = typedMatchData.get("isReplay")
            if isinstance(isReplay, bool):
                match.isReplay = isReplay

            matchVideoLink = typedMatchData.get("matchVideoLink")
            if isinstance(matchVideoLink, str) and matchVideoLink.strip():
                match.matchVideoLink = matchVideoLink

            actualStartTime = typedMatchData.get("actualStartTime")
            if isinstance(actualStartTime, str) and actualStartTime.strip():
                match.actualStartTime = datetime.fromisoformat(actualStartTime)

            postResultTime = typedMatchData.get("postResultTime")
            if isinstance(postResultTime, str) and postResultTime.strip():
                match.postResultTime = datetime.fromisoformat(postResultTime)

            scoreRedFinal = typedMatchData.get("scoreRedFinal")
            if isinstance(scoreRedFinal, (int, float)):
                match.redScore = [scoreRedFinal]

            scoreBlueFinal = typedMatchData.get("scoreBlueFinal")
            if isinstance(scoreBlueFinal, (int, float)):
                match.blueScore = [scoreBlueFinal]

            alliancesByColor: dict[AllianceColor, Alliance] = {}

            teamsData = typedMatchData.get("teams")
            if isinstance(teamsData, list):
                typedTeamsData = cast(list[object], teamsData)
                for rawTeamData in typedTeamsData:
                    if not is_json_object(rawTeamData):
                        continue
                    typedTeamData = rawTeamData

                    teamNumber = typedTeamData.get("teamNumber")
                    station = typedTeamData.get("station")
                    disqualified = typedTeamData.get("dq")
                    if (
                        not isinstance(teamNumber, int)
                        or not isinstance(station, str)
                        or not isinstance(disqualified, bool)
                    ):
                        continue

                    stationInfo = stationMap.get(station)
                    if stationInfo is None:
                        continue

                    allianceColor, allianceRole = stationInfo
                    team = self.teams.get(teamNumber)
                    if team is None:
                        continue

                    match.assign_team(team, allianceRole, allianceColor, disqualified)

                    teamAlliance = team.alliance
                    if teamAlliance is None:
                        continue

                    assignedAlliance = alliancesByColor.get(allianceColor)
                    if assignedAlliance is None:
                        alliancesByColor[allianceColor] = teamAlliance
                    elif assignedAlliance != teamAlliance:
                        raise ValueError(
                            f"Inconsistent playoff alliance assignment for match {matchNumber} {allianceColor}"
                        )

            redAlliance = alliancesByColor.get(AllianceColor.RED)
            if redAlliance is not None:
                match.assign_alliance(redAlliance, AllianceColor.RED)

            blueAlliance = alliancesByColor.get(AllianceColor.BLUE)
            if blueAlliance is not None:
                match.assign_alliance(blueAlliance, AllianceColor.BLUE)

            self.playoffMatches[matchNumber] = match

    def _request_event_awards(self) -> None:
        if len(self.awards) > 0:
            return

        awardsData = self.request_event_data(EventRequestType.AWARDS)

        for rawAwardData in awardsData:
            if not is_json_object(rawAwardData):
                continue
            typedAwardData = rawAwardData

            awardName = typedAwardData.get("name")
            if not isinstance(awardName, str) or not awardName.strip():
                continue

            award = Award(awardName)

            series = typedAwardData.get("series")
            if isinstance(series, int):
                award.series = series

            awardId = typedAwardData.get("awardId")
            if isinstance(awardId, int):
                award.awardId = awardId

            cmpQualifying = typedAwardData.get("cmpQualifying")
            if isinstance(cmpQualifying, bool):
                award.cmpQualifying = cmpQualifying

            cmpQualifyingReason = typedAwardData.get("cmpQualifyingReason")
            if isinstance(cmpQualifyingReason, str) and cmpQualifyingReason.strip():
                award.cmpQualifyingReason = cmpQualifyingReason

            schoolName = typedAwardData.get("schoolName")
            if isinstance(schoolName, str) and schoolName.strip():
                award.schoolName = schoolName

            fullTeamName = typedAwardData.get("fullTeamName")
            if isinstance(fullTeamName, str) and fullTeamName.strip():
                award.fullTeamName = fullTeamName

            person = typedAwardData.get("person")
            if isinstance(person, str) and person.strip():
                award.person = person

            teamNumber = typedAwardData.get("teamNumber")
            if isinstance(teamNumber, int):
                team = self.teams.get(teamNumber)
                if team is not None:
                    award.team = team
                    team.awards.append(awardName)

            self.awards.setdefault(awardName, []).append(award)

    def _assign_score_details(
        self, tournamentLevel: TournamentLevel, requestType: EventRequestType
    ) -> None:
        scoreDetailsData = self.request_event_data(requestType)

        for rawScoreDetails in scoreDetailsData:
            if not is_json_object(rawScoreDetails):
                continue
            typedScoreDetails = rawScoreDetails

            matchNumber = typedScoreDetails.get("matchNumber")
            if not isinstance(matchNumber, int):
                continue

            match = self.get_match_from_number(tournamentLevel, matchNumber)

            winningAlliance = typedScoreDetails.get("winningAlliance")
            if winningAlliance == 1:
                match.winningAlliance = AllianceColor.RED
            elif winningAlliance == 2:
                match.winningAlliance = AllianceColor.BLUE
            elif winningAlliance is None:
                match.winningAlliance = AllianceColor.NONE

            alliancesData = typedScoreDetails.get("alliances")
            if not isinstance(alliancesData, list):
                continue

            typedAlliancesData = cast(list[object], alliancesData)
            for rawAllianceData in typedAlliancesData:
                if not is_json_object(rawAllianceData):
                    continue
                typedAllianceData = rawAllianceData

                allianceName = typedAllianceData.get("alliance")
                if allianceName == "Red":
                    match.redScoreDetails = typedAllianceData
                elif allianceName == "Blue":
                    match.blueScoreDetails = typedAllianceData

                for fieldName, fieldData in typedAllianceData.items():
                    match.generalScoreDetails[fieldName] = fieldData

    def _request_qualification_score_details(self) -> None:
        self._assign_score_details(
            TournamentLevel.QUALIFICATION,
            EventRequestType.QUALIFICATION_SCORE_DETAILS,
        )

    def _request_playoff_score_details(self) -> None:
        self._assign_score_details(
            TournamentLevel.PLAYOFF, EventRequestType.PLAYOFF_SCORE_DETAILS
        )

    # Getters
    def get_team_from_number(self, teamNumber: int) -> Team:
        team = self.teams.get(teamNumber)
        if team is not None:
            return team
        raise ValueError(f"Team with number {teamNumber} not found")

    def get_team_from_rank(self, rank: int) -> Team:
        team = self.rankings.get(rank)
        if team is not None:
            return team
        raise ValueError(f"Team with rank {rank} not found")

    def get_alliance_from_number(self, allianceNumber: int) -> Alliance:
        alliance = self.alliances.get(allianceNumber)
        if alliance is not None:
            return alliance
        raise ValueError(f"Alliance with number {allianceNumber} not found")

    def get_match_from_number(
        self, tournamentLevel: TournamentLevel, matchNumber: int
    ) -> Match:
        if tournamentLevel == TournamentLevel.QUALIFICATION:
            match = self.qualsMatches.get(matchNumber)
        elif tournamentLevel == TournamentLevel.PLAYOFF:
            match = self.playoffMatches.get(matchNumber)
        if match is not None:
            return match
        raise ValueError(
            f"Invalid match number {matchNumber} for tournament level {tournamentLevel}"
        )

    def get_award_from_name(self, awardName: str) -> list[Award]:
        awards = self.awards.get(awardName)
        if awards is not None:
            return awards
        raise ValueError(f"Award with name {awardName} not found")

    # Tournament

    def get_tournament_rule(self) -> TournamentRule:
        if self.tournamentRule is not None:
            return self.tournamentRule
        raise ValueError("Tournament rule not initialized for this event")

    def add_tournament_rule(self, tournamentRuleClass: Type[TournamentRule]):
        self.tournamentRule = tournamentRuleClass(self)

    def with_tournament_rule(
        self, tournamentRuleClass: Type[TournamentRule]
    ) -> "Event":
        self.add_tournament_rule(tournamentRuleClass)
        return self

    def add_default_tournament_rule(self):
        defaultTournamentRuleClass: Type[TournamentRule] = (
            default_tournament_rule_class(self)
        )
        self.add_tournament_rule(defaultTournamentRuleClass)

    def with_default_tournament_rule(self) -> "Event":
        self.add_default_tournament_rule()
        return self

    def get_playoff_from_round(
        self, round: PlayoffRound, part: int, match: int
    ) -> Match:
        return self.get_tournament_rule().get_playoff_from_round(round, part, match)

    def get_round_part_winner(self, round: PlayoffRound, part: int) -> Alliance:
        return self.get_tournament_rule().get_round_part_winner(round, part)

    def get_round_part_finalist(self, round: PlayoffRound, part: int) -> Alliance:
        return self.get_tournament_rule().get_round_part_finalist(round, part)
