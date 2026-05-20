"""
statistics.py
--------------
두 표정(Closed-mouth smile / Tooth-showing smile)의 동적 지표를
폴더 키워드 기반으로 수집·집계하여 CSV로 저장합니다.

지표 목록:
  DAA          — Dynamic Asymmetry Area (좌우 속도 적분 면적 차)
  Corr         — Pearson 상관계수 (좌우 속도 시계열)
  TimeLag      — 교차상관 기반 시간 지연 (프레임 단위)
  MeanRelPhase — 힐베르트 변환 기반 평균 상대 위상 (rad)
  PhaseVar     — 상대 위상의 표준편차
  AAI          — Acceleration Asymmetry Index (가속도 std 정규화 차)
  PEI          — Path Efficiency Index (경로 길이 / 직선 변위)

사용법:
  python statistics.py \\
      --root_dir  <Acquisition 결과 루트 폴더> \\
      --keyword_a "6. Closed-mouth" \\
      --keyword_b "7. Mouth stretch" \\
      --output    <저장할 CSV 경로>
"""

import argparse
import os
import glob

import numpy as np
import pandas as pd
from scipy.signal import correlate, hilbert
from scipy.stats import pearsonr


# ---------------------------------------------------------------------------
# 보조 함수
# ---------------------------------------------------------------------------

def calculate_pei(x: np.ndarray, y: np.ndarray) -> float:
    """Path Efficiency Index = 실제 경로 길이 / 직선 변위."""
    dx, dy = np.diff(x), np.diff(y)
    actual_path = float(np.sum(np.sqrt(dx**2 + dy**2)))
    total_disp  = float(np.sqrt((x[-1] - x[0])**2 + (y[-1] - y[0])**2))
    return actual_path / (total_disp + 1e-6)


def time_lag_cal(l_vel: np.ndarray, r_vel: np.ndarray) -> int:
    """
    교차상관(cross-correlation)으로 좌우 속도 신호의 시간 지연 추정.
    양수 → 오른쪽이 먼저 시작, 음수 → 왼쪽이 먼저 시작.
    """
    l = l_vel - np.mean(l_vel)
    r = r_vel - np.mean(r_vel)
    corr     = correlate(l, r, mode="full")
    best_idx = int(np.argmax(corr))
    return best_idx - (len(l) - 1)


def relative_phase_cal(l_vel: np.ndarray, r_vel: np.ndarray) -> np.ndarray:
    """힐베르트 변환으로 좌우 속도 신호의 순간 상대 위상(rad) 계산."""
    l_analytic = hilbert(l_vel - np.mean(l_vel))
    r_analytic = hilbert(r_vel - np.mean(r_vel))
    return np.unwrap(np.angle(l_analytic)) - np.unwrap(np.angle(r_analytic))


# ---------------------------------------------------------------------------
# 핵심 분석 함수
# ---------------------------------------------------------------------------

def analyze_by_keyword(root_path: str, keyword: str) -> pd.DataFrame:
    """
    root_path 하위에서 폴더 경로에 keyword가 포함된 CSV만 수집하여
    Pair별 지표의 mean ± std를 반환.
    """
    csv_files = glob.glob(
        os.path.join(root_path, "**", "dual_trajectory_analysis.csv"), recursive=True
    )
    filtered = [f for f in csv_files if keyword in f]
    print(f"[{keyword}] 키워드 매칭 파일: {len(filtered)}개")

    if not filtered:
        print(f"  ※ 키워드 '{keyword}'에 해당하는 폴더가 없습니다. 폴더명을 확인하세요.")
        return pd.DataFrame()

    all_data = []
    for file in filtered:
        try:
            df = pd.read_csv(file).dropna()
            df.columns = df.columns.str.strip()
            frames = df["Absolute_Frame"].values

            for p in range(1, 7):
                pid = f"P{p}"
                if f"{pid}_L_Vel" not in df.columns:
                    continue

                l_vel = df[f"{pid}_L_Vel"].values
                r_vel = df[f"{pid}_R_Vel"].values

                rel_phase = relative_phase_cal(l_vel, r_vel)

                l_std = float(np.std(np.diff(l_vel)))
                r_std = float(np.std(np.diff(r_vel)))

                l_pei = calculate_pei(df[f"{pid}_L_X"].values, df[f"{pid}_L_Y"].values)
                r_pei = calculate_pei(df[f"{pid}_R_X"].values, df[f"{pid}_R_Y"].values)

                all_data.append({
                    "Pair":          f"Pair {p}",
                    "DAA":           float(np.trapz(np.abs(l_vel - r_vel), x=frames)),
                    "Corr":          float(pearsonr(l_vel, r_vel)[0]),
                    "TimeLag":       time_lag_cal(l_vel, r_vel),
                    "MeanRelPhase":  float(np.mean(np.abs(rel_phase))),
                    "PhaseVar":      float(np.std(rel_phase)),
                    "AAI":           abs(l_std - r_std) / (l_std + r_std + 1e-6),
                    "PEI":           (l_pei + r_pei) / 2,
                })

        except Exception as exc:
            print(f"  [SKIP] {file}: {exc}")
            continue

    if not all_data:
        return pd.DataFrame()

    res_df = pd.DataFrame(all_data)

    def mean_sd(x: pd.Series) -> str:
        return f"{x.mean():.4f} ± {x.std():.4f}"

    return res_df.groupby("Pair").agg({col: mean_sd for col in res_df.columns if col != "Pair"})


# ---------------------------------------------------------------------------
# 진입점
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="두 표정 그룹의 동적 지표를 집계하여 CSV로 저장합니다."
    )
    parser.add_argument("--root_dir",  required=True, help="Acquisition 결과 루트 폴더")
    parser.add_argument("--keyword_a", default="6. Closed-mouth",  help="표정 A 키워드 (폴더명 부분 일치)")
    parser.add_argument("--keyword_b", default="7. Mouth stretch",  help="표정 B 키워드 (폴더명 부분 일치)")
    parser.add_argument("--output",    required=True, help="저장할 CSV 경로 (예: results/comparison.csv)")
    args = parser.parse_args()

    print("통합 분석 시작...\n")

    df_a = analyze_by_keyword(args.root_dir, args.keyword_a)
    df_b = analyze_by_keyword(args.root_dir, args.keyword_b)

    if df_a.empty or df_b.empty:
        print("\n❌ 한쪽 이상의 데이터가 없습니다. --keyword_a / --keyword_b 또는 --root_dir을 확인하세요.")
        return

    label_a = args.keyword_a.split(".")[-1].strip().replace(" ", "_")
    label_b = args.keyword_b.split(".")[-1].strip().replace(" ", "_")

    df_a.columns = [f"{label_a}_{c}" for c in df_a.columns]
    df_b.columns = [f"{label_b}_{c}" for c in df_b.columns]

    comparison_df = pd.concat([df_a, df_b], axis=1)

    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    comparison_df.to_csv(args.output, encoding="utf-8-sig")

    print(f"\n✨ 분석 완료! 결과 저장: {args.output}")
    print(comparison_df.to_string())


if __name__ == "__main__":
    main()
