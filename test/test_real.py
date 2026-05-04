# Copyright (c) 2026 FRC Team 6907, The G.O.A.T
# Licensed under the MIT License.

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
import unittest
from typing import Any, cast
from unittest.mock import patch

from data.event_requests import request_event_data
from data.frc_json import EventRequestType, SeasonRequestType
from real.alliance import Alliance, AnonymousAlliance, AllianceRole, AllianceColor
from real.event import Event
from real.match import MatchResult
from real.season import Season
from ruleset.tournament.protocol import TournamentLevel

TEST_CACHE_ROOT = Path(__file__).resolve().parent / "test_cache"
TEST_CACHE_2024 = TEST_CACHE_ROOT / "2024"


def _load_json_object(path: Path) -> dict[str, Any]:
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object at {path}")
    return cast(dict[str, Any], payload)


def _load_azva_event_listing() -> object:
    seasonData = _load_json_object(TEST_CACHE_2024 / "SeasonData.json")
    eventsValueRaw = seasonData.get("events")
    if not isinstance(eventsValueRaw, dict):
        raise ValueError("Expected 'events' object in SeasonData.json")
    eventsValue = cast(dict[str, Any], eventsValueRaw)

    eventListValueRaw = eventsValue.get("Events")
    if not isinstance(eventListValueRaw, list):
        raise ValueError("Expected 'Events' list in SeasonData.json")
    eventListValue = cast(list[object], eventListValueRaw)

    for eventData in eventListValue:
        if isinstance(eventData, dict):
            typedEventData = cast(dict[str, Any], eventData)
            if typedEventData.get("code") == "AZVA":
                return typedEventData
    raise ValueError("Expected AZVA event listing in test SeasonData.json")


def _load_azva_team_listing() -> list[object]:
    azvaData = _load_json_object(TEST_CACHE_2024 / "2024-AZVA.json")
    teamsValueRaw = azvaData.get("teams")
    if not isinstance(teamsValueRaw, dict):
        raise ValueError("Expected 'teams' object in 2024-AZVA.json")
    teamsValue = cast(dict[str, Any], teamsValueRaw)

    teamListValueRaw = teamsValue.get("teams")
    if not isinstance(teamListValueRaw, list):
        raise ValueError("Expected 'teams' list in 2024-AZVA.json")
    teamListValue = cast(list[object], teamListValueRaw)

    result: list[object] = []
    for teamData in teamListValue:
        if isinstance(teamData, dict):
            typedTeamData = cast(dict[str, Any], teamData)
            teamNumber = typedTeamData.get("teamNumber")
            if isinstance(teamNumber, int):
                result.append({"teamNumber": teamNumber})
    return result


AZVA_EVENT_LISTING: object = _load_azva_event_listing()
AZVA_TEAM_LISTING: list[object] = _load_azva_team_listing()


def build_azva_only_season() -> Season:
    def fake_request_season_data(
        requestType: SeasonRequestType, season: int
    ) -> list[object]:
        if season != 2024:
            raise AssertionError(f"Unexpected season {season}")
        if requestType is SeasonRequestType.TEAM_LISTING:
            return AZVA_TEAM_LISTING
        if requestType is SeasonRequestType.EVENT_LISTING:
            return [AZVA_EVENT_LISTING]
        raise AssertionError(f"Unexpected request type {requestType}")

    with patch("real.season.request_season_data", side_effect=fake_request_season_data):
        return Season(season=2024)


