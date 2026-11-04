"use client";
import type { ReactNode } from "react";

type Dataset = {
  id: string;
  name: string;
  modality: string;
  profile: { rows: number };
};

type Props = {
  page: string;
  datasets: Dataset[];
  modelReady: boolean;
  onNavigate: (page: string, datasetId?: string) => void;
};

const guides: Record<
  string,
  {
    tutorial: string;
    title: string;
    purpose: string;
    steps: string[];
    inputs: string[];
  }
> = {
  datasets: {
    tutorial: "T1",
    title: "Understand the patient and encounter tables",
    purpose: "Inspect EHR fields, records and how tables link together.",
    steps: [
      "Use the MIMIC-IV Demo tables already in the registry; no import is needed for the walkthrough.",
      "Click a table name to inspect its schema and summary. Use Browse and filter source records to view rows.",
      "Expand the relationship tool to validate how admissions link to patients.",
    ],
    inputs: [
      "Patients → admissions: child key subject_id; parent key subject_id.",
      "Diagnoses → admissions: child key hadm_id; parent key hadm_id.",
      "For a new file, provide its real source and license. Do not copy MIMIC details onto another dataset.",
    ],
  },
  preprocess: {
    tutorial: "T2–T3",
    title: "Clean a table without changing its source",
    purpose:
      "The MIMIC admissions table is selected as a ready example. Review types, missing values and duplicates before running.",
    steps: [
      "The MIMIC-IV admissions example is selected; choose another registered table only if you want.",
      "Read the available column names and types shown below the selector.",
      "Open Transformation configuration guide for settings; use actual column names and run the analysis.",
    ],
    inputs: [
      "Transform settings go in Advanced parameters (JSON). Leave a setting out if you are unsure.",
      "A repeated patient can have legitimate encounters. Do not deduplicate by patient ID alone.",
      "The source file stays unchanged; the transformed result is a separate artifact.",
    ],
  },
  image: {
    tutorial: "T4",
    title: "Run an image-processing method",
    purpose:
      "A real public ISIC practice image and fast CLAHE method are ready by default.",
    steps: [
      "The built-in ISIC image is selected; choose your own image from Image source if needed.",
      "CLAHE is selected as a quick first method. Other image methods remain available.",
      "The parameter defaults are ready. Choose Run image processing.",
    ],
    inputs: [
      "The local public example is data/raw/isic2018-task3/images/ISIC_0024309.jpg.",
      "Optional reference masks are for comparing segmentation only; they are not diagnoses.",
      "The original image and generated output are kept in local run history; avoid identifiable patient images.",
    ],
  },
  registration: {
    tutorial: "T5",
    title: "Compare two related images",
    purpose:
      "SIFT finds matching visual features; RANSAC estimates how one image aligns with the other.",
    steps: [
      "Upload two images that show shared visual structure.",
      "Select Extract features & register.",
      "Review keypoints, matches, inliers and the alignment. Unsuitable pairs can fail explicitly.",
    ],
    inputs: [
      "Use related views or versions of the same scene for a useful registration example.",
      "SIFT and RANSAC align images; they do not detect or diagnose cancer.",
    ],
  },
  training: {
    tutorial: "T5",
    title: "Check the model before starting a new training run",
    purpose:
      "Training needs the complete labeled lesion image set and can take time, especially on CPU.",
    steps: [
      "Check whether a model is already selected. If so, use Lesion detection for an image result.",
      "Check dataset readiness before starting a new experiment.",
      "Review validation and held-out test evidence before selecting an artifact.",
    ],
    inputs: [
      "The training source is configured by the project; you do not upload training images in this form.",
      "ImageNet weights are general image features, not a skin-lesion model.",
      "A new experiment does not automatically replace the selected model.",
    ],
  },
  inference: {
    tutorial: "T5",
    title: "Run the lesion research classifier",
    purpose:
      "The model scores the uploaded image against its seven learned dataset classes.",
    steps: [
      "The built-in ISIC research image is selected; use Image source to pick your own instead.",
      "Optionally check Compute actual Grad-CAM explanation.",
      "Leave score retention unchecked for an ephemeral run, then choose Run research inference.",
    ],
    inputs: [
      "For a project example, choose data/raw/isic2018-task3/images/ISIC_0024309.jpg.",
      "Scores are uncalibrated research outputs, not a diagnosis or clinical confidence.",
      "Do not use this application to decide care or treatment.",
    ],
  },
  visualization: {
    tutorial: "T6",
    title: "View charts and saved results",
    purpose:
      "Charts and images come from completed analyses; this page does not create new data.",
    steps: [
      "Run an image, model, text or analytics workflow first.",
      "Open Biomedical visualization or Reports & history.",
      "Choose Inspect to view a run, or JSON to export its recorded result.",
    ],
    inputs: [
      "No new input is required here.",
      "Grad-CAM is an activation visualization, not a clinically validated explanation.",
    ],
  },
  forecast: {
    tutorial: "T7",
    title: "Forecast the public daily admissions series",
    purpose:
      "Estimate future daily admissions, compare forecasting methods, and explain how far past predictions missed.",
    steps: [
      "Select the preloaded UKHSA England COVID admissions dataset.",
      "Use date for Date column, count for Observed count column, and 7 for Horizon.",
      "After running, read the daily estimate and past-error range; use the summary cards for the forecast period and highest estimated day.",
      "In the model comparison, MAE is the typical size of a miss and RMSE penalizes especially large misses. Lower is better.",
      "Leave staffing fields empty unless you have approved operational assumptions.",
    ],
    inputs: [
      "This is 120 days of national admissions data, not your hospital's patient arrivals.",
      "A forecast from this dataset cannot support local staffing recommendations.",
    ],
  },
  overview: {
    tutorial: "T8",
    title: "Summarize observed healthcare records",
    purpose:
      "Count the selected source records, describe monthly totals, and compare recorded categories.",
    steps: [
      "For a quick example, choose MIMIC-IV public demo 2.2: admissions.",
      "To chart monthly admissions, set Date column to admittime.",
      'Set Advanced parameters to {"date_format":"%Y-%m-%d %H:%M:%S"}; leave count blank to count source rows.',
      "After running, read Rows included and Calculated total first; then compare the monthly and category summaries.",
    ],
    inputs: [
      "The output shows each mapped source column, total-by-category table, and share of the calculated total.",
      "A source-row count is not automatically a unique patient count or hospital-wide statistic; one person may have multiple records.",
      "Start and end dates are optional filters on the observed records.",
    ],
  },
  planning: {
    tutorial: "T9",
    title: "Explore a forecast with explicit assumptions",
    purpose:
      "Separate historical data, forecast values and planning scenarios you define.",
    steps: [
      "Select the preloaded UKHSA dataset and keep date, count and 7-day horizon.",
      "Leave Named planning scenarios as [] to review the forecast without a staffing scenario.",
      "Only add a scenario when you have real staffing assumptions approved for your setting.",
    ],
    inputs: [
      "Scenario assumptions include patients per staff per shift; per-shift outputs also require shift hours and arrival fractions.",
      "No hospital staffing policy is preloaded, so the app does not invent a staffing recommendation.",
    ],
  },
  text: {
    tutorial: "T10–T12",
    title: "Explore the public clinical-text examples",
    purpose:
      "Group similar documents, check held-out text labels, highlight recognized medical terms, and search the public corpus.",
    steps: [
      "Cluster is selected by default. Run it to see document counts and common words for each group.",
      "Classification, search and NER use preloaded corpus text and matching columns. Their result panels explain scores, labels and outputs.",
      "Search defaults to BM25 and the query “patient”. Choose Clinical NER to see recognized spans and plain-language entity types.",
    ],
    inputs: [
      "Classification keeps excerpts from the same source document in one split. Its test examples show the dataset label beside the model label.",
      "The corpus contains published case reports, not hospital notes. Do not paste identifiable patient notes.",
      "The separate terminology panel needs an actual term and context from you; those values should not be invented.",
    ],
  },
  reduce: {
    tutorial: "T13",
    title: "Plot several measurements in two or three dimensions",
    purpose:
      "PCA or t-SNE turns selected numeric columns into coordinates for exploratory visualization.",
    steps: [
      "NHANES 2017–2018 adults is selected by default.",
      "Use age_years_topcoded80, female_reported, sedentary_minutes_day, sleep_weekday_hours_exact, meals_away_week_exact.",
      "Choose PCA and 3D for the simplest first run, then select Execute analysis.",
    ],
    inputs: [
      "Enter the five existing numeric column names separated by commas.",
      "A visual grouping is not proof of a medical category or clinical finding.",
    ],
  },
  research: {
    tutorial: "T14–T15",
    title: "Explore adult weight data and run a held-out research model",
    purpose:
      "Review descriptive data, then test how well selected observations predict BMI.",
    steps: [
      "NHANES 2017–2018 adults is selected by default.",
      "For Numeric feature columns, enter age_years_topcoded80, female_reported, sedentary_minutes_day, sleep_weekday_hours_exact, meals_away_week_exact.",
      "Set Observed numeric outcome to bmi_kg_m2 and choose Execute analysis.",
    ],
    inputs: [
      "Do not include participant_id or bmi_kg_m2 as a predictor.",
      "The data is unweighted and observational. The prior BMI model was weak and does not show causation.",
    ],
  },
  reports: {
    tutorial: "",
    title: "Find and export analyses you already ran",
    purpose:
      "Review completed, pending and failed runs with their recorded inputs and outputs.",
    steps: [
      "Choose Inspect to see a result.",
      "Choose JSON to export a completed run. Preprocessing runs also support CSV export.",
    ],
    inputs: ["No new input is required here."],
  },
  settings: {
    tutorial: "",
    title: "Check data and model readiness",
    purpose:
      "See which datasets, research models and local access settings are currently available.",
    steps: [
      "Review the status before choosing a workflow.",
      "Use Accounts and data access only if you need named local users.",
    ],
    inputs: [
      "Availability means an artifact or dataset is present; it does not mean clinical validation.",
    ],
  },
};

