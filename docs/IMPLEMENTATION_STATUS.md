# Implementation status — 2026-10-29

**INCOMPLETE.** Real public EHR, national admissions forecasting and adult research workflows execute. Lesion metadata is validated, but image acquisition is incomplete and no genuine lesion model is trained/selected. Clinical validation is not established.

## Executed with real public data
- MIMIC-IV demo 2.2: 100 patients, 275 encounters, 4,506 diagnosis rows; publisher checksums, primary/foreign key relationships and code dictionary verified. Imported into local registry; actual date transformation run persisted.
- NHANES 2017–2018: component joining, adult inclusion and documented special-code handling; real held-out unweighted exploratory BMI research executed. Weak measured fit retained honestly. See DATA_ACQUISITION.md.
- ISIC2018/HAM10000: administrator-only disk-byte/source-size/class-distribution status; 10,015 labels and 7,470 lesion groups validated; group-disjoint split verified. Large image archive still downloading. No clinical score/model claim.

- UKHSA England COVID admissions: 120 complete historical daily counts; 72/24/24 chronological split, validation-only ridge selection, independent test MAE 46.75973/RMSE 58.55738 counts and separate seven-day recursive retrospective check. Missing source days rejected, no staffing policy inferred. See DATA_ACQUISITION.md.

## Implemented and tested
- Local user accounts with administrator/researcher/viewer roles, salted password hashes, expiring/revocable sessions and login cooldowns; dataset ownership/read grants, actor audit attribution and administrator audit review and scoped reports/counts. Immutable imports, SQLAlchemy migrations and separate filesystem artifacts. No seeded real accounts.
- Classical image enhancement/restoration/normalization, segmentation/contours, compression and metrics, SIFT/RANSAC, actual failure reporting.
- CNN CLI **and web training**: dataset preflight, one active training run, persistent job/epoch progress, actual checkpoints/curves/embeddings, explicit artifact selection after review, checksum/preprocessing checks and ephemeral inference/Grad-CAM, downloadable actual result reports and opt-in score/hash retention without image storage. No automatic promotion or placeholder classifier.
- CSV/XLSX and strict de-identified FHIR R4 collection subset; linked Patient/Encounter/Observation/Condition validation. Unsupported/identifying fields rejected before raw persistence. Not full FHIR conformance.
- Reproducible tabular cleaning, quality/missingness, exact deduplication, near-duplicate review, explicit conversions and imputation. Read-only paginated/filterable dataset explorer and explicit many-to-one EHR relationship inspection; repeated encounters preserved.
- Genuine-label TF-IDF classifier, clustering, BM25/TF-IDF retrieval and contextual sense ranking; licensed local clinical NER adapter.
- Daily demand baselines and autoregressive ridge, separate chronological selection/test, dimensioned staff-shifts/day and explicit per-shift capacity scenarios, historical indicators, PCA/t-SNE and observational modeling/diagnostics/sensitivity.
- Integrated Next.js workspace, result charts, report inspection/export, honest missing-input states.

## Current verification
- **74 backend tests** pass in locked Python environment, including actual synthetic training/API selection/inference and FHIR rejection/privacy tests. Synthetic artifacts remain in isolated test storage.
- **26 tests pass against disposable PostgreSQL**, after actual Alembic migration; container removed. The complete Compose stack also passed isolated build/migration/HTTP/account/image-processing/export/runtime-gate checks; disposable resources removed.
- **15 frontend component tests**, TypeScript check and production build pass. Training component coverage includes missing inputs, measured terminal job results, failure display and no automatic model selection.
- Native Chrome navigation available, but application web content absent from accessibility tree and screenshot returned black. Browser flow/visual/viewport verification remains NOT VERIFIED; HTTP/component/build checks do not substitute.

## Remaining implementation and validation
- Complete real image download, full content/duplicate checks, real model experiments and selection based on validation evidence. Patient-disjoint/external/skin-tone evaluation remains required.
- SSO/MFA, encryption-at-rest, password recovery, distributed throttling and institutional privacy controls remain unimplemented. Local identity/roles/ownership are now implemented and tested; they are not production or clinical approval.
- Distributed durable task queue; current bounded in-process jobs mark interrupted work failed on restart. One API worker only.
- Genuine clinical notes/labels/gold entities/relevance judgments and licensed clinical model validation; genuine hospital demand and explicit operational staffing policies.
- Advanced staffing optimization, calibrated multi-step intervals, complex-survey/causal inference. Optional UMAP/SHAP/transformers not claimed implemented.
- Full FHIR interoperability, complete browser/accessibility/responsive review.

No tutorial is declared fully complete. See coverage matrix, acquisition evidence and verification record.
