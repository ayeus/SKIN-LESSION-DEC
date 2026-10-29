"""Synthetic fixtures for documented public-data transformations only."""

import pandas as pd
import pytest
from scripts.verify_public_weight import prepare


def test_nhanes_sentinels_are_not_numeric_behavior_observations():
    df = pd.DataFrame(
        {
            "RIDAGEYR": [19, 25, 80],
            "SEQN": [1, 2, 3],
            "RIAGENDR": [1, 2, 1],
            "BMXBMI": [20, 25, 30],
            "PAD680": [100, 9999, 120],
            "SLD012": [8, 2, 7.5],
            "DBD895": [0, 5555, 3],
            "WTMEC2YR": [1, 1, 1],
            "SDMVPSU": [1, 1, 2],
            "SDMVSTRA": [1, 1, 1],
        }
    )
    out, log = prepare(df)
    assert out.participant_id.tolist() == [2, 3]
    assert out.sedentary_minutes_day.isna().iloc[0]
    assert out.sleep_weekday_hours_exact.isna().iloc[0]
    assert out.meals_away_week_exact.isna().iloc[0]
    assert out.sleep_weekday_hours_exact.iloc[1] == 7.5
    assert out.female_reported.tolist() == [1, 0]
    assert "no structural" in log["DBD895"]
