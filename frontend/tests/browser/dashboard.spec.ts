import { test, expect } from "@playwright/test";
test('future diagnosis exports retain window-level prediction while the cursor moves',async({page})=>{
 // Test-only transport fixtures; no fictional diagnosis data is shipped.
 const episode={episode_id:'test-only',parent_family_id:'test-family',split:'test',ground_truth_class:'physical',input_origin:'source_simulation',trace_path:'diagnosis/test-only.json',observation_window:{start:'0 seconds',end:'2 seconds'},time_basis:'elapsed_seconds',sample_interval:1,sample_count:3,channel_definitions:[{channel_id:'voltage',source_component_id:'source-grid:bus:9',quantity:'voltage_magnitude',unit:'pu'}],limitations:['Test-only fixture']};
 await page.route('**/diagnosis/event_episodes.json',r=>r.fulfill({json:[episode]}));
 await page.route('**/diagnosis/diagnosis_predictions.json',r=>r.fulfill({json:[{prediction_id:'test-prediction',episode_id:'test-only',status:'complete',predicted_category:'physical',raw_score:0.6,score_class:'physical',decision_threshold:0.5,class_mapping:{sensor:0,physical:1},model_version:'test-only',diagnosed_at_utc:'2024-01-01T00:00:00Z',physical_location:null,reason:null}]}));
 await page.route('**/diagnosis/test-only.json',r=>r.fulfill({json:[{elapsed_seconds:0,voltage:1},{elapsed_seconds:1,voltage:0.95},{elapsed_seconds:2,voltage:0.94}]}));
 await page.goto('/');await page.getByRole('navigation').getByRole('button',{name:'Event diagnosis'}).click();
 await expect(page.getByRole('cell',{name:'1',exact:true})).toBeVisible();
 await page.getByRole('button',{name:'Next replay step'}).click();
 await expect(page.getByRole('cell',{name:'0.95',exact:true})).toBeVisible();
 await expect(page.getByText('Sample 2 / 3',{exact:true})).toBeVisible();
 await expect(page.getByRole('heading',{name:'physical',exact:true})).toBeVisible();
 await expect(page.getByText('source-grid:bus:9',{exact:true})).toBeVisible();
});
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
      name: "No genuine diagnosis exports supplied",
    }),
  ).toBeVisible();
  await page.getByRole('button', {name:'Show insufficient-input example'}).click();
  await expect(page.getByText('Unavailable — insufficient observation window', {exact:true})).toBeVisible();
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

test("overview supports keyboard inspection and direct module navigation", async ({ page }) => {
  await page.goto("/");
  const network = page.getByRole("group", { name: "Interactive illustrative 14-bus network" });
  const bus = network.getByRole("button", { name: "Inspect bus 01", exact: true });
  await bus.focus();
  await page.keyboard.press("Enter");
  await expect(bus).toHaveAttribute("aria-pressed", "true");
  await expect(page.getByText("Component inspector")).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
    await page.evaluate(() => window.innerWidth),
  );

  const modules = page.getByRole("region", { name: "Research modules" });
  await modules.getByRole("button", { name: /Cascade assessment/ }).click();
  await expect(page.getByRole("heading", { name: "Scenario laboratory", exact: true })).toBeFocused();
  await expect(page.getByRole("tab", { name: "Cascade" })).toHaveAttribute("aria-selected", "true");

  await page.getByRole("navigation").getByRole("button", { name: "Overview" }).click();
  await modules.getByRole("button", { name: /Telemetry reconstruction/ }).click();
  await expect(page.getByRole("tab", { name: "Reconstruction" })).toHaveAttribute("aria-selected", "true");
});
