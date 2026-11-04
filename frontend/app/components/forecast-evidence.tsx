"use client";
import type { ComponentType } from "react";
type Data = Record<string, any>;
type Props = {
  result: Data;
  Chart: ComponentType<{
    data: any[];
    keys: string[];
    seriesLabels?: Record<string, string>;
    yAxisLabel?: string;
  }>;
};
const measured = (v: unknown) =>
  typeof v === "number" && Number.isFinite(v) ? v.toFixed(2) : "Not measured";
const count = (v: unknown) =>
  typeof v === "number" && Number.isFinite(v)
    ? new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 }).format(v)
    : "Not measured";
const modelName = (name: string) =>
  ({
    last_value: "Repeat the most recent day's count",
    weekly_seasonal: "Repeat the same weekday's recent average",
    rolling_mean: "Average the previous seven days",
    autoregressive_ridge:
      "Trend model using recent counts and calendar pattern",
  })[name] || name.replaceAll("_", " ");
export default function ForecastEvidence({ result: r, Chart }: Props) {
  if (!r.forecast) return null;
  const forecast = r.forecast as Data[];
  const observed = (r.observed || []) as Data[];
  const forecastTotal = forecast.reduce(
    (sum, day) => sum + (Number.isFinite(day.count) ? day.count : 0),
    0,
  );
  const peakDay = forecast.reduce<Data | null>(
    (peak, day) =>
      Number.isFinite(day.count) && (!peak || day.count > peak.count)
        ? day
        : peak,
    null,
  );
  const lastObserved = observed.at(-1);
  const metric = (r.data_scope?.metric || "daily count").replaceAll("_", " ");
  return (
    <div>
      <h3>T7 · What this forecast says</h3>
      <p>
        The model estimates how many events may be recorded each day, based on
        the historical series. These are research estimates, not confirmed
        future counts.
      </p>
      <div className="metrics" aria-label="Forecast summary in plain language">
        <div>
          <strong>{forecast.length}</strong>
          <span>Days estimated</span>
          <small>
            {forecast[0]?.date?.slice(0, 10)} to{" "}
            {forecast.at(-1)?.date?.slice(0, 10)}
          </small>
        </div>
        <div>
          <strong>{count(forecastTotal)}</strong>
          <span>Estimated total across those days</span>
          <small>
            Sum of the model's daily estimates; not a separate patient count.
          </small>
        </div>
        <div>
          <strong>{peakDay ? count(peakDay.count) : "Not measured"}</strong>
          <span>Highest estimated day</span>
          <small>
            {peakDay?.date?.slice(0, 10) || "No forecast date recorded"}
          </small>
        </div>
        <div>
          <strong>
            {lastObserved ? count(lastObserved.count) : "Not recorded"}
          </strong>
          <span>Most recent observed day</span>
          <small>
            {lastObserved?.date?.slice(0, 10) || "Source date unavailable"}
          </small>
        </div>
      </div>
      <h3>Forecast for each day</h3>
      <p>
        “Estimated {metric}” is the model's central estimate. The lower and
        upper values show an empirical error band based on past validation
        misses; it is not a guaranteed range.
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Estimated {metric} (about)</th>
              <th>Lower past-error bound</th>
              <th>Upper past-error bound</th>
            </tr>
          </thead>
          <tbody>
            {forecast.map((day) => (
              <tr key={day.date}>
                <td>{day.date.slice(0, 10)}</td>
                <td>{count(day.count)}</td>
                <td>{count(day.lower)}</td>
                <td>{count(day.upper)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3>Which forecasting method was chosen?</h3>
      <p>
        The app compared several methods using the validation period, then
        selected <strong>{modelName(r.selected || "unknown")}</strong>. A
        smaller MAE means the typical prediction missed by fewer count units.
        RMSE also measures the miss, but penalizes large errors more strongly.
      </p>
      <div className="table-wrap">
        <table>
          <caption>
            MAE is the average size of a miss. RMSE also measures error, but
            gives more weight to days with especially large misses. Lower is
            better for both. Errors are in daily count units.
          </caption>
          <thead>
            <tr>
              <th>Forecasting method</th>
              <th>Typical miss on validation days (MAE)</th>
              <th>Miss with extra penalty for large errors (RMSE)</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(r.validation_metrics || {}).map(([name, value]) => {
              const v = value as Data;
              return (
                <tr key={name}>
                  <td>
                    {modelName(name)}
                    {name === r.selected ? " (selected)" : ""}
                  </td>
                  <td>{measured(v.mae)}</td>
                  <td>{measured(v.rmse)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <p>
        Forecast counts above are rounded to whole events for easier reading;
        the chart data keeps the model's full numeric values.
      </p>
      {r.test_metrics ? (
        <>
          <h3>Selected model: held-out one-step test</h3>
          <p>
            On later days held aside for a final check, the typical miss (MAE)
            was {measured(r.test_metrics.mae)} count units. The large-error
            sensitive score (RMSE) was {measured(r.test_metrics.rmse)}. This
            final check did not choose the model.
          </p>
          {r.test_predictions?.length > 0 && (
            <Chart
              data={r.test_predictions}
              keys={["observed", "predicted"]}
              seriesLabels={{
                observed: "What was recorded",
                predicted: "What the model estimated",
              }}
              yAxisLabel="Daily count"
            />
          )}
        </>
      ) : (
        <p className="notice">
          This historical run has no separately recorded test metrics. Its
          validation errors must not be presented as independent test
          performance.
        </p>
      )}
      <p className="notice">
        The app checks dates in order: earlier days teach the models, the next
        days help choose one, and the latest held-aside days check it. That
        helps prevent future data from leaking into the past.
      </p>
      {r.split && (
        <details>
          <summary>
            Show the date split and technical validation details
          </summary>
          <p>
            Training: {r.split.training_rows} days through{" "}
            {r.split.training_end?.slice(0, 10)}. Validation:{" "}
            {r.split.validation_rows} days from{" "}
            {r.split.validation_start?.slice(0, 10)} to{" "}
            {r.split.validation_end?.slice(0, 10)}. Final test:{" "}
            {r.split.test_rows} days from {r.split.test_start?.slice(0, 10)} to{" "}
            {r.split.test_end?.slice(0, 10)}.
          </p>
          <p>{r.validation_protocol}</p>
        </details>
      )}
      {r.data_scope && (
        <>
          <h3>Source and applicability</h3>
          <p>
            {r.data_scope.metric} · {r.data_scope.requested_start} to{" "}
            {r.data_scope.requested_end}
          </p>
          <p className="notice">{r.data_scope.limitations}</p>
          {r.data_scope.missing_days_within_full_observed_range?.length > 0 && (
            <p>
              Recorded source gaps, not zero-filled:{" "}
              {r.data_scope.missing_days_within_full_observed_range.join(", ")}.
            </p>
          )}
        </>
      )}
      {r.retrospective_horizon_test?.metrics && (
        <>
          <h3>Retrospective recursive-horizon check</h3>
          <p>{r.retrospective_horizon_test.protocol}</p>
          <p>
            Across this held-out multi-day replay, the average absolute miss
            (MAE) was {measured(r.retrospective_horizon_test.metrics.mae)}; the
            large-error-sensitive RMSE was{" "}
            {measured(r.retrospective_horizon_test.metrics.rmse)}.
          </p>
          <Chart
            data={r.retrospective_horizon_test.rows}
            keys={["observed", "predicted"]}
            seriesLabels={{
              observed: "What was recorded",
              predicted: "What the model estimated",
            }}
            yAxisLabel="Daily count"
          />
        </>
      )}
      {r.scenario && (
        <>
          <h3>User-defined capacity scenario</h3>
          <p>
            You supplied an assumption of{" "}
            {r.scenario.assumption_patients_per_staff_per_shift} expected
            patients per staff member per shift. The app divides the forecast by
            that assumed capacity and rounds up to whole staff-shifts. This is a
            workload illustration, not a staffing recommendation.{" "}
            {r.scenario.label}
          </p>
          {r.scenario.allocation_status && (
            <p className="notice">{r.scenario.allocation_status}</p>
          )}
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Estimated patients that day</th>
                  <th>Staff-shifts under your assumption</th>
                </tr>
              </thead>
              <tbody>
                {r.forecast.map((v: Data, i: number) => (
                  <tr key={v.date}>
                    <td>{v.date.slice(0, 10)}</td>
                    <td>{measured(v.count)}</td>
                    <td>
                      {r.scenario.required_staff_shifts_per_day?.[i] ??
                        "Not recorded"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {r.scenario.per_shift && (
            <>
              <p>
                Assumed shift duration: {r.scenario.assumed_shift_hours} hours;
                total assumed coverage:{" "}
                {r.scenario.assumed_coverage_hours_per_day} hours/day.
              </p>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Shift number</th>
                      <th>Estimated arrivals in this shift</th>
                      <th>Staff-shifts needed under your assumption</th>
                    </tr>
                  </thead>
                  <tbody>
                    {r.scenario.per_shift.flatMap((day: Data) =>
                      day.shifts.map((shift: Data) => (
                        <tr key={`${day.day_index}-${shift.shift_index}`}>
                          <td>{r.forecast[day.day_index].date.slice(0, 10)}</td>
                          <td>{shift.shift_index}</td>
                          <td>{measured(shift.expected_arrivals)}</td>
                          <td>{shift.staff_required_under_assumptions}</td>
                        </tr>
                      )),
                    )}
                  </tbody>
                </table>
              </div>
            </>
          )}
          <p className="notice">{r.scenario.limitations}</p>
        </>
      )}
    </div>
  );
}
