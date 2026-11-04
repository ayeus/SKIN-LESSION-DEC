/* Synthetic view fixture only: verifies explanations, never reported as study data. */
import { expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import HealthcareOverviewEvidence from "../app/components/healthcare-overview-evidence";

it("explains the row total, time summary, category totals and source mappings", () => {
  render(
    <HealthcareOverviewEvidence
      result={{
        rows_selected: 4,
        observed_total: 4,
        definition:
          "Count of source rows; rows are NOT assumed to be unique patients or encounters.",
        mapped_fields: {
          date_column: "admittime",
          category_column: "admission_type",
          count_column: null,
        },
        monthly_trend: [
          { date: "2020-01", count: 1 },
          { date: "2020-02", count: 3 },
        ],
        distribution: { emergency: 3, elective: 1 },
      }}
    />,
  );

  expect(screen.getByText("Rows included")).toBeVisible();
  expect(screen.getByText(/number of source rows/)).toBeVisible();
  expect(screen.getByText("Largest recorded category")).toBeVisible();
  expect(
    screen.getAllByText(
      (_, element) =>
        element?.textContent?.includes(
          "The highest monthly total in this selection was 3 in 2020-02.",
        ) || false,
    ).length,
  ).toBeGreaterThan(0);
  expect(
    screen.getByRole("columnheader", { name: "Share of calculated total" }),
  ).toBeVisible();
  expect(
    screen.getByText(/one person can have multiple records/),
  ).toBeVisible();
});
