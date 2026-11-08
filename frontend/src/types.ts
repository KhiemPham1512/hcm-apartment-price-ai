export type ServingStatus = "ready" | "stale" | "unavailable";

export interface District {
  code: string;
  label: string;
}

export interface FeatureField {
  type?: string;
  title?: string;
  description?: string;
  minimum?: number;
  maximum?: number;
  exclusiveMinimum?: number;
  exclusiveMaximum?: number;
  default?: unknown;
  anyOf?: Array<{ type?: string; minimum?: number; maximum?: number }>;
}

export interface Metadata {
  serving_status: ServingStatus;
  schema_version?: string;
  model_id?: string | null;
  dataset_version?: string | null;
  data_as_of?: string | null;
  data_latest_at?: string | null;
  source_snapshot_at?: string | null;
  area_basis?: string | null;
  supported_districts: District[];
  feature_schema?: {
    properties?: Record<string, FeatureField>;
    required?: string[];
  };
  age_summary?: {
    median_listing_age_days?: number;
    median_price_age_days?: number;
    computed_at?: string;
  } | null;
  training_ranges?: Record<string, [number, number]>;
}

export interface ApiErrorBody {
  error?: {
    code?: string;
    message?: string;
    request_id?: string;
    details?: Record<string, unknown>;
  };
}

export interface Prediction {
  predicted_price_vnd: number;
  predicted_price_per_m2_vnd: number;
  target: string;
  model_id: string;
  run_id: string;
  dataset_version: string;
  schema_version: string;
  area_basis: string;
  data_as_of: string;
  data_latest_at: string;
  source_snapshot_at: string;
  age_summary?: Metadata["age_summary"];
  warnings: string[];
  request_id: string;
}

export type PredictionForm = {
  area_m2: string;
  district_code: string;
  bedrooms: string;
  bathrooms: string;
  floor_level: string;
};
