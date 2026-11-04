type Data = Record<string, any>;

const number = (value: unknown) =>
  typeof value === "number" && Number.isFinite(value)
    ? new Intl.NumberFormat(undefined, { maximumFractionDigits: 1 }).format(
        value,
      )
    : "Not measured";

const readable = (value: unknown) =>
  typeof value === "string" ? value.replaceAll("_", " ") : "Not mapped";

export default function HealthcareOverviewEvidence({
  result: r,
}: {
  result: Data;
}) {
  if (typeof r.rows_selected !== "number") return null;
  const categories = Object.entries(r.distribution || {}).sort(
    ([, a], [, b]) => Number(b) - Number(a),
  );
  const topCategory = categories[0];
  const months = (r.monthly_trend || []) as Data[];
  const busiestMonth = months.reduce<Data | null>(
    (best, month) =>
      Number.isFinite(month.count) && (!best || month.count > best.count)
        ? month
        : best,
    null,
  );
  const mapped = r.mapped_fields || {};
  const countMeaning = mapped.count_column
    ? `sum of the values in “${mapped.count_column}”`
    : "number of source rows";

  return (
    <section aria-labelledby="healthcare-overview-title">
      <h3 id="healthcare-overview-title">
        T8 · What the healthcare data shows
      </h3>
      <p>
        These are descriptive totals from the selected dataset and date filters.
        They summarize the rows you analyzed; they are not predictions or
        hospital-wide rates.
      </p>
      <div className="metrics" aria-label="Healthcare summary explained">
        <div>
          <strong>{number(r.rows_selected)}</strong>
          <span>Rows included</span>
          <small>Records remaining after the selected date filters.</small>
        </div>
        <div>
          <strong>{number(r.observed_total)}</strong>
          <span>Calculated total</span>
          <small>Calculated as the {countMeaning}.</small>
        </div>
        <div>
          <strong>{months.length || "Not available"}</strong>
          <span>Months summarized</span>
          <small>
            {months.length
              ? `${months[0].date} through ${months.at(-1)?.date}`
              : "No date column was mapped."}
          </small>
        </div>
        <div>
          <strong>
            {topCategory ? readable(topCategory[0]) : "Not available"}
          </strong>
          <span>Largest recorded category</span>
          <small>
            {topCategory
              ? `${number(topCategory[1])} in this category.`
              : "No grouping column was mapped."}
          </small>
        </div>
      </div>
      <p className="notice">
        Calculation rule: {r.definition} This does not automatically count
        unique people; one person can have multiple records.
      </p>
      {busiestMonth && (
        <p>
          The highest monthly total in this selection was{" "}
          {number(busiestMonth.count)} in {busiestMonth.date}. This identifies
          the largest observed month in this dataset, not a future trend.
        </p>
      )}
      {mapped.date_column || mapped.category_column || mapped.count_column ? (
        <details>
          <summary>Which source columns were used?</summary>
          <ul>
            <li>Date grouping: {readable(mapped.date_column)}.</li>
            <li>Category grouping: {readable(mapped.category_column)}.</li>
            <li>Count measure: {readable(mapped.count_column)}.</li>
            {mapped.start_date && <li>Starting on: {mapped.start_date}.</li>}
            {mapped.end_date && <li>Ending on: {mapped.end_date}.</li>}
          </ul>
        </details>
      ) : null}
      {categories.length > 0 && (
        <div className="table-wrap">
          <table>
            <caption>
              Recorded totals by the selected category column. A category value
              of “nan” means the source value was missing.
            </caption>
            <thead>
              <tr>
                <th>Recorded category</th>
                <th>Records or total in category</th>
                <th>Share of calculated total</th>
              </tr>
            </thead>
            <tbody>
              {categories.map(([category, value]) => (
                <tr key={category}>
                  <th scope="row">
                    {category === "nan"
                      ? "Missing category"
                      : readable(category)}
                  </th>
                  <td>{number(value)}</td>
                  <td>
                    {r.observed_total > 0 && Number.isFinite(Number(value))
                      ? `${number((Number(value) / r.observed_total) * 100)}%`
                      : "Not calculated"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
