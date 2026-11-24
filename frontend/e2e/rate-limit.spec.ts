import { expect, test } from "@playwright/test";
import { mockMetadata } from "./fixtures";

test("429 shows the Retry-After wait and blocks resubmission until it passes", async ({ page }) => {
  await mockMetadata(page);
  let calls = 0;
  await page.route("**/api/v1/predictions", (route) => {
    calls += 1;
    return route.fulfill({
      status: 429,
      contentType: "application/json",
      headers: { "Retry-After": "2" },
      body: JSON.stringify({ error: { code: "rate_limited", message: "Too many requests", request_id: "r-429", details: {} } }),
    });
  });
  await page.goto("/");
  await page.getByLabel("Diện tích sử dụng").fill("70");
  await page.getByLabel("Khu vực được hỗ trợ").selectOption("fixture_area_1");
  const button = page.getByRole("button", { name: /Ước tính giá căn hộ/ });
  await button.click();

  await expect(page.getByRole("alert")).toContainText("thử lại sau 2 giây");
  await expect(button).toBeDisabled();
  await expect(button).toBeEnabled({ timeout: 4000 });
  expect(calls).toBe(1);
});
