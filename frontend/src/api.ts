import type { ApiErrorBody, Metadata, Prediction, PredictionForm } from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");

export class ApiError extends Error {
  status: number;
  code: string;
  requestId?: string;

  constructor(message: string, status: number, code = "request_failed", requestId?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { Accept: "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError("Không kết nối được máy chủ. Kiểm tra API và thử lại.", 0, "network_error");
  }

  const body = (await response.json().catch(() => ({}))) as T & ApiErrorBody;
  if (!response.ok) {
    const apiError = body.error;
    const message = apiError?.message ?? friendlyError(response.status, apiError?.code);
    throw new ApiError(message, response.status, apiError?.code, apiError?.request_id);
  }
  return body as T;
}

function friendlyError(status: number, code?: string): string {
  if (code === "stale_model") return "Dữ liệu của mô hình đã quá hạn. Hiện chưa thể cung cấp ước tính.";
  if (code === "model_unavailable") return "Mô hình chưa được duyệt hoặc chưa sẵn sàng phục vụ.";
  if (code === "unsupported_district") return "Khu vực này chưa nằm trong phạm vi hỗ trợ.";
  if (status === 422) return "Thông tin gửi lên chưa hợp lệ. Vui lòng kiểm tra lại.";
  if (status === 503) return "Dịch vụ tạm thời chưa sẵn sàng. Không có giá ước tính được cung cấp.";
  return `Máy chủ phản hồi lỗi (${status}). Vui lòng thử lại sau.`;
}

export const getMetadata = () => request<Metadata>("/api/v1/metadata");
export const getReport = () => request<Record<string, unknown>>("/api/v1/report");

export function postPrediction(form: PredictionForm) {
  const payload = {
    area_m2: Number(form.area_m2),
    district_code: form.district_code,
    bedrooms: form.bedrooms === "" ? null : Number(form.bedrooms),
    bathrooms: form.bathrooms === "" ? null : Number(form.bathrooms),
    floor_level: form.floor_level === "" ? null : Number(form.floor_level),
  };
  return request<Prediction>("/api/v1/predictions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