class TestRealEventRequests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._cacheRootPatch = patch.dict(
            os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}
        )
        cls._cacheRootPatch.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._cacheRootPatch.stop()

    def test_request_qualification_matches(self) -> None:
        event = Event(season=2024, eventCode="AZVA")
        team = event.get_team_from_number(6907)

        self.assertEqual(
            len(team.qualsMatches),
            11,
            "Expected team 6907 to have exactly 11 qualification matches",
        )

        match = team.qualsMatches[0]
        self.assertEqual(
            match.matchNumber,
            2,
            "Expected the first qualification match for team 6907 to be match 2",
        )
        self.assertIsInstance(
            match.redAlliance,
            AnonymousAlliance,
            "Expected red alliance to be anonymous",
        )
        redAlliance = cast(AnonymousAlliance, match.redAlliance)
        self.assertEqual(
            redAlliance.get_team_from_station(AllianceRole.STATION_3).teamNumber,
            6907,
            "Expected team 6907 to be assigned to red station 3",
        )
        self.assertEqual(
            match.get_team_from_station(
                AllianceColor.RED, AllianceRole.STATION_3
            ).teamNumber,
            6907,
            "Expected team 6907 to be assigned to red station 3",
        )

    def test_request_qualification_matches_initializes_match_times(self) -> None:
        event = Event(season=2024, eventCode="AZVA")
        team = event.get_team_from_number(6907)

        match = team.qualsMatches[0]
        self.assertEqual(
            match.actualStartTime,
            datetime.fromisoformat("2024-03-15T16:24:39.95+00:00"),
            "Expected actualStartTime to be normalized from AZVA local time to UTC",
        )
        self.assertEqual(
            match.postResultTime,
            datetime.fromisoformat("2024-03-15T16:28:23.23+00:00"),
            "Expected postResultTime to be normalized from AZVA local time to UTC",
        )

    def test_request_playoff_matches_initializes_match_and_team_links(self) -> None:
        event = Event(season=2024, eventCode="AZVA")
        team = event.get_team_from_number(6907)

        self.assertEqual(
            len(event.playoffMatches),
            16,
            "Expected exactly 16 playoff matches for 2024 AZVA",
        )
        self.assertEqual(
            len(team.playoffMatches),
            5,
            "Expected team 6907 to have exactly 5 playoff matches",
        )

        match = event.get_match_from_number(TournamentLevel.PLAYOFF, 2)
        self.assertIsInstance(
            team.alliance,
            Alliance,
            "Expected playoff team alliance to be a named alliance",
        )
        self.assertIsInstance(
            match.blueAlliance,
            Alliance,
            "Expected playoff blue alliance to be a named alliance",
        )
        teamAlliance = cast(Alliance, team.alliance)
        blueAlliance = cast(Alliance, match.blueAlliance)
        self.assertEqual(
            match.matchNumber, 2, "Expected playoff match 2 to be initialized"
        )
        self.assertIs(
            match.redAlliance,
            teamAlliance,
            "Expected red alliance to resolve from team alliance",
        )
        self.assertEqual(
            teamAlliance.allianceNumber,
            4,
            "Expected team 6907 alliance to be Alliance 4",
        )
        self.assertEqual(
            blueAlliance.allianceNumber,
            5,
            "Expected opposing alliance to be Alliance 5",
        )
        self.assertIn(
            match,
            team.playoffMatches,
            "Expected playoff match 2 to be linked on team 6907",
        )
        self.assertIn(
            match,
            teamAlliance.playoffMatches,
            "Expected playoff match 2 to be linked on Alliance 4",
        )
        self.assertEqual(
            [playoffMatch.matchNumber for playoffMatch in team.playoffMatches],
            [2, 7, 9, 12, 13],
            "Expected team 6907 playoff match numbers to match playoff JSON",
        )

    def test_request_playoff_matches_initializes_match_times_and_scores(self) -> None:
        event = Event(season=2024, eventCode="AZVA")

        match = event.get_match_from_number(TournamentLevel.PLAYOFF, 9)
        self.assertEqual(
            match.actualStartTime,
            datetime.fromisoformat("2024-03-16T22:33:07.313+00:00"),
            "Expected actualStartTime to be normalized from AZVA local time to UTC",
        )
        self.assertEqual(
            match.postResultTime,
            datetime.fromisoformat("2024-03-16T22:36:55.023+00:00"),
            "Expected postResultTime to be normalized from AZVA local time to UTC",
        )
        self.assertEqual(
            match.redScore,
            [80],
            "Expected red final score to match playoff match 9 JSON",
        )
        self.assertEqual(
            match.blueScore,
            [73],
            "Expected blue final score to match playoff match 9 JSON",
        )
        self.assertEqual(
            match.winningAlliance,
            AllianceColor.RED,
            "Expected playoff match 9 winner to be initialized from score details",
        )
        self.assertEqual(
            match.redScoreDetails.get("alliance"),
            "Red",
            "Expected red score details to be initialized",
        )
        self.assertEqual(
            match.blueScoreDetails.get("alliance"),
            "Blue",
            "Expected blue score details to be initialized",
        )

    def test_request_event_awards_initializes_awards_and_team_links(self) -> None:
        event = Event(season=2024, eventCode="AZVA")

        self.assertEqual(
            len(event.awards),
            20,
            "Expected grouped award names to match AZVA 2024 awards JSON",
        )

        innovationAwards = event.get_award_from_name("Innovation in Control Award")
        self.assertEqual(
            len(innovationAwards),
            1,
            "Expected Innovation in Control Award to have one recipient",
        )
        innovationAward = innovationAwards[0]
        self.assertEqual(
            innovationAward.name,
            "Innovation in Control Award",
            "Expected award name to be initialized",
        )
        self.assertIs(
            innovationAward.team,
            event.get_team_from_number(6907),
            "Expected award team to link to team 6907",
        )
        self.assertIsNone(
            innovationAward.person, "Expected team award person to be None"
        )
        self.assertIn(
            "Innovation in Control Award",
            event.get_team_from_number(6907).awards,
            "Expected team 6907 awards list to include Innovation in Control Award",
        )

        volunteerAwards = event.get_award_from_name("Volunteer of the Year")
        self.assertEqual(
            len(volunteerAwards),
            1,
            "Expected Volunteer of the Year to have one recipient",
        )
        volunteerAward = volunteerAwards[0]
        self.assertEqual(
            volunteerAward.person,
            "George Williams",
            "Expected Volunteer of the Year person to match JSON",
        )
        self.assertIs(
            volunteerAward.team,
            event.get_team_from_number(60),
            "Expected Volunteer of the Year to link to team 60",
        )

    def test_request_event_awards_groups_duplicate_award_names(self) -> None:
        event = Event(season=2024, eventCode="AZVA")

        winnersAwards = event.get_award_from_name("Regional Winners")
        self.assertEqual(
            len(winnersAwards),
            3,
            "Expected Regional Winners to keep all three award recipients",
        )
        self.assertEqual(
            [
                award.team.teamNumber
                for award in winnersAwards
                if award.team is not None
            ],
            [3128, 6036, 9501],
            "Expected Regional Winners team order to match JSON series order",
        )

        deanListAwards = event.get_award_from_name("FIRST Dean's List Finalist Award")
        self.assertEqual(
            len(deanListAwards), 2, "Expected Dean's List award to keep both recipients"
        )
        self.assertEqual(
            [award.person for award in deanListAwards],
            ["Elizabeth S", "David Y"],
            "Expected Dean's List recipients to match JSON",
        )

    def test_match_result_helpers_for_real_playoff_match(self) -> None:
        event = Event(season=2024, eventCode="AZVA")

        match = event.get_match_from_number(TournamentLevel.PLAYOFF, 2)
        redAlliance = event.get_alliance_from_number(4)
        blueAlliance = event.get_alliance_from_number(5)
        redTeam = event.get_team_from_number(6907)
        blueTeam = event.get_team_from_number(696)

        result = match.get_result()
        self.assertEqual(
            result[MatchResult.WIN],
            [redAlliance],
            "Expected Alliance 4 to win playoff match 2",
        )
        self.assertEqual(
            result[MatchResult.LOSS],
            [blueAlliance],
            "Expected Alliance 5 to lose playoff match 2",
        )
        self.assertEqual(
            result[MatchResult.TIE], [], "Expected playoff match 2 to have no tie"
        )
        self.assertEqual(
            result[MatchResult.DQ], [], "Expected playoff match 2 to have no DQ"
        )
        self.assertEqual(
            match.get_result_by_alliance(redAlliance),
            MatchResult.WIN,
            "Expected Alliance 4 to be the winner of playoff match 2",
        )
        self.assertEqual(
            match.get_result_by_alliance(blueAlliance),
            MatchResult.LOSS,
            "Expected Alliance 5 to be the loser of playoff match 2",
        )
        self.assertEqual(
            match.get_result_by_team(redTeam),
            MatchResult.WIN,
            "Expected team 6907 to win playoff match 2",
        )
        self.assertEqual(
            match.get_result_by_team(blueTeam),
            MatchResult.LOSS,
            "Expected team 696 to lose playoff match 2",
        )
        self.assertIs(
            match.get_alliance_by_team(redTeam),
            redAlliance,
            "Expected team 6907 to map back to Alliance 4 in playoff match 2",
        )
        self.assertIs(
            match.get_alliance_by_team(blueTeam),
            blueAlliance,
            "Expected team 696 to map back to Alliance 5 in playoff match 2",
        )
        self.assertEqual(
            match.get_team_from_station(
                AllianceColor.BLUE, AllianceRole.STATION_2
            ).teamNumber,
            2659,
            "Expected playoff Blue2 station to map to team 2659",
        )

    def test_match_result_helpers_for_real_tied_qualification_match(self) -> None:
        event = Event(season=2024, eventCode="AZVA")

        match = event.get_match_from_number(TournamentLevel.QUALIFICATION, 30)
        redTeam = event.get_team_from_number(3128)
        blueTeam = event.get_team_from_number(60)

        result = match.get_result()
        self.assertEqual(
            result[MatchResult.WIN],
            [],
            "Expected qualification match 30 to have no winner",
        )
        self.assertEqual(
            result[MatchResult.LOSS],
            [],
            "Expected qualification match 30 to have no loser",
        )
        self.assertEqual(
            result[MatchResult.DQ], [], "Expected qualification match 30 to have no DQ"
        )
        self.assertEqual(
            len(result[MatchResult.TIE]),
            2,
            "Expected qualification match 30 to list both alliances as tie",
        )
        self.assertEqual(
            match.winningAlliance,
            AllianceColor.NONE,
            "Expected qualification match 30 to use AllianceColor.NONE for a tie",
        )
        self.assertEqual(
            match.get_result_by_team(redTeam),
            MatchResult.TIE,
            "Expected team 3128 to be tied in qualification match 30",
        )
        self.assertEqual(
            match.get_result_by_team(blueTeam),
            MatchResult.TIE,
            "Expected team 60 to be tied in qualification match 30",
        )
        self.assertEqual(
            str(match),
            "<Qualification 30>",
            "Expected qualification string format to include the real match number",
        )

    def test_match_string_formats_for_real_match_numbers(self) -> None:
        event = Event(season=2024, eventCode="AZVA")

        self.assertEqual(
            str(event.get_match_from_number(TournamentLevel.QUALIFICATION, 2)),
            "<Qualification 2>",
            "Expected qualification match string format to match match number",
        )
        self.assertEqual(
            str(event.get_match_from_number(TournamentLevel.PLAYOFF, 12)),
            "<Playoff Match 12>",
            "Expected playoff bracket string format to match API numbering",
        )
        self.assertEqual(
            str(event.get_match_from_number(TournamentLevel.PLAYOFF, 14)),
            "<Final 1>",
            "Expected playoff match 14 to render as Final 1",
        )
        self.assertEqual(
            str(event.get_match_from_number(TournamentLevel.PLAYOFF, 16)),
            "<Final Tiebreaker>",
            "Expected playoff match 16 to render as Final Tiebreaker",
        )

    def test_alliance_helpers_and_team_succession_methods(self) -> None:
        event = Event(season=2024, eventCode="AZVA")
        alliance = event.get_alliance_from_number(4)
        captain = event.get_team_from_number(3256)
        firstPick = event.get_team_from_number(6907)
        secondPick = event.get_team_from_number(9704)

        self.assertTrue(
            alliance.is_member(captain),
            "Expected captain to be recognized as alliance member",
        )
        self.assertFalse(
            alliance.is_member(event.get_team_from_number(6036)),
            "Expected a team from another alliance to not be recognized as a member",
        )
        self.assertEqual(
            str(alliance),
            "<Alliance 4>",
            "Expected alliance string format to include alliance number",
        )
        self.assertEqual(
            repr(alliance),
            "<Alliance 4>",
            "Expected alliance repr to match string output",
        )
        self.assertEqual(
            str(captain),
            "<Team 3256>",
            "Expected team string format to include team number",
        )
        self.assertEqual(
            repr(firstPick), "<Team 6907>", "Expected team repr to match string output"
        )
        self.assertEqual(
            captain.get_succession(),
            7,
            "Expected captain succession to match alliance selection order",
        )
        self.assertEqual(
            firstPick.get_succession(),
            8,
            "Expected first pick succession to match alliance selection order",
        )
        self.assertEqual(
            secondPick.get_succession(),
            21,
            "Expected second pick succession to match alliance selection order",
        )
        self.assertEqual(
            captain.get_succession_of_selection(),
            0,
            "Expected captain selection succession to be 0",
        )
        self.assertEqual(
            firstPick.get_succession_of_selection(),
            1,
            "Expected first pick selection succession to match ranking math",
        )
        self.assertEqual(
            secondPick.get_succession_of_selection(),
            14,
            "Expected second pick selection succession to match ranking math",
        )
        self.assertEqual(
            [match.matchNumber for match in alliance.get_win_playoffs()],
            [2, 9, 12],
            "Expected Alliance 4 winning playoff matches to match event results",
        )

    def test_team_matches_and_result_filtering(self) -> None:
        event = Event(season=2024, eventCode="AZVA")
        team = event.get_team_from_number(6907)

        self.assertEqual(
            len(team.matches),
            len(team.qualsMatches) + len(team.playoffMatches),
            "Expected Team.matches to combine qualification and playoff matches",
        )
        winMatches = team.get_matches_by_result([MatchResult.WIN])
        lossMatches = team.get_matches_by_result([MatchResult.LOSS])
        tieMatches = team.get_matches_by_result([MatchResult.TIE])
        self.assertGreater(
            len(winMatches), 0, "Expected team 6907 to have at least one win"
        )
        self.assertGreater(
            len(lossMatches), 0, "Expected team 6907 to have at least one loss"
        )
        self.assertEqual(
            tieMatches, [], "Expected team 6907 to have no tied matches at AZVA 2024"
        )
        self.assertIn(
            2,
            [match.matchNumber for match in winMatches],
            "Expected qualification match 2 to be a win",
        )
        self.assertIn(
            7,
            [match.matchNumber for match in lossMatches],
            "Expected playoff match 7 to be a loss",
        )

    def test_team_without_alliance_returns_none_for_succession_methods(self) -> None:
        event = Event(season=2024, eventCode="AZVA")
        team = event.get_team_from_number(6833)

        self.assertIsNone(
            team.get_succession(),
            "Expected unselected team to have no alliance succession",
        )
        self.assertIsNone(
            team.get_succession_of_selection(),
            "Expected unselected team to have no selection succession",
        )

    def test_request_alliances_initializes_event_and_team_links(self) -> None:
        event = Event(season=2024, eventCode="AZVA")

        self.assertEqual(
            len(event.alliances), 8, "Expected exactly 8 alliances for 2024 AZVA"
        )

        alliance = event.get_alliance_from_number(4)
        self.assertEqual(
            alliance.allianceNumber, 4, "Expected alliance number to be initialized"
        )
        self.assertEqual(
            alliance.name, "Alliance 4", "Expected alliance name to match API data"
        )
        self.assertIsNotNone(
            alliance.get_team_from_role(AllianceRole.CAPTAIN),
            "Expected captain to be initialized",
        )
        self.assertIsNotNone(
            alliance.get_team_from_role(AllianceRole.PICK_1ST),
            "Expected round1 pick to be initialized",
        )
        self.assertIsNotNone(
            alliance.get_team_from_role(AllianceRole.PICK_2ND),
            "Expected round2 pick to be initialized",
        )
        self.assertEqual(
            [
                alliance.get_team_from_role(role).teamNumber
                for role in (
                    AllianceRole.CAPTAIN,
                    AllianceRole.PICK_1ST,
                    AllianceRole.PICK_2ND,
                )
            ],
            [3256, 6907, 9704],
            "Expected alliance teams to match API data",
        )

        captain = event.get_team_from_number(3256)
        self.assertIs(
            captain.alliance, alliance, "Expected captain to point back to alliance"
        )
        self.assertEqual(captain.allianceRole, 1, "Expected captain role to be 1")

        firstPick = event.get_team_from_number(6907)
        self.assertIs(
            firstPick.alliance,
            alliance,
            "Expected first pick to point back to alliance",
        )
        self.assertEqual(firstPick.allianceRole, 2, "Expected first pick role to be 2")

    def test_validate_team_ranking_fields(self) -> None:
        event = Event(season=2024, eventCode="AZVA")
        team = event.get_team_from_number(6907)

        self.assertEqual(team.ranking, 8, "Expected team 6907 ranking to be 8")
        self.assertEqual(
            team.sortOrder,
            (2.18, 0.36, 50.55, 16.82, 2.36, 0.0),
            "Expected team 6907 sortOrder to match ranking data",
        )

        self.assertIs(
            event.get_team_from_rank(8), team, "Expected rank 8 to map to team 6907"
        )

    def test_validate_team_basic_fields(self) -> None:
        event = Event(season=2024, eventCode="AZVA")
        team = event.get_team_from_number(6907)

        self.assertEqual(
            team.nameShort,
            "The G.O.A.T",
            "Expected team 6907 nameShort to match API data",
        )
        self.assertEqual(
            team.rookieYear, 2018, "Expected team 6907 rookieYear to be 2018"
        )
        self.assertIsNone(
            team.districtCode, "Expected team 6907 districtCode to be None"
        )

    def test_initialize_teams_and_get_team_by_number(self) -> None:
        event = Event(season=2024, eventCode="AZVA")

        self.assertEqual(
            len(event.teams), 41, "Expected exactly 41 teams for 2024 AZVA"
        )

        team = event.get_team_from_number(6907)
        self.assertIsNotNone(team, "Expected to retrieve team 6907")
        self.assertEqual(
            team.teamNumber, 6907, "Expected returned team number to be 6907"
        )
        self.assertIs(
            team.event,
            event,
            "Expected team.event to reference the same Event instance",
        )

    def test_request_teams_reads_azva_team_listing_from_test_cache(self) -> None:
        teamsData = request_event_data(EventRequestType.TEAMS, 2024, "AZVA")

        self.assertEqual(
            len(teamsData),
            41,
            "Expected 2024 AZVA team listing from test cache to contain 41 teams",
        )

    def test_request_event_data_all_request_types(self) -> None:
        event = Event(season=2024, eventCode="AZVA")

        expectedMeta: dict[EventRequestType, tuple[str, str]] = {
            EventRequestType.TEAMS: ("teams", "teams"),
            EventRequestType.RANKINGS: ("rankings", "Rankings"),
            EventRequestType.ALLIANCES: ("alliances", "Alliances"),
            EventRequestType.QUALIFICATION_MATCHES: (
                "qualification_matches",
                "Matches",
            ),
            EventRequestType.PLAYOFF_MATCHES: ("playoff_matches", "Matches"),
            EventRequestType.AWARDS: ("awards", "Awards"),
            EventRequestType.QUALIFICATION_SCORE_DETAILS: (
                "qualification_score_details",
                "MatchScores",
            ),
            EventRequestType.PLAYOFF_SCORE_DETAILS: (
                "playoff_score_details",
                "MatchScores",
            ),
        }

        cacheFile = TEST_CACHE_2024 / "2024-AZVA.json"
        cacheData: Any = json.loads(cacheFile.read_text(encoding="utf-8"))
        self.assertIsInstance(
            cacheData, dict, "Expected test cache file content to be JSON object"
        )

        # All requests should resolve directly from test cache without network.
        for requestType in EventRequestType:
            with self.subTest(requestType=requestType.name):
                dataList = event.request_event_data(requestType)
                self.assertIsInstance(
                    dataList, list, "Expected response payload to be list"
                )
                self.assertGreater(len(dataList), 0, "Expected non-empty data list")

        for requestType in EventRequestType:
            cacheKey, _ = expectedMeta[requestType]
            self.assertIn(
                cacheKey, cacheData, f"Expected cache key '{cacheKey}' in cache file"
            )
            self.assertIsInstance(
                cacheData[cacheKey], dict, "Expected cached entry to be a dict"
            )

        with patch(
            "data.frc_json.fetch_frc_json", side_effect=RuntimeError("network disabled")
        ):
            for requestType in EventRequestType:
                with self.subTest(cacheRequestType=requestType.name):
                    dataList = event.request_event_data(requestType)
                    self.assertIsInstance(
                        dataList, list, "Expected cached response payload to be list"
                    )
                    self.assertGreater(
                        len(dataList), 0, "Expected non-empty cached data list"
                    )

    def test_event_metadata_initializes_utc_dates_from_event_timezone(self) -> None:
        event = Event(season=2024, eventCode="AZVA")

        self.assertEqual(
            event.timezone,
            "Pacific Standard Time",
            "Expected event timezone to be initialized from SeasonData listing",
        )
        self.assertEqual(
            event.dateStart,
            datetime(2024, 3, 13, 7, 0, 0, tzinfo=timezone.utc),
            "Expected AZVA dateStart to be normalized from local midnight to UTC",
        )
        self.assertEqual(
            event.dateEnd,
            datetime(2024, 3, 17, 6, 59, 59, tzinfo=timezone.utc),
            "Expected AZVA dateEnd to be normalized from local end-of-day to UTC",
        )


