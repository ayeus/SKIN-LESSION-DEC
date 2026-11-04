type Data = Record<string, any>;
export default function SenseEvidence({ result: r }: { result: Data }) {
  if (!r.sense_candidates) return null;
  const scoreLabel = r.sense_candidates.some(
    (candidate: Data) => typeof candidate.context_similarity === "number",
  )
    ? "Text-match score"
    : "Model ranking score";
  return (
    <section aria-label="Contextual candidate evidence">
      <h3>Possible meanings ranked for review</h3>
      <p>{r.status || r.resolution}</p>
      {r.inventory && (
        <p>
          {r.inventory.attribution} · {r.inventory.version}. Source:{" "}
          <a href={r.inventory.source} target="_blank" rel="noreferrer">
            NLM terminology documentation
          </a>
        </p>
      )}
      {r.candidate_generation && <p>{r.candidate_generation}</p>}
      <p className="notice">{r.uncertainty || r.reason || r.method}</p>
      {r.sense_candidates.length ? (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Rank</th>
                <th>Possible meaning</th>
                <th>Source definition</th>
                <th>{scoreLabel} (not certainty)</th>
                <th>Words shared with the context</th>
              </tr>
            </thead>
            <tbody>
              {r.sense_candidates.map((candidate: Data, index: number) => {
                const score =
                  candidate.context_similarity ?? candidate.uncalibrated_score;
                return (
                  <tr key={candidate.id || index}>
                    <td>Rank {index + 1}</td>
                    <td>
                      {candidate.label || candidate.sense}
                      {candidate.id && /^D\d+$/.test(candidate.id) && (
                        <>
                          <br />
                          <a
                            href={"https://id.nlm.nih.gov/mesh/" + candidate.id}
                            target="_blank"
                            rel="noreferrer"
                          >
                            {candidate.id}
                          </a>
                        </>
                      )}
                    </td>
                    <td>{candidate.definition || "Definition not supplied"}</td>
                    <td>
                      {typeof score === "number" && Number.isFinite(score)
                        ? score.toFixed(3)
                        : "Not recorded"}
                    </td>
                    <td>
                      {candidate.shared_context_terms?.join(", ") ||
                        "No lexical overlap recorded"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <p>No source candidates found. No arbitrary sense was substituted.</p>
      )}
      <p className="notice">
        Candidates are ordered from best text match to lower text match for this
        input. The score is not a probability or clinical confidence, and
        ranking does not verify a medical fact.
      </p>
    </section>
  );
}
