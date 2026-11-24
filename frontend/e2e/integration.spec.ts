import { expect, test } from "@playwright/test";

// Cần backend thật ở 127.0.0.1:8000; chạy bằng: E2E_BACKEND=1 npx playwright test e2e/integration.spec.ts
test.skip(!process.env.E2E_BACKEND, "cần backend thật (đặt E2E_BACKEND=1)");
test("real backend metadata controls prediction availability", async ({ page }) => {
  let predictionRequested = false;

  page.on("request", (request) => {
    if (request.url().includes("/api/v1/predictions")) {
      predictionRequested = true;
    }
  });

  const metadataResponsePromise = page.waitForResponse(
    (response) =>
      response.url().includes("/api/v1/metadata") &&
      response.request().method() === "GET",
  );

  await page.goto("/");

  const metadataResponse = await metadataResponsePromise;

  expect(metadataResponse.status()).toBe(200);

  const metadata = await metadataResponse.json();

  expect(["ready", "stale", "unavailable"]).toContain(metadata.serving_status);
  expect(Array.isArray(metadata.supported_districts)).toBe(true);

  const predictButton = page.getByRole("button", {
    name: /Ước tính giá căn hộ/i,
  });

  if (metadata.serving_status === "unavailable" || metadata.serving_status === "stale") {
    await expect(predictButton).toBeDisabled();
  }

  if (metadata.serving_status === "ready") {
    expect(metadata.model_id).toBeTruthy();
    expect(metadata.supported_districts.length).toBeGreaterThan(0);
    await expect(predictButton).toBeEnabled();
  }

  expect(predictionRequested).toBe(false);
});