class TestRealSeasonRequests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._cacheRootPatch = patch.dict(
            os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}
        )
        cls._cacheRootPatch.start()
        cls.season = build_azva_only_season()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._cacheRootPatch.stop()

    def test_request_event_listing_initializes_season_teams_from_listing(self) -> None:
        season = self.season

        self.assertEqual(
            len(season.events),
            1,
            "Expected test season to initialize exactly one event week",
        )
        self.assertEqual(
            len(season.teams),
            41,
            "Expected AZVA-only season to initialize exactly 41 teams",
        )
        self.assertIn(
            3, season.events, "Expected week 3 events to be initialized for 2024 season"
        )
        self.assertIn(
            "AZVA",
            [event.eventCode for event in season.events[3]],
            "Expected Arizona Valley Regional to be present in the AZVA-only test season",
        )
        self.assertEqual(
            len(season.events[3]),
            1,
            "Expected only AZVA to be present in the test season",
        )

        seasonTeam = season.get_team_from_number(6907)
        self.assertEqual(
            seasonTeam.teamNumber, 6907, "Expected to retrieve season team 6907"
        )
        self.assertEqual(
            len(seasonTeam.events),
            1,
            "Expected season team 6907 to be linked to one event",
        )
        self.assertEqual(
            len(seasonTeam.eventTeams),
            1,
            "Expected season team 6907 to be linked to one event team",
        )
        self.assertEqual(
            [event.eventCode for _, event in seasonTeam.events],
            ["AZVA"],
            "Expected season team 6907 to be linked to Arizona Valley Regional in 2024",
        )
        self.assertIs(
            seasonTeam.eventTeams[0][1].seasonTeam,
            seasonTeam,
            "Expected event team to link back to season team",
        )

    def test_get_team_from_number_raises_for_unknown_team(self) -> None:
        season = self.season

        with self.assertRaises(
            ValueError, msg="Expected unknown season team lookup to raise ValueError"
        ):
            season.get_team_from_number(999999)


