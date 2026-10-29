# Verification record

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
