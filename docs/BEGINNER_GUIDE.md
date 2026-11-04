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

After connecting, the dashboard shows **Start with data already loaded**. Pick a path there. Every section also displays a short guide above its forms. The tutorial tags in the sidebar show which tutorial each section covers.

### T1 — EHR tables

1. Open **EHR & dataset management (T1)**.
2. The following MIMIC-IV Demo tables are already loaded: patients, admissions, and diagnoses with their dictionary. You do not need to import them again.
3. Click a table name in the registry to inspect its schema and summary. Use **Browse and filter source records** to view rows.
4. Expand **Inspect patient / encounter table relationships**. To verify admissions connect to patients, select `admissions` as the child table and `patients` as the parent table; enter `subject_id` for both key fields.

For your own file, import only data you are allowed to use. Select its file, choose the correct modality, cite its actual source, enter its actual license or authorization, and confirm that it is appropriately de-identified. Do not copy MIMIC's source or license for a different file.

### T2 and T3 — Preprocessing, duplicates, and missing data

1. Open **Data preprocessing (T2–T3)** and choose a registered EHR, weight, or tabular dataset.
2. Read the column list and missing-value counts under the dataset selector.
3. Expand **Transformation configuration guide**. Use only real column names from the selected dataset; enter chosen settings as JSON under **Advanced parameters**.
4. Run the analysis and inspect the before/after report. The original source is preserved.

For a first look, leave the advanced settings as `{}` and inspect the reported transformation and data quality. Do not remove rows just because they have the same patient ID; repeat visits can be valid records.

### T4 — Image processing

1. Open **Image processing lab (T4)**.
2. Choose an image file (PNG, JPEG, or WebP; up to 20 MiB). A project image for practice is `data/raw/isic2018-task3/images/ISIC_0024309.jpg`.
3. Choose an algorithm. Try **Learned segmentation** to generate a mask, or select an enhancement method to change image contrast.
4. Keep parameters as `{}` for a first run, then select **Run image processing**. Compare the original, output, mask, and histogram.

### T5 — Image registration and lesion classification

T5 appears in three sidebar sections because it covers three different image methods:

- **SIFT & RANSAC:** upload two related images with shared visual features, then choose **Extract features & register**. It shows matches and the estimated alignment; it does not classify a lesion.
- **Lesion detection:** upload one image, optionally check **Compute actual Grad-CAM explanation**, leave score retention unchecked for an ephemeral run, then choose **Run research inference**. You can use the practice image above. The output is a top-ranked research label and uncalibrated class scores, not a diagnosis.
- **CNN training & evaluation:** the project already has a selected research classifier. Use Lesion detection for a prediction. Open the training page only when you intend to start another experiment; training uses the configured dataset and can take time.

### T6 — Visualizations

Run an image, model, text, or analytics workflow first. Then open **Biomedical visualization (T6)** or **Reports & history**. Select **Inspect** to view a completed run or **JSON** to export its report. This section visualizes real results; it does not create new observations.

### T7 — Patient-demand forecasting

1. Open **Patient demand (T7)**. The public UKHSA England COVID admissions dataset is already available.
2. Select that dataset. The columns are `date` and `count`; the horizon defaults to 7 days.
3. Select **Execute analysis**. Leave staffing fields empty unless you have real, approved assumptions.

This forecasts national COVID admissions, not your hospital's arrivals or dermatology workload.

### T8 — Historical healthcare indicators

1. Open **Historical healthcare indicators (T8)**.
2. Select **MIMIC-IV public demo 2.2: admissions**.
3. For a monthly count of admission rows, enter `admittime` as the date column, leave count blank, and set **Advanced parameters (JSON)** to:

   ```json
   {"date_format":"%Y-%m-%d %H:%M:%S"}
   ```

4. Optionally enter `admission_type` as the grouping column. Run the analysis.

The result counts rows in this demo table. It is not a hospital-wide total or an automatic unique-patient count.

### T9 — Healthcare planning

1. Open **Healthcare planning (T9)** and select the UKHSA demand dataset.
2. Keep `date`, `count`, and the 7-day horizon to review the forecast.
3. Leave planning scenarios as `[]` if you only want the forecast. To model staffing, enter assumptions supplied by your organization; the app does not provide hospital staffing policies.

### T10, T11, and T12 — Clinical text

Open **Clinical text analytics (T10–T12)**. The public MACCROBAT case-report corpus is already loaded.

- **Cluster documents (T10):** choose `MACCROBAT2020: published clinical case reports`; text column is `text`.
- **Classify labeled text (T10):** choose `MACCROBAT2020: gold mention semantic-type contexts`; use `text` as the text column and `label` as the genuine label column. To keep examples from the same source document together, set advanced JSON to `{"group_column":"document_id"}`.
- **Clinical NER (T11):** choose that task and a compatible text dataset; inspect the extracted spans and review the model evidence panel.
- **Search and rank (T12):** choose search, use the `text` column, and enter a real query. The terminology panel needs an ambiguous term plus its real context.

This public corpus contains published case reports, not your hospital notes. Do not paste identifiable clinical notes.

### T13 — Dimensionality reduction

1. Open **Dimensionality reduction (T13)** and choose **NHANES 2017–2018 adults**.
2. Enter these numeric columns, separated by commas:

   ```text
   age_years_topcoded80,female_reported,sedentary_minutes_day,sleep_weekday_hours_exact,meals_away_week_exact
   ```

3. Choose PCA, select 3D, and run. You can rotate the result and inspect input rows. A visible cluster is not proof of a clinical group.

### T14 and T15 — Adult weight research

1. Open **Adult weight research (T14–T15)** and select **NHANES 2017–2018 adults**.
2. In **Numeric feature columns**, enter:

   ```text
   age_years_topcoded80,female_reported,sedentary_minutes_day,sleep_weekday_hours_exact,meals_away_week_exact
   ```

3. In **Observed numeric outcome**, enter `bmi_kg_m2` and select **Execute analysis**.

The report includes descriptive data and a held-out model comparison, residual checks, feature importance, and sensitivity analysis. Do not include `participant_id` or BMI itself as an input feature. This is unweighted observational research; it does not prove that a behavior causes weight change.

## If something does not work

- If the dashboard says **API not connected**, make sure the backend Terminal is still running.
- If a selector says no compatible dataset is loaded, open **EHR & dataset management** and check the registry or import an authorized file with its actual source and license.
- If a model-dependent action is disabled, open **Data & model status** to see whether its real model artifact is available.
- For medical concerns, use a qualified healthcare professional. This app is not intended to guide care.