class TestRealDomainHelpers(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._cacheRootPatch = patch.dict(
            os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}
        )
        cls._cacheRootPatch.start()
        cls.event = Event(season=2024, eventCode="AZVA")
        cls.season = build_azva_only_season()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._cacheRootPatch.stop()

    def test_event_and_award_string_representations(self) -> None:
        event = self.event
        singleAward = event.get_award_from_name("Regional Winners")[0]
        seriesAward = event.get_award_from_name("FIRST Dean's List Finalist Award")[0]

        self.assertEqual(
            str(event),
            "<Event 2024 AZVA>",
            "Expected event string format to include season and code",
        )
        self.assertEqual(
            repr(event),
            "<Event 2024 AZVA>",
            "Expected event repr to match string output",
        )
        self.assertEqual(
            str(singleAward),
            "<Award Regional Winners>",
            "Expected award string format to include name",
        )
        self.assertEqual(
            repr(singleAward),
            "<Award Regional Winners>",
            "Expected award repr to match string output",
        )
        self.assertEqual(
            str(seriesAward),
            "<Award FIRST Dean's List Finalist Award>",
            "Expected award string to match current award name rendering",
        )
        self.assertEqual(
            repr(seriesAward),
            "<Award FIRST Dean's List Finalist Award>",
            "Expected series award repr to match string output",
        )

    def test_anonymous_alliance_helpers_and_registration(self) -> None:
        event = self.event
        match = event.get_match_from_number(TournamentLevel.QUALIFICATION, 2)

        self.assertIsInstance(
            match.redAlliance,
            AnonymousAlliance,
            "Expected qualification red alliance to be anonymous",
        )
        redAlliance = cast(AnonymousAlliance, match.redAlliance)
        redAlliance.register_match(match, AllianceColor.RED)

        self.assertEqual(
            str(redAlliance),
            "<Alliance 5430 6036 6907>",
            "Expected anonymous alliance string to list station team numbers",
        )
        self.assertEqual(
            repr(redAlliance),
            "<Alliance 5430 6036 6907>",
            "Expected anonymous alliance repr to match string output",
        )
        self.assertIs(
            redAlliance.match,
            match,
            "Expected anonymous alliance to register its owning match",
        )
        self.assertEqual(
            redAlliance.color,
            AllianceColor.RED,
            "Expected anonymous alliance color to be assigned",
        )
        self.assertTrue(
            redAlliance.is_member(event.get_team_from_number(6907)),
            "Expected anonymous alliance membership check to recognize team 6907",
        )
        self.assertEqual(
            redAlliance.get_team_from_station(AllianceRole.STATION_1).teamNumber,
            5430,
            "Expected anonymous alliance station lookup to return the real team",
        )
        with self.assertRaises(
            ValueError,
            msg="Expected captain role lookup to fail for anonymous alliance",
        ):
            redAlliance.get_team_from_station(AllianceRole.CAPTAIN)

    def test_season_team_helpers_and_string_representations(self) -> None:
        seasonTeam = self.season.get_team_from_number(6907)

        self.assertEqual(
            str(seasonTeam),
            "<SeasonTeam 6907>",
            "Expected SeasonTeam string format to include number",
        )
        self.assertEqual(
            repr(seasonTeam),
            "<SeasonTeam 6907>",
            "Expected SeasonTeam repr to match string output",
        )
        self.assertEqual(
            [team.teamNumber for team in seasonTeam.get_events_by_weeks([3])],
            [6907],
            "Expected SeasonTeam.get_events_by_weeks to return event teams for the selected week",
        )
        self.assertEqual(
            seasonTeam.get_events_by_weeks([1, 2]),
            [],
            "Expected SeasonTeam.get_events_by_weeks to return empty list for weeks without appearances",
        )

    def test_event_getters_raise_for_unknown_keys(self) -> None:
        event = self.event

        with self.assertRaises(
            ValueError, msg="Expected missing team lookup to raise ValueError"
        ):
            event.get_team_from_number(999999)
        with self.assertRaises(
            ValueError, msg="Expected missing rank lookup to raise ValueError"
        ):
            event.get_team_from_rank(999999)
        with self.assertRaises(
            ValueError, msg="Expected missing alliance lookup to raise ValueError"
        ):
            event.get_alliance_from_number(999999)
        with self.assertRaises(
            ValueError, msg="Expected missing match lookup to raise ValueError"
        ):
            event.get_match_from_number(TournamentLevel.QUALIFICATION, 999999)
        with self.assertRaises(
            ValueError, msg="Expected missing award lookup to raise ValueError"
        ):
            event.get_award_from_name("Not A Real Award")

    def test_alliance_get_team_from_role_raises_when_role_missing(self) -> None:
        alliance = self.event.get_alliance_from_number(4)

        with self.assertRaises(
            ValueError, msg="Expected missing backup role lookup to raise ValueError"
        ):
            alliance.get_team_from_role(AllianceRole.BACKUP)

    def test_match_getters_raise_when_team_or_alliance_missing(self) -> None:
        event = self.event
        match = event.get_match_from_number(TournamentLevel.QUALIFICATION, 2)
        outsider = event.get_team_from_number(6833)

        with self.assertRaises(
            ValueError, msg="Expected invalid station lookup to raise ValueError"
        ):
            match.get_team_from_station(AllianceColor.RED, AllianceRole.CAPTAIN)
        with self.assertRaises(
            ValueError, msg="Expected outsider team result lookup to raise ValueError"
        ):
            match.get_result_by_team(outsider)
        with self.assertRaises(
            ValueError, msg="Expected outsider alliance lookup to raise ValueError"
        ):
            match.get_alliance_by_team(outsider)


if __name__ == "__main__":
    unittest.main()
