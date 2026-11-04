# Verification record

## Current local demo verification — 2026-10-30

- `.venv/bin/python -m pytest backend/tests -q`: **105 passed**, 11.52s. One visible upstream Starlette/AnyIO deprecation warning.
- `cd frontend && npm test`: **23 tests passed** across 8 files, 2.51s.
- `cd frontend && npm run typecheck`: passed.
- `cd frontend && npm run build`: optimized Next.js production build passed.
- Authenticated local HTTP: `/health` and the frontend returned 200; `/status` returned 200 with a private token and confirmed selected lesion and segmentation artifacts, 9 datasets, 19 processed images and 40 completed runs. The token is not written to this report.
- Actual browser workflow against the live frontend/API: unlocked with the local token, uploaded the public held-out ISIC image `ISIC_0024309.jpg`, received its real EfficientNet-B0 scores and model-generated Grad-CAM, and rendered the top-ranked class with an explicit uncalibrated/research-only note. A second browser workflow ran selected Tiny U-Net segmentation and displayed the computed overlay and binary mask. Both workflows completed without browser errors.
- Live captures: `docs/screenshots/local-demo-dashboard.png`, `local-demo-inference.png`, and `local-demo-segmentation.png`. The image used is public research data; see LOCAL_DEMO.md for its evaluation-split caveat.
- A preliminary browser harness attempt queried the navigation as buttons; the real app uses anchor links. Corrected the harness and completed the workflows. An initial `npm run test:unit -- --run` invocation failed because there is no `test:unit` script; the project's documented `npm test` command passed. No application assertions were weakened.

The screenshot/browser checks are local presentation evidence only. They do not establish clinical validity, patient-independent generalization, or compatibility with other browsers.

2026-10-29: inspected repository; supplied upstream has README only. Python imports verified torch 2.13.0, OpenCV 5.0.0 and SIFT availability; CUDA/MPS false in current process. No tests or model evaluations existed. No real-data verification performed. Clinical inference BLOCKED.

## First algorithm/API milestone
- `python3 -m pytest backend/tests -q`: failed before collection because shell selected Python 3.14 without pytest. Corrected by selecting installed interpreter explicitly; no assertions changed.
- `/usr/local/bin/python3.13 -m pytest backend/tests -q`: **32 passed**, 6.12s. Synthetic fixtures isolated in tests: PNG identity/SSIM, gamma identity, dark-disk segmentation Dice/IoU, variance reduction, real SIFT/RANSAC translation recovery, every image algorithm, immutable tabular transformations, exact duplicates vs encounters, unit conversion, missing dates, temporal leakage, PCA rank, held-out regression, BM25, NLP label requirement, group-disjoint CNN splits, tensor shape/eval determinism, authenticated API import→transform→persist→export and failure persistence.
- `npm run typecheck`: passed.
- `npm run build`: passed, Next.js 16.4.3, route `/` prerendered.
- `npm install next@latest react@latest react-dom@latest`: completed; audit reported 0 vulnerabilities. Exact dependency graph in package-lock.json.
- Joblib emitted physical-core detection warning; it fell back to logical cores. Not suppressed.
- Actual lesion training, inference, clinical performance and all real healthcare analytics: BLOCKED / NOT VERIFIED (inputs missing). Unit tests do not establish medical validity.

## Expanded verification
- Backend suite: **37 passed**, 3.67s, installed Python 3.13 environment. Added real synthetic train→checkpoint→checksum→deterministic inference→Grad-CAM, persisted queued run, contextual sense ranking, fuzzy candidate review and mapped strategic aggregates.
- Frontend `npm run test`: **6 passed**, isolated jsdom components. Checks token gate, model-missing inference, provenance/file/authorization requirements, missing operational inputs, image upload constraints, lock clearing, and visible authentication failure. This is NOT browser end-to-end testing.
- Typecheck initially caught unsupported `exact` options in Testing Library getByRole calls. Corrected the option types; rerun passed. No assertions weakened.
- Real local HTTP: `/` returned 200; `/health` returned `{"status":"alive","research_only":true}`. Network sandbox required escalation for loopback checks.
- `alembic ... upgrade head` executed against isolated SQLite storage successfully.
- Docker daemon unavailable even outside sandbox: PostgreSQL/Compose NOT VERIFIED.
- Browser: in-app browser unavailable, native Chrome control denied with “Computer Use permissions are not granted.” Screenshots, responsive viewport checks and browser end-to-end flows NOT VERIFIED. No screenshots fabricated.
- Hash-locked Python dependencies generated with uv for Python 3.13. Isolated installation/checks in progress; resolution alone is not runtime verification.
- A float32 probability normalization warning in synthetic CNN evaluation was fixed by normalizing measured softmax vectors in float64 before sklearn metrics; no warning suppression. Joblib physical-core warning remains documented.

