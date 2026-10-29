"""Strict de-identified research import subset of FHIR R4, not a FHIR server/validator."""

from typing import Annotated, Literal, Union
import json
import pandas as pd
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    AwareDatetime,
    TypeAdapter,
    model_validator,
)

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9\-.]{1,64}$")]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class PatientRef(Strict):
    reference: Annotated[str, Field(pattern=r"^Patient/[A-Za-z0-9\-.]{1,64}$")]


class EncounterRef(Strict):
    reference: Annotated[str, Field(pattern=r"^Encounter/[A-Za-z0-9\-.]{1,64}$")]


class Coding(Strict):
    system: str
    code: str
    display: str | None = None


class Concept(Strict):
    coding: list[Coding] = Field(min_length=1)


class Period(Strict):
    start: AwareDatetime
    end: AwareDatetime | None = None

    @model_validator(mode="after")
    def ordered(self):
        if self.end and self.end < self.start:
            raise ValueError("Period ends before it starts")
        return self


class Quantity(Strict):
    value: float
    unit: str
    system: str | None = None
    code: str | None = None


class Patient(Strict):
    resourceType: Literal["Patient"]
    id: Identifier
    gender: Literal["male", "female", "other", "unknown"] | None = None


class Encounter(Strict):
    resourceType: Literal["Encounter"]
    id: Identifier
    status: Literal[
        "planned",
        "arrived",
        "triaged",
        "in-progress",
        "onleave",
        "finished",
        "cancelled",
        "entered-in-error",
        "unknown",
    ]
    subject: PatientRef
    period: Period | None = None
    classification: Coding | None = Field(default=None, alias="class")


class Observation(Strict):
    resourceType: Literal["Observation"]
    id: Identifier
    status: Literal[
        "registered",
        "preliminary",
        "final",
        "amended",
        "corrected",
        "cancelled",
        "entered-in-error",
        "unknown",
    ]
    subject: PatientRef
    encounter: EncounterRef | None = None
    code: Concept
    effectiveDateTime: AwareDatetime | None = None
    valueQuantity: Quantity


class Condition(Strict):
    resourceType: Literal["Condition"]
    id: Identifier
    subject: PatientRef
    encounter: EncounterRef | None = None
    code: Concept
    onsetDateTime: AwareDatetime | None = None
    clinicalStatus: Concept | None = None


Resource = Annotated[
    Union[Patient, Encounter, Observation, Condition],
    Field(discriminator="resourceType"),
]


class Entry(Strict):
    resource: Resource


class Bundle(Strict):
    resourceType: Literal["Bundle"]
    type: Literal["collection"]
    entry: list[Entry] = Field(min_length=1, max_length=10000)


def parse(data):
    try:
        bundle = Bundle.model_validate(json.loads(data))
    except (ValidationError, ValueError, TypeError) as error:
        # Never echo rejected PHI fields or their values into logs/error responses.
        raise ValueError(
            "Invalid FHIR research subset. Use a collection Bundle with de-identified Patient/Encounter/Observation/Condition resources, relative references and offset timestamps. Names, identifiers, narratives, extensions and unsupported fields are rejected; see docs/FHIR_SUBSET.md."
        ) from error
    indexed = {}
    for entry in bundle.entry:
        resource = entry.resource
        key = f"{resource.resourceType}/{resource.id}"
        if key in indexed:
            raise ValueError("Duplicate resource type/id in FHIR bundle")
        indexed[key] = resource
    rows = []
    for key, resource in indexed.items():
        row = {"resource_type": resource.resourceType, "resource_id": resource.id}
        if isinstance(resource, Patient):
            row["gender"] = resource.gender
        else:
            subject = resource.subject.reference
            if subject not in indexed:
                raise ValueError("FHIR subject reference has no Patient in bundle")
            row["subject_id"] = subject.split("/")[1]
            if isinstance(resource, Encounter):
                row["status"] = resource.status
                if resource.period:
                    row.update(
                        start=resource.period.start.isoformat(),
                        end=resource.period.end.isoformat()
                        if resource.period.end
                        else None,
                    )
            else:
                if resource.encounter:
                    ref = resource.encounter.reference
                    if ref not in indexed:
                        raise ValueError("FHIR encounter reference missing from bundle")
                    if indexed[ref].subject.reference != subject:
                        raise ValueError(
                            "FHIR encounter and clinical resource refer to different patients"
                        )
                    row["encounter_id"] = ref.split("/")[1]
                row["codings_json"] = json.dumps(
                    [v.model_dump(exclude_none=True) for v in resource.code.coding]
                )
                if isinstance(resource, Observation):
                    row.update(
                        status=resource.status,
                        value=resource.valueQuantity.value,
                        unit=resource.valueQuantity.unit,
                    )
                    if resource.effectiveDateTime:
                        row["effective_time"] = resource.effectiveDateTime.isoformat()
                elif resource.onsetDateTime:
                    row["onset_time"] = resource.onsetDateTime.isoformat()
        rows.append(row)
    return pd.DataFrame(rows)
