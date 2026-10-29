/* Synthetic HTTP responses are isolated component-test fixtures, never application data. */
import { beforeEach, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Home from "../app/page";
beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async (url: string) =>
        new Response(
          JSON.stringify(
            url.endsWith("/status")
              ? {
                  datasets: 0,
                  processed_images: 0,
                  completed_runs: 0,
                  model_available: false,
                  modalities: {},
                }
              : [],
          ),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
    ),
  );
});
async function unlock() {
  const user = userEvent.setup();
  render(<Home />);
  await user.type(
    screen.getByLabelText("Research access token"),
    "isolated-component-test-token",
  );
  await user.click(screen.getByRole("button", { name: "Connect workspace" }));
  await screen.findByText("API connected");
  return user;
}
it("requires access before rendering data and never persists the token", () => {
  render(<Home />);
  expect(screen.getByLabelText("Research access token")).toHaveAttribute(
    "minlength",
    "24",
  );
  expect(screen.queryByText("Imported datasets")).not.toBeInTheDocument();
  expect(localStorage.length).toBe(0);
});
it("shows actual zero counts and disables lesion prediction without a model", async () => {
  const user = await unlock();
  expect(screen.getByText("Awaiting model")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Lesion detection" }));
  expect(screen.getByText("A trained lesion model is required")).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "Run research inference" }),
  ).not.toBeInTheDocument();
});
it("requires authorized files and provenance to import data", async () => {
  const user = await unlock();
  await user.click(
    screen.getByRole("button", { name: "EHR & dataset management" }),
  );
  expect(screen.getByLabelText("Dataset file")).toBeRequired();
  expect(screen.getByLabelText("Source URL / citation")).toBeRequired();
  expect(screen.getByLabelText("License / authorization")).toBeRequired();
  expect(screen.getByRole("checkbox")).toBeRequired();
  expect(screen.getByText(/No datasets imported/)).toBeVisible();
});
it("shows missing operational inputs instead of fabricated demand", async () => {
  const user = await unlock();
  await user.click(screen.getByRole("button", { name: "Patient demand" }));
  expect(screen.getByText("Waiting for a compatible dataset")).toBeVisible();
  expect(screen.getByText(/28 complete daily observations/)).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "Execute analysis" }),
  ).not.toBeInTheDocument();
});
it("validates image upload and clears data when workspace is locked", async () => {
  const user = await unlock();
  await user.click(
    screen.getByRole("button", { name: "Image processing lab" }),
  );
  expect(screen.getByLabelText("Image", { exact: true })).toBeRequired();
  expect(screen.getByLabelText("Image", { exact: true })).toHaveAttribute(
    "accept",
    "image/png,image/jpeg,image/webp",
  );
  await user.click(screen.getByRole("button", { name: "Lock workspace" }));
  expect(screen.getByLabelText("Research access token")).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "Run image processing" }),
  ).not.toBeInTheDocument();
});
it("surfaces API authentication failures without inventing metrics", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(
          JSON.stringify({ detail: "Valid research access token required" }),
          { status: 401 },
        ),
    ),
  );
  const user = userEvent.setup();
  render(<Home />);
  await user.type(
    screen.getByLabelText("Research access token"),
    "invalid-component-test-token",
  );
  await user.click(screen.getByRole("button", { name: "Connect workspace" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Valid research access token required",
  );
  expect(screen.getByText("API not connected")).toBeVisible();
});
