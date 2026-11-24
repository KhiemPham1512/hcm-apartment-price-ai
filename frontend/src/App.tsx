import { useEffect, useMemo, useState, type FormEvent } from "react";
import { ApiError, getMetadata, getReport, postPrediction } from "./api";
import HistoricalResults from "./HistoricalResults";
import type { Metadata, Prediction, PredictionForm } from "./types";

const emptyForm: PredictionForm = {
  area_m2: "",
  district_code: "",
  bedrooms: "",
  bathrooms: "",
  floor_level: "",
};

const money = new Intl.NumberFormat("vi-VN", {
  style: "currency",
  currency: "VND",
  maximumFractionDigits: 0,
});

function dateLabel(value?: string | null) {
  if (!value) return "Chưa có dữ liệu";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "Không xác định"
    : new Intl.DateTimeFormat("vi-VN", { dateStyle: "medium", timeZone: "Asia/Ho_Chi_Minh" }).format(date);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function fieldBounds(metadata: Metadata | null, name: string, fallback: [number, number]) {
  const field = metadata?.feature_schema?.properties?.[name];
  const nullable = field?.anyOf?.find((item) => item.type === "integer" || item.type === "number");
  const min = field?.minimum ?? nullable?.minimum ?? fallback[0];
  const max = field?.maximum ?? nullable?.maximum ?? fallback[1];
  return {
    min: field?.exclusiveMinimum === undefined ? min : Math.max(min, field.exclusiveMinimum + Number.EPSILON),
    max: field?.exclusiveMaximum === undefined ? max : Math.min(max, field.exclusiveMaximum - Number.EPSILON),
  };
}

const fieldDefinitions = [
  { key: "area_m2", label: "Diện tích sử dụng", placeholder: "Ví dụ: 70", fallback: [10, 500] as [number, number], wide: true },
  { key: "bedrooms", label: "Phòng ngủ", placeholder: "Không bắt buộc", fallback: [0, 10] as [number, number], wide: false },
  { key: "bathrooms", label: "Phòng tắm", placeholder: "Không bắt buộc", fallback: [0, 10] as [number, number], wide: false },
  { key: "floor_level", label: "Tầng căn hộ", placeholder: "Không bắt buộc", fallback: [0, 100] as [number, number], wide: true },
] as const;

function App() {
  const [metadata, setMetadata] = useState<Metadata | null>(null);
  const [metadataError, setMetadataError] = useState("");
  const [loadingMetadata, setLoadingMetadata] = useState(true);
  const [form, setForm] = useState<PredictionForm>(emptyForm);
  const [prediction, setPrediction] = useState<Prediction | null>(null);
  const [predictionError, setPredictionError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [reportMessage, setReportMessage] = useState("");
  const [reportLoading, setReportLoading] = useState(false);

  const status = metadata?.serving_status ?? "unavailable";
  const demo = status === "historical_demo";
  const canPredict = (status === "ready" || demo)
    && (metadata?.supported_districts?.length ?? 0) > 0
    && Boolean(metadata?.feature_schema?.properties?.area_m2)
    && Boolean(metadata?.feature_schema?.properties?.district_code);
  const requiredFields = metadata?.feature_schema?.required ?? ["area_m2", "district_code"];
  const availableFields = useMemo(() => fieldDefinitions.filter(({ key }) =>
    Boolean(metadata?.feature_schema?.properties?.[key]),
  ), [metadata]);

  async function refreshMetadata() {
    setLoadingMetadata(true);
    setMetadataError("");
    try {
      const data = await getMetadata();
      setMetadata(data);
      setForm((current) => ({
        ...current,
        district_code: data.supported_districts?.some((item) => item.code === current.district_code)
          ? current.district_code
          : data.supported_districts?.[0]?.code ?? "",
      }));
    } catch (error) {
      setMetadata(null);
      setMetadataError(error instanceof Error ? error.message : "Không tải được metadata.");
    } finally {
      setLoadingMetadata(false);
    }
  }

  useEffect(() => {
    void refreshMetadata();
  }, []);

  function update<K extends keyof PredictionForm>(key: K, value: PredictionForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
    setPrediction(null);
    setPredictionError("");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPrediction(null);
    setPredictionError("");
    if (!canPredict) {
      setPredictionError("Mô hình chưa sẵn sàng. Không gửi yêu cầu dự đoán.");
      return;
    }
    setSubmitting(true);
    try {
      const result = await postPrediction(form);
      setPrediction(result);
    } catch (error) {
      if (error instanceof ApiError) {
        setPredictionError(`${error.message}${error.requestId ? ` (Mã yêu cầu: ${error.requestId})` : ""}`);
      } else {
        setPredictionError("Đã xảy ra lỗi không xác định.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function loadReport() {
    setReportLoading(true);
    setReport(null);
    setReportMessage("");
    try {
      setReport(await getReport());
    } catch (error) {
      setReport(null);
      setReportMessage(error instanceof Error ? error.message : "Chưa có báo cáo được duyệt.");
    } finally {
      setReportLoading(false);
    }
  }

  const reportMetrics = report && isRecord(report.test) ? report.test : null;
  const modelLabels: Record<string, string> = {
    baseline: "Baseline",
    linear: "Linear Regression",
    polynomial: "Polynomial Regression",
    tree: "Decision Tree",
  };

  const statusText = {
    ready: "Mô hình sẵn sàng",
    historical_demo: "Demo trên dữ liệu lịch sử",
    stale: "Dữ liệu mô hình đã quá hạn",
    unavailable: "Mô hình chưa sẵn sàng",
  }[status];

  return (
    <main className="page-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="HCM Apartment Price AI - Trang chủ">
          <span className="brand-mark">H</span>
          <span>HCM <strong>APARTMENT AI</strong></span>
        </a>
        <span className="topbar-note">Công cụ tham khảo giá rao bán</span>
      </header>

      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">HO CHI MINH CITY · APARTMENT MARKET</p>
          <h1>Ước tính giá căn hộ<br /><em>theo dữ liệu được duyệt.</em></h1>
          <p className="hero-description">
            Nhập thông tin căn hộ để xem ước tính tổng giá rao bán và đơn giá trên mỗi mét vuông.
          </p>
          <p className="disclaimer">
            Kết quả chỉ phản ánh giá rao bán trong dữ liệu của mô hình; không phải giá giao dịch
            đã chốt hay dự báo giá tương lai.
          </p>
        </div>
        <div className="hero-orbit" aria-hidden="true">
          <div className="orbit orbit-one" /><div className="orbit orbit-two" />
          <div className="building building-back" /><div className="building building-front" />
          <div className="building building-side" />
        </div>
      </section>

      <section className="workspace">
        <div className="section-heading">
          <div><p className="eyebrow">PROPERTY ESTIMATOR</p><h2>Thông tin căn hộ</h2></div>
          <span className={`status-pill ${status}`}><span />{loadingMetadata ? "Đang kiểm tra..." : statusText}</span>
        </div>

        {metadataError && (
          <div className="notice error" role="alert">
            <strong>Không thể kết nối API</strong><p>{metadataError}</p>
            <button className="text-button" type="button" onClick={() => void refreshMetadata()}>Thử tải lại</button>
          </div>
        )}

        {!loadingMetadata && !metadataError && demo && (
          <div className="notice warning" role="status">
            <strong>Chế độ demo: mô hình học từ tin rao {dateLabel(metadata?.data_as_of)} – {dateLabel(metadata?.data_latest_at)}</strong>
            <p>Giá hiển thị là giá rao ước tính theo dữ liệu lịch sử, không phải giá hiện tại và không dùng cho quyết định mua bán.</p>
          </div>
        )}

        {!loadingMetadata && !metadataError && status !== "ready" && !demo && (
          <div className={`notice ${status === "stale" ? "warning" : "info"}`} role="status">
            <strong>{status === "stale" ? "Dữ liệu mô hình đã quá hạn" : "Chưa có mô hình được duyệt"}</strong>
            <p>
              {status === "stale"
                ? "API vẫn cung cấp metadata để tham khảo, nhưng không cho phép dự đoán bằng dữ liệu đã quá hạn."
                : "Giao diện đã kết nối API, nhưng hệ thống chưa có artifact hợp lệ để phục vụ dự đoán. Chức năng dự đoán sẽ mở khi mô hình được duyệt."}
            </p>
          </div>
        )}

        <div className="content-grid">
          <form className="form-card" onSubmit={submit}>
            <div className="card-heading"><span className="step-number">01</span><div><h3>Đặc điểm bất động sản</h3><p>Các trường có dấu * là bắt buộc</p></div></div>
            <div className="form-grid">
              {availableFields.map((field) => {
                const key = field.key;
                const bounds = fieldBounds(metadata, key, field.fallback);
                const isRequired = requiredFields.includes(key);
                const schemaField = metadata?.feature_schema?.properties?.[key];
                const isInteger = schemaField?.type === "integer" || schemaField?.anyOf?.some((item) => item.type === "integer");
                const description = schemaField?.description;
                const input = (
                  <input
                    aria-label={field.label}
                    type="number"
                    inputMode="decimal"
                    min={bounds.min}
                    max={bounds.max}
                    step={isInteger ? "1" : "any"}
                    required={isRequired}
                    value={form[key]}
                    onChange={(event) => update(key, event.target.value)}
                    placeholder={field.placeholder}
                    disabled={!canPredict || submitting}
                  />
                );
                return (
                  <label className={`field${field.wide ? " field-wide" : ""}`} key={key}>
                    <span>{field.label}{isRequired && <> <b>*</b></>}</span>
                    {key === "area_m2" ? <div className="input-unit">{input}<span>m²</span></div> : input}
                    <small>{description ?? (isRequired
                      ? `Bắt buộc · Trong khoảng ${bounds.min}–${bounds.max}`
                      : `Không bắt buộc · Trong khoảng ${bounds.min}–${bounds.max}`)}</small>
                  </label>
                );
              })}
              {metadata?.feature_schema?.properties?.district_code && (
                <label className="field field-wide">
                  <span>Khu vực được hỗ trợ{requiredFields.includes("district_code") && <> <b>*</b></>}</span>
                  <select aria-label="Khu vực được hỗ trợ" required={requiredFields.includes("district_code")} value={form.district_code} onChange={(event) => update("district_code", event.target.value)} disabled={!canPredict || submitting}>
                    <option value="">Chọn khu vực</option>
                    {metadata?.supported_districts?.map((district) => <option key={district.code} value={district.code}>{district.label}</option>)}
                  </select>
                  <small>{metadata.feature_schema.properties.district_code.description ?? "Danh sách lấy trực tiếp từ metadata API"}</small>
                </label>
              )}
            </div>
            {predictionError && <div className="inline-error" role="alert">{predictionError}</div>}
            <button className="primary-button" type="submit" disabled={!canPredict || submitting || loadingMetadata}>
              {submitting ? <><span className="spinner" />Đang tính toán...</> : <>Ước tính giá căn hộ <span aria-hidden="true">↗</span></>}
            </button>
            <p className="form-footnote">Thông tin chỉ được gửi đến API dự đoán; không nhập địa chỉ chi tiết hoặc dữ liệu cá nhân.</p>
          </form>

          <aside className="result-card" aria-live="polite">
            <div className="card-heading"><span className="step-number">02</span><div><h3>Kết quả ước tính</h3><p>Giá rao bán tham khảo</p></div></div>
            {prediction ? (
              <div className="result-content">
                <span className="result-label">TỔNG GIÁ ƯỚC TÍNH</span>
                <strong className="price">{money.format(prediction.predicted_price_vnd)}</strong>
                <div className="per-meter"><span>Đơn giá / m²</span><strong>{money.format(prediction.predicted_price_per_m2_vnd)}</strong></div>
                {prediction.warnings?.length > 0 && <div className="notice warning compact"><strong>Lưu ý từ mô hình</strong><ul>{prediction.warnings.map((warning) => <li key={warning}>{warning === "historical_snapshot" ? "Giá rao ước tính theo dữ liệu lịch sử, không phải giá hiện tại." : warning === "outside_training_range" ? "Một số thông tin nằm ngoài khoảng dữ liệu huấn luyện." : warning === "optional_features_missing" ? "Có trường thông tin tùy chọn chưa được cung cấp." : warning}</li>)}</ul></div>}
                <dl className="metadata-list">
                  <div><dt>Ngày dữ liệu</dt><dd>{dateLabel(prediction.data_as_of)}</dd></div>
                  <div><dt>Quan sát mới nhất</dt><dd>{dateLabel(prediction.data_latest_at)}</dd></div>
                  <div><dt>Snapshot nguồn</dt><dd>{dateLabel(prediction.source_snapshot_at)}</dd></div>
                  <div><dt>Phạm vi diện tích</dt><dd>{prediction.area_basis}</dd></div>
                  <div><dt>Phiên bản dữ liệu</dt><dd>{prediction.dataset_version}</dd></div>
                  <div><dt>Phiên bản schema</dt><dd>{prediction.schema_version}</dd></div>
                  <div><dt>Mã mô hình</dt><dd>{prediction.model_id}</dd></div>
                </dl>
                <small className="request-id">Mã yêu cầu: {prediction.request_id}</small>
              </div>
            ) : (
              <div className="empty-result">
                <div className="empty-icon">⌂</div>
                <strong>Chưa có kết quả</strong>
                <p>{canPredict ? "Hoàn thành biểu mẫu và chọn ước tính để xem kết quả tại đây." : "Kết quả chỉ xuất hiện khi API xác nhận mô hình hợp lệ và còn hạn."}</p>
              </div>
            )}
          </aside>
        </div>
      </section>

      <section className="data-section">
        <div className="section-heading">
          <div><p className="eyebrow">MODEL TRANSPARENCY</p><h2>Thông tin dữ liệu</h2></div>
          <button className="secondary-button" type="button" onClick={() => void loadReport()} disabled={reportLoading}>
            {reportLoading ? "Đang tải..." : "Xem báo cáo mô hình"}
          </button>
        </div>
        <div className="data-grid">
          <div className="data-tile"><span>Ngày dữ liệu sớm nhất</span><strong>{dateLabel(metadata?.data_as_of)}</strong></div>
          <div className="data-tile"><span>Ngày quan sát mới nhất</span><strong>{dateLabel(metadata?.data_latest_at)}</strong></div>
          <div className="data-tile"><span>Phiên bản schema</span><strong>{metadata?.schema_version ?? "—"}</strong></div>
          <div className="data-tile"><span>Khu vực hỗ trợ</span><strong>{metadata?.supported_districts?.length ?? 0}</strong></div>
          <div className="data-tile"><span>Phiên bản dữ liệu</span><strong>{metadata?.dataset_version ?? "—"}</strong></div>
          <div className="data-tile"><span>Mã mô hình</span><strong>{metadata?.model_id ?? "Chưa có"}</strong></div>
        </div>
        {reportMessage && <div className="notice info report-message" role="status">{reportMessage}</div>}
        {report && (
          <div className="report-panel">
            <h3>Báo cáo đánh giá từ API</h3>
            {reportMetrics ? (
              <>
                <div className="report-meta">
                  <span>Loại đánh giá: <strong>{String(report.evaluation_kind ?? "Không xác định")}</strong></span>
                  <span>Winner validation: <strong>{String(report.winner_selected_by_validation ?? "Chưa có")}</strong></span>
                  <span>Loại dữ liệu: <strong>{String(report.data_kind ?? "Không xác định")}</strong></span>
                </div>
                <div className="table-scroll">
                  <table className="metrics-table">
                    <thead><tr><th>Mô hình</th><th>RMSE (VND)</th><th>MAE (VND)</th><th>R²</th><th>n</th></tr></thead>
                    <tbody>
                      {Object.entries(reportMetrics).map(([key, value]) => {
                        if (!isRecord(value)) return null;
                        const rmse = typeof value.rmse_vnd === "number" ? money.format(value.rmse_vnd) : "—";
                        const mae = typeof value.mae_vnd === "number" ? money.format(value.mae_vnd) : "—";
                        const r2 = typeof value.r2 === "number" ? value.r2.toFixed(3) : "—";
                        const n = typeof value.n === "number" ? value.n.toLocaleString("vi-VN") : "—";
                        return <tr key={key}><th scope="row">{modelLabels[key] ?? key}</th><td>{rmse}</td><td>{mae}</td><td>{r2}</td><td>{n}</td></tr>;
                      })}
                    </tbody>
                  </table>
                </div>
                <p>Đây là metric trên tập test do API cung cấp. RMSE/MAE có đơn vị VND; R² không phải phần trăm độ chính xác. Giao diện không tự tính lại metric.</p>
              </>
            ) : (
              <><pre>{JSON.stringify(report, null, 2)}</pre><p>API chưa trả cấu trúc metric test mà giao diện nhận diện được; nội dung được giữ nguyên, không tự suy diễn.</p></>
            )}
          </div>
        )}
        <p className="data-note">Thông tin được đọc từ metadata API. Khi chưa có model, các giá trị có thể chưa được cung cấp. Metric chỉ được hiển thị theo báo cáo API, không được frontend tự tính lại.</p>
      </section>

      <HistoricalResults />

      <footer className="footer">
        <span>HCM APARTMENT PRICE AI</span>
        <span>Ước tính giá rao bán · Không thay thế tư vấn định giá chuyên môn</span>
      </footer>
    </main>
  );
}

export default App;
