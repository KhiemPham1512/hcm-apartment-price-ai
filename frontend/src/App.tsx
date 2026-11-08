import { useEffect, useMemo, useState, type FormEvent } from "react";
import { ApiError, getMetadata, getReport, postPrediction } from "./api";
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
  return {
    min: field?.minimum ?? nullable?.minimum ?? fallback[0],
    max: field?.maximum ?? nullable?.maximum ?? fallback[1],
  };
}

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
  const canPredict = status === "ready" && (metadata?.supported_districts?.length ?? 0) > 0;
  const areaBounds = useMemo(() => fieldBounds(metadata, "area_m2", [10, 500]), [metadata]);
  const bedroomBounds = useMemo(() => fieldBounds(metadata, "bedrooms", [0, 10]), [metadata]);
  const bathroomBounds = useMemo(() => fieldBounds(metadata, "bathrooms", [0, 10]), [metadata]);
  const floorBounds = useMemo(() => fieldBounds(metadata, "floor_level", [0, 100]), [metadata]);

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

        {!loadingMetadata && !metadataError && status !== "ready" && (
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
              <label className="field field-wide">
                <span>Diện tích sử dụng <b>*</b></span>
                <div className="input-unit"><input aria-label="Diện tích sử dụng" type="number" inputMode="decimal" min={areaBounds.min} max={areaBounds.max} step="any" required value={form.area_m2} onChange={(e) => update("area_m2", e.target.value)} placeholder="Ví dụ: 70" disabled={!canPredict || submitting} /><span>m²</span></div>
                <small>Trong khoảng {areaBounds.min}–{areaBounds.max} m²</small>
              </label>
              <label className="field field-wide">
                <span>Khu vực được hỗ trợ <b>*</b></span>
                <select aria-label="Khu vực được hỗ trợ" required value={form.district_code} onChange={(e) => update("district_code", e.target.value)} disabled={!canPredict || submitting}>
                  <option value="">Chọn khu vực</option>
                  {metadata?.supported_districts?.map((district) => <option key={district.code} value={district.code}>{district.label}</option>)}
                </select>
                <small>Danh sách lấy trực tiếp từ metadata API</small>
              </label>
              <label className="field">
                <span>Phòng ngủ</span>
                <input aria-label="Phòng ngủ" type="number" min={bedroomBounds.min} max={bedroomBounds.max} step="1" value={form.bedrooms} onChange={(e) => update("bedrooms", e.target.value)} placeholder="Không bắt buộc" disabled={!canPredict || submitting} />
                <small>Bỏ trống nếu chưa rõ</small>
              </label>
              <label className="field">
                <span>Phòng tắm</span>
                <input aria-label="Phòng tắm" type="number" min={bathroomBounds.min} max={bathroomBounds.max} step="1" value={form.bathrooms} onChange={(e) => update("bathrooms", e.target.value)} placeholder="Không bắt buộc" disabled={!canPredict || submitting} />
                <small>Bỏ trống nếu chưa rõ</small>
              </label>
              <label className="field field-wide">
                <span>Tầng căn hộ</span>
                <input aria-label="Tầng căn hộ" type="number" min={floorBounds.min} max={floorBounds.max} step="1" value={form.floor_level} onChange={(e) => update("floor_level", e.target.value)} placeholder="Không bắt buộc" disabled={!canPredict || submitting} />
                <small>Nhập tầng của căn hộ, không phải số tầng tòa nhà</small>
              </label>
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
                {prediction.warnings?.length > 0 && <div className="notice warning compact"><strong>Lưu ý từ mô hình</strong><ul>{prediction.warnings.map((warning) => <li key={warning}>{warning === "outside_training_range" ? "Một số thông tin nằm ngoài khoảng dữ liệu huấn luyện." : warning === "optional_features_missing" ? "Có trường thông tin tùy chọn chưa được cung cấp." : warning}</li>)}</ul></div>}
                <dl className="metadata-list">
                  <div><dt>Ngày dữ liệu</dt><dd>{dateLabel(prediction.data_as_of)}</dd></div>
                  <div><dt>Phạm vi diện tích</dt><dd>{prediction.area_basis}</dd></div>
                  <div><dt>Phiên bản dữ liệu</dt><dd>{prediction.dataset_version}</dd></div>
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
        <p className="data-note">Thông tin được đọc từ metadata API. Khi chưa có model, các giá trị có thể chưa được cung cấp.</p>
      </section>

      <footer className="footer">
        <span>HCM APARTMENT PRICE AI</span>
        <span>Ước tính giá rao bán · Không thay thế tư vấn định giá chuyên môn</span>
      </footer>
    </main>
  );
}

export default App;
