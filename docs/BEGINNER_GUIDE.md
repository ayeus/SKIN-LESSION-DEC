# DermaInsight AI: beginner guide

DermaInsight AI is a local academic research app. It has separate sections for image algorithms, EHR tables, clinical text and healthcare analytics. It does not make medical diagnoses. Use the preloaded public research datasets for the walkthrough; do not upload identifiable patient information.

## Open the app

The app runs in your browser at <http://127.0.0.1:3000> when the API and web server are running.

If the app is stopped, open Terminal in the project folder. Run the backend in one window:

```sh
.venv/bin/python -m scripts.serve
```

Run the web app in a second window:

```sh
cd frontend
npm run dev
```

Open <http://127.0.0.1:3000>. At the sign-in page, copy the value after `DERMA_API_TOKEN=` from the private root `.env` file. Keep it private.

## Start with the dashboard

After connecting, the dashboard shows **Start with data already loaded**. Pick a path there. Every section also displays a short guide above its forms. The tutorial tags in the sidebar show which tutorial each section covers. When you open a module, the app preselects a compatible dataset and fills known example columns and quick-start settings. Review them, then press **Run**; you do not have to type the examples below again.

### T1 — EHR tables

1. Open **EHR & dataset management (T1)**.
2. The following MIMIC-IV Demo tables are already loaded: patients, admissions, and diagnoses with their dictionary. You do not need to import them again.
3. Click a table name in the registry to inspect its schema and summary. Use **Browse and filter source records** to view rows.
4. Expand **Inspect patient / encounter table relationships**. The admissions child table, patients parent table, and both `subject_id` keys are preselected. Choose **Inspect relationship**.

For your own file, import only data you are allowed to use. Select its file, choose the correct modality, cite its actual source, enter its actual license or authorization, and confirm that it is appropriately de-identified. These fields intentionally need your real information and are not prefilled. Do not copy MIMIC's source or license for a different file.

### T2 and T3 — Preprocessing, duplicates, and missing data

1. Open **Data preprocessing (T2–T3)**. The MIMIC-IV admissions table is selected automatically; you can change to a compatible registered EHR, weight, or tabular dataset.
2. Read the column list and missing-value counts under the dataset selector.
3. Expand **Transformation configuration guide**. Use only real column names from the selected dataset; enter chosen settings as JSON under **Advanced parameters**.
4. Run the analysis and inspect the before/after report. The original source is preserved.

For a first look, leave the advanced settings as `{}` and inspect the reported transformation and data quality. Do not remove rows just because they have the same patient ID; repeat visits can be valid records.

### T4 — Image processing

1. Open **Image processing lab (T4)**.
2. The built-in ISIC 2018 research image `ISIC_0024309.jpg` is selected automatically. You can switch **Image source** to **Choose my own image** to use a local PNG, JPEG, or WebP (up to 20 MiB).
3. CLAHE is selected as a quick starting method. Keep the default parameters and select **Run image processing**. Compare the original, processed image, mask, and histogram.

### T5 — Image registration and lesion classification

T5 appears in three sidebar sections because it covers three different image methods:

- **SIFT & RANSAC:** upload two related images with shared visual features, then choose **Extract features & register**. It shows matches and the estimated alignment; it does not classify a lesion.
- **Lesion detection:** the built-in ISIC practice image is preselected. Optionally check **Compute actual Grad-CAM explanation**, leave score retention unchecked for an ephemeral run, then choose **Run research inference**. You may switch the image source to upload your own. The sample was in this model's held-out image split, so this walkthrough is not independent evaluation. The output is a top-ranked research label and uncalibrated class scores, not a diagnosis.
- **CNN training & evaluation:** the project already has a selected research classifier. Use Lesion detection for a prediction. Open the training page only when you intend to start another experiment; training uses the configured dataset and can take time.

### T6 — Visualizations

Run an image, model, text, or analytics workflow first. Then open **Biomedical visualization (T6)** or **Reports & history**. Select **Inspect** to view a completed run or **JSON** to export its report. This section visualizes real results; it does not create new observations.

### T7 — Patient-demand forecasting

1. Open **Patient demand (T7)**. The public UKHSA England COVID admissions dataset is already available and selected automatically.
2. The columns `date` and `count` and a 7-day horizon are prefilled.
3. Select **Execute analysis**. Leave staffing fields empty unless you have real, approved assumptions.

The results summarize how many days are forecast, the estimated total across that period, the highest estimated day, and the last observed day. A daily table gives the rounded estimate plus lower and upper bounds based on past model errors. The model comparison explains which method was selected and what MAE and RMSE mean; lower error is better. The chart legend spells out recorded counts, model estimates, and past-error bounds. Chart values retain their numeric precision.

