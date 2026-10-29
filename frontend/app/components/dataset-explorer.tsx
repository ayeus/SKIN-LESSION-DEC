"use client";
import { FormEvent, useState } from "react";
type Data = Record<string, any>;
type Source = {
  id: string;
  name: string;
  modality: string;
  profile: { columns: { name: string }[] };
};
type Props = {
  datasets: Source[];
  api: (path: string, init?: RequestInit) => Promise<any>;
  onResult: (result: Data) => void;
};
export default function DatasetExplorer({ datasets, api, onResult }: Props) {
  const [selected, setSelected] = useState(""),
    [page, setPage] = useState<Data | null>(null),
    [filter, setFilter] = useState({ column: "", value: "", match: "equals" }),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const source = datasets.find((d) => d.id === selected);
  const ehr = datasets.filter((d) => d.modality === "ehr");
  async function load(offset = 0) {
    if (!selected) return;
    setBusy(true);
    setError("");
    try {
      const params = new URLSearchParams({
        offset: String(offset),
        limit: "25",
      });
      if (filter.column) {
        params.set("column", filter.column);
        params.set("value", filter.value);
        params.set("match", filter.match);
      }
      setPage(await api("/datasets/" + selected + "/rows?" + params));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function relate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const fields = Object.fromEntries(new FormData(e.currentTarget));
      onResult(
        await api("/relationships", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(fields),
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (!datasets.length) return null;
  return (
    <section className="panel">
      <h2>Browse and filter source records</h2>
      <p>
        Read-only source exploration. Row totals reflect the selected table, not
        automatically unique patients.
      </p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      <label>
        Dataset to browse
        <select
          value={selected}
          onChange={(e) => {
            setSelected(e.target.value);
            setPage(null);
            setFilter({ column: "", value: "", match: "equals" });
          }}
        >
          <option value="">Select dataset</option>
          {datasets.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
      </label>
      {source && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void load();
          }}
        >
          <div className="form-grid">
            <label>
              Filter column
              <select
                value={filter.column}
                onChange={(e) => (
                  setFilter({ ...filter, column: e.target.value }),
                  setPage(null)
                )}
              >
                <option value="">All rows</option>
                {source.profile.columns.map((c) => (
                  <option key={c.name}>{c.name}</option>
                ))}
              </select>
            </label>
            <label>
              Match
              <select
                value={filter.match}
                onChange={(e) => (
                  setFilter({ ...filter, match: e.target.value }),
                  setPage(null)
                )}
              >
                <option value="equals">Exact value</option>
                <option value="contains">Contains literal text</option>
              </select>
            </label>
            <label>
              Filter value
              <input
                value={filter.value}
                onChange={(e) => (
                  setFilter({ ...filter, value: e.target.value }),
                  setPage(null)
                )}
              />
            </label>
          </div>
          <button disabled={busy}>Read matching records</button>
        </form>
      )}
      {page && (
        <>
          <p>
            {page.matched_rows} matching source rows. Showing{" "}
            {page.rows.length ? page.offset + 1 : 0}–
            {page.offset + page.rows.length}.
          </p>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {page.columns.map((c: string) => (
                    <th key={c}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {page.rows.map((row: Data, i: number) => (
                  <tr key={i}>
                    {page.columns.map((c: string) => (
                      <td key={c}>
                        {row[c] === null ? "Missing" : String(row[c] ?? "")}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button
            disabled={busy || page.offset === 0}
            onClick={() => void load(Math.max(0, page.offset - 25))}
          >
            Previous records
          </button>
          <button
            disabled={busy || page.offset + 25 >= page.matched_rows}
            onClick={() => void load(page.offset + 25)}
          >
            Next records
          </button>
        </>
      )}
      {ehr.length >= 2 && (
        <details>
          <summary>Inspect patient / encounter table relationships</summary>
          <p>
            Choose the child table and its foreign key, then a parent table with
            a unique primary key. Repeated child keys are preserved.
          </p>
          <form onSubmit={relate}>
            <div className="form-grid">
              <label>
                Child EHR table
                <select name="child_dataset_id" required>
                  {ehr.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Child foreign key
                <input
                  name="child_key"
                  required
                  placeholder="e.g. subject_id"
                />
              </label>
              <label>
                Parent EHR table
                <select name="parent_dataset_id" required>
                  {ehr.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Parent primary key
                <input
                  name="parent_key"
                  required
                  placeholder="e.g. subject_id"
                />
              </label>
            </div>
            <button disabled={busy}>Validate relationship</button>
          </form>
        </details>
      )}
    </section>
  );
}
