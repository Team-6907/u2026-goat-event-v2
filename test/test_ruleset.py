# Copyright (c) 2026 FRC Team 6907, The G.O.A.T
# Licensed under the MIT License.

from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from real.event import Event
from real.match import PlayoffRound
from ruleset.cmpqual.simple import SimpleCMPQualification
from ruleset.tournament.double_elim import DoubleElimTournament
from ruleset.tournament.simple import SimpleTournament

TEST_CACHE_ROOT = Path(__file__).resolve().parent / "test_cache"
TEST_NOW_UTC = datetime(2027, 1, 1, 0, 0, tzinfo=timezone.utc)


class TestSimpleTournamentRealData(unittest.TestCase):
    def test_get_round_part_outcomes_match_real_2019_galileo_results(
        self,
    ) -> None:
        with (
            patch.dict(os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}),
            patch("data.frc_json._current_utc_time", return_value=TEST_NOW_UTC),
        ):
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
        with (
            patch.dict(os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}),
            patch("data.frc_json._current_utc_time", return_value=TEST_NOW_UTC),
        ):
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
        with (
            patch.dict(os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}),
            patch("data.frc_json._current_utc_time", return_value=TEST_NOW_UTC),
        ):
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
        with (
            patch.dict(os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}),
            patch("data.frc_json._current_utc_time", return_value=TEST_NOW_UTC),
        ):
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


