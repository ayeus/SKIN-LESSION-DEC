"""Mathematical fixtures verify geometry, not clinical cluster performance."""

import numpy as np
import pandas as pd
import pytest
from backend.app.services.analytics import reduce


def test_three_component_pca_preserves_rank_and_row_order():
    x = np.arange(12, dtype=float)
    frame = pd.DataFrame({"a": x, "b": 2 * x, "c": -x})
    result = reduce(frame, {"features": list(frame), "dimensions": 3})
    coordinates = np.array(result["coordinates"])
    assert coordinates.shape == (12, 3)
    assert result["rows"] == 12 and result["dimensions"] == 3
    assert sum(result["explained_variance_ratio"]) == pytest.approx(1)
    assert result["explained_variance_ratio"][0] == pytest.approx(1)
    assert np.all(np.diff(coordinates[:, 0]) > 0) or np.all(
        np.diff(coordinates[:, 0]) < 0
    )
    assert abs(coordinates[0, 0] - coordinates[-1, 0]) > abs(
        coordinates[0, 0] - coordinates[1, 0]
    )


def test_constant_data_does_not_report_undefined_variance_as_zero():
    frame = pd.DataFrame({"a": [4] * 8, "b": [9] * 8})
    for method in ["pca", "tsne"]:
        with pytest.raises(ValueError, match="No varying features"):
            reduce(frame, {"features": list(frame), "method": method})


def test_fractional_dimensions_cannot_silently_truncate():
    with pytest.raises(ValueError, match="whole number"):
        reduce(
            pd.DataFrame({"a": range(8), "b": range(8)}),
            {"features": ["a", "b"], "dimensions": 2.5},
        )
