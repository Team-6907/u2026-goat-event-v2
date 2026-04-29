# Copyright (c) 2026 FRC Team 6907, The G.O.A.T
# Licensed under the MIT License.

from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from real.event import Event
from real.match import PlayoffRound
from ruleset.tournament.double_elim import DoubleElimTournament
from ruleset.tournament.simple import SimpleTournament

TEST_CACHE_ROOT = Path(__file__).resolve().parent / "test_cache"


class TestSimpleTournamentRealData(unittest.TestCase):
    def test_get_round_part_outcomes_match_real_2019_galileo_results(
        self,
    ) -> None:
        with patch.dict(os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}):
            event = Event(season=2019, eventCode="GALILEO")
            event.with_tournament_rule(SimpleTournament)

        expectedRounds = {
            PlayoffRound.QUARTER: {
                1: (1, 8),
                2: (5, 4),
                3: (2, 7),
                4: (3, 6),
            },
            PlayoffRound.SEMI: {
                1: (1, 5),
                2: (2, 3),
            },
            PlayoffRound.FINAL: {
                1: (1, 2),
            },
        }

        for round_value, parts in expectedRounds.items():
            for part, (winner, finalist) in parts.items():
                with self.subTest(round=round_value.name, part=part):
                    self.assertEqual(
                        event.get_round_part_winner(round_value, part).allianceNumber,
                        winner,
                        f"Expected GALILEO 2019 {round_value.name.lower()} part {part} winner to be Alliance {winner}",
                    )
                    self.assertEqual(
                        event.get_round_part_finalist(round_value, part).allianceNumber,
                        finalist,
                        f"Expected GALILEO 2019 {round_value.name.lower()} part {part} finalist to be Alliance {finalist}",
                    )

    def test_get_round_part_outcomes_match_real_2022_galileo_results(
        self,
    ) -> None:
        with patch.dict(os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}):
            event = Event(season=2022, eventCode="GALILEO")
            event.with_tournament_rule(SimpleTournament)

        expectedRounds = {
            PlayoffRound.QUARTER: {
                1: (1, 8),
                2: (4, 5),
                3: (7, 2),
                4: (6, 3),
            },
            PlayoffRound.SEMI: {
                1: (1, 4),
                2: (6, 7),
            },
            PlayoffRound.FINAL: {
                1: (1, 6),
            },
        }

        for round_value, parts in expectedRounds.items():
            for part, (winner, finalist) in parts.items():
                with self.subTest(round=round_value.name, part=part):
                    self.assertEqual(
                        event.get_round_part_winner(round_value, part).allianceNumber,
                        winner,
                        f"Expected GALILEO 2022 {round_value.name.lower()} part {part} winner to be Alliance {winner}",
                    )
                    self.assertEqual(
                        event.get_round_part_finalist(round_value, part).allianceNumber,
                        finalist,
                        f"Expected GALILEO 2022 {round_value.name.lower()} part {part} finalist to be Alliance {finalist}",
                    )


class TestDoubleElimTournamentRealData(unittest.TestCase):
    def test_get_round_part_outcomes_match_real_2024_azva_results(self) -> None:
        with patch.dict(os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}):
            event = Event(season=2024, eventCode="AZVA")
            event.with_tournament_rule(DoubleElimTournament)

        expectedSemi = {
            1: (1, 8),
            2: (4, 5),
            3: (7, 2),
            4: (6, 3),
            5: (5, 8),
            6: (2, 3),
            7: (1, 4),
            8: (7, 6),
            9: (4, 2),
            10: (5, 6),
            11: (1, 7),
            12: (4, 5),
            13: (7, 4),
        }

        for part, (winner, finalist) in expectedSemi.items():
            with self.subTest(round="semi", part=part):
                self.assertEqual(
                    event.get_round_part_winner(PlayoffRound.SEMI, part).allianceNumber,
                    winner,
                    f"Expected AZVA 2024 semi part {part} winner to be Alliance {winner}",
                )
                self.assertEqual(
                    event.get_round_part_finalist(
                        PlayoffRound.SEMI, part
                    ).allianceNumber,
                    finalist,
                    f"Expected AZVA 2024 semi part {part} finalist to be Alliance {finalist}",
                )

        self.assertEqual(
            event.get_round_part_winner(PlayoffRound.FINAL, 1).allianceNumber,
            1,
            "Expected AZVA 2024 final winner to be Alliance 1",
        )
        self.assertEqual(
            event.get_round_part_finalist(PlayoffRound.FINAL, 1).allianceNumber,
            7,
            "Expected AZVA 2024 final finalist to be Alliance 7",
        )


class TestDefaultTournamentRule(unittest.TestCase):
    def test_with_default_tournament_rule_uses_expected_rule_class_by_season(
        self,
    ) -> None:
        with patch.dict(os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}):
            cases = {
                2019: ("GALILEO", SimpleTournament),
                2022: ("GALILEO", SimpleTournament),
                2024: ("AZVA", DoubleElimTournament),
            }

            for season, (eventCode, expectedRuleClass) in cases.items():
                with self.subTest(season=season, eventCode=eventCode):
                    event = Event(season=season, eventCode=eventCode)

                    self.assertIsInstance(
                        event.tournamentRule,
                        expectedRuleClass,
                        f"Expected default tournament rule for {season} {eventCode} to be {expectedRuleClass.__name__}",
                    )


if __name__ == "__main__":
    unittest.main()
