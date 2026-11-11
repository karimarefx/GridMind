import { test, expect } from "@playwright/test";
test("replay, coordinated reset, simulation and evidence walkthrough", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  const external: string[] = [];
  page.on("request", (r) => {
    if (!r.url().startsWith("http://127.0.0.1:4173")) external.push(r.url());
  });
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Control center", exact: true }),
  ).toBeVisible();
  await page.screenshot({
    path: `test-results/overview-${test.info().project.name}.png`,
    fullPage: true,
  });
  await expect(
    page.getByText("No genuine diagnosis exports supplied"),
  ).toHaveCount(0);
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Forecasting", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Reveal actual", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Hide actual", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Next replay step", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Reveal actual", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("combobox", { name: "Demonstration scenario" })
    .selectOption("day-two");
  await expect(
    page.getByRole("slider", { name: "Replay timeline" }),
  ).toHaveValue("24");
  await page.getByRole("button", { name: "Show value table" }).click();
  await expect(
    page.getByRole("cell", { name: "Hidden until reveal" }).first(),
  ).toBeVisible();
  await page.screenshot({
    path: `test-results/forecasting-${test.info().project.name}.png`,
    fullPage: true,
  });
  if (test.info().project.name === 'mobile') {
    const columns = await page.locator('.details-grid').evaluate(el => getComputedStyle(el).gridTemplateColumns);
    expect(columns.split(' ')).toHaveLength(1);
  }
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Event diagnosis" })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Upload measurements",
    }),
  ).toBeVisible();
  await expect(page.getByRole('region', { name: 'Scenario and timeline controls' })).toHaveCount(0);
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Scenario laboratory" })
    .click();
  await page.getByLabel("Equipment status").selectOption("out_of_service");
  await expect(
    page.getByText("Reconstruction unavailable", { exact: true }),
  ).toBeVisible();
  await page.getByRole("tab", { name: "Cascade", exact: true }).click();
  await page
    .getByRole("button", { name: "Next replay step", exact: true })
    .click();
  await expect(
    page.getByText("Moderate illustration", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("tab", { name: "Corrective actions", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Compare illustration" })
    .nth(1)
    .click();
  await expect(page.getByRole("cell", { name: "94%" })).toBeVisible();
  await page.getByRole("button", { name: "Reset", exact: true }).click();
  await expect(
    page
      .getByRole("combobox")
      .filter({ has: page.locator('option[value="in_service"]') }),
  ).toHaveValue("in_service");
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Evaluation & provenance" })
    .click();
  await expect(
    page.getByRole("heading", { name: "Chronological forecasting split" }),
  ).toBeVisible();
  await expect(page.getByText("76.48 seconds", { exact: true })).toBeVisible();
  await expect(page.locator("body")).not.toContainText("Dashboard unavailable");
  expect(errors).toEqual([]);
  expect(external).toEqual([]);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: `test-results/dashboard-${test.info().project.name}.png`,
    fullPage: true,
  });
});
test("missing genuine prediction file leaves other capabilities available", async ({
  page,
}) => {
  await page.route("**/forecasting/forecast_predictions.json", (route) =>
    route.fulfill({ status: 404, body: "Missing" }),
  );
  await page.goto("/");
  await expect(page.getByText("Some artifacts could not load")).toBeVisible();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Forecasting", exact: true })
    .click();
  await expect(
    page.getByText("forecasting/forecast_predictions.json: HTTP 404").first(),
  ).toBeVisible();
  await page
    .getByRole("navigation")
    .getByRole("button", { name: "Scenario laboratory" })
    .click();
  await expect(
    page.getByRole("heading", {
      name: "Missing measurement, operating equipment",
    }),
  ).toBeVisible();
});
