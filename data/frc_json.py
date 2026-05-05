# Copyright (c) 2026 FRC Team 6907, The G.O.A.T
# Licensed under the MIT License.

from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
from enum import IntEnum
import json
import os
from pathlib import Path
from typing import Any, cast

from dotenv import load_dotenv
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from utils.data_util import is_json_object
from utils.time_util import normalize_event_datetime_to_utc


class FRCRequestError(Exception):
    """Base exception for FRC JSON fetch failures."""


class FRCNetworkError(FRCRequestError):
    """Raised when a network-level request error occurs."""


class FRCHTTPError(FRCRequestError):
    """Raised when the server returns a non-2xx response."""


class FRCJSONDecodeError(FRCRequestError):
    """Raised when the response body is not valid JSON."""


class FRCJSONTypeError(FRCRequestError):
    """Raised when the JSON payload is not an object/dict."""


class FRCAuthorizationError(FRCRequestError):
    """Raised when API authorization is missing or malformed."""


class EventRequestType(IntEnum):
    TEAMS = 1
    RANKINGS = 2
    ALLIANCES = 3
    QUALIFICATION_MATCHES = 4
    PLAYOFF_MATCHES = 5
    AWARDS = 6
    QUALIFICATION_SCORE_DETAILS = 7
    PLAYOFF_SCORE_DETAILS = 8


class SeasonRequestType(IntEnum):
    EVENT_LISTING = 1
    TEAM_LISTING = 2


CACHE_FETCHED_AT_FIELD = "_cacheFetchedAtUtc"


def _cache_root_path() -> Path:
    cacheRootOverride = os.getenv("GOAT_EVENT_CACHE_ROOT")
    if cacheRootOverride and cacheRootOverride.strip():
        return Path(cacheRootOverride).expanduser()
    return Path(__file__).resolve().parents[1] / "cache"


def _cache_file_path(season: int, eventCode: str) -> Path:
    cacheRoot = _cache_root_path()
    seasonStr = str(season)
    return cacheRoot / seasonStr / f"{seasonStr}-{eventCode}.json"


def _bypass_file_path(season: int) -> Path:
    cacheRoot = _cache_root_path()
    seasonStr = str(season)
    return cacheRoot / seasonStr / f"BypassEvents.json"


def _season_cache_file_path(season: int) -> Path:
    cacheRoot = _cache_root_path()
    seasonStr = str(season)
    return cacheRoot / seasonStr / "SeasonData.json"


def _current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def _should_always_refresh_season_cache(season: int) -> bool:
    return _current_utc_time().year <= season


