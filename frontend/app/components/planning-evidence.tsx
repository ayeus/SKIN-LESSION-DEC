type Data = Record<string, any>;
export default function PlanningEvidence({ result: r }: { result: Data }) {
  if (!r.planning_status) return null;
  return (
    <section aria-label="Planning assumptions and comparisons">
      <h3>Planning evidence and scenario comparison</h3>
      <p>{r.planning_status}</p>
      <p className="notice">
        Historical rows are observed counts. Future counts are model forecasts.
        Capacity, staff and minimum coverage are user assumptions. These
        scenarios are not observed utilization or safe staffing recommendations.
      </p>
      {r.planning_scenarios?.map((scenario: Data) => (
        <details key={scenario.name}>
          <summary>{scenario.name}</summary>
          <p>{scenario.interpretation}</p>
          <p>
            Peak daily workload:{" "}
            {scenario.summary.peak_daily_workload_staff_shifts} staff-shift
            equivalents. Maximum shift workload gap:{" "}
            {scenario.summary.maximum_shift_workload_shortfall ??
              "Not calculated: no available-staff assumption"}
            .
          </p>
          {scenario.per_shift ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Forecast date</th>
                    <th>Shift</th>
                    <th>Allocated expected count</th>
                    <th>Required under assumptions</th>
                    <th>Available staff assumption</th>
                    <th>Workload gap</th>
                    <th>Demand / assumed capacity</th>
                  </tr>
                </thead>
                <tbody>
                  {scenario.per_shift.flatMap((day: Data) =>
                    day.shifts.map((shift: Data) => (
                      <tr key={`${day.day_index}-${shift.shift_index}`}>
                        <td>{r.forecast[day.day_index].date.slice(0, 10)}</td>
                        <td>{shift.shift_index}</td>
                        <td>{shift.expected_arrivals.toFixed(2)}</td>
                        <td>
                          {shift.staff_required_including_coverage ??
                            shift.staff_required_under_assumptions}
                        </td>
                        <td>
                          {shift.available_staff_assumption ?? "Not supplied"}
                        </td>
                        <td>
                          {shift.workload_shortfall_staff ?? "Not calculated"}
                        </td>
                        <td>
                          {shift.forecast_demand_to_assumed_capacity_ratio ==
                          null
                            ? shift.capacity_ratio_status || "Not calculated"
                            : shift.forecast_demand_to_assumed_capacity_ratio.toFixed(
                                2,
                              )}
                        </td>
                      </tr>
                    )),
                  )}
                </tbody>
              </table>
            </div>
          ) : (
            <p>{scenario.allocation_status}</p>
          )}
          <p>{scenario.minimum_coverage_status || scenario.limitations}</p>
        </details>
      ))}
    </section>
  );
}
