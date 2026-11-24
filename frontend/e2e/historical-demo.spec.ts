import { expect, test } from "@playwright/test";
import { readyMetadata, readyPrediction } from "./fixtures";

const demoMetadata = {
  ...readyMetadata,
  serving_status: "historical_demo",
  snapshot_kind: "historical",
  data_as_of: "2025-06-01T01:08:56Z",
  data_latest_at: "2026-03-30T23:20:21Z",
};

test("historical demo allows predictions but labels every price as historical", async ({ page }) => {
  await page.route("**/api/v1/metadata", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(demoMetadata) }),
  );
  await page.route("**/api/v1/predictions", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ ...readyPrediction, snapshot_kind: "historical", warnings: ["historical_snapshot"] }),
    }),
  );
  await page.goto("/");
  await expect(page.getByText("Demo trên dữ liệu lịch sử", { exact: true })).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "không phải giá hiện tại" })).toBeVisible();

  await page.getByLabel("Diện tích sử dụng").fill("70");
  await page.getByLabel("Khu vực được hỗ trợ").selectOption("fixture_area_1");
  await page.getByRole("button", { name: /Ước tính giá căn hộ/ }).click();

  await expect(page.getByText("5.000.000.000 ₫")).toBeVisible();
  await expect(page.getByText("Giá rao ước tính theo dữ liệu lịch sử, không phải giá hiện tại.")).toBeVisible();
});
