# Copyright (c) 2026 FRC Team 6907, The G.O.A.T
# Licensed under the MIT License.

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo


class DSTRule:
    def __init__(
        self,
        start_month: int,
        start_weekday: int,
        start_occurrence: int,
        start_hour: int,
        end_month: int,
        end_weekday: int,
        end_occurrence: int,
        end_hour: int,
        daylight_offset_minutes: int,
    ):
        self.start_month = start_month
        self.start_weekday = start_weekday
        self.start_occurrence = start_occurrence
        self.start_hour = start_hour
        self.end_month = end_month
        self.end_weekday = end_weekday
        self.end_occurrence = end_occurrence
        self.end_hour = end_hour
        self.daylight_offset_minutes = daylight_offset_minutes


WINDOWS_TIMEZONE_DATA: dict[str, tuple[int, DSTRule | None]] = {
    "AUS Eastern Standard Time": (
        600,
        DSTRule(10, 6, 1, 2, 4, 6, 1, 3, 660),
    ),
    "Central Standard Time": (
        -360,
        DSTRule(3, 6, 2, 2, 11, 6, 1, 2, -300),
    ),
    "Central Standard Time (Mexico)": (-360, None),
    "China Standard Time": (480, None),
    "E. South America Standard Time": (-180, None),
    "Eastern Standard Time": (
        -300,
        DSTRule(3, 6, 2, 2, 11, 6, 1, 2, -240),
    ),
    "Hawaiian Standard Time": (-600, None),
    "Israel Standard Time": (
        120,
        DSTRule(3, 4, -1, 2, 10, 6, -1, 2, 180),
    ),
    "Mountain Standard Time": (
        -420,
        DSTRule(3, 6, 2, 2, 11, 6, 1, 2, -360),
    ),
    "Pacific Standard Time": (
        -480,
        DSTRule(3, 6, 2, 2, 11, 6, 1, 2, -420),
    ),
    "Taipei Standard Time": (480, None),
    "Turkey Standard Time": (180, None),
    "Venezuela Standard Time": (-240, None),
}


def _nth_weekday_of_month(
    year: int, month: int, weekday: int, occurrence: int
) -> datetime:
    if occurrence > 0:
        first_day = datetime(year, month, 1)
        days_until_weekday = (weekday - first_day.weekday()) % 7
        day = 1 + days_until_weekday + (occurrence - 1) * 7
        return datetime(year, month, day)

    if month == 12:
        next_month = datetime(year + 1, 1, 1)
    else:
        next_month = datetime(year, month + 1, 1)
    last_day = next_month - timedelta(days=1)
    days_since_weekday = (last_day.weekday() - weekday) % 7
    day = last_day.day - days_since_weekday
    return datetime(year, month, day)


def _is_in_dst(localDateTime: datetime, dstRule: DSTRule) -> bool:
    year = localDateTime.year

    dst_start = _nth_weekday_of_month(
        year, dstRule.start_month, dstRule.start_weekday, dstRule.start_occurrence
    ).replace(hour=dstRule.start_hour)
    dst_end = _nth_weekday_of_month(
        year, dstRule.end_month, dstRule.end_weekday, dstRule.end_occurrence
    ).replace(hour=dstRule.end_hour)

    if dst_start < dst_end:
        return dst_start <= localDateTime < dst_end
    return localDateTime >= dst_start or localDateTime < dst_end


def _offset_timezone(offset_minutes: int) -> tzinfo:
    hours, minutes = divmod(abs(offset_minutes), 60)
    delta = timedelta(hours=hours, minutes=minutes)
    if offset_minutes < 0:
        delta = -delta
    return timezone(delta)


def normalize_event_datetime_to_utc(
    dateTimeString: str, eventTimezoneName: str | None
) -> datetime:
    parsedDateTime = datetime.fromisoformat(dateTimeString)
    if parsedDateTime.tzinfo is not None:
        return parsedDateTime.astimezone(timezone.utc)

    if eventTimezoneName is None or not eventTimezoneName.strip():
        raise ValueError("event timezone is required to normalize naive datetime")

    normalizedTimezoneName = eventTimezoneName.strip()
    timezoneData = WINDOWS_TIMEZONE_DATA.get(normalizedTimezoneName)
    if timezoneData is None:
        raise ValueError(f"Unsupported event timezone '{normalizedTimezoneName}'")

    standardOffsetMinutes, dstRule = timezoneData
    offsetMinutes = standardOffsetMinutes
    if dstRule is not None and _is_in_dst(parsedDateTime, dstRule):
        offsetMinutes = dstRule.daylight_offset_minutes

    localTimezone = _offset_timezone(offsetMinutes)
    return parsedDateTime.replace(tzinfo=localTimezone).astimezone(timezone.utc)
