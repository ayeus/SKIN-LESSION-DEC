"use client";
import { type FormEvent, useEffect, useState } from "react";
type Data = Record<string, any>;
export default function TerminologyPanel({
  api,
  onResult,
}: {
  api: (path: string, init?: RequestInit) => Promise<any>;
  onResult: (value: Data) => void;
}) {
  const [status, setStatus] = useState<Data | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function check() {
    try {
      setStatus(await api("/terminology/status"));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    void check();
  }, []);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const fields = new FormData(event.currentTarget);
    try {
      onResult(
        await api("/terminology/disambiguate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            term: fields.get("term"),
            context: fields.get("context"),
            retain: fields.get("retain") === "true",
          }),
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel">
      <h2>Medical terminology in context</h2>
      <p>
        Rank genuine dictionary candidates using local context. No term, note or
        context is sent to an external terminology service.
      </p>
      {error && (
        <p className="error" role="alert">
          {error}
        </p>
      )}
      {status?.available ? (
        <>
          <p>
            {status.metadata.attribution} · {status.metadata.version} ·{" "}
            {status.descriptor_records.toLocaleString()} descriptors
          </p>
          <p className="notice">{status.metadata.limitations}</p>
          <form onSubmit={submit}>
            <label>
              Medical term or abbreviation
              <input
                name="term"
                required
                maxLength={200}
                autoComplete="off"
                spellCheck={false}
              />
            </label>
            <label>
              Authorized, de-identified local context
              <textarea
                name="context"
                required
                minLength={5}
                maxLength={10000}
              />
            </label>
            <label className="check-label">
              <input type="checkbox" name="retain" value="true" />
              Save this context and ranking in local report history (optional).
            </label>
            <button className="primary" disabled={busy}>
              {busy ? "Ranking…" : "Rank contextual candidates"}
            </button>
          </form>
        </>
      ) : (
        <p className="notice">
          {status?.reason || "Checking local terminology inventory…"}
        </p>
      )}
      <button type="button" disabled={busy} onClick={() => void check()}>
        Recheck terminology data
      </button>
    </section>
  );
}
