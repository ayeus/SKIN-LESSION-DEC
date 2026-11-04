type Entity = {
  start: number;
  end: number;
  text: string;
  label: string;
  negated: boolean | null;
  uncertainty?: string;
};
const entityLabels: Record<string, string> = {
  Disease_disorder: "Disease or disorder",
  Sign_symptom: "Symptom or sign",
  Medication: "Medication",
  Anatomical_site: "Body part or location",
  Procedure: "Medical procedure",
  Lab_value: "Lab test or value",
  Date: "Date or time",
};
const readableLabel = (value: string) =>
  entityLabels[value] || value.replaceAll("_", " ");
const negationText = (value: boolean | null) =>
  value === true
    ? "The model marked this mention as negated."
    : value === false
      ? "The model did not mark this mention as negated."
      : "Negation was not determined.";
export default function EntityDocument({
  text,
  entities,
}: {
  text: string;
  entities: Entity[];
}) {
  const ordered = [...entities].sort((a, b) => a.start - b.start);
  let previous = 0;
  const valid = ordered.every((e) => {
    const okay =
      Number.isInteger(e.start) &&
      Number.isInteger(e.end) &&
      e.start >= previous &&
      e.end > e.start &&
      e.end <= text.length &&
      text.slice(e.start, e.end) === e.text;
    previous = e.end;
    return okay;
  });
  const pieces: React.ReactNode[] = [];
  previous = 0;
  if (valid) {
    ordered.forEach((e, i) => {
      pieces.push(text.slice(previous, e.start));
      pieces.push(
        <mark
          key={i}
          title={`${readableLabel(e.label)}; ${negationText(e.negated)}`}
          style={{ padding: "1px 2px" }}
        >
          {text.slice(e.start, e.end)}
        </mark>,
      );
      previous = e.end;
    });
    pieces.push(text.slice(previous));
  }
  return (
    <>
      <p style={{ whiteSpace: "pre-wrap" }}>{valid ? pieces : text}</p>
      {!valid && (
        <p className="notice">
          Entity offsets are invalid or overlapping. Source text is shown
          without unreliable highlights.
        </p>
      )}
      {ordered.length ? (
        <ul>
          {ordered.map((e, i) => (
            <li key={i}>
              <strong>{e.text}</strong> — {readableLabel(e.label)}.{" "}
              {negationText(e.negated)}{" "}
              <small>
                Text position: characters {e.start}–{e.end}.
                {e.uncertainty ? ` ${e.uncertainty}.` : ""}
              </small>
            </li>
          ))}
        </ul>
      ) : (
        <p>No terms were recognized in this text by the configured model.</p>
      )}
    </>
  );
}
