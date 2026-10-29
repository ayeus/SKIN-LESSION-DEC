"use client";
import { useEffect, useState, FormEvent } from "react";
import {
  Activity,
  LayoutDashboard,
  ScanLine,
  SlidersHorizontal,
  Layers,
  BrainCircuit,
  Database,
  FileText,
  TrendingUp,
  ChartNoAxesCombined,
  ScatterChart,
  Scale,
  FolderDown,
  Settings,
  ChevronRight,
  ShieldCheck,
  Upload,
  LogOut,
  Menu,
  Microscope,
  Check,
  AlertCircle,
} from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ScatterChart as Plot,
  Scatter,
} from "recharts";
type Result = Record<string, any>;
type Dataset = {
  id: string;
  name: string;
  modality: string;
  source: string;
  profile: {
    rows: number;
    columns: { name: string; dtype: string; missing: number }[];
  };
};
type Run = {
  id: string;
  kind: string;
  status: string;
  created_at: string;
  error?: string;
};
const modules = [
  { id: "dashboard", name: "Research overview", icon: LayoutDashboard },
  { id: "inference", name: "Lesion detection", icon: ScanLine },
  { id: "image", name: "Image processing lab", icon: SlidersHorizontal },
  { id: "registration", name: "SIFT & RANSAC", icon: Layers },
  { id: "training", name: "CNN training & evaluation", icon: BrainCircuit },
  { id: "visualization", name: "Biomedical visualization", icon: Microscope },
  { id: "datasets", name: "EHR & dataset management", icon: Database },
  { id: "preprocess", name: "Data preprocessing", icon: SlidersHorizontal },
  { id: "text", name: "Clinical text analytics", icon: FileText },
  { id: "forecast", name: "Patient demand", icon: TrendingUp },
  {
    id: "overview",
    name: "Historical healthcare indicators",
    icon: ChartNoAxesCombined,
  },
  { id: "planning", name: "Healthcare planning", icon: ChartNoAxesCombined },
  { id: "reduce", name: "Dimensionality reduction", icon: ScatterChart },
  { id: "research", name: "Adult weight research", icon: Scale },
  { id: "reports", name: "Reports & history", icon: FolderDown },
  { id: "settings", name: "Data & model status", icon: Settings },
];
const descriptions: Record<string, string> = {
  overview:
    "Explicitly mapped observed indicators, never assumed patient counts.",
  dashboard: "One workspace for transparent, reproducible healthcare research.",
  image:
    "Explore the actual pixels. Every adjustment runs a documented algorithm.",
  registration: "Estimate geometry from valid feature correspondences.",
  datasets: "Import authorized research data with traceable provenance.",
  preprocess: "Standardize data without overwriting your source.",
  text: "Explore clinical language with clearly scoped methods.",
  forecast: "Build temporal baselines from observed daily arrivals.",
  planning: "Separate observed demand, forecasts and your assumptions.",
  reduce: "Explore numeric research features.",
  research: "Study observational associations in adult datasets.",
  inference: "Research predictions require a real trained classifier.",
  training:
    "Independent groups, reproducible experiments and held-out evaluation.",
  visualization: "Inspect artifacts from completed runs.",
  reports: "Review execution history and export actual results.",
  settings: "Understand what is available and what is missing.",
};
function Chart({ data, keys }: { data: any[]; keys: string[] }) {
  return (
    <div className="chart">
      <ResponsiveContainer width="100%" height={260}>
        <LineChart data={data}>
          <CartesianGrid strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey={data[0]?.date ? "date" : "index"}
            tick={{ fontSize: 11 }}
          />
          <YAxis />
          <Tooltip />
          {keys.map((k, i) => (
            <Line
              key={k}
              dataKey={k}
              stroke={["#087f83", "#bd6b37", "#6879b6"][i % 3]}
              dot={false}
              strokeWidth={2}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
function Results({ value }: { value: Result }) {
  const r = value.result || value;
  return (
    <section className="panel">
      <div className="section-title">
        <h2>Execution results</h2>
        <span className="badge green">Calculated from your input</span>
      </div>
      {r.limitation && <p className="notice">{r.limitation}</p>}
      {r.image && (
        <div className="image-grid">
          {[
            ["original", "Original"],
            ["image", "Algorithm output"],
            ["mask", "Computed mask"],
          ].map(
            ([k, label]) =>
              r[k] && (
                <figure key={k}>
                  <img src={r[k]} alt={label} />
                  <figcaption>{label}</figcaption>
                </figure>
              ),
          )}
        </div>
      )}
      {["keypoint_image", "matches_image", "registered"].map(
        (k) =>
          r[k] && (
            <figure key={k}>
              <img src={r[k]} alt={k.replaceAll("_", " ")} />
              <figcaption>{k.replaceAll("_", " ")}</figcaption>
            </figure>
          ),
      )}
      {r.image && (
        <a className="download-link" href={r.image} download="processed.png">
          Download processed PNG
        </a>
      )}
      {r.metrics?.download && (
        <a
          className="download-link"
          href={r.metrics.download}
          download={`compressed.${r.method}`}
        >
          Download actual compressed file
        </a>
      )}
      {r.histogram && (
        <Chart
          data={r.histogram[0].map((_: number, i: number) => ({
            index: i * 8,
            red: r.histogram[0][i],
            green: r.histogram[1][i],
            blue: r.histogram[2][i],
          }))}
          keys={["red", "green", "blue"]}
        />
      )}
      {r.forecast && (
        <>
          <h3>Observed daily arrivals</h3>
          <Chart data={r.observed} keys={["count"]} />
          <h3>Forecast and empirical residual band</h3>
          <Chart data={r.forecast} keys={["count", "lower", "upper"]} />
          <p>{r.uncertainty}</p>
        </>
      )}
      {r.monthly_trend && <Chart data={r.monthly_trend} keys={["count"]} />}
      {r.history && (
        <>
          <h3>Training and validation loss</h3>
          <Chart
            data={r.history.map((h: any) => ({
              index: h.epoch,
              train_loss: h.train.loss,
              validation_loss: h.validation.loss,
            }))}
            keys={["train_loss", "validation_loss"]}
          />
        </>
      )}
      {r.manifest?.evaluation?.confusion_matrix && (
        <>
          <h3>Held-out confusion matrix</h3>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Actual / predicted</th>
                  {r.manifest.labels.map((label: string) => (
                    <th key={label}>{label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {r.manifest.evaluation.confusion_matrix.map(
                  (row: number[], i: number) => (
                    <tr key={i}>
                      <th>{r.manifest.labels[i]}</th>
                      {row.map((v, j) => (
                        <td key={j}>{v}</td>
                      ))}
                    </tr>
                  ),
                )}
              </tbody>
            </table>
          </div>
          {Object.entries(r.manifest.evaluation.curves || {}).map(
            ([label, value]) => {
              const v = value as any;
              return (
                <div key={label}>
                  <h3>{label}: ROC</h3>
                  <Chart
                    data={v.fpr.map((x: number, i: number) => ({
                      index: x,
                      recall: v.tpr[i],
                    }))}
                    keys={["recall"]}
                  />
                  <h3>{label}: precision-recall</h3>
                  <Chart
                    data={v.recall.map((x: number, i: number) => ({
                      index: x,
                      precision: v.precision[i],
                    }))}
                    keys={["precision"]}
                  />
                </div>
              );
            },
          )}
        </>
      )}
      {r.documents &&
        r.documents.map((d: any, i: number) => (
          <article key={i}>
            <h3>Document {i}</h3>
            <p>{d.text}</p>
            <ul>
              {d.entities.map((e: any, j: number) => (
                <li key={j}>
                  <mark>{e.text}</mark> {e.label} (characters {e.start}–{e.end}
                  ); negation:{" "}
                  {e.negated === null ? "unknown" : String(e.negated)}
                </li>
              ))}
            </ul>
          </article>
        ))}
      {Object.entries(
        r.histograms ||
          r.profile?.histograms ||
          r.descriptive?.histograms ||
          {},
      ).map(([name, value]) => {
        const v = value as any;
        return (
          <div key={name}>
            <h3>{name}: observed distribution</h3>
            <Chart
              data={v.counts.map((count: number, i: number) => ({
                index: Number(v.edges[i].toPrecision(3)),
                count,
              }))}
              keys={["count"]}
            />
          </div>
        );
      })}
      {r.coordinates && (
        <div className="chart">
          <ResponsiveContainer width="100%" height={300}>
            <Plot>
              <CartesianGrid />
              <XAxis type="number" dataKey="x" />
              <YAxis type="number" dataKey="y" />
              <Tooltip />
              <Scatter
                data={r.coordinates.map((v: number[]) => ({
                  x: v[0],
                  y: v[1],
                }))}
                fill="#087f83"
              />
            </Plot>
          </ResponsiveContainer>
        </div>
      )}
      {r.predicted && (
        <Chart
          data={r.predicted.map((v: number, i: number) => ({
            index: i,
            predicted: v,
            observed: r.observed[i],
          }))}
          keys={["observed", "predicted"]}
        />
      )}
      {r.before && (
        <div className="metrics">
          <div>
            <strong>{r.before.rows}</strong>Source rows
          </div>
          <div>
            <strong>{r.after.rows}</strong>Output rows
          </div>
          <div>
            <strong>{r.history.length}</strong>Transformations
          </div>
        </div>
      )}
      {r.results?.map((v: any) => (
        <article key={v.document_index}>
          <strong>
            Document {v.document_index} · score {v.score.toFixed(3)}
          </strong>
          <p>{v.text}</p>
        </article>
      ))}
      {r.explanation?.overlay && (
        <figure>
          <img
            src={r.explanation.overlay}
            alt="Grad-CAM from model activations and gradients"
          />
          <figcaption>
            Grad-CAM · explanatory visualization, not clinical localization
          </figcaption>
        </figure>
      )}
      {r.scores &&
        Object.entries(r.scores).map(([k, v]) => (
          <p key={k}>
            {k}: {Number(v).toFixed(4)}
          </p>
        ))}
      <details>
        <summary>Structured metrics, parameters and report</summary>
        <pre>
          {JSON.stringify(
            r,
            (k, v) =>
              typeof v === "string" && v.startsWith("data:")
                ? "[image artifact]"
                : v,
            2,
          )}
        </pre>
      </details>
    </section>
  );
}
export default function Home() {
  const [token, setToken] = useState(""),
    [entry, setEntry] = useState(""),
    [page, setPage] = useState("dashboard"),
    [status, setStatus] = useState<Result | null>(null),
    [datasets, setDatasets] = useState<Dataset[]>([]),
    [runs, setRuns] = useState<Run[]>([]),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [result, setResult] = useState<Result | null>(null),
    [selected, setSelected] = useState(""),
    [method, setMethod] = useState("clahe"),
    [parameters, setParameters] = useState("{}"),
    [mobile, setMobile] = useState(false),
    [query, setQuery] = useState("");
  async function api(path: string, init: RequestInit = {}) {
    const response = await fetch("/api" + path, {
      ...init,
      headers: { Authorization: "Bearer " + token, ...init.headers },
    });
    if (!response.ok) {
      let body;
      try {
        body = await response.json();
      } catch {
        throw new Error(`Server returned ${response.status}`);
      }
      throw new Error(
        typeof body.detail === "string"
          ? body.detail
          : JSON.stringify(body.detail),
      );
    }
    return response.json();
  }
  async function refresh() {
    try {
      const [s, d, r] = await Promise.all([
        api("/status"),
        api("/datasets"),
        api("/runs"),
      ]);
      setStatus(s);
      setDatasets(d);
      setRuns(r);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  useEffect(() => {
    if (token) void refresh();
  }, [token]);
  function navigate(id: string) {
    setPage(id);
    setResult(null);
    setError("");
    setParameters("{}");
    setMobile(false);
    setSelected("");
  }
  async function submit(e: FormEvent<HTMLFormElement>, type: string) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setResult(null);
    try {
      const fd = new FormData(e.currentTarget);
      let output;
      if (type === "datasets") {
        output = await api("/datasets", { method: "POST", body: fd });
      } else if (["image", "registration", "inference"].includes(type)) {
        if (type === "image") {
          fd.set("method", method);
          fd.set("parameters", parameters);
        }
        if (type === "image" && !(fd.get("mask") as File)?.size)
          fd.delete("mask");
        output = await api(
          type === "image"
            ? "/images/process"
            : type === "registration"
              ? "/images/register"
              : "/inference",
          { method: "POST", body: fd },
        );
      } else {
        const p = JSON.parse(parameters);
        if (type === "overview") {
          for (const key of [
            "date_column",
            "count_column",
            "group_column",
            "start_date",
            "end_date",
          ])
            if (fd.get(key)) p[key] = fd.get(key);
        }
        if (type === "text") {
          p.task = fd.get("task");
          p.text_column = fd.get("text_column");
          p.query = fd.get("query");
          p.label_column = fd.get("label_column");
        }
        if (type === "forecast" || type === "planning") {
          p.date_column = fd.get("date_column");
          p.count_column = fd.get("count_column");
          p.horizon = Number(fd.get("horizon"));
          if (fd.get("capacity"))
            p.patients_per_staff_per_shift = Number(fd.get("capacity"));
        }
        if (type === "reduce" || type === "research") {
          p.features = String(fd.get("features"))
            .split(",")
            .map((v) => v.trim())
            .filter(Boolean);
          if (type === "reduce") p.method = fd.get("reduction");
          else p.target = fd.get("target");
        }
        output = await api(
          "/analyze/" +
            (type === "planning" ? "forecast" : type) +
            "?background=true",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ dataset_id: selected, parameters: p }),
          },
        );
      }
      if (output.status === "pending") {
        while (output.status === "pending" || output.status === "running") {
          await new Promise((resolve) => setTimeout(resolve, 700));
          output = await api("/runs/" + output.id);
        }
        if (output.status === "failed")
          throw new Error(output.error || "Analysis failed");
      }
      setResult(output);
      void refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function exportRun(id: string, format = "json") {
    try {
      const response = await fetch(`/api/runs/${id}/export/${format}`, {
        headers: { Authorization: "Bearer " + token },
      });
      if (!response.ok) throw new Error("Artifact unavailable");
      const url = URL.createObjectURL(await response.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = `research-${id}.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  const current = modules.find((m) => m.id === page)!;
  const ds = datasets.find((d) => d.id === selected);
  const compatible = datasets.filter((d) =>
    page === "text"
      ? d.modality === "clinical_text"
      : ["forecast", "planning"].includes(page)
        ? d.modality === "demand"
        : page === "research"
          ? ["weight", "tabular"].includes(d.modality)
          : [
              "ehr",
              "weight",
              "tabular",
              ...(page === "overview" ? ["demand"] : []),
            ].includes(d.modality),
  );
  return (
    <div className="shell">
      <aside className={mobile ? "sidebar open" : "sidebar"}>
        <a className="brand" href="#" onClick={() => navigate("dashboard")}>
          <span className="brand-icon">
            <Activity size={27} />
          </span>
          <span>
            DermaInsight
            <span className="brand-small">AI research platform</span>
          </span>
        </a>
        <div className="workspace">
          <i /> Local research workspace
        </div>
        <nav aria-label="Research modules">
          {modules.map((m, i) => (
            <div key={m.id}>
              {[0, 6, 9, 13].includes(i) && (
                <div className="nav-group">
                  {i === 0
                    ? "Biomedical research"
                    : i === 6
                      ? "Data & language"
                      : i === 9
                        ? "Healthcare analytics"
                        : "Workspace"}
                </div>
              )}
              <button
                aria-current={page === m.id ? "page" : undefined}
                className={page === m.id ? "nav-item active" : "nav-item"}
                onClick={() => navigate(m.id)}
              >
                <m.icon size={17} />
                {m.name}
                {page === m.id && <ChevronRight size={14} />}
              </button>
            </div>
          ))}
        </nav>
        <div className="sidebar-foot">
          <ShieldCheck size={18} />
          <div>
            Research use only<small>Clinical validation not established</small>
          </div>
        </div>
      </aside>
      <main>
        <header className="topbar">
          <button
            className="icon-button mobile-toggle"
            aria-label="Toggle navigation"
            onClick={() => setMobile(!mobile)}
          >
            <Menu />
          </button>
          <span className="breadcrumb">
            Workspace <ChevronRight size={14} /> {current.name}
          </span>
          <div className="connection">
            <i className={status ? "online" : ""} />
            {status ? "API connected" : "API not connected"}
          </div>
          {token && (
            <button
              className="icon-button"
              aria-label="Lock workspace"
              onClick={() => {
                setToken("");
                setStatus(null);
                setDatasets([]);
                setRuns([]);
                setResult(null);
              }}
            >
              <LogOut size={17} />
            </button>
          )}
        </header>
        <div className="content">
          <div className="page-heading">
            <div>
              <p className="kicker">DermaInsight AI</p>
              <h1>{current.name}</h1>
              <p>{descriptions[page]}</p>
            </div>
            <span className="badge">Academic research</span>
          </div>
          {!token ? (
            <section className="access-panel">
              <ShieldCheck size={34} />
              <h2>Open your research workspace</h2>
              <p>
                Enter the local API access token configured in your environment.
                Authorized, de-identified datasets only.
              </p>
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  setToken(entry);
                  setEntry("");
                }}
              >
                <label htmlFor="token">Research access token</label>
                <input
                  id="token"
                  type="password"
                  value={entry}
                  onChange={(e) => setEntry(e.target.value)}
                  minLength={24}
                  required
                  autoComplete="off"
                />
                <button className="primary">Connect workspace</button>
              </form>
              <small>
                Token stays in memory and clears when this page closes.
              </small>
            </section>
          ) : (
            <>
              {error && (
                <div className="error" role="alert">
                  <AlertCircle size={18} />
                  {error}
                </div>
              )}
              {page === "dashboard" && (
                <>
                  <section className="overview-banner">
                    <div>
                      <span className="badge pale">
                        Evidence before conclusions
                      </span>
                      <h2>
                        A clear view of your
                        <br />
                        research, from source to result.
                      </h2>
                      <p>
                        Process images, inspect data and compare methods in one
                        traceable workspace. Start with your approved source
                        data.
                      </p>
                      <button
                        className="primary"
                        onClick={() => navigate("datasets")}
                      >
                        <Upload size={16} /> Import a dataset
                      </button>
                      <button
                        className="text-button"
                        onClick={() => navigate("image")}
                      >
                        Open image laboratory <ChevronRight size={16} />
                      </button>
                    </div>
                    <div className="research-mark" aria-hidden="true">
                      <Microscope size={110} strokeWidth={0.9} />
                      <span>Observe. Measure. Verify.</span>
                    </div>
                  </section>
                  <section className="metrics">
                    {[
                      [
                        Database,
                        status?.datasets ?? "—",
                        "Imported datasets",
                        "Authorized source files",
                      ],
                      [
                        ScanLine,
                        status?.processed_images ?? "—",
                        "Processed images",
                        "Completed algorithm runs",
                      ],
                      [
                        Check,
                        status?.completed_runs ?? "—",
                        "Completed analyses",
                        "Persisted execution results",
                      ],
                      [
                        BrainCircuit,
                        status?.model_available
                          ? "Configured"
                          : "Awaiting model",
                        "Lesion classifier",
                        "No prediction substitute",
                      ],
                    ].map(([Icon, v, label, note], i) => {
                      const I = Icon as typeof Database;
                      return (
                        <div key={i}>
                          <I />
                          <strong className={i === 3 ? "word-stat" : ""}>
                            {v as string}
                          </strong>
                          <span>{label as string}</span>
                          <small>{note as string}</small>
                        </div>
                      );
                    })}
                  </section>
                  <div className="dashboard-grid">
                    <section className="panel">
                      <div className="section-title">
                        <h2>Research pathways</h2>
                        <span className="muted">Choose a workflow</span>
                      </div>
                      {[
                        {
                          id: "image",
                          name: "Biomedical image laboratory",
                          text: "Enhancement, masks, compression and comparisons",
                          icon: ScanLine,
                        },
                        {
                          id: "preprocess",
                          name: "EHR & data quality",
                          text: "Missing values, schemas and transformation history",
                          icon: Database,
                        },
                        {
                          id: "text",
                          name: "Clinical text exploration",
                          text: "Classification, clustering and document retrieval",
                          icon: FileText,
                        },
                        {
                          id: "forecast",
                          name: "Demand & capacity planning",
                          text: "Temporal baselines and explicit resource scenarios",
                          icon: TrendingUp,
                        },
                      ].map((m) => (
                        <button
                          key={m.id}
                          className="pathway"
                          onClick={() => navigate(m.id)}
                        >
                          <span className="pathway-icon">
                            <m.icon size={22} />
                          </span>
                          <span>
                            <strong>{m.name}</strong>
                            <small>{m.text}</small>
                          </span>
                          <ChevronRight size={18} />
                        </button>
                      ))}
                    </section>
                    <section className="panel availability">
                      <h2>Data readiness</h2>
                      <p>
                        Availability reflects imports, not clinical validation.
                      </p>
                      {[
                        ["ehr", "EHR records"],
                        ["clinical_text", "Clinical documents"],
                        ["demand", "Patient arrival history"],
                        ["weight", "Adult weight & behavior"],
                      ].map(([key, name]) => (
                        <div className="readiness" key={key}>
                          <span>{name}</span>
                          <span
                            className={
                              status?.modalities?.[key]
                                ? "badge green"
                                : "badge"
                            }
                          >
                            {status?.modalities?.[key]
                              ? "Available"
                              : "Not imported"}
                          </span>
                        </div>
                      ))}
                      <p className="notice">
                        No dataset? Run classical image algorithms on an
                        authorized local image.
                      </p>
                    </section>
                  </div>
                </>
              )}
              {["image", "registration", "inference"].includes(page) && (
                <section className="panel">
                  <div className="section-title">
                    <h2>
                      {page === "registration"
                        ? "Register two related images"
                        : page === "inference"
                          ? "Research lesion prediction"
                          : "Process an image"}
                    </h2>
                    <span className="badge">Real algorithm execution</span>
                  </div>
                  {page === "inference" && !status?.model_available ? (
                    <div className="empty">
                      <BrainCircuit size={35} />
                      <h3>A trained lesion model is required</h3>
                      <p>
                        Provide licensed images with genuine labels and
                        patient/lesion groups. Train, review held-out results
                        and configure DERMA_MODEL_DIR. Inference remains
                        disabled until then.
                      </p>
                      <button onClick={() => navigate("training")}>
                        View model requirements
                      </button>
                    </div>
                  ) : (
                    <form onSubmit={(e) => void submit(e, page)}>
                      <div className="upload-zone">
                        <Upload size={28} />
                        <h3>
                          {page === "registration"
                            ? "Choose overlapping images"
                            : "Choose your research image"}
                        </h3>
                        <p>
                          PNG, JPEG or WebP · up to 20 MiB · no patient
                          identifiers
                        </p>
                        <label>
                          {page === "registration" ? "First image" : "Image"}
                          <input
                            name={page === "registration" ? "first" : "file"}
                            type="file"
                            accept="image/png,image/jpeg,image/webp"
                            required
                          />
                        </label>
                        {page === "registration" && (
                          <label>
                            Second image
                            <input
                              name="second"
                              type="file"
                              accept="image/png,image/jpeg,image/webp"
                              required
                            />
                          </label>
                        )}
                      </div>
                      {page === "image" && (
                        <div className="form-grid">
                          <label>
                            Processing method
                            <select
                              value={method}
                              onChange={(e) => setMethod(e.target.value)}
                            >
                              {[
                                "clahe",
                                "contrast",
                                "equalize",
                                "gamma",
                                "gray_world",
                                "gaussian",
                                "median",
                                "bilateral",
                                "denoise",
                                "threshold",
                                "otsu",
                                "edges",
                                "morphology",
                                "grabcut",
                                "jpeg",
                                "png",
                                "webp",
                              ].map((m) => (
                                <option key={m}>{m}</option>
                              ))}
                            </select>
                          </label>
                          <label>
                            Optional reference mask
                            <input type="file" name="mask" accept="image/png" />
                          </label>
                          <label className="full">
                            Algorithm parameters (JSON)
                            <textarea
                              value={parameters}
                              onChange={(e) => setParameters(e.target.value)}
                            />
                            <small>
                              kernel (odd 1–31), gamma (0.1–5), clip (0–20),
                              threshold (0–255), quality (1–100).
                            </small>
                          </label>
                        </div>
                      )}
                      <p className="notice">
                        {page === "registration"
                          ? "SIFT finds local structure; RANSAC estimates geometry. Neither diagnoses cancer. Unsuitable image pairs fail explicitly."
                          : page === "inference"
                            ? "Uncalibrated research scores, never confirmed diagnoses. Image and prediction are not retained."
                            : "Generated images and parameters are retained in local run history. Original pixels and generated results are retained; original encoded files and EXIF are not retained. Masks require clinical validation."}
                      </p>
                      {page === "inference" && (
                        <label className="check-label">
                          <input name="explain" type="checkbox" value="true" />
                          Compute actual Grad-CAM explanation
                        </label>
                      )}
                      <button className="primary" disabled={busy}>
                        {busy
                          ? "Executing…"
                          : page === "registration"
                            ? "Extract features & register"
                            : page === "inference"
                              ? "Run research inference"
                              : "Run image processing"}
                      </button>
                    </form>
                  )}
                </section>
              )}
              {page === "datasets" && (
                <>
                  <section className="panel">
                    <h2>Import a research dataset</h2>
                    <p>
                      Independent modalities, immutable source files and
                      recorded checksums.
                    </p>
                    <form
                      onSubmit={(e) => void submit(e, "datasets")}
                      className="form-grid"
                    >
                      <label>
                        Dataset file
                        <input
                          type="file"
                          name="file"
                          accept=".csv,.xlsx"
                          required
                        />
                      </label>
                      <label>
                        Modality
                        <select name="modality">
                          {[
                            "ehr",
                            "clinical_text",
                            "demand",
                            "weight",
                            "tabular",
                          ].map((v) => (
                            <option key={v}>{v}</option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Source URL / citation
                        <input name="source" required />
                      </label>
                      <label>
                        License / authorization
                        <input name="license" required />
                      </label>
                      <label className="check-label full">
                        <input
                          type="checkbox"
                          name="authorized"
                          value="true"
                          required
                        />
                        I confirm authorized, appropriately de-identified
                        research use. This does not automatically remove
                        identifiers.
                      </label>
                      <button className="primary" disabled={busy}>
                        {busy ? "Validating…" : "Validate & import"}
                      </button>
                    </form>
                  </section>
                  <section className="panel">
                    <div className="section-title">
                      <h2>Dataset registry</h2>
                      <input
                        aria-label="Search datasets"
                        placeholder="Filter filename"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                      />
                    </div>
                    {datasets.length ? (
                      <div className="table-wrap">
                        <table>
                          <thead>
                            <tr>
                              <th>Dataset</th>
                              <th>Modality</th>
                              <th>Rows</th>
                              <th>Source</th>
                            </tr>
                          </thead>
                          <tbody>
                            {datasets
                              .filter((d) =>
                                d.name
                                  .toLowerCase()
                                  .includes(query.toLowerCase()),
                              )
                              .map((d) => (
                                <tr key={d.id}>
                                  <td>
                                    <button onClick={() => setResult(d)}>
                                      {d.name}
                                    </button>
                                  </td>
                                  <td>{d.modality}</td>
                                  <td>{d.profile.rows}</td>
                                  <td>{d.source}</td>
                                </tr>
                              ))}
                          </tbody>
                        </table>
                      </div>
                    ) : (
                      <p className="empty">
                        No datasets imported. Add an approved CSV or XLSX.
                      </p>
                    )}
                  </section>
                </>
              )}
              {[
                "preprocess",
                "text",
                "forecast",
                "planning",
                "reduce",
                "research",
                "overview",
              ].includes(page) && (
                <section className="panel">
                  <h2>
                    Configure{" "}
                    {page === "planning" ? "capacity scenario" : "analysis"}
                  </h2>
                  {!compatible.length ? (
                    <div className="empty">
                      <Database size={34} />
                      <h3>Waiting for a compatible dataset</h3>
                      <p>
                        {["forecast", "planning"].includes(page)
                          ? "Provide at least 28 complete daily observations (date,count). Lesion images cannot supply arrival history."
                          : page === "text"
                            ? "Import authorized, de-identified notes; classification requires genuine labels."
                            : "Import an appropriate real dataset with dictionary, units and provenance."}
                      </p>
                      <button
                        className="primary"
                        onClick={() => navigate("datasets")}
                      >
                        Import dataset
                      </button>
                    </div>
                  ) : (
                    <form onSubmit={(e) => void submit(e, page)}>
                      <label>
                        Source dataset
                        <select
                          required
                          value={selected}
                          onChange={(e) => setSelected(e.target.value)}
                        >
                          <option value="">Select dataset</option>
                          {compatible.map((d) => (
                            <option key={d.id} value={d.id}>
                              {d.name} ({d.profile.rows} rows)
                            </option>
                          ))}
                        </select>
                      </label>
                      {ds && (
                        <div className="schema">
                          <h3>Available columns</h3>
                          {ds.profile.columns.map((c) => (
                            <span className="badge" key={c.name}>
                              {c.name} · {c.dtype} · {c.missing} missing
                            </span>
                          ))}
                        </div>
                      )}
                      {page === "text" && (
                        <div className="form-grid">
                          <label>
                            Task
                            <select name="task">
                              <option value="cluster">Cluster documents</option>
                              <option value="classify">
                                Classify labeled notes
                              </option>
                              <option value="search">Rank documents</option>
                              <option value="disambiguate">
                                Context-labeled sense ranking
                              </option>
                              <option value="ner">
                                Clinical NER (model required)
                              </option>
                            </select>
                          </label>
                          <label>
                            Text column
                            <input
                              name="text_column"
                              defaultValue="text"
                              required
                            />
                          </label>
                          <label>
                            Genuine label column
                            <input name="label_column" defaultValue="label" />
                          </label>
                          <label>
                            Search query
                            <input name="query" />
                          </label>
                        </div>
                      )}
                      {page === "overview" && (
                        <div className="form-grid">
                          <label>
                            Optional date column
                            <input name="date_column" />
                          </label>
                          <label>
                            Optional observed count column
                            <input name="count_column" />
                          </label>
                          <label>
                            Optional grouping column
                            <input name="group_column" />
                          </label>
                          <label>
                            Start date
                            <input name="start_date" type="date" />
                          </label>
                          <label>
                            End date
                            <input name="end_date" type="date" />
                          </label>
                        </div>
                      )}
                      {["forecast", "planning"].includes(page) && (
                        <div className="form-grid">
                          <label>
                            Date column
                            <input
                              name="date_column"
                              defaultValue="date"
                              required
                            />
                          </label>
                          <label>
                            Arrival count column
                            <input
                              name="count_column"
                              defaultValue="count"
                              required
                            />
                          </label>
                          <label>
                            Horizon (days)
                            <input
                              name="horizon"
                              type="number"
                              min={1}
                              max={90}
                              defaultValue={7}
                              required
                            />
                          </label>
                          <label>
                            Optional patients per staff per shift
                            <input
                              name="capacity"
                              type="number"
                              min="0.01"
                              step="any"
                              placeholder="Your operational assumption"
                            />
                          </label>
                        </div>
                      )}
                      {["reduce", "research"].includes(page) && (
                        <div className="form-grid">
                          <label>
                            Numeric feature columns (comma separated)
                            <input name="features" required />
                          </label>
                          {page === "reduce" ? (
                            <label>
                              Method
                              <select name="reduction">
                                <option value="pca">PCA</option>
                                <option value="tsne">t-SNE</option>
                              </select>
                            </label>
                          ) : (
                            <label>
                              Observed numeric outcome
                              <input name="target" required />
                            </label>
                          )}
                        </div>
                      )}
                      <label>
                        Advanced parameters (JSON)
                        <textarea
                          value={parameters}
                          onChange={(e) => setParameters(e.target.value)}
                        />
                      </label>
                      {page === "preprocess" && (
                        <details>
                          <summary>Transformation configuration guide</summary>
                          <pre>
                            {JSON.stringify(
                              {
                                normalize_columns: true,
                                types: { column: "numeric" },
                                date_formats: { date: "%Y-%m-%d" },
                                categories: {},
                                units: {},
                                ranges: {},
                                drop_exact_duplicates: false,
                                duplicate_keys: [],
                                impute: {},
                              },
                              null,
                              2,
                            )}
                          </pre>
                          <p>
                            Use actual columns. Keys flag repeated records for
                            review; only exact full-row duplicates are removed.
                            Unit conversions require factor, offset, from and
                            to. Ranges flag values without silently changing
                            them.
                          </p>
                        </details>
                      )}
                      <p className="notice">
                        {page === "research"
                          ? "Unweighted observational associations only. Verify adult inclusion, confounders and repeated-person groups. No causal claims."
                          : page === "planning"
                            ? "Capacity scenarios use your assumptions and are not staffing prescriptions."
                            : page === "reduce"
                              ? "Visual separation does not establish clinical validity."
                              : "Source data stays unchanged. Results and parameters are recorded."}
                      </p>
                      <button className="primary" disabled={busy || !selected}>
                        {busy ? "Running…" : "Execute analysis"}
                      </button>
                    </form>
                  )}
                </section>
              )}
              {page === "training" && (
                <section className="panel">
                  <span className="badge">CLI pipeline implemented</span>
                  <h2>Train on genuine labeled images</h2>
                  <button
                    onClick={async () => {
                      try {
                        setResult(await api("/models/current"));
                      } catch (e) {
                        setError((e as Error).message);
                      }
                    }}
                  >
                    Review configured model artifacts
                  </button>
                  <p>
                    No lesion model has been trained. Compare architectures
                    using validation results, then evaluate independent test
                    groups.
                  </p>
                  <ol className="steps">
                    <li>
                      Review license; place images in an ignored local
                      directory.
                    </li>
                    <li>
                      Create CSV columns <code>image_path,label,group_id</code>;
                      minimum five independent groups per class.
                    </li>
                    <li>
                      Document patient vs lesion grouping. Duplicate bytes
                      across groups are rejected.
                    </li>
                    <li>
                      Train and review history, manifest, confusion matrix and
                      held-out metrics.
                    </li>
                    <li>
                      Configure DERMA_MODEL_DIR only after artifact review.
                    </li>
                  </ol>
                  <pre>
                    python -m scripts.train --metadata
                    data/raw/lesions/metadata.csv --images
                    data/raw/lesions/images --output artifacts/experiment-01
                    --architecture small_cnn --epochs 5
                  </pre>
                  <p className="notice">
                    Architectures: small_cnn, resnet18, efficientnet_b0.
                    ImageNet download requires --pretrained. CPU supported.
                    Grad-CAM uses actual activations/gradients when requested
                    during inference. Web training orchestration and external
                    clinical validation are not implemented yet.
                  </p>
                </section>
              )}
              {["reports", "visualization"].includes(page) && (
                <section className="panel">
                  <div className="section-title">
                    <h2>Persisted execution artifacts</h2>
                    <button onClick={() => void refresh()}>Refresh</button>
                  </div>
                  {runs.length ? (
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            <th>Analysis</th>
                            <th>Status</th>
                            <th>Created</th>
                            <th>Actions</th>
                          </tr>
                        </thead>
                        <tbody>
                          {runs.map((r) => (
                            <tr key={r.id}>
                              <td>{r.kind}</td>
                              <td>
                                <span
                                  className={
                                    r.status === "completed"
                                      ? "badge green"
                                      : "badge"
                                  }
                                >
                                  {r.status}
                                </span>
                                {r.error && <small>{r.error}</small>}
                              </td>
                              <td>{new Date(r.created_at).toLocaleString()}</td>
                              <td>
                                <button
                                  onClick={async () => {
                                    try {
                                      setResult(await api("/runs/" + r.id));
                                    } catch (e) {
                                      setError((e as Error).message);
                                    }
                                  }}
                                >
                                  Inspect
                                </button>
                                {r.status === "completed" && (
                                  <button onClick={() => void exportRun(r.id)}>
                                    JSON
                                  </button>
                                )}
                                {r.kind === "preprocess" &&
                                  r.status === "completed" && (
                                    <button
                                      onClick={() =>
                                        void exportRun(r.id, "csv")
                                      }
                                    >
                                      CSV
                                    </button>
                                  )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="empty">
                      <FolderDown size={34} />
                      <h3>No execution artifacts yet</h3>
                      <p>
                        Run an image algorithm or import an approved dataset.
                      </p>
                    </div>
                  )}
                </section>
              )}
              {page === "settings" && (
                <section className="panel">
                  <h2>Environment & scientific readiness</h2>
                  <p>
                    Availability is separate from clinical validation. Access
                    uses a local single-owner token, not production multi-user
                    identity management.
                  </p>
                  <pre>{JSON.stringify(status, null, 2)}</pre>
                  <h3>Required inputs</h3>
                  <ul>
                    <li>
                      Licensed lesion images, labels and patient/lesion
                      grouping.
                    </li>
                    <li>Expert masks for segmentation evaluation.</li>
                    <li>Authorized EHR tables and clinical notes.</li>
                    <li>Daily operational arrivals and staffing policies.</li>
                    <li>Adult weight/behavior data and study dictionary.</li>
                    <li>
                      Licensed clinical NER and contextual terminology models.
                    </li>
                  </ul>
                  <button onClick={() => void refresh()}>
                    Refresh service status
                  </button>
                </section>
              )}
              {busy && (
                <p role="status" className="notice">
                  Executing. Keep this page open; large analyses may take time.
                </p>
              )}
              {result && (
                <>
                  <Results value={result} />
                  {result.id && result.status === "completed" && (
                    <button onClick={() => void exportRun(result.id)}>
                      Export report
                    </button>
                  )}
                </>
              )}
            </>
          )}
          <footer>
            <ShieldCheck size={16} />
            <span>
              For research and education. Predictions are not confirmed
              diagnoses. Authorized, de-identified data only.
            </span>
          </footer>
        </div>
      </main>
    </div>
  );
}