## Isolated locked-environment and final build checkpoint
- Created project `.venv` with Python 3.13.5 and installed **76 applicable packages** from `backend/requirements.lock` using `uv pip sync --require-hashes`; universal lock contains platform markers for other environments. Installation completed successfully.
- `.venv/bin/python -m pytest backend/tests -q`: **37 passed**, 32.69s, fresh locked environment. Warnings: upstream Starlette/AnyIO deprecated BlockingPortal alias and joblib physical-core detection fallback. Neither warning was suppressed. No real dataset/model is installed by tests.
- Final `npm run build`: passed after queued jobs, artifact charts, structured NER/sense output and frontend tests were added. `npm run typecheck` passed separately. `npm run test`: **6 passed**.
- Temporary local preview/API processes were stopped after HTTP checks. No browser screenshot or PostgreSQL claim is made.

## Real public-data acquisition verification
See DATA_ACQUISITION.md for executed commands, source licenses, publisher checksum matches, real EHR relationship/date checks and real held-out NHANES metrics. Initial download failed a Content-Length check because HTTP content encoding changed the body length; fixed by requesting identity encoding and comparing length only on unencoded responses. Failure was reported, not suppressed. Re-run succeeded. No raw patient rows or healthcare files committed.
- After adding public-data preparation: `.venv/bin/python -m pytest backend/tests -q`: **38 passed**, 3.53s. New isolated sentinel-code test confirms censored/unknown NHANES values are not treated as actual numeric behaviors; under-20 participants are excluded. Upstream Starlette/AnyIO deprecation warning remains visible. Real-data verification scripts also executed successfully as documented separately.

## Web training, structured EHR and PostgreSQL checkpoint
- `.venv/bin/python -m pytest backend/tests -q`: **48 passed**, 3.39s. Actual isolated training job → artifact review → explicit selection → inference verified; missing input and invalid epoch requests blocked. Weighted epoch loss accumulation corrected to weight each batch by summed class weights rather than batch size.
- FHIR tests verify linked resources, numeric quantity preservation, cross-patient encounter mismatch, duplicate IDs, unknown references, finite values, offset timestamps and pre-persistence rejection of identifying fields without echoing their values.
- `.venv/bin/python -m scripts.check_postgres`: **14 passed**, 4.38s, against fresh PostgreSQL 17 after Alembic migration. Disposable container removed. No production data used.
- `npm run typecheck`, `npm run test` (**6 passed**) and `npm run build`: passed. Build exposed ambiguous workspace-root inference due to an unrelated untracked root package-lock; explicit frontend root configuration pending.
- Native Chrome access now permits navigation to local app. Returned screenshot was entirely black and accessibility tree omitted application web content after refresh. Functional/visual browser verification remains incomplete; no screenshot saved as UI evidence.

## Dataset explorer and inference-report retention
- `.venv/bin/python -m pytest backend/tests -q`: **51 passed**, 3.58s. Added authentication, pagination bounds, numeric equality and literal (non-regex) text filtering; parent-key validation, orphan reporting and encounter preservation. Retention test verifies ephemeral inference does not create a score record, explicit opt-in persists actual scores/hashes, and stored reports exclude image/heatmap bytes.
- Real MIMIC relationship service execution: 275/275 child admissions matched 100/100 supplied parent patients, no missing/unmatched keys; repeated encounters retained. Report persisted in actual local run history.
- Frontend training component tests: source unavailability disables submission; terminal job results are reviewed without automatic model selection; real API-style failure messages remain failures. All fixtures are isolated component tests.
- Next.js now explicitly resolves Turbopack root to the frontend directory, using the installed version's documented root option. Unrelated untracked root package-lock was left untouched.
- Live Next.js `/api/status` proxy returned actual persisted registry counts: four datasets (three EHR, one weight), two completed runs at time of request, zero image runs and no available lesion model. This verifies HTTP/API integration, not rendered browser interaction.
- Final cross-database rerun: `.venv/bin/python -m scripts.check_postgres`: **17 passed**, 3.93s. Includes relationship and opt-in inference-retention cases; disposable container removed.
- Final frontend `npm run typecheck`, `npm run test` (**9 passed**, 1.91s), `npm run build`: passed without workspace-root warning after explicit configuration.

