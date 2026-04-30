# Copyright (c) 2026 FRC Team 6907, The G.O.A.T
# Licensed under the MIT License.

from __future__ import annotations

from typing import TYPE_CHECKING, Type
from ruleset.cmpqual.protocol import CMPQualRule
from ruleset.tournament.protocol import TournamentRule
from ruleset.tournament.simple import SimpleTournament
from ruleset.tournament.double_elim import DoubleElimTournament

if TYPE_CHECKING:
    from real.event import Event


def default_tournament_rule_class(event: Event) -> Type[TournamentRule]:
    season: int = event.season
    if season <= 2022:
        return SimpleTournament
    elif season >= 2023:
        return DoubleElimTournament
    else:
        raise ValueError(f"No default tournament rule defined for season {season}")


def default_cmp_qual_rule_class(event: Event) -> Type[CMPQualRule]:
    from ruleset.cmpqual.simple import SimpleCMPQualification

    return SimpleCMPQualification


class AwardNameMapping:

    @staticmethod
    def rookie_all_star_award(event: Event) -> str:
        return "Rookie All Star Award"

    @staticmethod
    def regional_first_impact_award(event: Event) -> str:
        if event.season >= 2024:
            return "Regional FIRST Impact Award"
        else:
            return "Regional Chairman's Award"

    @staticmethod
    def district_first_impact_award(event: Event) -> str:
        if event.season >= 2024:
            return "District FIRST Impact Award"
        else:
            return "District Chairman's Award"

    @staticmethod
    def dcmp_first_impact_award(event: Event) -> str:
        if event.season >= 2024:
            return "District Championship FIRST Impact Award"
        else:
            return "District Championship Chairman's Award"

    @staticmethod
    def regional_engineering_inspiration_award(event: Event) -> str:
        return "Regional Engineering Inspiration Award"

    @staticmethod
    def district_engineering_inspiration_award(event: Event) -> str:
        return "District Engineering Inspiration Award"

    @staticmethod
    def dcmp_engineering_inspiration_award(event: Event) -> str:
        return "District Championship Engineering Inspiration Award"

    @staticmethod
    def regional_winner(event: Event) -> str:
        return "Regional Winners"

    @staticmethod
    def district_winner(event: Event) -> str:
        return "District Event Winner"

    @staticmethod
    def dcmp_winner(event: Event) -> str:
        return "District Championship Winner"

    @staticmethod
    def regional_finalist(event: Event) -> str:
        return "Regional Finalists"

    @staticmethod
    def district_finalist(event: Event) -> str:
        return "District Event Finalist"

    @staticmethod
    def dcmp_finalist(event: Event) -> str:
        return "District Championship Finalist"
