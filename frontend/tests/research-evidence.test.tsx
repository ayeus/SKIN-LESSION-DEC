/* Isolated mathematical/text fixtures, not clinical findings. */
import { expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import TrainingHistory from "../app/components/training-history";
import EntityDocument from "../app/components/entity-document";
it("renders actual NER loss and F1 as distinct series without CNN-only fields", () => {
  const Chart = vi.fn(() => null);
  render(
    <TrainingHistory
      history={[
        { epoch: 1, loss: 20, validation: { f1: 0.3 } },
        { epoch: 2, loss: 12, validation: { f1: 0.4 } },
      ]}
      Chart={Chart}
    />,
  );
  expect(screen.getByText("Clinical NER training loss")).toBeInTheDocument();
  expect(Chart.mock.calls.map((c) => (c as any[])[0].keys)).toEqual([
    ["training_loss"],
    ["validation_f1"],
  ]);
});
it("highlights exact character spans and safely escapes source markup", () => {
  const { container, rerender } = render(
    <EntityDocument
      text={"rash <script>sample</script>"}
      entities={[
        {
          start: 0,
          end: 4,
          text: "rash",
          label: "Sign_symptom",
          negated: null,
        },
      ]}
    />,
  );
  expect(container.querySelector("mark")?.textContent).toBe("rash");
  expect(container.querySelector("script")).toBeNull();
  expect(screen.getByText(/negation: unknown/)).toBeInTheDocument();
  rerender(
    <EntityDocument
      text="rash"
      entities={[
        {
          start: 1,
          end: 4,
          text: "rash",
          label: "Sign_symptom",
          negated: null,
        },
      ]}
    />,
  );
  expect(container.querySelector("mark")).toBeNull();
  expect(screen.getByText(/offsets are invalid/)).toBeInTheDocument();
});
