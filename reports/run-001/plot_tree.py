"""Render aggregate Decision Tree charts for the official historical run."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "figures"
BILLION = 1_000_000_000
BLUE = "#285987"
TEAL = "#13847a"
GRAY = "#747b84"
FEATURES = {
    "area_m2": "Diện tích",
    "district_code": "Khu vực",
    "bedrooms": "Số phòng ngủ",
    "bathrooms": "Số phòng tắm",
    "floor_level": "Tầng căn hộ",
}
DISTRICTS = dict(
    zip(
        "binh_chanh binh_tan binh_thanh can_gio go_vap hoc_mon nha_be phu_nhuan "
        "tan_binh tan_phu thu_duc".split(),
        ["Bình Chánh", "Bình Tân", "Bình Thạnh", "Cần Giờ", "Gò Vấp",
         "Hóc Môn", "Nhà Bè", "Phú Nhuận", "Tân Bình", "Tân Phú", "Thủ Đức"],
        strict=True,
    )
)
AREA = {"lt_40": "< 40 m²", "40_70": "40–<70 m²",
        "70_100": "70–<100 m²", "ge_100": "≥ 100 m²"}


def number(value, digits=2):
    return f"{value:,.{digits}f}".translate(str.maketrans(",.", ".,"))


def read(name):
    return json.loads((ROOT / f"{name}.json").read_text(encoding="utf-8"))


def axes(title, subtitle, height):
    fig, ax = plt.subplots(figsize=(10, height), layout="constrained")
    fig.suptitle(title, fontsize=17, fontweight="bold")
    ax.set_title(subtitle, fontsize=10, color="#465260", pad=14)
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", alpha=0.2)
    ax.set_axisbelow(True)
    ax.tick_params(axis="y", length=0)
    ax.invert_yaxis()
    return fig, ax


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=160, facecolor="white")
    plt.close(fig)


def permutation(report):
    rows = sorted(report["models"]["tree"]["permutation"], key=lambda row: row["rank"])
    fig, ax = axes(
        "Mức ảnh hưởng của đặc trưng lên Decision Tree",
        f"run-001 · Validation n = {number(report['n_validation'], 0)} · "
        f"{report['repeats']} lần xáo trộn mỗi cột · seed {report['seed']}",
        4.3,
    )
    means = [row["importance_mean_vnd"] / BILLION for row in rows]
    deviations = [row["importance_std_vnd"] / BILLION for row in rows]
    ax.barh(range(len(rows)), means, xerr=deviations, capsize=4, color=BLUE)
    ax.set_yticks(range(len(rows)), [FEATURES[row["feature"]] for row in rows])
    for i, (mean, sd) in enumerate(zip(means, deviations, strict=True)):
        ax.text(mean + sd + 0.16, i, f"{number(mean, 3)} ± {number(sd, 3)}", va="center")
    ax.set_xlim(-0.15, max(means) * 1.27)
    ax.axvline(0, color=GRAY, linewidth=0.8)
    ax.set_xlabel("Mức tăng RMSE trung bình ± độ lệch chuẩn (tỷ VND)")
    save(fig, "tree-permutation")


def ablation(report):
    tree = report["models"]["tree"]
    fig, ax = axes(
        "Sai số validation khi bỏ đặc trưng",
        f"run-001 · Validation n = {number(report['n_validation'], 0)} · "
        "Cùng split và cấu hình cây",
        3.9,
    )
    base = tree["validation_rmse_vnd"] / BILLION
    rows = tree["ablation"]
    values = [base] + [row["validation_rmse_vnd"] / BILLION for row in rows]
    labels = ["Đủ đặc trưng"] + [
        "Bỏ " + " và ".join(FEATURES[part].lower() for part in row["removed"].split("+"))
        for row in rows
    ]
    bars = ax.barh(labels, values, color=[GRAY] + [BLUE] * len(rows))
    deltas = ["mốc"] + [
        number(row["delta_vs_full_vnd"] / BILLION, 3) for row in rows
    ]
     bar_labels = [
     f"{number(value, 3)} ({delta})" for value, delta in zip(values, deltas, strict=True)
 ]
 ax.bar_label(bars, labels=bar_labels, padding=5)
    ax.set_xlim(0, max(values) * 1.23)
    ax.set_xlabel("RMSE (tỷ VND) · trong ngoặc là chênh lệch so với đủ đặc trưng")
    save(fig, "tree-ablation")


def group_label(kind, row):
    key = row["group"]
    if kind == "district":
        code = key.removeprefix("hcm_")
        return DISTRICTS.get(code, code.replace("_", " ").capitalize())
    if kind == "area_band":
        return AREA[key]
    low = number(row["price_min_vnd"] / BILLION, 3)
    high = number(row["price_max_vnd"] / BILLION, 3)
    return f"{key.upper()} · {low}–{high} tỷ"


def breakdown(kind, rows, total):
    title = {"district": "khu vực", "area_band": "nhóm diện tích",
             "price_band": "nhóm giá rao thực tế"}[kind]
    comparable = [row for row in rows if not row["descriptive_only"]]
    descriptive = [row for row in rows if row["descriptive_only"]]
    if kind == "district":
        comparable.sort(key=lambda row: -row["rmse_vnd"])
    descriptive.sort(key=lambda row: group_label(kind, row))
    fig, ax = axes(
        f"Sai số test của Decision Tree theo {title}",
        f"run-001 · Test lịch sử n = {number(total, 0)} · "
        + ("Nhóm so sánh sắp theo RMSE" if kind == "district" else "Theo thứ tự nhóm"),
        3.1 + 0.39 * len(comparable),
    )
    positions = range(len(comparable))
    labels = [f"{group_label(kind, row)}  (n={number(row['n'], 0)})" for row in comparable]
    for metric, offset, color in [("rmse", -0.18, BLUE), ("mae", 0.18, TEAL)]:
        values = [row[f"{metric}_vnd"] / BILLION for row in comparable]
        bars = ax.barh([i + offset for i in positions], values, height=0.33,
                       color=color, label=metric.upper())
        ax.bar_label(bars, labels=[number(v) for v in values], padding=4, fontsize=8)
    ax.set_yticks(list(positions), labels)
    ax.legend(loc="upper right", frameon=False)
    ax.set_xlim(0, max(row["rmse_vnd"] for row in comparable) / BILLION * 1.28)
    ax.set_xlabel("RMSE và MAE (tỷ VND)")
    if descriptive:
        notes = [
            f"{group_label(kind, row)} (n={row['n']})   "
            f"RMSE {number(row['rmse_vnd'] / BILLION)}   "
            f"MAE {number(row['mae_vnd'] / BILLION)}"
            for row in descriptive
        ]
        note = fig.supxlabel("Chỉ mô tả, không xếp hạng (tỷ VND)\n" + "\n".join(notes))
        note.set_fontsize(10)
        note.set_color(GRAY)
    save(fig, f"tree-error-{kind.replace('_', '-')}")


def main():
    importance = read("importance")
    evaluation = read("evaluation")
    selection = read("selection")
    for key in ("dataset_sha256", "candidate_sha256", "splits_sha256"):
        if importance[key] != evaluation[key]:
            raise ValueError(f"Run inputs disagree on {key}")
    total = evaluation["test"]["tree"]["n"]
    if total != selection["counts"]["test"]:
        raise ValueError("Test counts disagree")
    for kind, rows in evaluation["breakdowns"]["tree"].items():
        if sum(row["n"] for row in rows) != total:
            raise ValueError(f"Test counts do not sum to n for {kind}")
    OUT.mkdir(exist_ok=True)
    permutation(importance)
    ablation(importance)
    for kind, rows in evaluation["breakdowns"]["tree"].items():
        breakdown(kind, rows, total)


if __name__ == "__main__":
    main()
