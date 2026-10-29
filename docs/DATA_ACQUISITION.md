# Public dataset acquisition checkpoint — 2026-10-29

Owner authorized selecting suitable public sources and reported no existing approved datasets. Sources are kept separate by modality; datasets are never combined merely to increase size.

## Lesion classification
Selected official ISIC 2018 Task 3 training resources (HAM10000), CC-BY-NC 4.0 with contributor attribution. Official source https://challenge.isic-archive.com/data/ . Harvard Dataverse API returned HTTP 403/anti-bot challenge; no bypass attempted. Official ISIC S3 downloads are accessible.

Downloaded and validated labels and lesion groupings: 10,015 images, 7,470 lesion groups, seven actual class columns. Group-disjoint split check yielded 6,004 training / 1,997 validation / 2,014 test rows. These are **metadata checks**, not trained-model results. Lesion groups do not establish patient-disjointness. HAM10000 overlaps other ISIC releases; pooling them without overlap audits would invalidate independence.

The original image transfer timed out with an incomplete archive. A resumed HTTP Range/If-Range transfer is in progress at this checkpoint (2,771,732,744 expected bytes from the official resource HEAD). Cached source files are reused only when their receipt URL and local SHA match. No complete archive/extracted image set, CNN training or lesion inference is claimed. Download supports partial-file resumption and records local SHA-256 after completion; that hash is not a publisher checksum unless explicitly provided.

## EHR
Selected MIMIC-IV Clinical Database Demo 2.2, https://physionet.org/content/mimic-iv-demo/2.2/ , Johnson et al. (2023), DOI 10.13026/dp1f-ex47. Open Data Commons Open Database License 1.0, retained locally. This is a genuine de-identified public subset, despite its product name 'demo'; it is not synthetic.

Acquired patients, admissions, diagnoses and diagnosis dictionary; all four gzip files match publisher SHA256SUMS. Executed checks: 100 unique patient keys, 275 unique admission keys, 4,506 diagnosis rows, zero orphan relationships and zero unmapped diagnosis codes. Registered three EHR tables in local metadata DB; transformed admission dates through the actual service and persisted a run. No individual patient records are included in this document or Git.

The public subset excludes clinical free-text notes. Patient-shifted dates and selected patients cannot supply a real daily hospital arrival series. It does not unblock clinical NLP or staffing forecasting.

## Adult behavioral research
Selected CDC NHANES 2017–2018 official public-use DEMO_J/BMX_J/PAQ_J/SLQ_J/DBQ_J XPT files and manuals. Official index https://wwwn.cdc.gov/Nchs/Nhanes/Search/DataPage.aspx?Cycle=2017-2018 ; data-use restrictions https://www.cdc.gov/nchs/policy/data-user-agreement.html . Statistical analysis only; no re-identification or linkage to identifiable data. Same-cycle SEQN component joining is used, not identity linkage.

One-to-one component joins: 9,254 participants; 5,569 adults with RIDAGEYR >=20. Preserved original files/codes. Derived selected behavior fields using actual manuals: PAD680 7777/9999 missing; SLD012 censored 2/14 values not treated as exact sleep hours; DBD895 5555/7777/9999 not treated as exact meal counts. Weights/strata/PSU retained. Age 80 is top-coded. No automatic structural missingness-to-zero.

Real exploratory BMI regression executed using age, reported binary sex code, sedentary minutes, exact weekday sleep and exact meals-away fields. Weight/height excluded from predictors to avoid algebraic BMI leakage. Train-fitted imputation/scaling; participant-group held-out split; 3,881 training and 1,294 test outcomes observed. Measured ridge MAE=5.48619 BMI units, RMSE=7.26447, R²=0.03604. This weak explanatory performance is retained, not concealed or replaced. Missing-outcome adults are excluded, not assigned invented outcomes. These are unweighted exploratory associations, not US population estimates or causal effects. Results and comparison/diagnostic artifacts are stored locally in the actual research run.

Rejected UCI Obesity Levels as primary real-observation case study: its official description says 77% of rows are synthetic (https://archive.ics.uci.edu/dataset/544/estimation+of+obesity+levels+based+on+eating+habits+and+physical+condition). No hidden synthetic alternative was used.

## Historical public demand case study
Official UKHSA API, [access documentation](https://ukhsa-dashboard.data.gov.uk/access-our-data/getting-started), [metric definition](https://ukhsa-dashboard.data.gov.uk/metrics-documentation/covid-19-healthcare-admission-by-day) and [source dashboard](https://ukhsa-dashboard.data.gov.uk/respiratory-viruses/covid-19). Open Government Licence v3.0, with UKHSA/NHS England attribution and no endorsement. Metric `COVID-19_healthcare_admissionByDay`, Nation=England, age/sex=all, stratum=default. This is national COVID admissions, not all ED arrivals, dermatology demand, local hospital operations or staffing history. Publisher definitions, testing and reporting changes limit comparability.

Acquired 363 observations for 2023; raw JSON and local SHA-256 receipt retained outside Git. Missing May 30/31 caused the initial January–May window to be rejected **before modeling**. No invented zeros. The complete January 1–April 30 input window has 120 daily observations, precedes the June collection-change boundary, and reserves May 1–7 for a separate retrospective recursive check. Source schema, scope, uniqueness, finite whole counts and reporting-delay flags are validated. Registered demand dataset `9a32a6fa-8149-44e3-b94c-233910f18ae9`; measured run `d7ce41e3-a651-4518-9911-95289e8d047a`.

Actual chronological protocol: 72 train / 24 validation / 24 test days. Training ends March 13, validation March 14–April 6, test April 7–30. Validation MAE: last-value 81.83333, weekly 99.12500, rolling mean 89.62500, autoregressive ridge 73.85319 admission counts. Ridge selected using validation only. Its independent rolling one-step test MAE=46.75973 and RMSE=58.55738 counts. Separate seven-day recursive May 1–7 retrospective MAE=36.18150, RMSE=47.92160. These are same-source historical errors, not external-hospital validation or current operational advice. No staffing scenario was generated. Exact boundaries/predictions/quality reports persist under `data/processed/public/ukhsa/` and application run history.

## Remaining sources
Clinical notes/gold labels/NER annotations remain unavailable. Institution-specific operational daily arrivals remain unavailable, despite the separate public national admissions case study. MIMIC credentialing requires owner action if that source is desired. Published research articles are a separate text modality, not a substitute for patient notes. Staffing additionally requires explicit operational policies. Masks and external/patient-aware lesion validation remain pending.

## Commands
- `.venv/bin/python -m scripts.acquire_public_data` (or `--source mimic|nhanes|lesions`; `--lesion-images` enables large archive).
- `.venv/bin/python -m alembic -c backend/alembic.ini upgrade head`
- `.venv/bin/python -m scripts.verify_public_ehr`
- `.venv/bin/python -m scripts.verify_public_weight`
- `.venv/bin/python -m scripts.acquire_public_demand` (official API; cached raw SHA verification; real forecasting and retrospective checks)
- `.venv/bin/python -m scripts.prepare_isic` validates labels/groups and safely extracts only matching image basenames once archive exists.

Do not launch a second download against the same destination while a first is running. Data, checksums, participant rows, images, DB and model artifacts remain outside source control. Code/docs only are pushed.
