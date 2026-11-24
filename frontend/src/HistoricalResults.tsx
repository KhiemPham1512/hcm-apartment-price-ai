import { useEffect, useState } from "react";

// Static copy of reports/run-001/evaluation.json: the API serves a report only for an approved package,
// and run-001 is historical, so it is read as a file and labelled as such.
type Metric = { rmse_vnd: number; mae_vnd: number; r2: number | null; n: number; invalid_output_count?: number };
type Group = Metric & { group: string; descriptive_only: boolean };
type Evaluation = {
  snapshot_kind?: string;
  winner_selected_by_validation?: string;
  test: Record<string, Metric>;
  bootstrap?: { models?: Record<string, { rmse_vnd_ci95?: [number, number] }> };
  breakdowns?: Record<string, Record<string, Group[]>>;
};

const MODELS: [string, string][] = [
  ["baseline", "B0 Baseline (trung vị)"],
  ["linear", "M1 Linear"],
  ["polynomial", "M2 Polynomial bậc 2"],
  ["tree", "M3 Decision Tree"],
];
const BANDS: Record<string, string> = {
  lt_40: "< 40 m²", "40_70": "40–70 m²", "70_100": "70–100 m²", ge_100: "≥ 100 m²",
};
const ty = (vnd: number) => (vnd / 1e9).toLocaleString("vi-VN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function HistoricalResults() {
  const [data, setData] = useState<Evaluation | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    fetch("/evaluation.json")
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error(String(response.status)))))
      .then((json: Evaluation) => (json?.test ? setData(json) : setFailed(true)))
      .catch(() => setFailed(true));
  }, []);

  const winner = data?.winner_selected_by_validation;
  const areaBands = winner ? data?.breakdowns?.[winner]?.area_band ?? [] : [];

  return (
    <section className="data-section" aria-labelledby="historical-title">
      <div className="section-heading">
        <div><p className="eyebrow">OFFLINE EVALUATION</p><h2 id="historical-title">Kết quả đánh giá run-001</h2></div>
      </div>
      {failed && <div className="notice info" role="status">Chưa đọc được báo cáo đánh giá. Kiểm tra file evaluation.json.</div>}
      {!data && !failed && <div className="notice info" role="status">Đang tải báo cáo đánh giá...</div>}
      {data && (
        <div className="report-panel">
          {data.snapshot_kind === "historical" && (
            <div className="notice warning"><strong>Đánh giá trên dữ liệu lịch sử, không phải giá hiện hành</strong>
              <p>Số liệu đo trên tập test độc lập (nhóm căn hộ chưa dùng khi huấn luyện), sau khi đã khóa mô hình. RMSE/MAE tính bằng tỷ VND; R² không phải phần trăm dự đoán đúng.</p></div>
          )}
          <div className="table-scroll">
            <table className="metrics-table">
              <thead><tr><th>Mô hình</th><th>RMSE test</th><th>Khoảng 95% RMSE</th><th>MAE test</th><th>R²</th><th>Dự đoán ≤ 0</th></tr></thead>
              <tbody>
                {MODELS.filter(([key]) => data.test[key]).map(([key, label]) => {
                  const m = data.test[key];
                  const ci = data.bootstrap?.models?.[key]?.rmse_vnd_ci95;
                  return (
                    <tr key={key}>
                      <th scope="row">{label}{key === winner ? " (chọn bằng validation)" : ""}</th>
                      <td>{ty(m.rmse_vnd)}</td>
                      <td>{ci ? `${ty(ci[0])}–${ty(ci[1])}` : "—"}</td>
                      <td>{ty(m.mae_vnd)}</td>
                      <td>{m.r2 === null ? "—" : m.r2.toLocaleString("vi-VN", { maximumFractionDigits: 3 })}</td>
                      <td>{(m.invalid_output_count ?? 0).toLocaleString("vi-VN")}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          {areaBands.length > 0 && (
            <>
              <h3>Sai số của mô hình được chọn theo nhóm diện tích</h3>
              <div className="table-scroll">
                <table className="metrics-table">
                  <thead><tr><th>Nhóm</th><th>n</th><th>RMSE</th><th>MAE</th><th>Ghi chú</th></tr></thead>
                  <tbody>
                    {areaBands.map((g) => (
                      <tr key={g.group}>
                        <th scope="row">{BANDS[g.group] ?? g.group}</th>
                        <td>{g.n.toLocaleString("vi-VN")}</td>
                        <td>{ty(g.rmse_vnd)}</td>
                        <td>{ty(g.mae_vnd)}</td>
                        <td>{g.descriptive_only ? "n < 20, chỉ mô tả" : ""}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </section>
  );
}
