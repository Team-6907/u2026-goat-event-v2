# Copyright (c) 2026 FRC Team 6907, The G.O.A.T
# Licensed under the MIT License.

from __future__ import annotations

from typing import TYPE_CHECKING
from math import ceil

from real.alliance import AllianceColor
from real.match import Match, PlayoffRound
from ruleset.tournament.double_elim import DoubleElimTournament
from ruleset.tournament.protocol import TournamentType
from ruleset.tournament.simple import SimpleTournament
from utils.math_util import erfinv
from utils.rule_util import AwardNameMapping

if TYPE_CHECKING:
    from real.event import Event
    from real.team import Team


class SimpleEventPoints:
    event: Event

    def __init__(self, event: Event):
        self.event = event

    # CMP Eligibility Points Calculation

    def get_qualification_points(self, team: Team) -> int:
        R = team.ranking
        N = len(self.event.teams)
        if R <= 0:
            return 0
        if R > N:
            raise ValueError(
                f"Team {team.teamNumber} is not ranked in event {self.event.eventCode}"
            )
        ALPHA = 1.07
        return ceil(10 * erfinv((N - R * 2 + 2) / (N * ALPHA)) / erfinv(1 / ALPHA) + 12)

    def _get_points_based_succession(self, team: Team) -> int:
        if team.alliance is not None:
            match team.allianceRole:
                case 1:
                    return team.alliance.allianceNumber
                case 2:
                    return team.alliance.allianceNumber
                case 3:
                    return 17 - team.alliance.allianceNumber
                case _:
                    return 17
        else:
            return 17

    def get_alliance_selection_points(self, team: Team) -> int:
        if self.event.type == TournamentType.DISTRICT_CHAMPIONSHIP_WITH_LEVELS:
            return 0
        return 17 - self._get_points_based_succession(team)

    def _get_team_attendance_count(self, team: Team, matches: list[Match]) -> int:
        alliance = team.alliance
        if alliance is None:
            return 0

        attendance = 0
        for match in matches:
            allianceColor = None
            if match.redAlliance == alliance:
                allianceColor = AllianceColor.RED
            elif match.blueAlliance == alliance:
                allianceColor = AllianceColor.BLUE

            if allianceColor is None:
                continue

            if team in match.station[allianceColor].values():
                attendance += 1

        return attendance

    def _get_team_attendance_points(
        self, team: Team, beta: int, matches: list[Match]
    ) -> int:
        if len(matches) == 0:
            return 0
        return ceil(
            beta * self._get_team_attendance_count(team, matches) / len(matches)
        )

    def _get_match_winner_color(self, match: Match) -> AllianceColor | None:
        winningAlliance = match.winningAlliance
        if winningAlliance in (AllianceColor.RED, AllianceColor.BLUE):
            return winningAlliance

        if len(match.redScore) > 0 and len(match.blueScore) > 0:
            if match.redScore > match.blueScore:
                return AllianceColor.RED
            if match.blueScore > match.redScore:
                return AllianceColor.BLUE

        return None

    def _get_dcmp_level_finalist_points(self, team: Team) -> int:
        alliance = team.alliance
        if alliance is None:
            return 0

        finalMatches = [
            match
            for matchNumber, match in sorted(self.event.playoffMatches.items())
            if matchNumber >= 6
        ]
        decidingMatch: Match | None = None
        for match in reversed(finalMatches):
            if self._get_match_winner_color(match) is not None:
                decidingMatch = match
                break

        if decidingMatch is None:
            return 0

        winnerColor = self._get_match_winner_color(decidingMatch)
        if winnerColor is None:
            return 0

        winnerAlliance = decidingMatch.get_alliance(winnerColor)
        loserAlliance = decidingMatch.get_alliance(
            AllianceColor.BLUE
            if winnerColor == AllianceColor.RED
            else AllianceColor.RED
        )

        if alliance == winnerAlliance:
            return 20
        if alliance == loserAlliance:
            return 10
        return 0

    def get_playoff_round_points(self, team: Team) -> int:
        alliance = team.alliance
        if alliance is None:
            return 0

        if self.event.type == TournamentType.DISTRICT_CHAMPIONSHIP_WITH_LEVELS:
            return self._get_dcmp_level_finalist_points(team)

        if isinstance(self.event.tournamentRule, SimpleTournament):
            points = 0
            for round_value, parts in (
                (PlayoffRound.QUARTER, range(1, 5)),
                (PlayoffRound.SEMI, range(1, 3)),
                (PlayoffRound.FINAL, range(1, 2)),
            ):
                for part in parts:
                    if self.event.get_round_part_winner(round_value, part) == alliance:
                        points += 10
            return points

        if isinstance(self.event.tournamentRule, DoubleElimTournament):
            winningMatches = alliance.get_win_playoffs()
            preFinalWinningMatches = [
                match for match in winningMatches if match.matchNumber <= 13
            ]
            finalWinningMatches = [
                match for match in winningMatches if match.matchNumber >= 14
            ]

            if self.event.get_round_part_winner(PlayoffRound.FINAL, 1) == alliance:
                return self._get_team_attendance_points(
                    team, 20, preFinalWinningMatches
                ) + 5 * self._get_team_attendance_count(team, finalWinningMatches)
            if self.event.get_round_part_finalist(PlayoffRound.FINAL, 1) == alliance:
                return self._get_team_attendance_points(
                    team, 20, preFinalWinningMatches
                )
            if self.event.get_round_part_finalist(PlayoffRound.SEMI, 13) == alliance:
                return self._get_team_attendance_points(
                    team, 13, preFinalWinningMatches
                )
            if self.event.get_round_part_finalist(PlayoffRound.SEMI, 12) == alliance:
                return self._get_team_attendance_points(team, 7, preFinalWinningMatches)
            return 0

        raise ValueError(
            f"Playoff round points are not defined for tournament rule {type(self.event.tournamentRule).__name__}"
        )

    def get_team_age_points(self, team: Team) -> int:
        if team.rookieYear == self.event.season:
            return 10
        elif team.rookieYear == self.event.season - 1:
            return 5
        return 0

    def get_award_points(self, team: Team) -> int:
        specialAwardsMapping = {
            AwardNameMapping.rookie_all_star_award(self.event): 8,
            AwardNameMapping.regional_engineering_inspiration_award(self.event): 28,
            AwardNameMapping.district_engineering_inspiration_award(self.event): 8,
            AwardNameMapping.dcmp_engineering_inspiration_award(self.event): 8,
            AwardNameMapping.regional_first_impact_award(self.event): 45,
            AwardNameMapping.district_first_impact_award(self.event): 10,
            AwardNameMapping.dcmp_first_impact_award(self.event): 10,
            AwardNameMapping.regional_winner(self.event): 0,
            AwardNameMapping.district_winner(self.event): 0,
            AwardNameMapping.dcmp_winner(self.event): 0,
            AwardNameMapping.regional_finalist(self.event): 0,
            AwardNameMapping.district_finalist(self.event): 0,
            AwardNameMapping.dcmp_finalist(self.event): 0,
        }
        points = 0
        for award in team.awards:
            for prefix, value in specialAwardsMapping.items():
                if award.startswith(prefix):
                    points += value
                    break
            else:
                points += 5
        return points

    def get_total_points(self, team: Team) -> int:
        basePoints = (
            self.get_qualification_points(team)
            + self.get_alliance_selection_points(team)
            + self.get_playoff_round_points(team)
            + self.get_team_age_points(team)
            + self.get_award_points(team)
        )
        match self.event.type:
            case TournamentType.DISTRICT_CHAMPIONSHIP:
                return basePoints * 3
            case TournamentType.DISTRICT_CHAMPIONSHIP_WITH_LEVELS:
                return basePoints * 3
            case TournamentType.DISTRICT_CHAMPIONSHIP_DIVISION:
                return basePoints * 3
            case TournamentType.CHAMPIONSHIP_SUBDIVISION:
                return 0
            case TournamentType.CHAMPIONSHIP_DIVISION:
                return 0
            case TournamentType.CHAMPIONSHIP:
                return 0
            case _:
                return basePoints


class SimpleCMPQualification(SimpleEventPoints):

    # CMP Qualification Succession

    def get_direct_qualification_succession(self) -> list[Team]: ...