def _format_utc_datetime(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _parse_iso_datetime(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        parsedDateTime = datetime.fromisoformat(value)
    except ValueError:
        return None

    if parsedDateTime.tzinfo is None:
        return parsedDateTime.replace(tzinfo=timezone.utc)
    return parsedDateTime.astimezone(timezone.utc)


def _get_cached_event_listing(season: int) -> list[dict[str, Any]]:
    seasonCacheData = _read_cache_file(_season_cache_file_path(season))
    eventsPayload = seasonCacheData.get("events")
    if not is_json_object(eventsPayload):
        return []

    eventList = eventsPayload.get("Events")
    if not isinstance(eventList, list):
        return []

    typedEventList: list[dict[str, Any]] = []
    for rawEventData in cast(list[object], eventList):
        if is_json_object(rawEventData):
            typedEventList.append(rawEventData)
    return typedEventList


def _get_event_listing_metadata(
    season: int, eventCode: str
) -> dict[str, Any] | None:
    normalizedEventCode = eventCode.strip()
    if not normalizedEventCode:
        return None

    for eventData in _get_cached_event_listing(season):
        if eventData.get("code") == normalizedEventCode:
            return eventData
    return None


def _get_event_end_utc(season: int, eventCode: str) -> datetime | None:
    eventMetadata = _get_event_listing_metadata(season, eventCode)
    if eventMetadata is None:
        return None

    dateEnd = eventMetadata.get("dateEnd")
    eventTimezone = eventMetadata.get("timezone")
    if not isinstance(dateEnd, str) or not dateEnd.strip():
        return None
    if not isinstance(eventTimezone, str) or not eventTimezone.strip():
        return None

    return normalize_event_datetime_to_utc(dateEnd, eventTimezone)


def _get_event_cache_refresh_deadline(
    season: int, eventCode: str
) -> datetime | None:
    eventEndUtc = _get_event_end_utc(season, eventCode)
    if eventEndUtc is None:
        return None
    return eventEndUtc + timedelta(days=1)


def _should_refresh_event_payload(
    cachedValue: dict[str, Any], season: int, eventCode: str
) -> bool:
    refreshDeadlineUtc = _get_event_cache_refresh_deadline(season, eventCode)
    if refreshDeadlineUtc is None:
        return False

    cachedFetchedAtUtc = _parse_iso_datetime(
        cachedValue.get(CACHE_FETCHED_AT_FIELD)
    )
    if cachedFetchedAtUtc is None:
        return False

    currentUtc = _current_utc_time()
    if currentUtc < refreshDeadlineUtc:
        return True

    return cachedFetchedAtUtc < refreshDeadlineUtc


def _normalize_bypass_entry(rawEntry: object) -> dict[str, str] | None:
    if isinstance(rawEntry, str) and rawEntry.strip():
        return {"eventCode": rawEntry.strip()}
    if not is_json_object(rawEntry):
        return None

    eventCode = rawEntry.get("eventCode")
    if not isinstance(eventCode, str) or not eventCode.strip():
        return None

    normalizedEntry: dict[str, str] = {"eventCode": eventCode.strip()}
    for fieldName in ("bypassedAtUtc", "reason", "eventEndUtc"):
        fieldValue = rawEntry.get(fieldName)
        if isinstance(fieldValue, str) and fieldValue.strip():
            normalizedEntry[fieldName] = fieldValue
    return normalizedEntry


def _is_service_bypass_reason(reason: str | None) -> bool:
    if reason is None:
        return False

    normalizedReason = reason.strip().lower()
    if not normalizedReason:
        return False

    if "http 500" in normalizedReason:
        return True

    if "not found" in normalizedReason:
        return True

    return False


def _read_bypass_entries(season: int) -> list[dict[str, str]]:
    bypassData = _read_cache_file(_bypass_file_path(season=season))
    bypassList = bypassData.get("bypassEvents")
    if not isinstance(bypassList, list):
        return []

    entries: list[dict[str, str]] = []
    for rawEntry in cast(list[object], bypassList):
        normalizedEntry = _normalize_bypass_entry(rawEntry)
        if normalizedEntry is not None:
            entries.append(normalizedEntry)
    return entries


def _write_bypass_entries(season: int, entries: list[dict[str, str]]) -> None:
    _write_cache_file(
        _bypass_file_path(season=season), {"bypassEvents": entries}
    )


def bypass_event_cache_file(
    season: int, eventCode: str, reason: str | None = None
) -> None:
    normalizedEventCode = eventCode.strip()
    if not normalizedEventCode:
        raise ValueError("eventCode cannot be empty")

    cachePath = _cache_file_path(season=season, eventCode=normalizedEventCode)
    bypassEntries = [
        entry
        for entry in _read_bypass_entries(season)
        if entry.get("eventCode") != normalizedEventCode
    ]

    bypassEntry: dict[str, str] = {
        "eventCode": normalizedEventCode,
        "bypassedAtUtc": _format_utc_datetime(_current_utc_time()),
    }

    try:
        eventEndUtc = _get_event_end_utc(season, normalizedEventCode)
    except ValueError:
        eventEndUtc = None
    if eventEndUtc is not None:
        bypassEntry["eventEndUtc"] = _format_utc_datetime(eventEndUtc)

    if reason is not None and reason.strip():
        bypassEntry["reason"] = reason.strip()

    bypassEntries.append(bypassEntry)
    _write_bypass_entries(season, bypassEntries)

    try:
        cachePath.unlink(missing_ok=True)
    except OSError:
        return


def bypassed_events_for_season(season: int) -> list[str]:
    currentUtc = _current_utc_time()
    bypassedEventCodes: list[str] = []

    for entry in _read_bypass_entries(season):
        eventCode = entry["eventCode"]
        reason = entry.get("reason")
        eventEndUtc = _parse_iso_datetime(entry.get("eventEndUtc"))

        if not _is_service_bypass_reason(reason):
            continue

        if eventEndUtc is not None:
            if currentUtc > eventEndUtc + timedelta(days=1):
                bypassedEventCodes.append(eventCode)
            continue

    return bypassedEventCodes


def _read_cache_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        data: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if is_json_object(data):
        return data
    return {}


def _write_cache_file(path: Path, cacheData: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(cacheData, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _build_basic_auth_header() -> str:
    envPath = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=envPath)

    username = os.getenv("AUTH_USERNAME")
    token = os.getenv("AUTH_TOKEN")
    if not username or not token:
        raise FRCAuthorizationError(
            "Missing AUTH_USERNAME or AUTH_TOKEN in .env for FRC API authorization."
        )

    raw = f"{username}:{token}".encode("utf-8")
    encoded = base64.b64encode(raw).decode("ascii")
    return f"Basic {encoded}"


def fetch_frc_json(url: str, timeout: float = 15.0) -> dict[str, Any]:
    """
    Fetch JSON data from an FRC endpoint and return it as a dictionary.

    Args:
        url: Full endpoint URL.
        timeout: Request timeout in seconds.

    Returns:
        Parsed JSON object as dict.

    Raises:
        ValueError: If URL is empty.
        FRCAuthorizationError: If API auth credentials are missing.
        FRCNetworkError: If network request fails.
        FRCHTTPError: If HTTP status is not successful.
        FRCJSONDecodeError: If body cannot be decoded as JSON.
        FRCJSONTypeError: If decoded JSON is not a dict.
    """
    if not url or not url.strip():
        raise ValueError("url cannot be empty")

    headers = {
        "Accept": "application/json",
        "User-Agent": "goat-event-v2/26.4.0",
        "Authorization": _build_basic_auth_header(),
    }
    request = Request(url=url, headers=headers, method="GET")

    try:
        with urlopen(request, timeout=timeout) as response:
            bodyBytes = response.read()
    except HTTPError as exc:
        statusCode = getattr(exc, "code", "unknown")
        body = ""
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        raise FRCHTTPError(
            f"HTTP {statusCode} returned for URL '{url}'. Response: {body[:300]}"
        ) from exc
    except URLError as exc:
        raise FRCNetworkError(f"Request failed for URL '{url}': {exc}") from exc
    except TimeoutError as exc:
        raise FRCNetworkError(f"Request failed for URL '{url}': {exc}") from exc

    try:
        text = bodyBytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise FRCJSONDecodeError(
            f"Response from URL '{url}' is not UTF-8 text JSON."
        ) from exc

    try:
        payload: Any = json.loads(text)
    except json.JSONDecodeError as exc:
        raise FRCJSONDecodeError(
            f"Response from URL '{url}' is not valid JSON. Body: {text[:300]}"
        ) from exc

    if not is_json_object(payload):
        raise FRCJSONTypeError(
            f"Expected JSON object (dict) from URL '{url}', got {type(payload).__name__}"
        )

    return payload


def request_frc_json(
    url: str, key: str, season: int, eventCode: str, timeout: float = 15.0
) -> dict[str, Any]:
    """
    Return cached FRC JSON by key when available; otherwise fetch and cache it.

    Cache layout:
        cache/{season}/{season}-{eventCode}.json
    """
    if not key or not key.strip():
        raise ValueError("key cannot be empty")
    normalizedEventCode = eventCode.strip()
    if not normalizedEventCode:
        raise ValueError("eventCode cannot be empty")

    cachePath = _cache_file_path(season=season, eventCode=normalizedEventCode)
    cacheData = _read_cache_file(cachePath)

    cachedValue = cacheData.get(key)
    if is_json_object(cachedValue) and not _should_refresh_event_payload(
        cachedValue, season, normalizedEventCode
    ):
        return cachedValue

    payload = fetch_frc_json(url=url, timeout=timeout)
    payload[CACHE_FETCHED_AT_FIELD] = _format_utc_datetime(_current_utc_time())
    cacheData[key] = payload
    _write_cache_file(cachePath, cacheData)
    return payload


def _request_paginated_json(
    cachePath: Path,
    url: str,
    key: str,
    payloadKey: str,
    season: int | None = None,
    eventCode: str | None = None,
    forceRefresh: bool = False,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """
    Return cached paginated FRC JSON by key when available; otherwise fetch all pages and cache the merged payload.

    The cached payload keeps the original top-level object shape, but replaces `payloadKey`
    with the concatenated list from every page.
    """
    if not key or not key.strip():
        raise ValueError("key cannot be empty")
    if not payloadKey or not payloadKey.strip():
        raise ValueError("payloadKey cannot be empty")

    cacheData = _read_cache_file(cachePath)

    cachedValue = cacheData.get(key)
    shouldRefreshEventPayload = (
        season is not None
        and eventCode is not None
        and is_json_object(cachedValue)
        and _should_refresh_event_payload(cachedValue, season, eventCode)
    )
    if (
        is_json_object(cachedValue)
        and not forceRefresh
        and not shouldRefreshEventPayload
    ):
        cachedDataValue = cachedValue.get(payloadKey)
        cachedTotal = cachedValue.get("teamCountTotal")
        cachedPageTotal = cachedValue.get("pageTotal")
        if isinstance(cachedDataValue, list):
            cachedData = cast(list[object], cachedDataValue)
            if (
                isinstance(cachedTotal, int)
                and cachedTotal > 0
                and len(cachedData) == cachedTotal
            ):
                return cachedValue
            if not isinstance(cachedTotal, int) and cachedPageTotal == 1:
                return cachedValue

    mergedPayload: dict[str, Any] | None = None
    mergedData: list[object] = []
    pageCurrent = 1
    pageTotal = 1

    try:
        while pageCurrent <= pageTotal:
            separator = "&" if "?" in url else "?"
            pageUrl = f"{url}{separator}page={pageCurrent}"
            payload = fetch_frc_json(url=pageUrl, timeout=timeout)

            pageData = payload.get(payloadKey)
            if not isinstance(pageData, list):
                raise ValueError(
                    f"Invalid event data format for '{payloadKey}': expected a list"
                )
            typedPageData = cast(list[object], pageData)

            if mergedPayload is None:
                mergedPayload = dict(payload)

            mergedData.extend(typedPageData)

            rawPageTotal = payload.get("pageTotal")
            if isinstance(rawPageTotal, int) and rawPageTotal > 0:
                pageTotal = rawPageTotal

            pageCurrent += 1
    except FRCRequestError:
        if is_json_object(cachedValue):
            cachedDataValue = cachedValue.get(payloadKey)
            cachedTotal = cachedValue.get("teamCountTotal")
            cachedPageTotal = cachedValue.get("pageTotal")
            if isinstance(cachedDataValue, list):
                cachedData = cast(list[object], cachedDataValue)
                if (
                    isinstance(cachedTotal, int)
                    and cachedTotal > 0
                    and len(cachedData) == cachedTotal
                ):
                    return cachedValue
                if not isinstance(cachedTotal, int) and cachedPageTotal == 1:
                    return cachedValue
        raise

    if mergedPayload is None:
        raise ValueError(f"Missing paginated payload for '{payloadKey}'")

    mergedPayload[payloadKey] = mergedData
    mergedPayload["pageCurrent"] = 1
    mergedPayload["pageTotal"] = 1

    teamCountTotal = mergedPayload.get("teamCountTotal")
    if isinstance(teamCountTotal, int):
        mergedPayload["teamCountTotal"] = len(mergedData)

    teamCountPage = mergedPayload.get("teamCountPage")
    if isinstance(teamCountPage, int):
        mergedPayload["teamCountPage"] = len(mergedData)

    mergedPayload[CACHE_FETCHED_AT_FIELD] = _format_utc_datetime(
        _current_utc_time()
    )
    cacheData[key] = mergedPayload
    _write_cache_file(cachePath, cacheData)
    return mergedPayload


def request_paginated_frc_json(
    url: str,
    key: str,
    payloadKey: str,
    season: int,
    eventCode: str,
    timeout: float = 15.0,
) -> dict[str, Any]:
    normalizedEventCode = eventCode.strip()
    if not normalizedEventCode:
        raise ValueError("eventCode cannot be empty")

    cachePath = _cache_file_path(season=season, eventCode=normalizedEventCode)
    return _request_paginated_json(
        cachePath,
        url,
        key,
        payloadKey,
        season,
        normalizedEventCode,
        False,
        timeout,
    )


def request_paginated_season_frc_json(
    url: str,
    key: str,
    payloadKey: str,
    season: int,
    timeout: float = 15.0,
) -> dict[str, Any]:
    """
    Return cached paginated season-level FRC JSON by key when available; otherwise fetch all pages and cache the merged payload.

    Cache layout:
        cache/{season}/SeasonData.json
    """
    cachePath = _season_cache_file_path(season=season)
    return _request_paginated_json(
        cachePath,
        url,
        key,
        payloadKey,
        None,
        None,
        _should_always_refresh_season_cache(season),
        timeout,
    )


def request_season_frc_json(
    url: str, key: str, season: int, timeout: float = 15.0
) -> dict[str, Any]:
    """
    Return cached FRC JSON by key when available; otherwise fetch and cache it.

    Cache layout:
        cache/{season}/SeasonData.json
    """
    if not key or not key.strip():
        raise ValueError("key cannot be empty")

    cachePath = _season_cache_file_path(season=season)
    cacheData = _read_cache_file(cachePath)

    cachedValue = cacheData.get(key)
    shouldForceRefresh = _should_always_refresh_season_cache(season)
    if is_json_object(cachedValue) and not shouldForceRefresh:
        return cachedValue

    try:
        payload = fetch_frc_json(url=url, timeout=timeout)
    except FRCRequestError:
        if is_json_object(cachedValue):
            return cachedValue
        raise
    payload[CACHE_FETCHED_AT_FIELD] = _format_utc_datetime(_current_utc_time())
    cacheData[key] = payload
    _write_cache_file(cachePath, cacheData)
    return payload
