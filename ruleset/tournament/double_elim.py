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


class DoubleElimTournament:
    event: Event

    allianceCount: int

    def __init__(self, event: Event):
        self.event = event
        self.allianceCount = len(event.alliances)

    def get_playoff_from_round(
        self, round: PlayoffRound, part: int, match: int
    ) -> Match:
        matchNumber: Optional[int] = None

        match round:
            case PlayoffRound.QUARTER:
                pass
            case PlayoffRound.SEMI:
                if part in range(1, 14) and match == 1:
                    matchNumber = part
            case PlayoffRound.FINAL:
                if part == 1 and match >= 1:
                    matchNumber = 13 + match

        if matchNumber is not None:
            return self.event.get_match_from_number(
                TournamentLevel.PLAYOFF, matchNumber
            )

        raise ValueError(f"Invalid playoff round {round}, part {part}, match {match}")

    def _get_existing_round_matches(
        self, round: PlayoffRound, part: int
    ) -> list[Match]:
        if round == PlayoffRound.SEMI:
            return [self.get_playoff_from_round(round, part, 1)]

        if round == PlayoffRound.FINAL and part == 1:
            finalMatchCount = max(
                matchNumber - 13
                for matchNumber in self.event.playoffMatches
                if matchNumber >= 14
            )
            return [
                self.get_playoff_from_round(round, part, matchNumber)
                for matchNumber in range(1, finalMatchCount + 1)
            ]

        raise ValueError(f"Invalid playoff round {round}, part {part}")

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
