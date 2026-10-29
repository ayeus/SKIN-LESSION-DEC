# FHIR R4 research import subset

This is a strict tabular ingestion profile, not a complete FHIR implementation or certified FHIR server. Reference: https://hl7.org/fhir/R4/bundle.html . Import JSON as EHR with source/license and explicit de-identification authorization. It preserves source bytes only after subset validation. No arbitrary remote references are fetched.

Supported envelope: Bundle with resourceType=Bundle,type=collection,entry=[{resource:...}]. 1–10,000 entries. Unknown fields are rejected, not silently dropped. Resources:

| Resource | Supported fields |
|---|---|
| Patient | resourceType,id, optional gender (male/female/other/unknown) |
| Encounter | resourceType,id,status,subject.reference, optional period.start/end and class coding |
| Observation | resourceType,id,status,subject,code.coding[],valueQuantity; optional encounter,effectiveDateTime |
| Condition | resourceType,id,subject,code.coding[]; optional encounter,onsetDateTime,clinicalStatus |

IDs must be pseudonymous FHIR logical IDs (1–64 letters/digits/hyphen/dot). References must be `Patient/id` or `Encounter/id` and resolve inside the collection. Encounter references must belong to the same patient as the observation/condition. Type+ID collisions and inverted periods are rejected. All supported timestamps require timezone offsets. Codings use system/code/optional display; all codings are preserved, not arbitrarily mapped. Quantities use finite numeric value/unit/optional system/code; no silent unit conversion.

Patient names, direct identifiers, addresses, telecom, birth dates, narratives, contained resources, extensions, medication resources, fullUrl/urn references, components and other value types are intentionally unsupported and rejected. No unsupported payload is persisted before rejection; validation errors do not echo its values. This limited field check does not prove de-identification—pseudonymous IDs, code display strings and dates still require appropriate authorized handling.

The resulting table has resource_type/resource_id, optional subject_id/encounter_id, gender/status/timestamps, codings_json and value/unit. Row totals are resources, not automatically patient/encounter totals. Filter resource_type explicitly before interpreting aggregates. Patient/encounter relationships are validated during import. Raw source remains separate from later transformations.

No genuine FHIR clinical dataset has been imported yet. Synthetic tests cover valid linked resources, mixed-patient references, unknown/identifying fields, duplicate IDs, timestamp and finite-measurement validation.
