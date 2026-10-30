type Data = Record<string, any>;
export default function SenseEvidence({ result: r }: { result: Data }) {
  if (!r.sense_candidates) return null;
  return (
    <section aria-label="Contextual candidate evidence">
      <h3>Contextual candidates for review</h3>
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
                <th>Candidate</th>
                <th>Source definition</th>
                <th>Research score</th>
                <th>Shared context terms</th>
              </tr>
            </thead>
            <tbody>
              {r.sense_candidates.map((candidate: Data, index: number) => {
                const score =
                  candidate.context_similarity ?? candidate.uncalibrated_score;
                return (
                  <tr key={candidate.id || index}>
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
                        ? score.toFixed(4)
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
      <p>
        Scores are lexical similarity or uncalibrated classifier scores, not
        clinical confidence. Recognition and ranking do not verify clinical
        facts.
      </p>
    </section>
  );
}