class TestDefaultCMPQualificationRule(unittest.TestCase):
    def test_with_default_cmp_qual_rule_uses_expected_rule_class_by_season(
        self,
    ) -> None:
        with (
            patch.dict(os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}),
            patch("data.frc_json._current_utc_time", return_value=TEST_NOW_UTC),
        ):
            cases = {
                2019: "GALILEO",
                2022: "GALILEO",
                2026: "MNDU2",
            }

            for season, eventCode in cases.items():
                with self.subTest(season=season, eventCode=eventCode):
                    event = Event(season=season, eventCode=eventCode)
                    event.with_default_cmp_qual_rule()

                    self.assertIsInstance(
                        event.cmpQualRule,
                        SimpleCMPQualification,
                        f"Expected default CMP qualification rule for {season} {eventCode} to be SimpleCMPQualification",
                    )

    def test_cmp_qual_event_helpers_delegate_to_rule(self) -> None:
        with (
            patch.dict(os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}),
            patch("data.frc_json._current_utc_time", return_value=TEST_NOW_UTC),
        ):
            event = Event(season=2026, eventCode="MNDU2")
            event.with_default_cmp_qual_rule()

        team = event.get_team_from_number(6907)
        directRule = SimpleCMPQualification(event)

        self.assertEqual(
            event.get_qualification_points(team),
            directRule.get_qualification_points(team),
            "Expected Event.get_qualification_points to delegate to CMP qualification rule",
        )

    def test_qualification_points_match_real_2026_mndu2_rankings(self) -> None:
        with (
            patch.dict(os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}),
            patch("data.frc_json._current_utc_time", return_value=TEST_NOW_UTC),
        ):
            event = Event(season=2026, eventCode="MNDU2")
            event.with_default_cmp_qual_rule()

        self.assertEqual(
            event.get_qualification_points(event.get_team_from_rank(1)),
            22,
            "Expected MNDU2 2026 rank 1 qualification points to be 22",
        )
        self.assertEqual(
            event.get_qualification_points(
                event.get_team_from_rank(len(event.rankings))
            ),
            4,
            "Expected MNDU2 2026 last-place qualification points to be 4",
        )
        self.assertEqual(
            event.get_qualification_points(event.get_team_from_number(6907)),
            22,
            "Expected MNDU2 2026 team 6907 qualification points to be 22",
        )

    def test_playoff_round_points_match_real_simple_tournament_results(self) -> None:
        with (
            patch.dict(os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}),
            patch("data.frc_json._current_utc_time", return_value=TEST_NOW_UTC),
        ):
            event2019 = Event(season=2019, eventCode="GALILEO")
            event2019.with_tournament_rule(SimpleTournament)
            event2019.with_default_cmp_qual_rule()

            event2022 = Event(season=2022, eventCode="GALILEO")
            event2022.with_tournament_rule(SimpleTournament)
            event2022.with_default_cmp_qual_rule()

        self.assertEqual(
            event2019.get_playoff_round_points(event2019.get_team_from_number(971)),
            30,
            "Expected 2019 GALILEO champion alliance teams to get 30 playoff round points",
        )
        self.assertEqual(
            event2019.get_playoff_round_points(event2019.get_team_from_number(4587)),
            20,
            "Expected 2019 GALILEO finalist alliance teams to get 20 playoff round points",
        )
        self.assertEqual(
            event2019.get_playoff_round_points(event2019.get_team_from_number(1986)),
            10,
            "Expected 2019 GALILEO quarter-winning alliance teams to get 10 playoff round points",
        )

        self.assertEqual(
            event2022.get_playoff_round_points(event2022.get_team_from_number(1619)),
            30,
            "Expected 2022 GALILEO champion alliance teams to get 30 playoff round points",
        )
        self.assertEqual(
            event2022.get_playoff_round_points(event2022.get_team_from_number(3476)),
            20,
            "Expected 2022 GALILEO finalist alliance teams to get 20 playoff round points",
        )
        self.assertEqual(
            event2022.get_playoff_round_points(event2022.get_team_from_number(1771)),
            10,
            "Expected 2022 GALILEO quarter-winning alliance teams to get 10 playoff round points",
        )

    def test_playoff_round_points_match_real_double_elim_results(self) -> None:
        with (
            patch.dict(os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}),
            patch("data.frc_json._current_utc_time", return_value=TEST_NOW_UTC),
        ):
            event = Event(season=2026, eventCode="MNDU2")
            event.with_default_cmp_qual_rule()

        self.assertEqual(
            event.get_playoff_round_points(event.get_team_from_number(2491)),
            30,
            "Expected 2026 MNDU2 champion alliance teams to get 30 playoff round points",
        )
        self.assertEqual(
            event.get_playoff_round_points(event.get_team_from_number(6907)),
            20,
            "Expected 2026 MNDU2 finalist alliance teams to get 20 playoff round points",
        )
        self.assertEqual(
            event.get_playoff_round_points(event.get_team_from_number(8122)),
            13,
            "Expected 2026 MNDU2 semi 13 losing alliance teams to get 13 playoff round points",
        )
        self.assertEqual(
            event.get_playoff_round_points(event.get_team_from_number(6758)),
            7,
            "Expected 2026 MNDU2 semi 12 losing alliance teams to get 7 playoff round points",
        )
        self.assertEqual(
            event.get_playoff_round_points(event.get_team_from_number(9532)),
            0,
            "Expected 2026 MNDU2 backup teams without winning-match attendance to get 0 playoff round points",
        )

    def test_total_points_match_expected_real_event_breakdowns(self) -> None:
        with (
            patch.dict(os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}),
            patch("data.frc_json._current_utc_time", return_value=TEST_NOW_UTC),
        ):
            cases = {
                (2026, "MNDU2", 6907): (22, 16, 20, 0, 5, 63),
                (2026, "MNDU2", 2052): (21, 16, 20, 0, 28, 85),
                (2026, "MILIV", 27): (22, 16, 30, 0, 10, 78),
                (2026, "MICMP1", 27): (22, 16, 30, 0, 0, 204),
                (2026, "MICMP1", 5907): (20, 15, 20, 0, 0, 165),
                (2026, "MICMP", 27): (0, 0, 20, 0, 10, 90),
                (2026, "TUIS3", 10131): (21, 15, 30, 5, 45, 116),
            }

            for (season, eventCode, teamNumber), expected in cases.items():
                with self.subTest(
                    season=season, eventCode=eventCode, teamNumber=teamNumber
                ):
                    event = Event(season=season, eventCode=eventCode)
                    event.with_default_cmp_qual_rule()
                    team = event.get_team_from_number(teamNumber)

                    self.assertEqual(
                        (
                            event.get_qualification_points(team),
                            event.get_alliance_selection_points(team),
                            event.get_playoff_round_points(team),
                            event.get_team_age_points(team),
                            event.get_award_points(team),
                            event.get_total_points(team),
                        ),
                        expected,
                        f"Expected total-point breakdown for {season} {eventCode} team {teamNumber} to match the validated real data",
                    )


if __name__ == "__main__":
    unittest.main()
