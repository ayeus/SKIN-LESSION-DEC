"use client";
import { FormEvent, useEffect, useState } from "react";
type Data = Record<string, any>;
type Props = {
  api: (path: string, init?: RequestInit) => Promise<any>;
  onResult: (result: Data) => void;
  onChange: () => void;
};
export default function TrainingPanel({ api, onResult, onChange }: Props) {
  const [ready, setReady] = useState<Data | null>(null),
    [job, setJob] = useState<Data | null>(null),
    [error, setError] = useState(""),
    [submitting, setSubmitting] = useState(false);
  async function check() {
    try {
      setReady(await api("/training/readiness"));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    void check();
  }, []);
  useEffect(() => {
    if (!job?.id || !["pending", "running"].includes(job.status)) return;
    let stopped = false;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const update = await api("/runs/" + job!.id);
        if (stopped) return;
        setJob(update);
        if (update.status === "completed") {
          onResult(update);
          onChange();
        } else if (update.status === "failed") {
          setError(update.error || "Training failed");
          onChange();
        } else timer = setTimeout(poll, 1500);
      } catch (e) {
        if (!stopped) setError((e as Error).message);
      }
    }
    timer = setTimeout(poll, 500);
    return () => {
      stopped = true;
      clearTimeout(timer);
    };
  }, [job?.id, job?.status]);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    const fields = new FormData(e.currentTarget);
    try {
      setJob(
        await api("/training", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            architecture: fields.get("architecture"),
            epochs: Number(fields.get("epochs")),
            batch_size: Number(fields.get("batch_size")),
            pretrained: fields.get("pretrained") === "true",
          }),
        }),
      );
      onChange();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }
  const active =
    submitting || (!!job && ["pending", "running"].includes(job.status));
  return (
    <section className="panel">
      <span className="badge">Actual experiment pipeline</span>
      <h2>Train and review a research classifier</h2>
      <p>
        Training uses the configured labeled image manifest. It never
        substitutes test fixtures or automatically enables inference.
      </p>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <div className="section-title">
        <strong>
          {ready?.ready
            ? "Dataset files are present"
            : ready?.reason || "Checking image dataset…"}
        </strong>
        <button onClick={() => void check()}>Recheck dataset</button>
      </div>
      {ready?.manifest_rows && (
        <p>
          {ready.manifest_rows} manifest images; {ready.missing_images} missing.{" "}
          {ready.grouping_limit}
        </p>
      )}
      <form onSubmit={submit}>
        <div className="form-grid">
          <label>
            Architecture
            <select name="architecture" disabled={active}>
              <option value="small_cnn">Small CNN baseline</option>
              <option value="resnet18">ResNet18</option>
              <option value="efficientnet_b0">EfficientNet-B0</option>
            </select>
          </label>
          <label>
            Epochs
            <input
              name="epochs"
              type="number"
              min={1}
              max={1000}
              defaultValue={5}
              required
              disabled={active}
            />
          </label>
          <label>
            Batch size
            <input
              name="batch_size"
              type="number"
              min={1}
              max={128}
              defaultValue={16}
              required
              disabled={active}
            />
          </label>
        </div>
        <label className="check-label">
          <input
            type="checkbox"
            name="pretrained"
            value="true"
            disabled={active}
          />
          Allow official torchvision ImageNet weight download for
          ResNet/EfficientNet. These are not lesion-trained weights.
        </label>
        <button className="primary" disabled={!ready?.ready || active}>
          {active ? "Training job active" : "Start training experiment"}
        </button>
      </form>
      {job && (
        <div role="status" className="notice">
          Run {job.id}: {job.status}
          {job.result?.epoch && (
            <>
              <p>
                Completed epoch {job.result.epoch} of {job.result.total_epochs}
              </p>
              <progress
                max={job.result.total_epochs}
                value={job.result.epoch}
              />
              <p>
                Measured loss: training{" "}
                {job.result.latest.train.loss.toFixed(4)}, validation{" "}
                {job.result.latest.validation.loss.toFixed(4)}
              </p>
            </>
          )}
        </div>
      )}
      <p className="notice">
        Only one training job runs at a time. Progress and failures persist in
        Reports. Navigation stops polling, not training. Compare validation
        evidence; repeated test-set selection biases results. Scores remain
        uncalibrated; clinical validation is not established.
      </p>
      <button
        onClick={async () => {
          try {
            onResult(await api("/models/current"));
          } catch (e) {
            setError((e as Error).message);
          }
        }}
      >
        Review selected model artifacts
      </button>
      {job?.status === "completed" && (
        <button
          onClick={async () => {
            try {
              await api("/models/select/" + job.id, { method: "POST" });
              onChange();
              setError("");
            } catch (e) {
              setError((e as Error).message);
            }
          }}
        >
          Select this reviewed research artifact
        </button>
      )}
    </section>
  );
}
