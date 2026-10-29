# Implementation status

**INCOMPLETE — real-data evaluation and clinical validation blocked.** No genuine lesion model is installed and no healthcare observations have been fabricated.

## Implemented and algorithm-tested
- Next.js/React workspace: all module navigation, token access, real empty states, CSV/XLSX import, schema display, image comparisons, actual result charts, run history and exports.
- FastAPI: runtime token enforcement, input validation, immutable file storage, SQLAlchemy metadata/audit/run persistence, Alembic migrations. SQLite execution verified; PostgreSQL deployment configuration exists but daemon unavailable.
- Image laboratory: enhancement/restoration/normalization, threshold/Otsu/GrabCut masks, edges/morphology/contours, JPEG/PNG/WebP encoding, measured PSNR/SSIM, paired-mask Dice/IoU, SIFT descriptors/matching, RANSAC registration and genuine failure handling.
- CNN CLI: small baseline/ResNet18/EfficientNet, explicit optional ImageNet download, group-aware stratified splits, duplicate-byte leakage checks, augmentation, class weighting, deterministic CPU training, checkpoint checksums, held-out metrics/curves/calibration diagnostics and embeddings. Ephemeral inference and actual Grad-CAM from configured artifact. Synthetic checkpoint round-trip is isolated to tests; no medical model trained.
- EHR/tabular: schema/quality/missingness, explicit conversions/date formats/unit maps/ranges, exact deduplication, near-duplicate review, imputation and transformation history; source preserved.
- NLP: genuine-label TF-IDF logistic regression, k-means/hierarchical clustering, BM25/TF-IDF retrieval, context-labeled sense ranking. Licensed local clinical spaCy NER adapter requires model card; never assumed clinically validated.
- Analytics: daily temporal baselines and validation, empirical residual bands, explicit capacity scenarios, mapped/filterable historical aggregates; PCA/t-SNE; held-out ridge/random-forest comparison, associations, permutation importance, residual diagnostics and sensitivity.
- Bounded background queue for tabular analyses, persistent statuses and failure/restart reporting. Run one API process; this is not a distributed task queue.

## Verification
37 backend tests passed in a fresh hash-locked project virtual environment; 6 frontend component tests passed. Typecheck and final production build pass. See TEST_RESULTS.md for commands, warnings and verification limits. No browser screenshot/viewport verification: Computer Use permission not granted. All real datasets and clinical validation remain missing.

## Remaining implementation scope (not merely data blockers)
- Production users/roles/per-user ownership, SSO, encryption-at-rest and shared-deployment hardening.
- Full healthcare interoperability/FHIR, patient/encounter relationship model and terminology normalization beyond explicit tabular fields.
- Durable distributed queue and web-orchestrated CNN training; training currently CLI, progress in history.json.
- Context-labeled/clinical models and external validation; no clinical NER performance, retrieval relevance evaluation or calibrated medical score claim.
- Complex-survey/causal inference, clinical staffing optimization with coverage/skills/queue constraints, validated advanced forecasting intervals.
- Optional UMAP/SHAP/transformers are not installed or claimed implemented. Three-component reduction is available in backend; interactive plot currently displays first two coordinates.
- Full browser end-to-end, accessibility/responsive visual review and PostgreSQL container verification.

Tutorials remain PARTIAL / REAL-DATA VALIDATION BLOCKED. Consult TUTORIAL_COVERAGE.md for evidence.
