# Implementation status — 2026-10-30

**INCOMPLETE; local presentation demo ready.** The authenticated local app is running, both research image models are explicitly selected, and real-image HTTP and browser workflows have been exercised. Clinical validation is not established, and several modules remain blocked on owner-only records, policies, expert review or external validation.

## Executed with real public data
- MIMIC-IV demo 2.2: 100 patients, 275 encounters, 4,506 diagnosis rows; publisher checksums, primary/foreign key relationships and code dictionary verified. Imported into local registry; actual date transformation run persisted.
- NHANES 2017–2018: component joining, adult inclusion and documented special-code handling; real held-out unweighted exploratory BMI research executed. Weak measured fit retained honestly. See DATA_ACQUISITION.md.
- ISIC2018/HAM10000: official 10,015-image archive acquired and content-audited (no invalid images or exact cross-group pixel duplicates); 7,470 lesion groups, group-disjoint 6,004/1,997/2,014 split. Actual three-epoch validation-only small-CNN, ResNet18 and frozen-backbone EfficientNet-B0 comparison completed. EfficientNet-B0 was chosen on validation loss before test evaluation, then scored once on the held-out test: accuracy 0.62115, balanced accuracy 0.51307, macro F1 0.41722 (2,014 images). It is selected for research inference only; class performance is uneven, class scores are uncalibrated, and lesion grouping does not prove patient independence. See IMAGE_EXPERIMENT_PROTOCOL.md.
- ISIC2018 Task 1: official 100 paired validation images/masks acquired. Classical Otsu benchmarks and a genuine 50-epoch Tiny U-Net V2 run completed. V2 used 70/15/15 images from that 100-image cohort; validation-selected threshold 0.75; held-out mean Dice 0.89046 and IoU 0.81544. Artifact explicitly selected and real-image segmentation executed via authenticated HTTP and the browser. The small image-disjoint cohort and 256-pixel representation do not establish patient-independent, native-resolution or clinical quality.

- UKHSA England COVID admissions: 120 complete historical daily counts; 72/24/24 chronological split, validation-only ridge selection, independent test MAE 46.75973/RMSE 58.55738 counts and separate seven-day recursive retrospective check. Missing source days rejected, no staffing policy inferred. See DATA_ACQUISITION.md.

- MACCROBAT2020: all 200 text/annotation pairs validated; actual mention-type classification, weak-separation clustering and lexical retrieval; locally trained 41-type NER with 140/30/30 document split, held-out exact contiguous-span F1 0.53319471 and authenticated HTTP inference/export verified. No clinical effectiveness or hospital-note generalization claim. See CLINICAL_NLP.md.

## Implemented and tested
- Local user accounts with administrator/researcher/viewer roles, salted password hashes, expiring/revocable sessions and login cooldowns; dataset ownership/read grants, actor audit attribution and administrator audit review and scoped reports/counts. Immutable imports, SQLAlchemy migrations and separate filesystem artifacts. No seeded real accounts.
- Classical image enhancement/restoration/normalization, segmentation/contours, compression and metrics, SIFT/RANSAC, actual failure reporting.
- CNN CLI **and web training**: dataset preflight, one active training run, persistent job/epoch progress, actual checkpoints/curves/embeddings, explicit artifact selection after review, checksum/preprocessing checks and ephemeral inference/Grad-CAM, downloadable actual result reports and opt-in score/hash retention without image storage. No automatic promotion or placeholder classifier.
- CSV/XLSX and strict de-identified FHIR R4 collection subset; linked Patient/Encounter/Observation/Condition validation. Unsupported/identifying fields rejected before raw persistence. Not full FHIR conformance.
- Reproducible tabular cleaning, quality/missingness, exact deduplication, near-duplicate review, explicit conversions and imputation. Read-only paginated/filterable dataset explorer and explicit many-to-one EHR relationship inspection; repeated encounters preserved.
- Genuine-label TF-IDF classifier, clustering, BM25/TF-IDF retrieval and contextual sense ranking; licensed local clinical NER adapter, real corpus training, checkpoint selection, SHA-verified explicit model review/selection and unknown negation.
- Daily demand baselines and autoregressive ridge, separate chronological selection/test, dimensioned staff-shifts/day and explicit per-shift capacity scenarios, historical indicators, PCA/t-SNE and observational modeling/diagnostics/sensitivity. Interactive 2D/rotatable 3D actual-coordinate viewing, variance table, input-row inspection and disclosed bounded display. Constant-feature matrices rejected instead of emitting undefined variance. Real 5,569-adult NHANES 3D PCA and t-SNE runs persisted.
- Integrated Next.js workspace, result charts, report inspection/export, honest missing-input states.

## Current verification
- **105 backend tests** pass in the locked local Python environment, including actual synthetic training/API selection/inference and FHIR rejection/privacy tests. Synthetic artifacts remain in isolated test storage. One upstream Starlette/AnyIO deprecation warning remains visible.
- **31 tests pass against disposable PostgreSQL**, after actual Alembic migration; container removed. The complete Compose stack also passed isolated build/migration/HTTP/account/image-processing/export/runtime-gate checks; disposable resources removed.
- **23 frontend component tests**, TypeScript check and production build pass. Training component coverage includes missing inputs, measured terminal job results, failure display and no automatic model selection. The prediction result component test verifies top-ranked label display with research-only limitations; it uses an isolated fixture, not model metrics.
- Headless Playwright against the live local API and Next.js app executed authenticated dashboard, real held-out lesion inference with gradient-based Grad-CAM, and real learned segmentation without browser errors. Live screenshots are in `docs/screenshots/local-demo-*.png`; automated UI runs used isolated test fixtures in the separate browser test suite. Native Chrome accessibility behavior, Safari/Firefox and full WCAG review remain unverified.

## Remaining implementation and validation
- Patient-disjoint/external-site/skin-tone evaluation and expert clinical review remain required; the available HAM group IDs are lesion-level and cannot establish patient independence.
- SSO/MFA, encryption-at-rest, password recovery, distributed throttling and institutional privacy controls remain unimplemented. Local identity/roles/ownership are now implemented and tested; they are not production or clinical approval.
- Distributed durable task queue; current bounded in-process jobs mark interrupted work failed on restart. One API worker only.
- Institutional clinical-note generalization, expert relevance/sense judgments, negation/normalization and external clinical-model validation; hospital-specific demand and operational staffing policies.
- Advanced staffing optimization, calibrated multi-step intervals, complex-survey/causal inference. Optional UMAP/SHAP/transformers not claimed implemented.
- Full FHIR interoperability, complete browser/accessibility/responsive review.

No tutorial is declared fully complete. See coverage matrix, acquisition evidence and verification record.
