/* Isolated identity fixtures, never real account credentials. */
import { expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AccountLogin from "../app/components/account-login";
import AccountPanel from "../app/components/account-panel";

it("signs in without browser credential storage and clears successful password input", async () => {
  const onToken = vi.fn();
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(
          JSON.stringify({ access_token: "isolated-fixture-token" }),
          { status: 200 },
        ),
    ),
  );
  const user = userEvent.setup();
  render(<AccountLogin onToken={onToken} />);
  await user.type(screen.getByLabelText("Username"), "fixture_user");
  await user.type(
    screen.getByLabelText("Password"),
    "isolated-fixture-password",
  );
  await user.click(screen.getByRole("button", { name: "Sign in" }));
  await waitFor(() =>
    expect(onToken).toHaveBeenCalledWith("isolated-fixture-token"),
  );
  expect(screen.getByLabelText("Password")).toHaveValue("");
  expect(localStorage.length).toBe(0);
});
it("surfaces failed credentials without establishing a session", async () => {
  const onToken = vi.fn();
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response(
          JSON.stringify({ detail: "Invalid username or password" }),
          { status: 401 },
        ),
    ),
  );
  const user = userEvent.setup();
  render(<AccountLogin onToken={onToken} />);
  await user.type(screen.getByLabelText("Username"), "fixture_user");
  await user.type(
    screen.getByLabelText("Password"),
    "isolated-fixture-password",
  );
  await user.click(screen.getByRole("button", { name: "Sign in" }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Invalid username or password",
  );
  expect(onToken).not.toHaveBeenCalled();
});
it("viewer profile does not offer account creation or dataset grants", async () => {
  const api = vi.fn(async () => ({
    id: "fixture-viewer-id",
    username: "fixture_viewer",
    role: "viewer",
  }));
  render(<AccountPanel api={api} datasets={[]} />);
  expect(await screen.findByText("fixture_viewer")).toBeVisible();
  expect(
    screen.queryByRole("button", { name: "Create account" }),
  ).not.toBeInTheDocument();
  expect(
    screen.queryByRole("button", { name: "Grant dataset read access" }),
  ).not.toBeInTheDocument();
  expect(api).toHaveBeenCalledTimes(1);
});
