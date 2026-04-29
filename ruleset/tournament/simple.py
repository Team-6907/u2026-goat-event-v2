# Copyright (c) 2026 FRC Team 6907, The G.O.A.T
# Licensed under the MIT License.

from __future__ import annotations

from typing import TYPE_CHECKING
from typing import Optional, cast

from real.alliance import Alliance, AllianceColor
from real.match import PlayoffRound
from ruleset.tournament.protocol import TournamentLevel

if TYPE_CHECKING:
    from real.event import Event
    from real.match import Match, PlayoffRound


class SimpleTournament:
    event: Event

    allianceCount: int

    def __init__(self, event: Event):
        self.event = event
        self.allianceCount = len(event.alliances)

    # Getters

    def get_playoff_from_round(
        self, round: PlayoffRound, part: int, match: int
    ) -> Match:
        matchNumber = None
        if match in (1, 2, 3) or round == PlayoffRound.FINAL:
            match round:
                case PlayoffRound.QUARTER:
                    if part in (1, 2, 3, 4):
                        matchNumber = 4 * (match - 1) + part
                case PlayoffRound.SEMI:
                    if part in (1, 2):
                        matchNumber = 12 + 2 * (match - 1) + part
                case PlayoffRound.FINAL:
                    matchNumber = 18 + match
        if matchNumber is not None:
            resultMatch = self.event.get_match_from_number(
                TournamentLevel.PLAYOFF, matchNumber
            )
            return resultMatch
        raise ValueError(f"Invalid playoff round {round}, part {part}, match {match}")

    def _get_existing_round_matches(
        self, round: PlayoffRound, part: int
    ) -> list[Match]:
        result: list[Match] = []
        maxMatches = 6 if round == PlayoffRound.FINAL else 3

        for matchNumber in range(1, maxMatches + 1):
            try:
                result.append(self.get_playoff_from_round(round, part, matchNumber))
            except ValueError:
                if matchNumber <= 2:
                    raise
                break

        return result

    def _get_match_winner_color(self, match: Match) -> Optional[AllianceColor]:
        winningAlliance = match.winningAlliance
        if winningAlliance in (AllianceColor.RED, AllianceColor.BLUE):
            return winningAlliance

        if len(match.redScore) > 0 and len(match.blueScore) > 0:
            if match.redScore > match.blueScore:
                return AllianceColor.RED
            if match.blueScore > match.redScore:
                return AllianceColor.BLUE

        return None

    def _get_deciding_match(self, matches: list[Match]) -> Match:
        for match in reversed(matches):
            if self._get_match_winner_color(match) is not None:
                return match
        raise ValueError("Winner is not assigned for this playoff round")

    def get_round_part_winner(self, round: PlayoffRound, part: int) -> Alliance:
        matches = self._get_existing_round_matches(round, part)
        decidingMatch = self._get_deciding_match(matches)
        winningAlliance = self._get_match_winner_color(decidingMatch)

        if winningAlliance == AllianceColor.RED:
            return cast(Alliance, decidingMatch.get_alliance(AllianceColor.RED))
        if winningAlliance == AllianceColor.BLUE:
            return cast(Alliance, decidingMatch.get_alliance(AllianceColor.BLUE))

        raise ValueError(f"Winner is not assigned for match {decidingMatch}")

    def get_round_part_finalist(self, round: PlayoffRound, part: int) -> Alliance:
        matches = self._get_existing_round_matches(round, part)
        decidingMatch = self._get_deciding_match(matches)
        winningAlliance = self._get_match_winner_color(decidingMatch)

        if winningAlliance == AllianceColor.RED:
            return cast(Alliance, decidingMatch.get_alliance(AllianceColor.BLUE))
        if winningAlliance == AllianceColor.BLUE:
            return cast(Alliance, decidingMatch.get_alliance(AllianceColor.RED))

        raise ValueError(f"Winner is not assigned for match {decidingMatch}")
