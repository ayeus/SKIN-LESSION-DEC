import EntityDocument from "./entity-document";

type Data = Record<string, any>;

const label = (value: string) => value.replaceAll("_", " ");
const score = (value: unknown, digits = 2) =>
  typeof value === "number" && Number.isFinite(value)
    ? value.toFixed(digits)
    : "Not measured";
const excerpt = (value: string, max = 380) =>
  value.length > max ? value.slice(0, max).trim() + "…" : value;

function Preprocessing({ value }: { value?: Data }) {
  if (!value) return null;
  return (
    <details>
      <summary>How the text was prepared</summary>
      <ul>
        <li>
          Lowercase text: {value.lowercase_tfidf_features ? "yes" : "no"}.
        </li>
        <li>
          Stop-word removal:{" "}
          {value.stop_words ? "configured" : "off by default"}.
        </li>
        <li>
          Negation words such as “no” and “not” are kept in the text features.
        </li>
        <li>
          Lemmatization: {value.lookup_lemmatization ? "on" : "off"}; this is
          basic English processing, not medical language understanding.
        </li>
      </ul>
      <p>{value.limitation}</p>
    </details>
  );
}

function ClusterResults({ result: r }: { result: Data }) {
  const groups = Object.entries(r.top_terms || {});
  return (
    <section aria-labelledby="text-cluster-title">
      <h3 id="text-cluster-title">T10 · Document groups</h3>
      <p>
        The system grouped similar documents by their word patterns. “Group 1”
        and “Group 2” are just names; neither group is a diagnosis or a ranking.
        The terms below are the words most characteristic of each group.
      </p>
      <p>
        Documents grouped: {r.assignments.length}. Groups found: {groups.length}
        .
      </p>
      <div className="table-wrap">
        <table>
          <caption>
            The “documents in group” count shows how many corpus records were
            assigned there. Common terms help describe the group but do not
            validate its medical meaning.
          </caption>
          <thead>
            <tr>
              <th>Group</th>
              <th>Documents in group</th>
              <th>Common words that describe this group</th>
            </tr>
          </thead>
          <tbody>
            {groups.map(([group, terms]) => (
              <tr key={group}>
                <th scope="row">Group {Number(group) + 1}</th>
                <td>
                  {
                    r.assignments.filter((v: number) => String(v) === group)
                      .length
                  }
                </td>
                <td>
                  {Array.isArray(terms) ? terms.join(", ") : "Not recorded"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {typeof r.silhouette_cosine === "number" && (
        <p className="notice">
          Group-separation score: {score(r.silhouette_cosine, 3)} on a scale
          from −1 to +1. Higher can mean clearer word-pattern groups; around
          zero means overlap. It is not an accuracy score or proof of medical
          groups.
        </p>
      )}
      <Preprocessing value={r.text_preprocessing} />
    </section>
  );
}

function ClassificationResults({ result: r }: { result: Data }) {
  const report = r.evaluation || {};
  const classes = Object.entries(report).filter(
    ([name, value]) =>
      value &&
      typeof value === "object" &&
      !["accuracy", "macro avg", "weighted avg"].includes(name),
  );
  return (
    <section aria-labelledby="text-classification-title">
      <h3 id="text-classification-title">T10 · Text-label results</h3>
      <p>
        The model learned from the training texts, then predicted labels for
        separate held-out texts. These are corpus labels, not confirmed clinical
        conclusions.
      </p>
      <p>Method used: {r.method || "recorded text classifier"}.</p>
      <div
        className="metrics"
        aria-label="Clinical text classification summary"
      >
        <div>
          <strong>{score(report.accuracy * 100, 1)}%</strong>
          <span>Accuracy · correct overall</span>
          <small>Share of held-out texts assigned the right label.</small>
        </div>
        <div>
          <strong>{score(report["macro avg"]?.["f1-score"], 2)}</strong>
          <span>Macro F1 · average across labels</span>
          <small>Balances missed examples and incorrect assignments.</small>
        </div>
        <div>
          <strong>{score(r.train_rows, 0)}</strong>
          <span>Training texts</span>
          <small>Used to teach the text classifier.</small>
        </div>
        <div>
          <strong>{score(r.test_predictions?.length, 0)}</strong>
          <span>Held-out test texts</span>
          <small>Kept separate to check its predictions.</small>
        </div>
      </div>
      <p>
        Precision means “when the model chooses this label, how often is it
        right?” Recall means “of texts that really have this label, how many did
        it find?” F1 balances those two. Each score ranges from 0 to 1; closer
        to 1 is better on this test set.
      </p>
      <div className="table-wrap">
        <table>
          <caption>
            Scores for each real label in the held-out test texts.
          </caption>
          <thead>
            <tr>
              <th>Dataset label</th>
              <th>Precision · correct when chosen</th>
              <th>Recall · examples found</th>
              <th>F1 · balance of precision and recall</th>
              <th>Test examples</th>
            </tr>
          </thead>
          <tbody>
            {classes.map(([name, values]) => (
              <tr key={name}>
                <th scope="row">{label(name)}</th>
                <td>{score((values as Data).precision)}</td>
                <td>{score((values as Data).recall)}</td>
                <td>{score((values as Data)["f1-score"])}</td>
                <td>{score((values as Data).support, 0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {r.test_predictions?.length > 0 && (
        <details>
          <summary>
            See held-out text examples and their predicted labels
          </summary>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Text excerpt</th>
                  <th>Dataset label</th>
                  <th>Model-assigned label</th>
                  <th>Match?</th>
                </tr>
              </thead>
              <tbody>
                {r.test_predictions
                  .slice(0, 20)
                  .map((item: Data, index: number) => (
                    <tr key={String(item.document_index) + "-" + index}>
                      <td>{excerpt(item.text)}</td>
                      <td>{label(item.observed_label)}</td>
                      <td>{label(item.predicted_label)}</td>
                      <td>
                        {item.observed_label === item.predicted_label
                          ? "Correct for this example"
                          : "Different from dataset label"}
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
      <Preprocessing value={r.text_preprocessing} />
      <p className="notice">{r.limitation}</p>
    </section>
  );
}

function SearchResults({ result: r }: { result: Data }) {
  return (
    <section aria-labelledby="text-search-title">
      <h3 id="text-search-title">T12 · Documents ranked by your search</h3>
      <p>
        Results are ordered by how closely their words match the search.{" "}
        {r.method === "bm25" ? "BM25" : "TF-IDF"} gives a text-match score, not
        a probability, diagnosis, or measure of medical truth. Compare the
        scores only within this same search.
      </p>
      {r.explanation && <p>{r.explanation}</p>}
      {r.results?.length ? (
        <ol>
          {r.results.slice(0, 10).map((item: Data, index: number) => (
            <li key={item.document_index}>
              <strong>
                Result {index + 1} · match score {score(item.score, 3)}
              </strong>
              <p>{excerpt(item.text)}</p>
            </li>
          ))}
        </ol>
      ) : (
        <p>No documents matched the current query.</p>
      )}
      <Preprocessing value={r.text_preprocessing} />
    </section>
  );
}

function EntityResults({ result: r }: { result: Data }) {
  const visible = r.documents.slice(0, 5);
  const remaining = r.documents.slice(5);
  const totalMentions = r.documents.reduce(
    (total: number, document: Data) => total + (document.entities?.length || 0),
    0,
  );
  const examples = (documents: Data[], start: number) =>
    documents.map((document, index) => (
      <article key={start + index}>
        <h4>Text sample {start + index + 1}</h4>
        <EntityDocument text={document.text} entities={document.entities} />
      </article>
    ));
  return (
    <section aria-labelledby="text-entity-title">
      <h3 id="text-entity-title">T11 · Medical terms found in the text</h3>
      <p>
        The configured language model highlights terms it recognizes. Labels
        describe the kind of term; they do not confirm that the clinical claim
        is true. Negation is only reported when the configured model supports
        it.
      </p>
      <p>
        The model marked {totalMentions} possible terms across{" "}
        {r.documents.length} texts. Showing {visible.length} text samples to
        start.
      </p>
      {examples(visible, 0)}
      {remaining.length > 0 && (
        <details>
          <summary>Show the remaining {remaining.length} text samples</summary>
          {examples(remaining, 5)}
        </details>
      )}
    </section>
  );
}

export default function ClinicalTextEvidence({ result: r }: { result: Data }) {
  if (r.assignments && r.top_terms) return <ClusterResults result={r} />;
  if (r.evaluation && r.test_predictions && !r.sense_candidates)
    return <ClassificationResults result={r} />;
  if (r.model_card && Array.isArray(r.documents))
    return <EntityResults result={r} />;
  if (r.method && Array.isArray(r.results)) return <SearchResults result={r} />;
  return null;
}
