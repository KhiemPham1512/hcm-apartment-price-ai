import type { Page } from "@playwright/test";

export const readyMetadata = {
  serving_status: "ready",
  schema_version: "1",
  model_id: "fixture-approved-model",
  dataset_version: "fixture-dataset-v1",
  data_as_of: "2026-10-01T00:00:00Z",
  data_latest_at: "2026-10-05T00:00:00Z",
  source_snapshot_at: "2026-10-06T00:00:00Z",
  area_basis: "net_usable_area",
  supported_districts: [{ code: "fixture_area_1", label: "Khu vực mẫu (fixture)" }],
  feature_schema: {
    required: ["area_m2", "district_code"],
    properties: {
      area_m2: { type: "number", minimum: 10, maximum: 500 },
      district_code: { type: "string" },
      bedrooms: { anyOf: [{ type: "integer", minimum: 0, maximum: 10 }, { type: "null" }] },
      bathrooms: { anyOf: [{ type: "integer", minimum: 0, maximum: 10 }, { type: "null" }] },
      floor_level: { anyOf: [{ type: "integer", minimum: 0, maximum: 100 }, { type: "null" }] },
    },
  },
  training_ranges: {},
};

export const readyPrediction = {
  predicted_price_vnd: 5_000_000_000,
  predicted_price_per_m2_vnd: 71_428_571.43,
  target: "asking_sale_price",
  model_id: "fixture-approved-model",
  run_id: "fixture-run-001",
  dataset_version: "fixture-dataset-v1",
  schema_version: "1",
  area_basis: "net_usable_area",
  data_as_of: "2026-10-01T00:00:00Z",
  data_latest_at: "2026-10-05T00:00:00Z",
  source_snapshot_at: "2026-10-06T00:00:00Z",
  warnings: [],
  request_id: "fixture-request-001",
};

export async function mockMetadata(page: Page, status: "ready" | "stale" | "unavailable" = "ready") {
  await page.route("**/api/v1/metadata", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ...readyMetadata,
        serving_status: status,
        supported_districts: status === "ready" ? readyMetadata.supported_districts : [],
      }),
    }),
  );
}