function ActionButton({
  children,
  onClick,
  secondary = false,
}: {
  children: ReactNode;
  onClick: () => void;
  secondary?: boolean;
}) {
  return (
    <button
      className={secondary ? "guide-action secondary" : "guide-action"}
      type="button"
      onClick={onClick}
    >
      {children}
    </button>
  );
}

export function StartHere({ datasets, onNavigate }: Props) {
  const pick = (modality: string, name?: string) =>
    datasets.find(
      (dataset) =>
        dataset.modality === modality && (!name || dataset.name.includes(name)),
    );
  const ehr = pick("ehr", "patients");
  const demand = pick("demand");
  const weight = pick("weight");
  const text = pick("clinical_text", "published clinical case reports");

  return (
    <section className="start-here" aria-labelledby="start-here-title">
      <div className="start-here-intro">
        <div>
          <span className="start-mark" aria-hidden="true">
            01
          </span>
        </div>
        <div>
          <h2 id="start-here-title">
            New here? Start with data already loaded.
          </h2>
          <p>
            Pick one short path. Each section explains what to enter and what
            the result means.
          </p>
        </div>
      </div>
      <div className="start-paths">
        <article>
          <h3>
            EHR tables <span>(T1)</span>
          </h3>
          <p>
            {ehr
              ? `${ehr.name} · ${ehr.profile.rows} rows`
              : "No EHR table is loaded yet."}
          </p>
          <ActionButton onClick={() => onNavigate("datasets")}>
            Open EHR walkthrough
          </ActionButton>
        </article>
        <article>
          <h3>
            Patient-demand forecast <span>(T7)</span>
          </h3>
          <p>
            {demand
              ? `${demand.name} · ${demand.profile.rows} days`
              : "No demand dataset is loaded yet."}
          </p>
          <ActionButton onClick={() => onNavigate("forecast", demand?.id)}>
            Open forecast walkthrough
          </ActionButton>
        </article>
        <article>
          <h3>
            Adult weight research <span>(T14–T15)</span>
          </h3>
          <p>
            {weight
              ? `${weight.name} · ${weight.profile.rows} adults`
              : "No adult weight dataset is loaded yet."}
          </p>
          <ActionButton onClick={() => onNavigate("research", weight?.id)}>
            Open weight walkthrough
          </ActionButton>
        </article>
        <article>
          <h3>
            Clinical text <span>(T10–T12)</span>
          </h3>
          <p>
            {text
              ? `${text.name} · ${text.profile.rows} documents`
              : "No clinical text dataset is loaded yet."}
          </p>
          <ActionButton onClick={() => onNavigate("text", text?.id)}>
            Open text walkthrough
          </ActionButton>
        </article>
        <article className="start-path-image">
          <h3>
            Lesion image tools <span>(T4–T6)</span>
          </h3>
          <p>
            Use an image you are authorized to analyze. No data table selection
            is needed.
          </p>
          <ActionButton secondary onClick={() => onNavigate("image")}>
            Open image lab
          </ActionButton>
          <ActionButton secondary onClick={() => onNavigate("inference")}>
            Open lesion research model
          </ActionButton>
        </article>
      </div>
      <p className="start-safety">
        Research and education only. Model outputs are not confirmed diagnoses
        or care advice.
      </p>
    </section>
  );
}

