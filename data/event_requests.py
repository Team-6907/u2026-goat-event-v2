# Copyright (c) 2026 FRC Team 6907, The G.O.A.T
# Licensed under the MIT License.

from typing import Any, cast
from data.frc_json import EventRequestType, request_frc_json, request_paginated_frc_json
from data.season_requests import request_season_data, SeasonRequestType
from utils.data_util import is_json_object

FRC_API_BASE_URL = "https://frc-api.firstinspires.org/v3.0"


def _get_event_request_details(
    requestType: EventRequestType, season: int, eventCode: str
) -> tuple[str, str, str]:
    match requestType:
        case EventRequestType.TEAMS:
            return f"{season}/teams?eventCode={eventCode}", "teams", "teams"
        case EventRequestType.RANKINGS:
            return f"{season}/rankings/{eventCode}", "rankings", "Rankings"
        case EventRequestType.ALLIANCES:
            return f"{season}/alliances/{eventCode}", "alliances", "Alliances"
        case EventRequestType.QUALIFICATION_MATCHES:
            return (
                f"{season}/matches/{eventCode}?tournamentLevel=Qualification",
                "qualification_matches",
                "Matches",
            )
        case EventRequestType.PLAYOFF_MATCHES:
            return (
                f"{season}/matches/{eventCode}?tournamentLevel=Playoff",
                "playoff_matches",
                "Matches",
            )
        case EventRequestType.AWARDS:
            return f"{season}/awards/event/{eventCode}", "awards", "Awards"
        case EventRequestType.QUALIFICATION_SCORE_DETAILS:
            return (
                f"{season}/scores/{eventCode}/Qualification",
                "qualification_score_details",
                "MatchScores",
            )
        case EventRequestType.PLAYOFF_SCORE_DETAILS:
            return (
                f"{season}/scores/{eventCode}/Playoff",
                "playoff_score_details",
                "MatchScores",
            )


def request_event_data(
    requestType: EventRequestType, season: int, eventCode: str
) -> list[object]:
    route, cacheKey, payloadKey = _get_event_request_details(
        requestType, season, eventCode
    )
    fullUrl = f"{FRC_API_BASE_URL}/{route}"
    if requestType is EventRequestType.TEAMS:
        payload = request_paginated_frc_json(
            fullUrl, cacheKey, payloadKey, season, eventCode
        )
    else:
        payload = request_frc_json(fullUrl, cacheKey, season, eventCode)

    data = payload.get(payloadKey)
    if data is None or not isinstance(data, list):
        raise ValueError(
            f"Invalid event data format for '{payloadKey}': expected a list"
        )
    return cast(list[object], data)


def request_event_metadata(season: int, eventCode: str) -> dict[str, Any]:
    normalizedEventCode = eventCode.strip()
    if not normalizedEventCode:
        raise ValueError("eventCode cannot be empty")

    eventData = request_season_data(SeasonRequestType.EVENT_LISTING, season)
    for rawEventData in eventData:
        if not is_json_object(rawEventData):
            continue
        typedEventData = rawEventData
        if typedEventData.get("code") == normalizedEventCode:
            return typedEventData

    raise ValueError(
        f"Event metadata not found for season {season} event {normalizedEventCode}"
    )
