/* Explicit isolated responses; never genuine clinical model evidence. */
import { expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ClinicalModelPanel from "../app/components/clinical-model-panel";

it("requires report review before explicit selection and never promotes on load", async () => {
  const user = userEvent.setup();
  const onResult = vi.fn();
  let selected = false;
  const api = vi.fn(async (path: string, init?: RequestInit) => {
    if (path === "/runs")
      return [
        {
          id: "fixture-run",
          kind: "clinical_ner_training",
          status: "completed",
        },
      ];
    if (path === "/runs/fixture-run")
      return {
        id: "fixture-run",
        status: "completed",
        result: { evaluation: { test_metrics: { micro: { f1: 0.4 } } } },
      };
    if (path === "/clinical-models/select/fixture-run") {
      expect(init?.method).toBe("POST");
      selected = true;
      return { research_only: true };
    }
    if (!selected) throw new Error("No clinical NER model selected");
    return {
      model_card: {
        source: "test-only",
        limitations: "Synthetic component fixture",
        evaluation: { micro: { precision: 0.5, recall: 0.4, f1: 0.44 } },
      },
    };
  });
  render(<ClinicalModelPanel api={api} onResult={onResult} canSelect />);
  const button = await screen.findByRole("button", {
    name: "Select reviewed NER model",
  });
  expect(button).toBeDisabled();
  expect(selected).toBe(false);
  await user.click(screen.getByRole("button", { name: "Review clinical run" }));
  expect(onResult).toHaveBeenCalledWith(
    expect.objectContaining({ id: "fixture-run" }),
  );
  await waitFor(() => expect(button).toBeEnabled());
  await user.click(button);
  await screen.findByText(/Recorded exact-span test precision 0.500/);
  expect(selected).toBe(true);
});
it("does not expose model-selection controls to readers", async () => {
  const api = vi.fn(async (path: string) =>
    path === "/runs"
      ? [
          {
            id: "fixture-run",
            kind: "clinical_ner_training",
            status: "completed",
          },
        ]
      : { model_card: { source: "test-only", limitations: "fixture" } },
  );
  render(<ClinicalModelPanel api={api} onResult={vi.fn()} />);
  await screen.findByRole("button", { name: "Review clinical run" });
  expect(
    screen.queryByRole("button", { name: "Select reviewed NER model" }),
  ).not.toBeInTheDocument();
});
