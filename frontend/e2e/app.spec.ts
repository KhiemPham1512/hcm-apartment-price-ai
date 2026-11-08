import { expect, test } from "@playwright/test";
import { mockMetadata, readyPrediction } from "./fixtures";

test("valid flow submits only the public feature contract and renders API price", async ({ page }) => {
  await mockMetadata(page);
  let submitted: Record<string, unknown> | undefined;
  await page.route("**/api/v1/predictions", async (route) => {
    submitted = route.request().postDataJSON() as Record<string, unknown>;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(readyPrediction) });
  });

  await page.goto("/");
  await page.getByLabel("Diện tích sử dụng").fill("70");
  await page.getByLabel("Khu vực được hỗ trợ").selectOption("fixture_area_1");
  await page.getByLabel("Phòng ngủ").fill("2");
  await page.getByRole("button", { name: /Ước tính giá căn hộ/ }).click();

  await expect(page.getByText("5.000.000.000 ₫")).toBeVisible();
  expect(submitted).toEqual({
    area_m2: 70,
    district_code: "fixture_area_1",
    bedrooms: 2,
    bathrooms: null,
    floor_level: null,
  });
});

test("unavailable model disables prediction and never calls predictions endpoint", async ({ page }) => {
  await mockMetadata(page, "unavailable");
  let called = false;
  await page.route("**/api/v1/predictions", async (route) => {
    called = true;
    await route.fulfill({ status: 500, body: "{}" });
  });
  await page.goto("/");
  await expect(page.getByText("Chưa có mô hình được duyệt")).toBeVisible();
  await expect(page.getByRole("button", { name: /Ước tính giá căn hộ/ })).toBeDisabled();
  expect(called).toBe(false);
});

test("stale metadata explains that predictions are unavailable", async ({ page }) => {
  await mockMetadata(page, "stale");
  await page.goto("/");
  await expect(page.getByRole("status").getByText("Dữ liệu mô hình đã quá hạn")).toBeVisible();
  await expect(page.getByRole("button", { name: /Ước tính giá căn hộ/ })).toBeDisabled();
});

test("422 response is shown without displaying a cached or mock price", async ({ page }) => {
  await mockMetadata(page);
  await page.route("**/api/v1/predictions", (route) =>
    route.fulfill({
      status: 422,
      contentType: "application/json",
      body: JSON.stringify({ error: { code: "unsupported_district", message: "Khu vực chưa nằm trong phạm vi hỗ trợ.", request_id: "req-422" } }),
    }),
  );
  await page.goto("/");
  await page.getByLabel("Diện tích sử dụng").fill("70");
  await page.getByLabel("Khu vực được hỗ trợ").selectOption("fixture_area_1");
  await page.getByRole("button", { name: /Ước tính giá căn hộ/ }).click();
  await expect(page.getByRole("alert")).toContainText("Khu vực chưa nằm trong phạm vi hỗ trợ");
  await expect(page.getByText("Chưa có kết quả")).toBeVisible();
});


test("503 from predictions is shown without a price", async ({ page }) => {
  await mockMetadata(page);
  await page.route("**/api/v1/predictions", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ error: { code: "model_unavailable", message: "Mô hình chưa được duyệt hoặc chưa sẵn sàng phục vụ.", request_id: "req-503" } }),
    }),
  );
  await page.goto("/");
  await page.getByLabel("Diện tích sử dụng").fill("70");
  await page.getByLabel("Khu vực được hỗ trợ").selectOption("fixture_area_1");
  await page.getByRole("button", { name: /Ước tính giá căn hộ/ }).click();
  await expect(page.getByRole("alert")).toContainText("Mô hình chưa được duyệt");
  await expect(page.getByText("Chưa có kết quả")).toBeVisible();
});

test("client-side validation prevents an empty submission", async ({ page }) => {
  await mockMetadata(page);
  let called = false;
  await page.route("**/api/v1/predictions", async (route) => {
    called = true;
    await route.fulfill({ status: 500, body: "{}" });
  });
  await page.goto("/");
  await page.getByRole("button", { name: /Ước tính giá căn hộ/ }).click();
  expect(called).toBe(false);
});

test("report metrics are rendered with VND units and sample counts", async ({ page }) => {
  await mockMetadata(page);
  await page.route("**/api/v1/report", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        evaluation_kind: "current_snapshot_grouped",
        winner_selected_by_validation: "linear",
        data_kind: "synthetic",
        test: {
          baseline: { rmse_vnd: 100000000, mae_vnd: 80000000, r2: 0.2, n: 80 },
          linear: { rmse_vnd: 90000000, mae_vnd: 70000000, r2: 0.3, n: 80 },
          polynomial: { rmse_vnd: 95000000, mae_vnd: 75000000, r2: 0.25, n: 80 },
          tree: { rmse_vnd: 92000000, mae_vnd: 72000000, r2: 0.28, n: 80 },
        },
      }),
    }),
  );
  await page.goto("/");
  await page.getByRole("button", { name: "Xem báo cáo mô hình" }).click();
  await expect(page.getByRole("table")).toBeVisible();
  await expect(page.getByRole("row", { name: /Baseline/ })).toContainText("80");
  await expect(page.getByText(/RMSE\/MAE có đơn vị VND/)).toBeVisible();
});

test("form remains usable on a narrow mobile viewport", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await mockMetadata(page);
  await page.goto("/");
  await expect(page.getByLabel("Diện tích sử dụng")).toBeVisible();
  await expect(page.getByLabel("Khu vực được hỗ trợ")).toBeVisible();
});


test("network failure clears any previous prediction and shows an explicit error", async ({ page }) => {
  await mockMetadata(page);
  let attempts = 0;
  await page.route("**/api/v1/predictions", async (route) => {
    attempts += 1;
    if (attempts === 1) {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(readyPrediction) });
      return;
    }
    await route.abort("failed");
  });

  await page.goto("/");
  await page.getByLabel("Diện tích sử dụng").fill("70");
  await page.getByLabel("Khu vực được hỗ trợ").selectOption("fixture_area_1");
  await page.getByRole("button", { name: /Ước tính giá căn hộ/ }).click();
  await expect(page.getByText("5.000.000.000 ₫")).toBeVisible();

  await page.getByRole("button", { name: /Ước tính giá căn hộ/ }).click();
  await expect(page.getByRole("alert")).toContainText("Không kết nối được máy chủ");
  await expect(page.getByText("Chưa có kết quả")).toBeVisible();
  await expect(page.getByText("5.000.000.000 ₫")).toHaveCount(0);
});

test("report API failure does not leave previously loaded report metrics visible", async ({ page }) => {
  await mockMetadata(page);
  let attempts = 0;
  await page.route("**/api/v1/report", async (route) => {
    attempts += 1;
    if (attempts === 1) {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ test: { baseline: { rmse_vnd: 100000000, mae_vnd: 80000000, r2: 0.2, n: 80 } } }),
      });
      return;
    }
    await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ error: { code: "model_unavailable", message: "Báo cáo hiện chưa khả dụng." } }) });
  });

  await page.goto("/");
  await page.getByRole("button", { name: "Xem báo cáo mô hình" }).click();
  await expect(page.getByRole("table")).toBeVisible();
  await page.getByRole("button", { name: "Xem báo cáo mô hình" }).click();
  await expect(page.getByRole("status")).toContainText("Báo cáo hiện chưa khả dụng");
  await expect(page.getByRole("table")).toHaveCount(0);
});
