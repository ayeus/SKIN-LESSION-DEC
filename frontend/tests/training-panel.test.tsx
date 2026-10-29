/* Isolated component fixtures; no synthetic model is installed in the application. */
import { expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TrainingPanel from "../app/components/training-panel";

it("blocks training when source images are missing", async () => {
  const api = vi.fn(async () => ({
    ready: false,
    reason: "Image download/extraction is incomplete",
    manifest_rows: 10,
    missing_images: 10,
  }));
  render(<TrainingPanel api={api} onResult={vi.fn()} onChange={vi.fn()} />);
  expect(
    await screen.findByText("Image download/extraction is incomplete"),
  ).toBeVisible();
  expect(
    screen.getByRole("button", { name: "Start training experiment" }),
  ).toBeDisabled();
});
it("polls actual job state and never selects a completed model without a user action", async () => {
  const result = vi.fn(),
    change = vi.fn();
  const api = vi.fn(async (path: string, init?: RequestInit) => {
    if (path === "/training/readiness")
      return { ready: true, manifest_rows: 20, missing_images: 0 };
    if (path === "/training") {
      expect(JSON.parse(String(init?.body))).toMatchObject({
        architecture: "small_cnn",
        epochs: 1,
        pretrained: false,
      });
      return { id: "isolated-fixture", status: "pending" };
    }
    if (path === "/runs/isolated-fixture")
      return {
        id: "isolated-fixture",
        status: "completed",
        result: { history: [], manifest: { research_only: true } },
      };
    if (path === "/models/select/isolated-fixture")
      return { research_only: true };
    throw new Error("Unexpected test request: " + path);
  });
  const user = userEvent.setup();
  render(<TrainingPanel api={api} onResult={result} onChange={change} />);
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Start training experiment" }),
    ).toBeEnabled(),
  );
  await user.clear(screen.getByLabelText("Epochs"));
  await user.type(screen.getByLabelText("Epochs"), "1");
  await user.click(
    screen.getByRole("button", { name: "Start training experiment" }),
  );
  await waitFor(() => expect(result).toHaveBeenCalled(), { timeout: 3000 });
  expect(
    api.mock.calls.some(([path]) => path.startsWith("/models/select")),
  ).toBe(false);
  await user.click(
    screen.getByRole("button", {
      name: "Select this reviewed research artifact",
    }),
  );
  await waitFor(() =>
    expect(
      api.mock.calls.some(
        ([path]) => path === "/models/select/isolated-fixture",
      ),
    ).toBe(true),
  );
});
it("shows persisted training failure instead of a successful result", async () => {
  const result = vi.fn();
  const api = vi.fn(async (path: string) =>
    path === "/training/readiness"
      ? { ready: true }
      : path === "/training"
        ? { id: "failed-fixture", status: "pending" }
        : {
            id: "failed-fixture",
            status: "failed",
            error: "Identical image bytes across different groups",
          },
  );
  const user = userEvent.setup();
  render(<TrainingPanel api={api} onResult={result} onChange={vi.fn()} />);
  await waitFor(() =>
    expect(
      screen.getByRole("button", { name: "Start training experiment" }),
    ).toBeEnabled(),
  );
  await user.click(
    screen.getByRole("button", { name: "Start training experiment" }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Identical image bytes across different groups",
  );
  expect(result).not.toHaveBeenCalled();
});
