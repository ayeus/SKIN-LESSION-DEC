/* Synthetic report fixture verifies labels only; it is not research evidence. */
import { expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import AdultWeightEvidence from "../app/components/adult-weight-evidence";

it("explains T14–T15 metric names and labels feature tables", () => {
  render(
    <AdultWeightEvidence
      result={{
        model: "Ridge regression",
        mae: 4.2,
        rmse: 5.7,
        r2: 0.1,
        train_rows: 75,
        test_rows: 25,
        observed: [22],
        predicted: [20],
        nonlinear_comparison: { test_mae: 4.3, test_rmse: 5.8 },
        permutation_importance: {
          age_years_topcoded80: { mean_mae_increase: 0.2, std: 0.1 },
        },
        sensitivity_leave_one_feature_out: [
          { omitted_feature: "age_years_topcoded80", test_mae: 4.4 },
        ],
        diagnostics: {
          residual_mean: 0.1,
          residual_std: 5.7,
          feature_correlation: {
            age_years_topcoded80: { sedentary_minutes_day: -0.2 },
            sedentary_minutes_day: { age_years_topcoded80: -0.2 },
          },
        },
      }}
    />,
  );

  expect(screen.getByText(/MAE · BMI error/)).toBeInTheDocument();
  expect(
    screen.getByText(/Average absolute prediction error/),
  ).toBeInTheDocument();
  expect(
    screen.getByText(/R² · fit compared with the average/),
  ).toBeInTheDocument();
  expect(
    screen.getAllByText("Age (years; top-coded at 80)", { exact: false })
      .length,
  ).toBeGreaterThan(0);
  expect(screen.getByText(/Feature correlations/)).toBeInTheDocument();
  expect(
    screen.getByText(/do not show that a behavior causes BMI to change/),
  ).toBeInTheDocument();
});
