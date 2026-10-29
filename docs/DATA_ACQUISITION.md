# Public dataset acquisition checkpoint — 2026-10-29

Owner authorized selecting suitable public sources and reported no existing approved datasets. Sources are kept separate by modality; datasets are never combined merely to increase size.

## Lesion classification
Selected official ISIC 2018 Task 3 training resources (HAM10000), CC-BY-NC 4.0 with contributor attribution. Official source https://challenge.isic-archive.com/data/ . Harvard Dataverse API returned HTTP 403/anti-bot challenge; no bypass attempted. Official ISIC S3 downloads are accessible.

Downloaded and validated labels and lesion groupings: 10,015 images, 7,470 lesion groups, seven actual class columns. Group-disjoint split check yielded 6,004 training / 1,997 validation / 2,014 test rows. These are **metadata checks**, not trained-model results. Lesion groups do not establish patient-disjointness. HAM10000 overlaps other ISIC releases; pooling them without overlap audits would invalidate independence.

Image archive download is in progress at this checkpoint (approximately 2.6 GB total). No complete archive/extracted image set, CNN training or lesion inference is claimed. Download supports partial-file resumption and records local SHA-256 after completion; that hash is not a publisher checksum unless explicitly provided.

## EHR
Selected MIMIC-IV Clinical Database Demo 2.2, https://physionet.org/content/mimic-iv-demo/2.2/ , Johnson et al. (2023), DOI 10.13026/dp1f-ex47. Open Data Commons Open Database License 1.0, retained locally. This is a genuine de-identified public subset, despite its product name 'demo'; it is not synthetic.

Acquired patients, admissions, diagnoses and diagnosis dictionary; all four gzip files match publisher SHA256SUMS. Executed checks: 100 unique patient keys, 275 unique admission keys, 4,506 diagnosis rows, zero orphan relationships and zero unmapped diagnosis codes. Registered three EHR tables in local metadata DB; transformed admission dates through the actual service and persisted a run. No individual patient records are included in this document or Git.

The public subset excludes clinical free-text notes. Patient-shifted dates and selected patients cannot supply a real daily hospital arrival series. It does not unblock clinical NLP or staffing forecasting.

## Adult behavioral research
Selected CDC NHANES 2017–2018 official public-use DEMO_J/BMX_J/PAQ_J/SLQ_J/DBQ_J XPT files and manuals. Official index https://wwwn.cdc.gov/Nchs/Nhanes/Search/DataPage.aspx?Cycle=2017-2018 ; data-use restrictions https://www.cdc.gov/nchs/policy/data-user-agreement.html . Statistical analysis only; no re-identification or linkage to identifiable data. Same-cycle SEQN component joining is used, not identity linkage.

One-to-one component joins: 9,254 participants; 5,569 adults with RIDAGEYR >=20. Preserved original files/codes. Derived selected behavior fields using actual manuals: PAD680 7777/9999 missing; SLD012 censored 2/14 values not treated as exact sleep hours; DBD895 5555/7777/9999 not treated as exact meal counts. Weights/strata/PSU retained. Age 80 is top-coded. No automatic structural missingness-to-zero.

Real exploratory BMI regression executed using age, reported binary sex code, sedentary minutes, exact weekday sleep and exact meals-away fields. Weight/height excluded from predictors to avoid algebraic BMI leakage. Train-fitted imputation/scaling; participant-group held-out split; 3,881 training and 1,294 test outcomes observed. Measured ridge MAE=5.48619 BMI units, RMSE=7.26447, R²=0.03604. This weak explanatory performance is retained, not concealed or replaced. Missing-outcome adults are excluded, not assigned invented outcomes. These are unweighted exploratory associations, not US population estimates or causal effects. Results and comparison/diagnostic artifacts are stored locally in the actual research run.

Rejected UCI Obesity Levels as primary real-observation case study: its official description says 77% of rows are synthetic (https://archive.ics.uci.edu/dataset/544/estimation+of+obesity+levels+based+on+eating+habits+and+physical+condition). No hidden synthetic alternative was used.

## Remaining sources
Clinical notes/gold labels/NER annotations and genuine operational daily arrivals remain unavailable. MIMIC credentialing requires owner action if that source is desired. Published research articles are a separate text modality, not a substitute for patient notes. Staffing additionally requires explicit operational policies. Masks and external/patient-aware lesion validation remain pending.

## Commands
- `.venv/bin/python -m scripts.acquire_public_data` (or `--source mimic|nhanes|lesions`; `--lesion-images` enables large archive).
- `.venv/bin/python -m alembic -c backend/alembic.ini upgrade head`
- `.venv/bin/python -m scripts.verify_public_ehr`
- `.venv/bin/python -m scripts.verify_public_weight`
- `.venv/bin/python -m scripts.prepare_isic` validates labels/groups and safely extracts only matching image basenames once archive exists.

Do not launch a second download against the same destination while a first is running. Data, checksums, participant rows, images, DB and model artifacts remain outside source control. Code/docs only are pushed.
