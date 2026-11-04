/* Isolated view fixtures; never published patient-demand observations. */
import { expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import ForecastEvidence from "../app/components/forecast-evidence";
const Chart = ({ data }: { data: any[]; keys: string[] }) => (
  <div aria-label="chart fixture">{data.length} supplied rows</div>
);
const base = {
  forecast: [{ date: "2020-01-01", count: 10, lower: 7, upper: 13 }],
  observed: [{ date: "2019-12-31", count: 8 }],
  selected: "weekly_seasonal",
  validation_metrics: { weekly_seasonal: { mae: 2, rmse: 3 } },
  validation_protocol: "Chronological validation fixture",
};
it("explains the forecast summary, daily estimates, bounds and error scores", () => {
  render(<ForecastEvidence result={base} Chart={Chart} />);
  expect(screen.getByText(/Estimated total across those days/)).toBeVisible();
  expect(screen.getByText("Highest estimated day")).toBeVisible();
  expect(
    screen.getByRole("columnheader", { name: "Estimated daily count (about)" }),
  ).toBeVisible();
  expect(screen.getByText("Lower past-error bound")).toBeVisible();
  expect(screen.getByText(/MAE is the average size of a miss/)).toBeVisible();
  expect(
    screen.getAllByText(/Repeat the same weekday's recent average/).length,
  ).toBeGreaterThan(0);
});
it("does not turn missing held-out metrics into zero performance", () => {
  render(<ForecastEvidence result={base} Chart={Chart} />);
  expect(screen.getByText(/no separately recorded test metrics/)).toBeVisible();
  expect(
    screen.queryByText(/These errors were not used/),
  ).not.toBeInTheDocument();
});
it("distinguishes measured test errors and explicit source scope", () => {
  render(
    <ForecastEvidence
      result={{
        ...base,
        test_metrics: { mae: 4.25, rmse: 5.5 },
        data_scope: {
          metric: "isolated_metric",
          requested_start: "2020-01-01",
          requested_end: "2020-01-31",
          limitations:
            "Fixture describes a scoped aggregate, not local hospital demand.",
        },
      }}
      Chart={Chart}
    />,
  );
  expect(
    screen.getByText(/typical miss \(MAE\) was 4.25 count units/),
  ).toBeVisible();
  expect(screen.getByText(/not local hospital demand/)).toBeVisible();
});
it("reports workload equivalents without inventing shift allocations", () => {
  render(
    <ForecastEvidence
      result={{
        ...base,
        scenario: {
          assumption_patients_per_staff_per_shift: 5,
          required_staff_shifts_per_day: [2],
          allocation_status:
            "Per-shift headcount unavailable: explicit shift inputs required",
          label: "User-assumed fixture",
          limitations: "No institutional staffing policy",
        },
      }}
      Chart={Chart}
    />,
  );
  expect(
    screen.getByRole("columnheader", {
      name: "Staff-shifts under your assumption",
    }),
  ).toBeVisible();
  expect(screen.getByText(/Per-shift headcount unavailable/)).toBeVisible();
  expect(
    screen.queryByRole("columnheader", {
      name: "Staff under supplied assumptions",
    }),
  ).not.toBeInTheDocument();
});