## Local identity and ownership checkpoint
- `.venv/bin/python -m pytest backend/tests -q`: **57 passed**, 5.51s. Tests exercise salted password hashing, generic login failure/throttling, private datasets/counts, viewer write denial, cross-user report/export denial, grant revocation affecting derived artifacts, session expiry/logout, disabled users, admin-only training, audit actor attribution and password-input redaction. Acquisition-state test measures actual partial bytes without claiming transfer liveness/readiness.
- Fresh PostgreSQL: **22 tests passed**, 5.49s, with revision 002 creating identity/ownership schema. Disposable database/container removed. An additional acquisition-state test was added after this PostgreSQL run; current final cross-database check is recorded below when executed.
- Owner's SQLite DB backed up under ignored data directory, upgraded to revision 002; verified 4 datasets, 3 real-data runs, 0 real user accounts. No real credentials created or committed.
- `npm run typecheck`, component tests (**12 passed**) and production build passed before final 401-cache-clearing adjustment. New component tests verify real form submission contracts, cleared successful password field/no localStorage, failed login establishing no session, and viewer profile excluding administrative creation/grant controls. Final rerun recorded separately.
- Official image-object HTTP HEAD measured expected length **2,771,732,744 bytes**; local source receipt retained outside Git. Status reports partial bytes/class labels only to administrators. A partial archive is not declared active, intact, extracted or model-ready.
- Final identity/acquisition/audit suite after Python formatting: **58 backend tests passed**, 5.43s; **24 passed on fresh PostgreSQL**, 5.41s; containers removed. Added administrator-only bounded audit review and credential-free event assertions. Upstream Starlette/AnyIO deprecation remains visible.
- Final frontend typecheck, **12 component tests** (1.80s) and optimized build passed after 401 cache clearing and account/audit UI changes.
- Formatting-only commit staged 22 existing Python files only after comparing their before/after ASTs and confirming equality. No assertions or algorithms were weakened.
- Full-stack Docker Compose build/HTTP verification is in progress; no success claimed yet.

## Full-stack Compose and runtime boundaries
- `.venv/bin/python -m scripts.check_compose`: first base check passed. Expanded check then failed on a SyntaxError in the test-fixture `python -c` newline escaping after image processing/export had passed. Corrected the fixture argv to use explicit byte encoding, compiled it locally, and reran without weakening any assertions.
- Final expanded Compose check **PASSED**: fresh real builds, PostgreSQL readiness/migrations, authenticated account persistence, frontend root/proxy HTTP, uploaded synthetic pixels → real PNG encoding/SSIM → persisted report → JSON export, missing real-model/data gate, and explicit absent-torch blocker after a temporary synthetic manifest was injected. Fixtures exist only in the disposable project; containers, volumes and network removed in finally.
- Default base Docker image intentionally excludes optional torch/spaCy. API now reports an explicit CNN/NER runtime dependency blocker instead of an unhandled import failure. Host environment retains full locked ML/NLP dependencies.
- Code review found small_cnn could record a requested pretrained flag although it has no ImageNet weights. Architecture and API validation now reject this configuration; no real trained artifacts existed to repair.
- Final `.venv/bin/python -m pytest backend/tests -q`: **60 passed**, 6.21s. `.venv/bin/python -m scripts.check_postgres`: **25 passed**, 5.41s, container removed. Frontend remains **12 passing component tests**, passing typecheck/build; no frontend source changed in this runtime-boundary patch.

