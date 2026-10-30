type Entity = {
  start: number;
  end: number;
  text: string;
  label: string;
  negated: boolean | null;
  uncertainty?: string;
};
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
          title={`${e.label}; negation: ${e.negated === null ? "unknown" : e.negated}`}
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
      <ul>
        {ordered.map((e, i) => (
          <li key={i}>
            <strong>{e.text}</strong> {e.label} (characters {e.start}–{e.end});
            negation: {e.negated === null ? "unknown" : String(e.negated)}.{" "}
            {e.uncertainty}
          </li>
        ))}
      </ul>
    </>
  );
}