If you provide a staffing assumption, the result says how many patients per staff member per shift you assumed and shows the workload calculation. This is an example based on your assumption, not a staffing recommendation. Daily counts cannot tell the app how arrivals divide across shifts, so shift estimates require arrival shares and shift lengths from you.

This forecasts national COVID admissions, not your hospital's arrivals or dermatology workload.

### T8 — Historical healthcare indicators

1. Open **Historical healthcare indicators (T8)**. **MIMIC-IV public demo 2.2: admissions** is selected automatically.
2. The `admittime` date and `admission_type` group columns and required date format are prefilled. The count field stays blank because this analysis counts actual rows; it is not a source column.
3. Select **Execute analysis**. The date format and grouping column are already entered.

The results label **Rows included** (records left after the date filters) and **Calculated total** (the number of source rows because no count column is selected). The month chart adds those records by month. The category table shows each `admission_type`, its count, and its share of the total. Open “Which source columns were used?” to see the date and grouping fields. These are counts in the demo table, not a hospital-wide total or an automatic unique-patient count; one person may have multiple records.

### T9 — Healthcare planning

1. Open **Healthcare planning (T9)**. The UKHSA demand dataset, `date`, `count`, and 7-day horizon are preselected.
2. Select **Execute analysis** to review the forecast.
3. Planning scenarios default to `[]`, so you can run the forecast without staffing assumptions. To model staffing, enter assumptions supplied by your organization; the app does not provide hospital staffing policies.

### T10, T11, and T12 — Clinical text

Open **Clinical text analytics (T10–T12)**. The public MACCROBAT case-report corpus is already loaded.

- **Cluster documents (T10):** this is selected by default with `MACCROBAT2020: published clinical case reports`. K-means and two groups are prefilled. The output explains each group count, common words, and the group-separation score. Group numbers are names, not diagnoses.
- **Classify labeled text (T10):** changing Task selects `MACCROBAT2020: gold mention semantic-type contexts`, uses `text` and `label`, and sets document-aware grouping to `{"group_column":"document_id"}`. The output defines accuracy, precision, recall, and F1, then compares the dataset label with the model label on held-out text examples.
- **Clinical NER (T11):** choose that task. The compatible public case reports and selected local model are ready. It highlights recognized text and translates entity labels, such as `Sign_symptom`, to readable names. Review the model limitations; extracted terms are not verified medical facts.
- **Search and rank (T12):** choose search. BM25, `text`, and the starter query `patient` are prefilled. The output lists ranked excerpts and explains that BM25 scores are text matches, not probabilities or diagnoses. The separate terminology panel needs a real term and context supplied by you.

This public corpus contains published case reports, not your hospital notes. Do not paste identifiable clinical notes.

### T13 — Dimensionality reduction

1. Open **Dimensionality reduction (T13)**. **NHANES 2017–2018 adults**, the feature columns below, PCA, and 3D are selected by default:

   ```text
   age_years_topcoded80,female_reported,sedentary_minutes_day,sleep_weekday_hours_exact,meals_away_week_exact
   ```

2. PCA and 3D are selected already. Choose **Execute analysis**. You can rotate the result and inspect input rows. A visible cluster is not proof of a clinical group.

### T14 and T15 — Adult weight research

1. Open **Adult weight research (T14–T15)**. **NHANES 2017–2018 adults**, the feature columns below, and `bmi_kg_m2` are prefilled:

   ```text
   age_years_topcoded80,female_reported,sedentary_minutes_day,sleep_weekday_hours_exact,meals_away_week_exact
   ```

2. Select **Execute analysis**.

The results explain each number beside it: **MAE** is average prediction error in BMI points; **RMSE** is a similar error measure that penalizes large misses more; **R²** compares model fit with predicting the test-sample average (negative means that simple average would do better). The page also labels the observed-vs-predicted BMI graph, model comparison, shuffled-feature importance, leave-one-feature-out sensitivity, correlations, and residuals in plain language. Do not include `participant_id` or BMI itself as an input feature. This is unweighted observational research; it does not prove that a behavior causes weight change.

## If something does not work

- If the dashboard says **API not connected**, make sure the backend Terminal is still running.
- If a selector says no compatible dataset is loaded, open **EHR & dataset management** and check the registry or import an authorized file with its actual source and license.
- If a model-dependent action is disabled, open **Data & model status** to see whether its real model artifact is available.
- For medical concerns, use a qualified healthcare professional. This app is not intended to guide care.

### Stop a CNN training run

Open **CNN training & evaluation (T5)**. The **Stop training** button is below **Start training experiment**. It is disabled when no CNN training run is active; when a run is active, the page finds it and enables the button. Stopping is cooperative and takes effect at safe checkpoints during setup and between training/evaluation batches. The run is recorded as cancelled; partial training artifacts are not selected as the active classifier.