export default function SectionGuide({
  page,
  datasets,
  modelReady,
  onNavigate,
}: Props) {
  const guide = guides[page];
  if (!guide) return null;
  const content =
    page === "training"
      ? {
          ...guide,
          title: modelReady
            ? "The trained classifier is ready to use"
            : "Train only after checking the data",
          purpose: modelReady
            ? "A research classifier is already selected. Use Lesion detection to run it; training is for a new experiment."
            : "Training needs the complete labeled lesion image set and takes time, especially on CPU.",
          steps: modelReady
            ? [
                "For a demo, open Lesion detection and upload a research image.",
                "Use this page only when you intend to start and review a new training run.",
              ]
            : [
                "Check dataset readiness first.",
                "Choose training settings only when the full labeled image source is available.",
                "Review validation and held-out test evidence before selecting an artifact.",
              ],
        }
      : guide;
  const available = datasets.filter((dataset) => {
    if (page === "forecast" || page === "planning")
      return dataset.modality === "demand";
    if (page === "research")
      return ["weight", "tabular"].includes(dataset.modality);
    if (page === "text") return dataset.modality === "clinical_text";
    if (page === "overview")
      return ["ehr", "demand", "weight", "tabular", "clinical_text"].includes(
        dataset.modality,
      );
    if (page === "preprocess")
      return ["ehr", "weight", "tabular"].includes(dataset.modality);
    if (page === "reduce")
      return ["ehr", "weight", "tabular"].includes(dataset.modality);
    return true;
  });
  const jumpTarget =
    page === "overview" || page === "preprocess" ? "datasets" : page;

  return (
    <section className="section-guide" aria-labelledby="section-guide-title">
      <div className="section-guide-heading">
        <div>
          {content.tutorial && (
            <span className="guide-tutorial">{content.tutorial}</span>
          )}
          <h2 id="section-guide-title">{content.title}</h2>
          <p>{content.purpose}</p>
        </div>
        {page !== "datasets" &&
          page !== "image" &&
          page !== "inference" &&
          page !== "registration" &&
          page !== "training" &&
          page !== "visualization" &&
          page !== "reports" &&
          page !== "settings" && (
            <span
              className={
                available.length
                  ? "guide-data-status ready"
                  : "guide-data-status"
              }
            >
              {available.length
                ? `${available.length} compatible dataset${available.length === 1 ? "" : "s"} loaded`
                : "No compatible dataset loaded"}
            </span>
          )}
      </div>
      <div className="section-guide-columns">
        <div>
          <h3>What to do</h3>
          <ol>
            {content.steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>
        </div>
        <div>
          <h3>What to enter or expect</h3>
          <ul>
            {content.inputs.map((input) => (
              <li key={input}>{input}</li>
            ))}
          </ul>
        </div>
      </div>
      {page === "datasets" && (
        <div className="guide-import-note">
          <strong>Importing your own file?</strong> Select its CSV, XLSX or
          supported FHIR JSON file, choose the right modality, enter the actual
          source citation and license, and confirm only if your data is
          authorized and de-identified. For the existing MIMIC Demo, the source
          is{" "}
          <a
            href="https://physionet.org/content/mimic-iv-demo/2.2/"
            target="_blank"
            rel="noreferrer"
          >
            PhysioNet MIMIC-IV Demo 2.2
          </a>{" "}
          and the dataset license is ODbL 1.0. You do not need to import it
          again.
        </div>
      )}
      {available.length === 0 &&
        [
          "overview",
          "preprocess",
          "forecast",
          "planning",
          "research",
          "reduce",
          "text",
        ].includes(page) && (
          <ActionButton secondary onClick={() => onNavigate(jumpTarget)}>
            Open dataset manager
          </ActionButton>
        )}
    </section>
  );
}
