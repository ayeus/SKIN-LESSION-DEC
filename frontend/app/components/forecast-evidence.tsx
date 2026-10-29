"use client";
import type { ComponentType } from "react";
type Data = Record<string, any>;
type Props = {
  result: Data;
  Chart: ComponentType<{ data: any[]; keys: string[] }>;
};
const measured = (v: unknown) =>
  typeof v === "number" && Number.isFinite(v) ? v.toFixed(2) : "Not measured";
export default function ForecastEvidence({ result: r, Chart }: Props) {
  if (!r.forecast) return null;
  return (
    <div>
      <h3>Model comparison on validation data</h3>
      <p>
        Selection: {r.selected}.{" "}
        {r.selection_criterion || "See the recorded protocol for this run."}
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Validation MAE</th>
              <th>Validation RMSE</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(r.validation_metrics || {}).map(([name, value]) => {
              const v = value as Data;
              return (
                <tr key={name}>
                  <td>
                    {name}
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
      {r.test_metrics ? (
        <>
          <h3>Selected model: held-out one-step test</h3>
          <p>
            MAE {measured(r.test_metrics.mae)} count units; RMSE{" "}
            {measured(r.test_metrics.rmse)} count units. These errors were not
            used for model selection.
          </p>
          {r.test_predictions?.length > 0 && (
            <Chart data={r.test_predictions} keys={["observed", "predicted"]} />
          )}
        </>
      ) : (
        <p className="notice">
          This historical run has no separately recorded test metrics. Its
          validation errors must not be presented as independent test
          performance.
        </p>
      )}
      <p className="notice">{r.validation_protocol}</p>
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
            MAE {measured(r.retrospective_horizon_test.metrics.mae)}; RMSE{" "}
            {measured(r.retrospective_horizon_test.metrics.rmse)}.
          </p>
          <Chart
            data={r.retrospective_horizon_test.rows}
            keys={["observed", "predicted"]}
          />
        </>
      )}
      {r.scenario && (
        <>
          <h3>User-defined capacity scenario</h3>
          <p>
            Assumed capacity:{" "}
            {r.scenario.assumption_patients_per_staff_per_shift} patients per
            staff-shift. {r.scenario.label}
          </p>
          {r.scenario.allocation_status && (
            <p className="notice">{r.scenario.allocation_status}</p>
          )}
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Forecast date</th>
                  <th>Forecast count</th>
                  <th>Daily staff-shift workload equivalents</th>
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
                      <th>Shift index</th>
                      <th>Allocated expected count</th>
                      <th>Staff under supplied assumptions</th>
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
