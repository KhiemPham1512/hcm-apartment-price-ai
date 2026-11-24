import { expect, test } from "@playwright/test";
import { mockMetadata } from "./fixtures";

const evaluation = {
  snapshot_kind: "historical",
  data_kind: "real",
  winner_selected_by_validation: "tree",
  test: {
    baseline: { rmse_vnd: 12e9, mae_vnd: 5e9, r2: -0.08, n: 10, invalid_output_count: 0 },
    tree: { rmse_vnd: 6.33e9, mae_vnd: 2.95e9, r2: 0.714, n: 10, invalid_output_count: 0 },
  },
  bootstrap: { models: { tree: { rmse_vnd_ci95: [5.82e9, 6.94e9], mae_vnd_ci95: [2.81e9, 3.11e9] } } },
  breakdowns: {
    tree: {
      area_band: [
        { group: "lt_40", rmse_vnd: 0.64e9, mae_vnd: 0.46e9, n: 238, descriptive_only: false },
        { group: "ge_100", rmse_vnd: 11.1e9, mae_vnd: 6.3e9, n: 5, descriptive_only: true },
      ],
    },
  },
};

test("historical results page labels the snapshot and shows test metrics with intervals", async ({ page }) => {
  await mockMetadata(page, "unavailable");
  await page.route("**/evaluation.json", (route) =>
    route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(evaluation) }),
  );
  await page.goto("/");
  const section = page.getByRole("region", { name: "Kết quả đánh giá run-001" });
  await expect(section.getByText("Đánh giá trên dữ liệu lịch sử, không phải giá hiện hành")).toBeVisible();
  const winner = section.getByRole("row", { name: /M3 Decision Tree/ });
  await expect(winner).toContainText("6,33");
  await expect(winner).toContainText("5,82–6,94");
  await expect(winner).toContainText("0,714");
  await expect(section.getByRole("row", { name: /≥ 100 m²/ })).toContainText("chỉ mô tả");
});

test("historical results page shows an error state when the file is missing", async ({ page }) => {
  await mockMetadata(page, "unavailable");
  await page.route("**/evaluation.json", (route) => route.fulfill({ status: 404, body: "" }));
  await page.goto("/");
  await expect(page.getByRole("region", { name: "Kết quả đánh giá run-001" }).getByRole("status"))
    .toContainText("Chưa đọc được báo cáo đánh giá");
});
