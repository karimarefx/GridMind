import { test, expect } from '@playwright/test';

// Synthetic software fixture; not a real event or accuracy benchmark.
function csv() {
  const rows = ['elapsed_seconds,angle,reconstructed,frequency,voltage_magnitude,current_magnitude,current_angle'];
  for (let n = 0; n < 1800; n++) {
    const t = n / 30, a = .01 * t + .1 * Math.floor(n / 450);
    rows.push(`${t},${a},0,60,1,2,${a-.3}`);
  }
  return rows.join('\n');
}

test('real local service diagnoses upload and cursor keeps the prediction fixed', async ({ page, request }) => {
  await page.goto('http://127.0.0.1:8000');
  await page.getByRole('navigation').getByRole('button', { name: 'Event diagnosis' }).click();
  const payload = csv();
  const direct = await request.post('http://127.0.0.1:8000/api/diagnosis', {
    multipart: { angle_unit: 'radian', file: { name: 'synthetic-software-fixture.csv', mimeType: 'text/csv', buffer: Buffer.from(payload) } },
  });
  expect(direct.ok()).toBeTruthy();
  const expected = (await direct.json()).prediction;
  await page.getByLabel('Measurement CSV', { exact: true }).setInputFiles({ name: 'synthetic-software-fixture.csv', mimeType: 'text/csv', buffer: Buffer.from(payload) });
  await page.getByLabel('Angle unit', { exact: true }).selectOption('radian');
  const response = page.waitForResponse(r => r.url().endsWith('/api/diagnosis') && r.request().method() === 'POST');
  await page.getByRole('button', { name: 'Run diagnosis', exact: true }).click();
  const result = await (await response).json();
  expect(result.prediction.category).toBe(expected.category);
  expect(result.prediction.detection).toEqual(expected.detection);
  await expect(page.getByText('Ground truth not supplied · gridmind-stage1-v1', { exact: true })).toBeVisible();
  await page.getByRole('slider', { name: 'Uploaded sample', exact: true }).fill('900');
  await expect(page.getByText('Sample 901 / 1800', { exact: false })).toBeVisible();
  await expect(page.getByText('Ground truth not supplied · gridmind-stage1-v1', { exact: true })).toBeVisible();
  await page.screenshot({ path: `test-results/upload-${test.info().project.name}.png`, fullPage: true });
  await page.getByLabel('Angle unit', { exact: true }).selectOption('degree');
  await expect(page.getByText('Ground truth not supplied · gridmind-stage1-v1', { exact: true })).toHaveCount(0);
});

test('invalid CSV has a clear error and no diagnosis result', async ({ page }) => {
  await page.goto('http://127.0.0.1:8000');
  await page.getByRole('navigation').getByRole('button', { name: 'Event diagnosis' }).click();
  await page.getByLabel('Measurement CSV', { exact: true }).setInputFiles({ name: 'invalid.csv', mimeType: 'text/csv', buffer: Buffer.from('time,value\n0,1') });
  await page.getByRole('button', { name: 'Run diagnosis', exact: true }).click();
  await expect(page.getByRole('alert').filter({ hasText: 'CSV requires exactly these columns' })).toBeVisible();
  await expect(page.getByText('Ground truth not supplied · gridmind-stage1-v1', { exact: true })).toHaveCount(0);
});

test('backend unavailable is explicit while forecasting remains usable', async ({ page }) => {
  await page.route('**/api/health', route => route.fulfill({ status: 503, json: { ready: false, reason: 'Test-only missing model' } }));
  await page.goto('http://127.0.0.1:8000');
  await page.getByRole('navigation').getByRole('button', { name: 'Event diagnosis' }).click();
  await expect(page.getByText('Test-only missing model', { exact: false })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Run diagnosis', exact: true })).toBeDisabled();
  await page.getByRole('navigation').getByRole('button', { name: 'Forecasting', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Reveal actual', exact: true })).toBeVisible();
});
