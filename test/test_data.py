# Copyright (c) 2026 FRC Team 6907, The G.O.A.T
# Licensed under the MIT License.

from __future__ import annotations

import hashlib
import json
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

from data.frc_json import (
    CACHE_FETCHED_AT_FIELD,
    EVENT_FILE_SHA256_FIELD,
    FRCNetworkError,
    bypass_event_cache_file,
    bypassed_events_for_season,
    request_frc_json,
    request_paginated_season_frc_json,
    request_season_frc_json,
)

TEST_CACHE_ROOT = Path(__file__).resolve().parent / "test_cache"
TEST_EVENT_CACHE_2024_AZVA = TEST_CACHE_ROOT / "2024" / "2024-AZVA.json"
TEST_SEASON_CACHE_2024 = TEST_CACHE_ROOT / "2024" / "SeasonData.json"
TEST_SEASON_CACHE_2026 = TEST_CACHE_ROOT / "2026" / "SeasonData.json"


class TestData(unittest.TestCase):
    def test_request_frc_json_reads_from_test_cache_without_network(self) -> None:
        originalContent = TEST_EVENT_CACHE_2024_AZVA.read_text(encoding="utf-8")
        try:
            with patch.dict(
                os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}
            ):
                with patch(
                    "data.frc_json.fetch_frc_json",
                    side_effect=RuntimeError("network disabled"),
                ):
                    with patch(
                        "data.frc_json._current_utc_time",
                        return_value=datetime(2024, 3, 20, 0, 0, tzinfo=timezone.utc),
                    ):
                        payload = request_frc_json(
                            url="https://frc-api.firstinspires.org/v3.0/2024/teams?eventCode=AZVA",
                            key="teams",
                            season=2024,
                            eventCode="AZVA",
                        )
        finally:
            TEST_EVENT_CACHE_2024_AZVA.write_text(originalContent, encoding="utf-8")

        expectedTopLevel = {
            "teamCountTotal": 41,
            "teamCountPage": 41,
            "pageCurrent": 1,
            "pageTotal": 1,
        }
        for key, value in expectedTopLevel.items():
            self.assertEqual(
                payload.get(key), value, f"Unexpected value for key '{key}'"
            )

        teamsValue: Any = payload.get("teams")
        self.assertIsInstance(teamsValue, list, "Expected 'teams' to be a list")
        self.assertEqual(
            len(teamsValue), 41, "Expected exactly 41 teams in cached AZVA response"
        )

        teamValue: Any = next(
            (
                team
                for team in teamsValue
                if isinstance(team, dict) and team.get("teamNumber") == 6907
            ),
            None,
        )
        self.assertIsInstance(
            teamValue,
            dict,
            "Expected team 6907 entry to exist in cached teams response",
        )

        expectedTeam = {
            "teamNumber": 6907,
            "nameShort": "The G.O.A.T",
            "country": "China",
            "rookieYear": 2018,
        }
        for key, value in expectedTeam.items():
            self.assertEqual(
                teamValue.get(key),
                value,
                f"Unexpected value for cached team 6907 field '{key}'",
            )

    def test_request_frc_json_writes_cache_fetch_time_on_refetch(self) -> None:
        originalContent = TEST_EVENT_CACHE_2024_AZVA.read_text(encoding="utf-8")
        originalSeasonContent = TEST_SEASON_CACHE_2024.read_text(encoding="utf-8")
        seasonCacheAfterWrite: Any = {}
        expectedHash = ""
        try:
            with patch.dict(
                os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}
            ):
                fakePayload = {"hello": "world"}
                fakeNow = datetime(2026, 5, 4, 12, 0, tzinfo=timezone.utc)

                with patch(
                    "data.frc_json.fetch_frc_json",
                    return_value=fakePayload.copy(),
                ) as mockFetch:
                    with patch("data.frc_json._current_utc_time", return_value=fakeNow):
                        payload = request_frc_json(
                            url="https://example.invalid/test",
                            key="custom_test_payload",
                            season=2024,
                            eventCode="AZVA",
                        )
                        seasonCacheAfterWrite = json.loads(
                            TEST_SEASON_CACHE_2024.read_text(encoding="utf-8")
                        )
                        expectedHash = hashlib.sha256(
                            TEST_EVENT_CACHE_2024_AZVA.read_bytes()
                        ).hexdigest()
        finally:
            TEST_EVENT_CACHE_2024_AZVA.write_text(originalContent, encoding="utf-8")
            TEST_SEASON_CACHE_2024.write_text(originalSeasonContent, encoding="utf-8")

        self.assertEqual(payload.get("hello"), "world")
        self.assertEqual(
            payload.get(CACHE_FETCHED_AT_FIELD),
            fakeNow.isoformat(),
            "Expected fetched payload to store UTC cache fetch time in ISO format",
        )
        self.assertEqual(mockFetch.call_count, 1, "Expected payload to be fetched once")

        self.assertIsInstance(
            seasonCacheAfterWrite,
            dict,
            "Expected SeasonData cache content to be a JSON object",
        )
        hashIndex = seasonCacheAfterWrite.get(EVENT_FILE_SHA256_FIELD)
        self.assertIsInstance(
            hashIndex, dict, "Expected SeasonData to store event file SHA-256 values"
        )
        self.assertEqual(
            hashIndex.get("2024-AZVA.json"),
            expectedHash,
            "Expected SeasonData to store the SHA-256 for the AZVA event cache file",
        )

    def test_request_frc_json_refreshes_event_cache_within_24h_after_event_end(
        self,
    ) -> None:
        originalContent = TEST_EVENT_CACHE_2024_AZVA.read_text(encoding="utf-8")
        originalSeasonContent = TEST_SEASON_CACHE_2024.read_text(encoding="utf-8")
        try:
            with patch.dict(
                os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}
            ):
                fakeNow = datetime(2024, 3, 17, 6, 0, tzinfo=timezone.utc)
                refreshedPayload = {
                    "teamCountTotal": 999,
                    "teamCountPage": 999,
                    "pageCurrent": 1,
                    "pageTotal": 1,
                    "teams": [],
                }

                with patch(
                    "data.frc_json.fetch_frc_json",
                    return_value=refreshedPayload.copy(),
                ) as mockFetch:
                    with patch("data.frc_json._current_utc_time", return_value=fakeNow):
                        payload = request_frc_json(
                            url="https://frc-api.firstinspires.org/v3.0/2024/teams?eventCode=AZVA",
                            key="teams",
                            season=2024,
                            eventCode="AZVA",
                        )
        finally:
            TEST_EVENT_CACHE_2024_AZVA.write_text(originalContent, encoding="utf-8")
            TEST_SEASON_CACHE_2024.write_text(originalSeasonContent, encoding="utf-8")

        self.assertEqual(
            payload.get("teamCountTotal"),
            999,
            "Expected event cache to be refreshed during the 24-hour post-event window",
        )
        self.assertEqual(
            payload.get(CACHE_FETCHED_AT_FIELD),
            fakeNow.isoformat(),
            "Expected refreshed event payload to update cache fetch time",
        )
        self.assertEqual(
            mockFetch.call_count,
            1,
            "Expected cache refresh to hit the network once during refresh window",
        )

    def test_bypass_event_cache_file_stores_metadata_and_expires_after_24h(
        self,
    ) -> None:
        with patch.dict(os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}):
            bypassFile = TEST_CACHE_ROOT / "2024" / "BypassEvents.json"
            eventCacheFile = TEST_EVENT_CACHE_2024_AZVA
            originalContent = (
                bypassFile.read_text(encoding="utf-8") if bypassFile.exists() else None
            )
            originalEventCacheContent = eventCacheFile.read_text(encoding="utf-8")
            originalSeasonContent = TEST_SEASON_CACHE_2024.read_text(encoding="utf-8")

            try:
                bypassFile.unlink(missing_ok=True)

                bypassTime = datetime(2024, 3, 17, 5, 0, tzinfo=timezone.utc)
                with patch("data.frc_json._current_utc_time", return_value=bypassTime):
                    bypass_event_cache_file(
                        2024, "AZVA", reason="incomplete event data"
                    )

                seasonPayload: Any = json.loads(
                    TEST_SEASON_CACHE_2024.read_text(encoding="utf-8")
                )
                self.assertNotIn(
                    "2024-AZVA.json",
                    seasonPayload.get(EVENT_FILE_SHA256_FIELD, {}),
                    "Expected bypassing an event cache to remove its SHA-256 entry",
                )

                bypassPayload = json.loads(bypassFile.read_text(encoding="utf-8"))
                bypassEntries: Any = bypassPayload.get("bypassEvents")
                self.assertIsInstance(
                    bypassEntries, list, "Expected bypassEvents to be stored as a list"
                )
                self.assertEqual(
                    bypassEntries[0]["eventCode"],
                    "AZVA",
                    "Expected bypass entry to record event code",
                )
                self.assertEqual(
                    bypassEntries[0]["reason"],
                    "incomplete event data",
                    "Expected bypass entry to store skip reason",
                )
                self.assertEqual(
                    bypassEntries[0]["bypassedAtUtc"],
                    bypassTime.isoformat(),
                    "Expected bypass entry to store bypass time in UTC",
                )
                self.assertEqual(
                    bypassEntries[0]["eventEndUtc"],
                    "2024-03-17T06:59:59+00:00",
                    "Expected bypass entry to store event end time in UTC",
                )

                with patch(
                    "data.frc_json._current_utc_time",
                    return_value=datetime(2024, 3, 17, 12, 0, tzinfo=timezone.utc),
                ):
                    self.assertNotIn(
                        "AZVA",
                        bypassed_events_for_season(2024),
                        "Expected network-related bypass entry to remain retryable on the next Season construction",
                    )

                with patch(
                    "data.frc_json._current_utc_time",
                    return_value=datetime(2024, 3, 18, 8, 0, tzinfo=timezone.utc),
                ):
                    self.assertNotIn(
                        "AZVA",
                        bypassed_events_for_season(2024),
                        "Expected bypassed event to become eligible again after 24 hours past event end",
                    )
            finally:
                eventCacheFile.write_text(originalEventCacheContent, encoding="utf-8")
                TEST_SEASON_CACHE_2024.write_text(
                    originalSeasonContent, encoding="utf-8"
                )
                if originalContent is None:
                    bypassFile.unlink(missing_ok=True)
                else:
                    bypassFile.write_text(originalContent, encoding="utf-8")

    def test_bypassed_events_for_season_skips_only_service_side_bypass_entries(
        self,
    ) -> None:
        with patch.dict(os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}):
            bypassFile = TEST_CACHE_ROOT / "2024" / "BypassEvents.json"
            originalContent = (
                bypassFile.read_text(encoding="utf-8") if bypassFile.exists() else None
            )

            try:
                bypassPayload = {
                    "bypassEvents": [
                        {
                            "eventCode": "AZVA",
                            "bypassedAtUtc": "2024-03-17T05:00:00+00:00",
                            "eventEndUtc": "2024-03-17T06:59:59+00:00",
                            "reason": "event request returned HTTP 500",
                        },
                        {
                            "eventCode": "OHCL",
                            "bypassedAtUtc": "2024-03-17T05:00:00+00:00",
                            "eventEndUtc": "2024-03-17T06:59:59+00:00",
                            "reason": "Request failed for URL 'https://example.invalid': network timeout",
                        },
                    ]
                }
                bypassFile.write_text(
                    json.dumps(
                        bypassPayload, ensure_ascii=False, indent=2, sort_keys=True
                    ),
                    encoding="utf-8",
                )

                with patch(
                    "data.frc_json._current_utc_time",
                    return_value=datetime(2024, 3, 17, 12, 0, tzinfo=timezone.utc),
                ):
                    bypassed = bypassed_events_for_season(2024)

                self.assertNotIn(
                    "AZVA",
                    bypassed,
                    "Expected service-side HTTP 500 bypass entry to remain retryable during the 24-hour cooldown window",
                )
                self.assertNotIn(
                    "OHCL",
                    bypassed,
                    "Expected network-related bypass entry to be retried instead of skipped",
                )
            finally:
                if originalContent is None:
                    bypassFile.unlink(missing_ok=True)
                else:
                    bypassFile.write_text(originalContent, encoding="utf-8")

    def test_request_season_frc_json_uses_cache_for_past_season_without_network(
        self,
    ) -> None:
        with patch.dict(os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}):
            with patch(
                "data.frc_json.fetch_frc_json",
                side_effect=RuntimeError("network disabled"),
            ):
                with patch(
                    "data.frc_json._current_utc_time",
                    return_value=datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc),
                ):
                    payload = request_season_frc_json(
                        url="https://frc-api.firstinspires.org/v3.0/2024/events",
                        key="events",
                        season=2024,
                    )

        eventsValue: Any = payload.get("Events")
        self.assertIsInstance(
            eventsValue, list, "Expected past-season cached event listing to be reused"
        )

    def test_request_season_frc_json_refreshes_current_or_future_season_but_falls_back_to_cache(
        self,
    ) -> None:
        with patch.dict(os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}):
            with patch(
                "data.frc_json.fetch_frc_json",
                side_effect=FRCNetworkError("network disabled"),
            ) as mockFetch:
                with patch(
                    "data.frc_json._current_utc_time",
                    return_value=datetime(2024, 3, 20, 0, 0, tzinfo=timezone.utc),
                ):
                    payload = request_season_frc_json(
                        url="https://frc-api.firstinspires.org/v3.0/2024/events",
                        key="events",
                        season=2024,
                    )

        self.assertEqual(
            mockFetch.call_count,
            1,
            "Expected current-season SeasonData to attempt an online refresh first",
        )
        eventsValue: Any = payload.get("Events")
        self.assertIsInstance(
            eventsValue,
            list,
            "Expected current-season request to fall back to cached event listing when offline",
        )

    def test_request_paginated_season_frc_json_refreshes_current_or_future_season_but_falls_back_to_cache(
        self,
    ) -> None:
        originalContent = TEST_SEASON_CACHE_2026.read_text(encoding="utf-8")
        try:
            seasonCache = json.loads(originalContent)
            seasonCache["teams"] = {
                "pageCurrent": 1,
                "pageTotal": 1,
                "teamCountPage": 1,
                "teamCountTotal": 1,
                "teams": [{"teamNumber": 6907}],
            }
            TEST_SEASON_CACHE_2026.write_text(
                json.dumps(seasonCache, ensure_ascii=False, indent=2, sort_keys=True),
                encoding="utf-8",
            )

            with patch.dict(
                os.environ, {"GOAT_EVENT_CACHE_ROOT": str(TEST_CACHE_ROOT)}
            ):
                with patch(
                    "data.frc_json.fetch_frc_json",
                    side_effect=FRCNetworkError("network disabled"),
                ) as mockFetch:
                    with patch(
                        "data.frc_json._current_utc_time",
                        return_value=datetime(2026, 5, 5, 0, 0, tzinfo=timezone.utc),
                    ):
                        payload = request_paginated_season_frc_json(
                            url="https://frc-api.firstinspires.org/v3.0/2026/teams",
                            key="teams",
                            payloadKey="teams",
                            season=2026,
                        )
        finally:
            TEST_SEASON_CACHE_2026.write_text(originalContent, encoding="utf-8")

        self.assertEqual(
            mockFetch.call_count,
            1,
            "Expected future/current season paginated SeasonData to attempt online refresh first",
        )
        teamsValue: Any = payload.get("teams")
        self.assertIsInstance(
            teamsValue,
            list,
            "Expected paginated SeasonData request to fall back to cached teams list when offline",
        )


if __name__ == "__main__":
    unittest.main()
