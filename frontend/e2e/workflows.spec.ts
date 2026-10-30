/** Real browser -> Next proxy -> disposable migrated API/DB. All input fixtures
 * are explicitly synthetic mathematical data, never healthcare observations. */
import { test, expect, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import { resolve } from "node:path";
const TOKEN = "isolated-browser-test-token-not-a-real-secret";
async function connect(page: Page) {
  await page.goto("/");
  await page.getByLabel("Research access token").fill(TOKEN);
  await page.getByRole("button", { name: "Connect workspace" }).click();
  await expect(page.getByText("API connected", { exact: true })).toBeVisible();
}
async function navigate(page: Page, name: string) {
  const toggle = page.getByRole("button", { name: "Toggle navigation" });
  if (await toggle.isVisible()) await toggle.click();
  await page.getByRole("link", { name, exact: true }).click();
  await expect(
    page.getByRole("heading", { level: 1, name, exact: true }),
  ).toBeVisible();
}
async function noOverflow(page: Page) {
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    ),
  ).toBe(true);
}
test("authentication, protected navigation and missing-model state", async ({
  page,
}, testInfo) => {
  await page.goto("/");
  await expect(page.getByLabel("Research access token")).toBeVisible();
  await page
    .getByLabel("Research access token")
    .fill("deliberately-invalid-test-token");
  await page.getByRole("button", { name: "Connect workspace" }).click();
  await expect(
    page
      .getByRole("alert")
      .filter({ hasText: /session expired|access was revoked/i }),
  ).toBeVisible();
  await connect(page);
  await navigate(page, "Lesion detection");
  await expect(page).toHaveURL(/#inference$/);
  await expect(
    page.getByText("A trained lesion model is required", { exact: false }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Run research inference" }),
  ).toHaveCount(0);
  await noOverflow(page);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: testInfo.outputPath("isolated-empty-model-state.png"),
    fullPage: true,
  });
  expect(await page.evaluate(() => Object.keys(localStorage))).toEqual([]);
});
test("actual image processing, invalid-file errors and persisted export", async ({
  page,
}, testInfo) => {
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await connect(page);
  await navigate(page, "Image processing lab");
  await page
    .getByLabel("Image", { exact: true })
    .setInputFiles(
      resolve("e2e/fixtures/synthetic-geometric-algorithm-test.png"),
    );
  await page.getByLabel("Processing method").selectOption("gamma");
  await page.getByLabel("Algorithm parameters (JSON)").fill('{"gamma":1}');
  const response = page.waitForResponse(
    (r) =>
      r.url().endsWith("/api/images/process") &&
      r.request().method() === "POST",
  );
  await page
    .getByRole("button", { name: "Run image processing", exact: true })
    .click();
  const operation = await response;
  expect(operation.ok()).toBe(true);
  const run = await operation.json();
  expect(run.result.image).toBe(run.result.original);
  await expect(
    page.getByRole("img", { name: "Algorithm output", exact: true }),
  ).toBeVisible();
  await page.getByText("View chart data", { exact: true }).click();
  await expect(
    page.getByText("Actual values plotted in this chart", { exact: true }),
  ).toBeVisible();
  const firstDataRow = page.getByRole("table").getByRole("row").nth(1);
  await expect(firstDataRow.getByRole("cell").nth(1)).toHaveText(
    String(run.result.histogram[0][0]),
  );
  const accessibility = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  expect(accessibility.violations).toEqual([]);
  const download = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Export report", exact: true })
    .click();
  const artifact = await download;
  expect(artifact.suggestedFilename()).toBe(`research-${run.id}.json`);
  await noOverflow(page);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: testInfo.outputPath("isolated-geometric-image-processing.png"),
    fullPage: true,
  });
  await page.getByLabel("Image", { exact: true }).setInputFiles({
    name: "synthetic-invalid.png",
    mimeType: "image/png",
    buffer: Buffer.from("invalid fixture"),
  });
  await page
    .getByRole("button", { name: "Run image processing", exact: true })
    .click();
  await expect(
    page.getByRole("alert").filter({ hasText: /Invalid or oversized image/i }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});
test("CSV import, true 3D reduction and exact coordinate inspection", async ({
  page,
}, testInfo) => {
  await connect(page);
  await navigate(page, "EHR & dataset management");
  const name = `synthetic-geometry-${testInfo.project.name}.csv`;
  await page.getByLabel("Dataset file").setInputFiles({
    name,
    mimeType: "text/csv",
    buffer: Buffer.from("a,b,c\n0,0,0\n1,2,-1\n2,4,-2\n3,6,-3\n4,8,-4\n"),
  });
  await page
    .getByRole("combobox", { name: "Modality", exact: true })
    .selectOption("tabular");
  await page
    .getByLabel("Source URL / citation")
    .fill("Explicit synthetic mathematical browser-test fixture");
  await page
    .getByLabel("License / authorization")
    .fill("Isolated test only; no healthcare data");
  await page.getByRole("checkbox", { name: /I confirm authorized/ }).check();
  await page.getByRole("button", { name: "Validate & import" }).click();
  await expect(page.getByRole("button", { name, exact: true })).toBeVisible();
  await navigate(page, "Dimensionality reduction");
  await page
    .getByLabel("Source dataset")
    .selectOption({ label: `${name} (5 rows)` });
  await page
    .getByLabel("Numeric feature columns (comma separated)")
    .fill("a,b,c");
  await page.getByLabel("Embedding dimensions").selectOption("3");
  await page
    .getByRole("button", { name: "Execute analysis", exact: true })
    .click();
  await expect(
    page.getByRole("heading", { name: "PCA: 3-dimensional exploration" }),
  ).toBeVisible();
  const horizontal = page.getByRole("slider", { name: /Horizontal rotation/ });
  await horizontal.focus();
  await horizontal.press("ArrowRight");
  await expect(horizontal).toHaveValue("26");
  await page.getByLabel("Inspect input row").fill("3");
  await expect(page.getByText(/Input row 3: Component 1:/)).toBeVisible();
  await noOverflow(page);
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.screenshot({
    path: testInfo.outputPath("isolated-3d-pca.png"),
    fullPage: true,
  });
});

test("automated accessibility on sign-in and actual module forms", async ({
  page,
}) => {
  await page.goto("/");
  for (const location of [
    "sign-in",
    "Research overview",
    "Image processing lab",
    "EHR & dataset management",
    "CNN training & evaluation",
  ]) {
    if (location === "Research overview") await connect(page);
    else if (location !== "sign-in") await navigate(page, location);
    const audit = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
      .analyze();
    expect(
      audit.violations,
      location +
        ": " +
        JSON.stringify(
          audit.violations.map((v) => ({
            id: v.id,
            nodes: v.nodes.map((n) => ({
              target: n.target,
              summary: n.failureSummary,
            })),
          })),
        ),
    ).toEqual([]);
  }
});
