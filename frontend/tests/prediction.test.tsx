/* Isolated result fixture checks rendering only, not a model prediction. */
import { expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Results } from "../app/page";

it("shows the returned top-ranked label with its research limitation", () => {
  render(
    <Results
      value={{
        research_prediction: "NV",
        calibrated: false,
        scores: { NV: 0.61, MEL: 0.39 },
        limitation: "Uncalibrated research scores.",
      }}
    />,
  );
  expect(screen.getByRole("status")).toHaveTextContent(
    "Research model top-ranked label: NV",
  );
  expect(screen.getByRole("status")).toHaveTextContent(
    "not a diagnosis or a measure of clinical confidence",
  );
});
