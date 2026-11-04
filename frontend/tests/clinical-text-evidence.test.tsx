/* Synthetic UI report fixtures test explanations, not clinical data/results. */
import { expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import ClinicalTextEvidence from "../app/components/clinical-text-evidence";

it("explains document groups and the silhouette score in plain language", () => {
  render(
    <ClinicalTextEvidence
      result={{
        assignments: [0, 0, 1],
        top_terms: { "0": ["rash", "skin"], "1": ["fever"] },
        silhouette_cosine: 0.24,
      }}
    />,
  );

  expect(
    screen.getByText("Documents grouped: 3. Groups found: 2."),
  ).toBeVisible();
  expect(screen.getByText("Group 1")).toBeVisible();
  expect(screen.getByText("2")).toBeVisible();
  expect(screen.getByText(/not an accuracy score/)).toBeVisible();
});

it("labels classifier scores and compares actual corpus labels with predictions", () => {
  render(
    <ClinicalTextEvidence
      result={{
        method: "TF-IDF + logistic regression",
        train_rows: 12,
        test_predictions: [
          {
            document_index: 1,
            text: "Example source excerpt.",
            observed_label: "Disease_or_Syndrome",
            predicted_label: "Disease_or_Syndrome",
          },
        ],
        evaluation: {
          accuracy: 1,
          "macro avg": { "f1-score": 1 },
          Disease_or_Syndrome: {
            precision: 1,
            recall: 1,
            "f1-score": 1,
            support: 1,
          },
        },
        limitation: "Held-out research baseline.",
      }}
    />,
  );

  expect(screen.getByText("100.0%")).toBeVisible();
  expect(screen.getByText(/Accuracy · correct overall/)).toBeVisible();
  expect(screen.getByText(/Precision means/)).toBeVisible();
  expect(screen.getAllByText("Disease or Syndrome").length).toBeGreaterThan(0);
  expect(
    screen.getByText(/Different from dataset label|Correct for this example/),
  ).toBeInTheDocument();
});

it("explains BM25 ranking scores as relative text matches, not probabilities", () => {
  render(
    <ClinicalTextEvidence
      result={{
        method: "bm25",
        results: [
          { document_index: 7, score: 2.75, text: "A matching case report." },
        ],
        explanation: "Lexical relevance only.",
      }}
    />,
  );

  expect(screen.getByText(/not a probability/)).toBeVisible();
  expect(screen.getByText("Result 1 · match score 2.750")).toBeVisible();
  expect(screen.getByText("A matching case report.")).toBeVisible();
});
