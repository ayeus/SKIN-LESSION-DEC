"use client";
import { useEffect, useState } from "react";
type Data = Record<string, any>;
type Props = {
  api: (path: string, init?: RequestInit) => Promise<any>;
  onResult: (result: Data) => void;
  canSelect?: boolean;
};
export default function ClinicalModelPanel({
  api,
  onResult,
  canSelect = false,
}: Props) {
  const [runs, setRuns] = useState<Data[]>([]),
    [card, setCard] = useState<Data | null>(null),
    [reviewed, setReviewed] = useState<string | null>(null),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState("");
  async function refresh() {
    setBusy(true);
    setError("");
    try {
      setRuns(
        (await api("/runs")).filter(
          (r: Data) => r.kind === "clinical_ner_training",
        ),
      );
      try {
        setCard((await api("/clinical-models/current")).model_card);
      } catch (e) {
        if ((e as Error).message.includes("No clinical NER model selected"))
          setCard(null);
        else throw e;
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    void refresh();
  }, []);
  async function review(id: string) {
    setBusy(true);
    setError("");
    try {
      onResult(await api("/runs/" + id));
      setReviewed(id);
      setMessage(
        "Review the measured report below before selecting this research model.",
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function select(id: string) {
    setBusy(true);
    setError("");
    try {
      await api("/clinical-models/select/" + id, { method: "POST" });
      setMessage(
        "Research NER model selected. Clinical validation is not established.",
      );
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel">
      <h2>Clinical entity model and evidence</h2>
      <p>
        Actual local corpus training runs appear here. Published case reports
        differ from institutional notes; entity extraction does not verify
        clinical facts.
      </p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {message && <p role="status">{message}</p>}
      {card ? (
        <>
          <p>Selected source: {card.source}</p>
          <p className="notice">{card.limitations}</p>
          {card.evaluation?.micro && (
            <p>
              Recorded exact-span test precision{" "}
              {card.evaluation.micro.precision.toFixed(3)}, recall{" "}
              {card.evaluation.micro.recall.toFixed(3)}, F1{" "}
              {card.evaluation.micro.f1.toFixed(3)}. Contiguous-span research
              benchmark only.
            </p>
          )}
        </>
      ) : (
        <p className="notice">
          No selected NER model. Entity extraction stays blocked until a real
          trained artifact is selected or configured.
        </p>
      )}
      <button type="button" disabled={busy} onClick={() => void refresh()}>
        Refresh clinical models
      </button>
      {runs.length === 0 ? (
        <p>
          No visible corpus training runs. See the documented clinical-corpus
          acquisition and training commands.
        </p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Run</th>
                <th>Status</th>
                <th>Evidence and selection</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.id}>
                  <td>{run.id}</td>
                  <td>{run.status}</td>
                  <td>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void review(run.id)}
                    >
                      Review clinical run
                    </button>
                    {canSelect && run.status === "completed" && (
                      <button
                        type="button"
                        disabled={busy || reviewed !== run.id}
                        onClick={() => void select(run.id)}
                      >
                        Select reviewed NER model
                      </button>
                    )}
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
