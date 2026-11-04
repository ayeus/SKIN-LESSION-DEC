/* Sample registry entries exercise help text only; they are not patient data. */
import { expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SectionGuide, { StartHere } from "../app/components/section-guides";

const datasets = [
  {
    id: "ehr-patients",
    name: "MIMIC-IV public demo 2.2: patients",
    modality: "ehr",
    profile: { rows: 100 },
  },
  {
    id: "uk-date-count",
    name: "UKHSA England COVID admissions",
    modality: "demand",
    profile: { rows: 120 },
  },
  {
    id: "nhanes-adults",
    name: "NHANES 2017–2018 adults: documented exploratory fields",
    modality: "weight",
    profile: { rows: 5569 },
  },
  {
    id: "maccrobat-docs",
    name: "MACCROBAT2020: published clinical case reports",
    modality: "clinical_text",
    profile: { rows: 200 },
  },
];

it("shows quick-start links for the data already in the workspace", async () => {
  const onNavigate = vi.fn();
  render(
    <StartHere
      page="dashboard"
      datasets={datasets}
      modelReady
      onNavigate={onNavigate}
    />,
  );
  expect(screen.getByText(/MIMIC-IV public demo/)).toBeVisible();
  expect(screen.getByText(/120 days/)).toBeVisible();
  expect(screen.getByText(/5569 adults/)).toBeVisible();
  await userEvent
    .setup()
    .click(screen.getByRole("button", { name: "Open forecast walkthrough" }));
  expect(onNavigate).toHaveBeenCalledWith("forecast", "uk-date-count");
});

it("gives the real NHANES feature names for the adult weight tutorials", () => {
  render(
    <SectionGuide
      page="research"
      datasets={datasets}
      modelReady
      onNavigate={vi.fn()}
    />,
  );
  expect(screen.getAllByText(/bmi_kg_m2/)).toHaveLength(2);
  expect(screen.getByText(/sleep_weekday_hours_exact/)).toBeVisible();
  expect(screen.getByText(/participant_id/)).toBeVisible();
});

it("explains the MIMIC timestamp mapping and row-count meaning for T8", () => {
  render(
    <SectionGuide
      page="overview"
      datasets={datasets}
      modelReady
      onNavigate={vi.fn()}
    />,
  );
  expect(screen.getByText(/admittime/)).toBeVisible();
  expect(screen.getByText(/%Y-%m-%d %H:%M:%S/)).toBeVisible();
  expect(
    screen.getByText(/not automatically a unique patient count/),
  ).toBeVisible();
});
