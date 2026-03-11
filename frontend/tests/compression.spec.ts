import { expect, test } from '@playwright/test';

const tinyPng = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4////fwAJ+wP9KobjigAAAABJRU5ErkJggg==',
  'base64'
);

test('single image compression previews before export', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /image compression/i }).click();
  await page.locator('input[type="file"]').setInputFiles({
    name: 'sample.png',
    mimeType: 'image/png',
    buffer: tinyPng,
  });

  await expect(page.getByText(/^colors$/i)).toBeVisible();
  await expect(page.getByText(/preview ready/i)).toBeVisible();
  await expect(page.getByAltText(/before compression/i)).toBeVisible();
  await expect(page.getByAltText(/after compression/i)).toBeVisible();
  await expect(page.getByRole('button', { name: /compress 1/i })).toHaveCount(0);

  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: /^apply$/i }).click();
  const download = await downloadPromise;
  expect(await download.suggestedFilename()).toContain('sample_compressed.png');
});
