type Data = Record<string, any>;

const labels: Record<string, string> = {
  age_years_topcoded80: "Age (years; top-coded at 80)",
  female_reported: "Reported female indicator",
  sedentary_minutes_day: "Sedentary time (minutes/day)",
  sleep_weekday_hours_exact: "Weekday sleep (hours)",
  meals_away_week_exact: "Meals eaten away from home (per week)",
  bmi_kg_m2: "Body mass index (kg/m²)",
};

export const adultWeightFeatureLabel = (value: string) =>
  labels[value] || value.replaceAll("_", " ");
const number = (value: unknown, digits = 2) =>
  typeof value === "number" && Number.isFinite(value)
    ? value.toFixed(digits)
    : "Not measured";

export default function AdultWeightEvidence({ result: r }: { result: Data }) {
  if (!r.model || typeof r.mae !== "number" || !Array.isArray(r.observed))
    return null;

  const correlations = r.diagnostics?.feature_correlation || {};
  const pairs: { first: string; second: string; value: number }[] = [];
  Object.entries(correlations).forEach(([first, values], index, entries) => {
    entries.slice(index + 1).forEach(([second]) => {
      const value = (values as Data)?.[second];
      if (typeof value === "number" && Number.isFinite(value))
        pairs.push({ first, second, value });
    });
  });

  return (
    <section aria-labelledby="adult-weight-results-title">
      <h3 id="adult-weight-results-title">T14–T15 adult weight results</h3>
      <p>
        These numbers describe this dataset and a held-out test sample. BMI is
        measured in kg/m². Lower MAE and RMSE indicate smaller errors; R² closer
        to 1 indicates a closer fit. A negative R² means the model did worse
        than predicting the test-sample average.
      </p>
      <div className="metrics" aria-label="Held-out BMI model results">
        <div>
          <strong>{number(r.mae)}</strong>
          <span>MAE · BMI error</span>
          <small>Average absolute prediction error, in BMI points.</small>
        </div>
        <div>
          <strong>{number(r.rmse)}</strong>
          <span>RMSE · BMI error</span>
          <small>Like MAE, but large misses count more heavily.</small>
        </div>
        <div>
          <strong>{number(r.r2, 3)}</strong>
          <span>R² · fit compared with the average</span>
          <small>How much better or worse predictions fit than the mean.</small>
        </div>
        <div>
          <strong>{number(r.test_rows, 0)}</strong>
          <span>Held-out test adults</span>
          <small>Records reserved for final model evaluation.</small>
        </div>
      </div>

      <p className="notice">
        Training adults: {number(r.train_rows, 0)}. Test adults:{" "}
        {number(r.test_rows, 0)}. The model was fitted on the training portion
        and evaluated on the held-out test portion. These are exploratory,
        unweighted observational results; they do not show that a behavior
        causes BMI to change.
      </p>

      {r.nonlinear_comparison && (
        <div className="table-wrap">
          <table>
            <caption>
              Model comparison. Compare test errors: lower is better; all error
              values are in BMI points.
            </caption>
            <thead>
              <tr>
                <th>Model</th>
                <th>Test MAE (average miss)</th>
                <th>Test RMSE (penalizes large misses)</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <th scope="row">Ridge regression</th>
                <td>{number(r.mae)}</td>
                <td>{number(r.rmse)}</td>
              </tr>
              <tr>
                <th scope="row">Random forest</th>
                <td>{number(r.nonlinear_comparison.test_mae)}</td>
                <td>{number(r.nonlinear_comparison.test_rmse)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {r.permutation_importance && (
        <div className="table-wrap">
          <table>
            <caption>
              Feature importance: change in test MAE after shuffling one input.
              A larger positive increase means the model relied more on that
              input; it does not mean the input causes BMI to change.
            </caption>
            <thead>
              <tr>
                <th>Input measurement</th>
                <th>Average increase in MAE (BMI points)</th>
                <th>Variation across shuffles</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(r.permutation_importance).map(
                ([feature, value]) => (
                  <tr key={feature}>
                    <th scope="row">{adultWeightFeatureLabel(feature)}</th>
                    <td>{number((value as Data).mean_mae_increase)}</td>
                    <td>{number((value as Data).std)}</td>
                  </tr>
                ),
              )}
            </tbody>
          </table>
        </div>
      )}

      {r.sensitivity_leave_one_feature_out?.length > 0 && (
        <div className="table-wrap">
          <table>
            <caption>
              Sensitivity check: test MAE after refitting without one input.
              Compare each row with the Ridge regression MAE above; lower means
              smaller errors in this test sample.
            </caption>
            <thead>
              <tr>
                <th>Input left out</th>
                <th>Test MAE (BMI points)</th>
              </tr>
            </thead>
            <tbody>
              {r.sensitivity_leave_one_feature_out.map((item: Data) => (
                <tr key={item.omitted_feature}>
                  <th scope="row">
                    {adultWeightFeatureLabel(item.omitted_feature)}
                  </th>
                  <td>{number(item.test_mae)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {pairs.length > 0 && (
        <div className="table-wrap">
          <table>
            <caption>
              Feature correlations: values range from −1 to +1. Near zero means
              little linear association in this dataset; correlation does not
              establish cause.
            </caption>
            <thead>
              <tr>
                <th>First measurement</th>
                <th>Second measurement</th>
                <th>Correlation (−1 to +1)</th>
              </tr>
            </thead>
            <tbody>
              {pairs.map((pair) => (
                <tr key={`${pair.first}-${pair.second}`}>
                  <td>{adultWeightFeatureLabel(pair.first)}</td>
                  <td>{adultWeightFeatureLabel(pair.second)}</td>
                  <td>{number(pair.value, 3)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <details>
        <summary>What are residuals?</summary>
        <p>
          A residual is the observed BMI minus the model&apos;s predicted BMI.
          Positive residuals mean the model predicted too low; negative values
          mean it predicted too high. The residual mean is{" "}
          {number(r.diagnostics?.residual_mean)} BMI points and the residual
          standard deviation is {number(r.diagnostics?.residual_std)} BMI
          points. These describe model errors, not people&apos;s health.
        </p>
      </details>
    </section>
  );
}