## Public demand and chronological forecasting milestone — 2026-10-29
- `.venv/bin/python -m scripts.acquire_public_demand`: executed against official UKHSA public API. Initial January–May window rejected for missing May 30/31, with no zero fill. Complete January–April 120-day case registered and real run persisted. Independent test and separate recursive-horizon errors recorded in DATA_ACQUISITION.md, with national COVID-admission scope. No staffing history or policy invented.
- `.venv/bin/python -m pytest backend/tests -q`: **74 passed**, 6.95s; visible upstream Starlette/AnyIO deprecation warning. New tests check chronology and untouched-test selection invariance, mathematical staffing units/explicit assumptions, source scope/gaps/reporting delay, cache source/hash tampering and API provenance without storage paths. Earlier failures exposed a minimum-split implementation bug (fixed to 14/7/7) and an invalid Pandas integer fixture assignment (fixture dtype corrected); assertions retained.
- `.venv/bin/python -m scripts.check_postgres`: **26 passed**, 5.67s, disposable migrated PostgreSQL removed (recorded before final display-label changes).
- `cd frontend && npm run typecheck && npm run test && npm run build`: **15 component tests passed**, 2.03s; typecheck and optimized build passed after final count-unit labels. Tests distinguish recorded independent test metrics from older validation-only reports and prevent daily workload from appearing as inferred per-shift staffing.
- Browser screenshot/responsive/interaction QA remains NOT VERIFIED. No clinical performance claim follows from these software checks.

## Interactive 3D exploratory geometry milestone — 2026-10-29
- `.venv/bin/python -m scripts.verify_public_reduction`: real 5,569-adult NHANES PCA and t-SNE executed, complete 3D coordinates and provenance persisted. Actual component variances and optimization objective recorded in DATA_ACQUISITION.md; no clinical validity inferred.
- `.venv/bin/python -m pytest backend/tests -q`: **78 passed**, 5.68s, one visible upstream deprecation warning. New mathematical tests cover three-component PCA rank/row order, rejection of constant matrices and fractional dimensions; API test checks real coordinates, persistence/provenance and exact exported coordinates. Initial API test assumed a run envelope around the JSON download; corrected to the documented raw-result export contract, retaining exact coordinate equality.
- `.venv/bin/python -m scripts.check_postgres`: **27 passed**, 5.64s after the same test-contract correction; disposable container removed.
- `cd frontend && npm run typecheck`, followed by `npm run test && npm run build`: passed; **18 component tests**, 2.16s; optimized build passed. Mathematical rotation tests preserve norms/use the actual third coordinate; component tests exercise rotation, row inspection, invalid-input rejection and disclosed bounded display.
- Full native-browser visual/viewport QA remains NOT VERIFIED.

## Real public clinical corpus and research NER milestone — 2026-10-29
- Actual commands: `scripts.acquire_public_clinical`, `scripts.verify_public_clinical`, `scripts.train_clinical_ner --epochs 20`, and `scripts.verify_public_ner` (now requires explicit `--training-run`). Complete measured evidence and run IDs in CLINICAL_NLP.md. Publisher MD5/size, all BRAT offsets, document grouping and genuine labels verified. Training's first real attempt failed with E024; unsupported boundary-whitespace supervision was counted/excluded for training while gold test scoring stayed intact. Failed run retained. The successful real NER test F1=0.53319471 is not clinical validation.
- Real authenticated HTTP verification selected the reviewed artifact, processed 200 published narratives, checked predicted offsets and exact exported result equality. Smoke includes training documents and has no claimed accuracy. Verification server stopped and ephemeral credential not retained.
- `.venv/bin/python -m pytest backend/tests -q`: **83 passed**, 7.69s; one visible upstream deprecation warning. New tests verify strict/discontinuous BRAT parsing, overlapping-gold recall denominator, grouped splits/duplicate rejection, actual isolated NER training/selection/inference and corruption rejection. An initial isolated test missed application lifespan/schema setup; fixed the test setup before rerun, preserving assertions. Relative-path acquisition logging was corrected after a real acquisition exposed the issue; cache provenance regression tested.
- `.venv/bin/python -m scripts.check_postgres`: **31 passed**, 7.02s, now includes clinical-corpus training/selection tests against migrated disposable PostgreSQL; container removed.
- `cd frontend && npm run typecheck`, then component tests/build: **20 tests passed**, 2.08s; optimized build passed. Selection requires prior report review, never promotes on load, and is hidden from readers. A test-file write initially used the wrong cwd; corrected the path and ran the intended tests. Browser visual QA remains NOT VERIFIED.

