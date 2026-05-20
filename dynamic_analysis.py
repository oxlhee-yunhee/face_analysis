"""
dynamic_analysis.py
--------------------
Acquisition.py가 생성한 dual_trajectory_analysis.csv를 읽어
각 피험자·랜드마크 쌍별로 두 가지 시각화 파일을 저장합니다.

출력 파일 (폴더당):
  Pair_{n}_Analysis.png     — 속도 & 가속도 그래프 (nDAA, Corr, AAI 표시)
  Pair_{n}_Smooth_Phase.png — Smoothed Phase Portrait (변위-속도)
"""

import argparse
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from scipy.stats import pearsonr

# ---------------------------------------------------------------------------
# 분석할 6쌍 정보
# ---------------------------------------------------------------------------
PAIRS = [
    {"id": "Pair_1", "prefix": "P1", "name": "Outer Corner (61-291)"},
    {"id": "Pair_2", "prefix": "P2", "name": "Lower Lip (181-405)"},
    {"id": "Pair_3", "prefix": "P3", "name": "Upper Lip (39-269)"},
    {"id": "Pair_4", "prefix": "P4", "name": "Mid-Cheek (117-346)"},
    {"id": "Pair_5", "prefix": "P5", "name": "Lower-Cheek (50-280)"},
    {"id": "Pair_6", "prefix": "P6", "name": "Side-Cheek (207-427)"},
]


def calculate_pei(x: np.ndarray, y: np.ndarray) -> float:
    """
    Path Efficiency Index (PEI) = 실제 이동 경로 길이 / 직선 변위.
    값이 1에 가까울수록 직선적(효율적)인 움직임.
    """
    dx, dy = np.diff(x), np.diff(y)
    actual_path = float(np.sum(np.sqrt(dx**2 + dy**2)))
    total_disp  = float(np.sqrt((x[-1] - x[0])**2 + (y[-1] - y[0])**2))
    return actual_path / (total_disp + 1e-6)


def smooth_disp_vel(
    x: np.ndarray, y: np.ndarray, v: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """변위 시계열과 속도 시계열에 Savitzky-Golay 스무딩 적용."""
    disp = np.sqrt((x - x[0])**2 + (y - y[0])**2)
    n    = len(disp)
    win  = 31 if n > 31 else (n // 2 * 2 - 1)
    if win < 3:
        return disp, v
    return savgol_filter(disp, win, 3), savgol_filter(v, win, 3)


def analyze_folder(person_path: str) -> None:
    """단일 피험자 폴더를 처리하여 시각화 파일을 저장."""
    csv_path = os.path.join(person_path, "dual_trajectory_analysis.csv")
    if not os.path.exists(csv_path):
        return

    folder_name = os.path.basename(person_path)
    print(f"ANALYZING: {folder_name}")

    try:
        df = pd.read_csv(csv_path)
        df.columns = df.columns.str.strip()
        df = df.dropna()

        frames = df["Absolute_Frame"].values

        for pair in PAIRS:
            pid  = pair["prefix"]
            name = pair["name"]
            pid_id = pair["id"]

            l_vel = df[f"{pid}_L_Vel"].values
            r_vel = df[f"{pid}_R_Vel"].values
            l_x   = df[f"{pid}_L_X"].values
            l_y   = df[f"{pid}_L_Y"].values
            r_x   = df[f"{pid}_R_X"].values
            r_y   = df[f"{pid}_R_Y"].values

            # --- 지표 계산 ---
            l_pei = calculate_pei(l_x, l_y)
            r_pei = calculate_pei(r_x, r_y)

            daa     = float(np.trapz(np.abs(l_vel - r_vel), x=frames))
            denom   = float(np.trapz(l_vel + r_vel, x=frames))
            nor_daa = daa / denom if denom > 1e-6 else 0.0

            corr, _ = pearsonr(l_vel, r_vel)

            l_acc = np.diff(l_vel)
            r_acc = np.diff(r_vel)
            l_std = float(np.std(l_acc))
            r_std = float(np.std(r_acc))
            aai   = abs(l_std - r_std) / (l_std + r_std + 1e-6)

            # --- Part 1: Velocity & Acceleration ---
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))

            ax1.plot(frames, l_vel, label=f"Left  (PEI: {l_pei:.2f})", color="cyan", lw=2)
            ax1.plot(frames, r_vel, label=f"Right (PEI: {r_pei:.2f})", color="red",  lw=2, ls="--")
            ax1.fill_between(frames, l_vel, r_vel, color="gray", alpha=0.3, label="Asymmetry area")
            ax1.set_title(f"[{name}] Velocity\nnDAA: {nor_daa:.4f} | Corr: {corr:.4f}")
            ax1.set_xlabel("Frame")
            ax1.set_ylabel("Velocity (px/frame)")
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            ax2.plot(frames[:-1], l_acc, label=f"Left  Accel (Std: {l_std:.2f})", color="deeppink", alpha=0.7)
            ax2.plot(frames[:-1], r_acc, label=f"Right Accel (Std: {r_std:.2f})", color="black",    alpha=0.7, ls="--")
            ax2.set_title(f"Acceleration Stability  AAI: {aai:.4f}")
            ax2.set_xlabel("Frame")
            ax2.set_ylabel("Acceleration (px/frame²)")
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.savefig(os.path.join(person_path, f"{pid_id}_Analysis.png"), dpi=150)
            plt.close()

            # --- Part 2: Smoothed Phase Portrait ---
            sl_disp, sl_vel = smooth_disp_vel(l_x, l_y, l_vel)
            sr_disp, sr_vel = smooth_disp_vel(r_x, r_y, r_vel)

            plt.figure(figsize=(8, 6))
            plt.plot(sl_disp, sl_vel, label="Left",  color="cyan", lw=3)
            plt.plot(sr_disp, sr_vel, label="Right", color="red",  lw=3, ls="--")
            plt.title(f"Phase Portrait (Displacement–Velocity)\n{name}")
            plt.xlabel("Displacement (px)")
            plt.ylabel("Velocity (px/frame)")
            plt.legend()
            plt.grid(True, ls=":", alpha=0.6)
            plt.savefig(os.path.join(person_path, f"{pid_id}_Smooth_Phase.png"), dpi=150)
            plt.close()

        print(f"  → SUCCESS: {folder_name}")

    except Exception as exc:
        print(f"  → ERROR [{folder_name}]: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="각 피험자 폴더의 CSV를 읽어 속도/가속도 및 Phase Portrait 그래프를 저장합니다."
    )
    parser.add_argument("--root_dir", required=True, help="Acquisition 결과 루트 폴더")
    args = parser.parse_args()

    if not os.path.exists(args.root_dir):
        print(f"ERROR: 경로를 찾을 수 없습니다: {args.root_dir}")
        return

    subfolders = [
        f for f in os.listdir(args.root_dir)
        if os.path.isdir(os.path.join(args.root_dir, f))
    ]
    print(f"{len(subfolders)}개의 피험자 폴더를 분석합니다.\n")

    for folder_name in subfolders:
        analyze_folder(os.path.join(args.root_dir, folder_name))

    print("\n✨ 모든 시각화가 완료되었습니다!")


if __name__ == "__main__":
    main()
