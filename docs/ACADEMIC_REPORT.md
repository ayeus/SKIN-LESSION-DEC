# Latest data checkpoint

Public MIMIC-IV demo EHR and NHANES adult data have now been acquired and exercised. ISIC2018 labels/groups validated; image archive downloading; CNN training not performed. See [DATA_ACQUISITION.md](DATA_ACQUISITION.md). Earlier no-data statements below describe the initial implementation checkpoint, not current acquisition status.

# DermaInsight AI academic report

## Problem and objectives
Healthcare research often separates image experiments, tabular cleaning, clinical language and operational planning into disconnected notebooks. This project provides a traceable local workspace for these modalities while preserving their distinct evidence requirements. Objectives are reproducible processing, explicit provenance, meaningful algorithm verification, honest uncertainty and integrated inspection/export. An image dataset cannot answer a staffing or behavioral research question.

## Scope and implementation
The current system implements classical image processing, geometric registration, a real CNN experiment pipeline, configurable EHR transformations, clinical text baselines, daily demand baselines, historical indicators and numeric observational research. See ARCHITECTURE.md for component/data flow and ALGORITHMS.md for definitions and configured hyperparameters. TUTORIAL_COVERAGE.md maps implementation and tests to all fifteen course topics.

## Evaluation methodology
Separate implementation correctness from dataset performance and clinical effectiveness. Mathematical synthetic fixtures verify identities, known geometry and leakage prevention; these establish neither diagnostic performance nor healthcare utility. Real model experiments require group-disjoint training/validation/test partitions, input/version hashes, train-only fitted transformations, suitable metrics and honest reporting of class imbalance. Patient groups are preferred over lesion groups. Test results used repeatedly for architecture selection cease to be independent. External datasets, expert review and skin-tone/generalization assessment are needed before medical claims.

Forecast selection uses temporal validation and explicitly does not label selected validation error independent test performance. Staffing capacity is user-defined, with omitted operational constraints stated. Weight research is observational and unweighted, requiring justified adult inclusion, confounders and survey design for population claims. Text extraction recognizes spans; it does not establish that a clinical statement is true.

## Results
No genuine healthcare dataset or trained lesion artifact has been supplied. There are **no clinical accuracy, staffing forecasts, population findings or validated NER scores to report**. TEST_RESULTS.md records executed software checks only. Implementation status is partial; real-data evaluation is blocked.

## Privacy and ethics
Only authorized, appropriately de-identified data belongs in this local research build. Dataset attestation is not de-identification. Raw and processed files are excluded from Git; storage permissions and institutional retention requirements remain the owner's responsibility. Token access restricts local endpoints but is not a production identity system. Research outputs are not diagnoses, confidence calibration is not assumed, and no definitive treatment is recommended. No regulatory approval is claimed.

## Limitations and further work
See IMPLEMENTATION_STATUS.md for unimplemented scope. Priority work is acquisition/approval of independent modality datasets, genuine model comparisons, clinical model/relevance annotations, external validation, production access/privacy controls, PostgreSQL/container execution, and browser/viewport review. Add UMAP/SHAP/transformers only when justified and validated; adding library names is not evidence of completeness.

## Viva preparation
- Why use patient-aware splits? Multiple related images/notes can leak subject information across partitions.
- Does ImageNet pretraining create a lesion classifier? No; the task head and fine-tuning require genuine labeled lesion data.
- Are softmax scores confidence? They are uncalibrated research scores unless calibration is measured and independently validated.
- Does RANSAC detect cancer? No; it estimates geometry robustly from feature correspondences.
- Does a clean PCA separation prove diagnosis? No; exploratory geometry is not predictive or clinical validation.
- Can duplicates be removed by patient ID? No; repeated legitimate encounters must be preserved.
- Why reject missing forecast dates? Missing observation is not evidence of zero arrivals.
- Can behavioral coefficients establish causation? No; observational confounding and design limitations remain.
- Why no accuracy shown yet? No genuine model experiment exists; a fabricated number would invalidate the project.

## Primary dataset and software references
- ISIC data/licensing and HAM10000 citation: https://challenge.isic-archive.com/data/
- MIT MIMIC access guidance: https://mimic.mit.edu/docs/faq/how-to-get-access.html
- PhysioNet usage/access FAQ: https://physionet.org/about/faqs/
- NHANES program candidate: https://www.cdc.gov/nchs/nhanes/ (cycle-specific manuals and usage suitability still require review before import).
- Next.js installation/system requirements: https://nextjs.org/docs/app/getting-started/installation
- PyTorch restricted weight loading: https://docs.pytorch.org/docs/stable/generated/torch.load.html

No UI screenshots are included because automated browser access was unavailable. No synthetic screenshots or arbitrary heatmaps are presented as evidence.
