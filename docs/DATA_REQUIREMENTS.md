# Dataset requirements and provenance

No real dataset is currently installed or approved. Each import requires source URL/citation, license, owner attestation and modality. Raw data remains separate from transformed output. An attestation is not automated de-identification.

| Area | Required format | Candidate and limitations |
|---|---|---|
| Lesions T5–6 | CSV image_path,label,group_id; paths relative to image directory, group_id patient where available, otherwise lesion with limitation declared | ISIC/HAM10000 https://challenge.isic-archive.com/data/ ; download-specific license (2018 aggregate CC-BY-NC), repeated lesion images must stay together; patient IDs not guaranteed. Dermatoscopy does not validate consumer phone photos. |
| Masks T4 | binary PNG per source image, identical shape with documented annotation provenance | ISIC segmentation resources; mask license and pairing must be checked independently. |
| EHR T1–3,8 | de-identified CSV/XLSX with dictionary, encounter key, explicit dates/units/categories | MIMIC https://mimic.mit.edu/docs/gettingstarted/ ; credentialing, training and DUA required. This app does not bypass access. |
| Notes T10–12 | CSV text, optional genuine label and group identifier; no direct identifiers | MIMIC-IV-Note requires separate access and DUA. A generic English spaCy model is not accepted as clinical NER validation. |
| Demand T7–9 | CSV date,count with documented observation frequency, complete daily records; optional department/staff/service fields | Authorized hospital daily operational aggregates preferred. Shifted MIMIC dates require careful suitability assessment; do not assume valid calendar demand. |
| Weight T14–15 | numeric CSV with dictionary, adult inclusion, outcome, behaviors, confounders, units, missing codes | CDC NHANES https://www.cdc.gov/nchs/nhanes/ ; join cycle-specific participant IDs, inspect variable manuals. Survey weights/design required for population estimates; unweighted results exploratory only. |

## Verified source references (2026-10-29)
- ISIC challenge data page documents image/label/grouping resources and specific licenses: https://challenge.isic-archive.com/data/
- MIT MIMIC access guidance requires training, credentialing and DUA: https://mimic.mit.edu/docs/faq/how-to-get-access.html
- PhysioNet credentialed data cannot be shared with users lacking individual access: https://physionet.org/about/faqs/

No download or license acceptance has been performed on the owner's behalf.