## Beginner usability guide — 2026-11-04

- `cd frontend && npm run typecheck`: passed.
- `cd frontend && npm test`: **27 passed** across 9 files. Added focused checks for dashboard quick starts, dataset selection, and T8/NHANES input instructions. The first run found an ambiguous test query for a field shown twice; the query was corrected without changing the application behavior; rerun passed.
- `cd frontend && npm run build`: optimized Next.js production build passed.
- Live headless Chromium against the running local app/API: authenticated using the local private token (not logged or saved), confirmed loaded MIMIC-IV, UKHSA, NHANES and MACCROBAT quick-starts, opened the NHANES walkthrough, and found no browser exceptions. Captures: `beginner-dashboard.png` and `beginner-weight-guide.png`.
- `git diff --check`: passed.
- `cd frontend && npm run test:browser`: **could not start** because the configured Next.js web server detected an already-running development server using the same `.next` development directory and exited. This is a harness/server-lock issue; the direct live-browser walkthrough above passed. Full isolated Playwright suite remains unverified in this run.

## T6 Inspect visibility fix — 2026-11-04

- Root cause: Inspect fetched and rendered the saved report after a long artifact table, below the current viewport, so the click appeared to do nothing.
- `cd frontend && npm run typecheck`: passed.
- `cd frontend && npm test`: **27 passed** across 9 files.
- `cd frontend && npm run build`: optimized production build passed.
- Live headless Chromium against the local app/API: clicked Inspect on an actual persisted run, confirmed the report loaded and its results heading scrolled into the viewport; no browser exceptions.

## T6 visualization library and active CNN interruption — 2026-11-04

- Replaced the flat all-runs dump on T6 with topic groups driven by persisted run kinds: Images, Model evaluation, Clinical text, Healthcare analytics, and Data quality. The overview shows up to four actual recent runs per group, with category filters to browse the full set. Search matches actual kind, status, date, run ID and error text; export and Inspect still call the real APIs.
- `cd frontend && npm run typecheck`: passed. `cd frontend && npm test`: **27 passed**. `cd frontend && npm run build`: passed.
- Live Chromium checked five category groups, forecast search (3 matching persisted runs), Images filter (31 persisted runs), Inspect loading a real result, and a 390px mobile viewport with no horizontal overflow. Capture: `docs/screenshots/t6-organized-library.png`.
- Responding to the owner's stop request, confirmed a live CNN job at epoch 2/5 with the API process consuming CPU. The then-current server had no cancellation route, so its API process was stopped and restarted. Startup correctly marked the interrupted run failed with the recorded process-ended reason. API health returned 200 after restart; no training run remains active. No completion or model result is claimed for the interrupted run.
- The web Playwright runner was not rerun; browser verification above used the live authenticated app and API directly.

## CNN Stop control — 2026-11-04

- The active CNN runs observed during this session were stopped by restarting the API because the previous server had no cancellation API. Startup marked interrupted runs failed with the process-ended explanation; this does not claim successful training. The restarted API reports no pending/running CNN jobs.
- Added an admin-only audited `POST /training/{id}/cancel` endpoint backed by cooperative cancellation checks before data loading, after model setup, and between training/evaluation minibatches. Cancellation persists as `cancelled`; no model is selected or promoted.
- The CNN training page now discovers a real active CNN run on entry. **Stop training** stays visible under Start; it is disabled when there is no active job and enabled for an active job.
- Backend: `.venv/bin/python -m pytest backend/tests -q` — **107 passed**, one visible upstream Starlette/AnyIO deprecation warning. Python compile check passed.
- Frontend: `cd frontend && npm run typecheck`, `npm test` — **28 passed**, and `npm run build` all passed.
- Live browser confirmed the Stop control's location and disabled no-active state; component and API integration tests verified active-run discovery, cancellation request, and persisted cancelled status. Screenshot: `docs/screenshots/cnn-stop-control.png`.
