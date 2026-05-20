"""
landmark_Trajectory_test.py
----------------------------
입술 3쌍(Pair 1–3)에 집중한 초기 탐색용 시각화 스크립트.
dynamic_analysis.py가 6쌍 전체를 처리하는 반면,
이 스크립트는 입술 영역만 빠르게 확인할 때 사용합니다.

출력 파일 (폴더당):
  Pair_{n}_Analysis.png     — 속도 & 가속도 그래프 (Pair 1–3)
  Pair_{n}_Smooth_Phase.png — Smoothed Phase Portrait (Pair 1–3)
"""

import argparse
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter
from scipy.stats import pearsonr

# 입술 3쌍만 분석
PAIRS = [
    {"id": "Pair_1", "prefix": "P1", "name": "Outer Corner (61-291)", "l_vel": "P1_L_Vel", "r_vel": "P1_R_Vel"},
    {"id": "Pair_2", "prefix": "P2", "name": "Lower Lip (181-405)",   "l_vel": "P2_L_Vel", "r_vel": "P2_R_Vel"},
    {"id": "Pair_3", "prefix": "P3", "name": "Upper Lip (39-269)",    "l_vel": "P3_L_Vel", "r_vel": "P3_R_Vel"},
]


def smooth_disp_vel(
    x: np.ndarray, y: np.ndarray, v: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    disp = np.sqrt((x - x[0])**2 + (y - y[0])**2)
    n    = len(disp)
    win  = 31 if n > 31 else (n // 2 * 2 - 1)
    if win < 3:
        return disp, v
    return savgol_filter(disp, win, 3), savgol_filter(v, win, 3)


def visualize_folder(person_path: str) -> None:
    csv_path = os.path.join(person_path, "dual_trajectory_analysis.csv")
    if not os.path.exists(csv_path):
        print(f"SKIPPING: {os.path.basename(person_path)} (CSV 없음)")
        return

    folder_name = os.path.basename(person_path)
    print(f"VISUALIZING: {folder_name}")

    try:
        df = pd.read_csv(csv_path)
        df.columns = df.columns.str.strip()
        df = df.dropna()

        frames = df["Absolute_Frame"].values

        # --- Part 1: Velocity & Acceleration (입술 3쌍) ---
        for pair in PAIRS:
            l_vel = df[pair["l_vel"]].values
            r_vel = df[pair["r_vel"]].values

            corr, _         = pearsonr(l_vel, r_vel)
            asymmetry_area  = float(np.trapz(np.abs(l_vel - r_vel), x=frames))

            l_acc  = np.diff(l_vel)
            r_acc  = np.diff(r_vel)
            l_std  = float(np.std(l_acc))
            r_std  = float(np.std(r_acc))

            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10))

            ax1.plot(frames, l_vel, label="Left Velocity",  color="cyan", lw=1.5)
            ax1.plot(frames, r_vel, label="Right Velocity", color="red",  lw=1.5, ls="--")
            ax1.fill_between(frames, l_vel, r_vel, color="gray", alpha=0.3, label="Asymmetry Area")
            ax1.set_title(f"[{pair['name']}] Velocity\nCorr: {corr:.4f} | DAA: {asymmetry_area:.2f}")
            ax1.set_xlabel("Frame")
            ax1.set_ylabel("Velocity (px/frame)")
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            ax2.plot(frames[:-1], l_acc, label=f"Left  Accel (Std: {l_std:.2f})", color="deeppink", alpha=0.6)
            ax2.plot(frames[:-1], r_acc, label=f"Right Accel (Std: {r_std:.2f})", color="black",    alpha=0.6, ls="--")
            ax2.set_title("Acceleration (Smoothness Analysis)")
            ax2.set_xlabel("Frame")
            ax2.set_ylabel("Acceleration (px/frame²)")
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.savefig(os.path.join(person_path, f"{pair['id']}_Analysis.png"), dpi=150)
            plt.close()

        # --- Part 2: Smoothed Phase Portrait (입술 3쌍) ---
        for pair in PAIRS:
            pid = pair["prefix"]
            l_x = df[f"{pid}_L_X"].values
            l_y = df[f"{pid}_L_Y"].values
            r_x = df[f"{pid}_R_X"].values
            r_y = df[f"{pid}_R_Y"].values
            l_vel = df[f"{pid}_L_Vel"].values
            r_vel = df[f"{pid}_R_Vel"].values

            sl_disp, sl_vel = smooth_disp_vel(l_x, l_y, l_vel)
            sr_disp, sr_vel = smooth_disp_vel(r_x, r_y, r_vel)

            plt.figure(figsize=(8, 6))
            plt.plot(sl_disp, sl_vel, label="Left",  color="cyan", lw=3)
            plt.plot(sr_disp, sr_vel, label="Right", color="red",  lw=3, ls="--")
            plt.title(f"Smoothed Phase Portrait\n{pair['name']}")
            plt.xlabel("Displacement (px)")
            plt.ylabel("Velocity (px/frame)")
            plt.legend()
            plt.grid(True, ls=":", alpha=0.6)
            plt.savefig(os.path.join(person_path, f"{pair['id']}_Smooth_Phase.png"), dpi=150)
            plt.close()

        print(f"  → SUCCESS: {folder_name}")

    except Exception as exc:
        print(f"  → ERROR [{folder_name}]: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="입술 3쌍(Pair 1–3) 랜드마크의 속도 및 Phase Portrait을 시각화"
    )
    parser.add_argument("--root_dir", required=True, help="Acquisition 결과 루트 폴더")
    args = parser.parse_args()

    subfolders = [
        f for f in os.listdir(args.root_dir)
        if os.path.isdir(os.path.join(args.root_dir, f))
    ]
    print(f"총 {len(subfolders)}개의 피험자 폴더를 시각화합니다.\n")

    for folder_name in subfolders:
        visualize_folder(os.path.join(args.root_dir, folder_name))

    print("\n 시각화 완료!")


if __name__ == "__main__":
    main()
