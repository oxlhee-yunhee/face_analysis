import argparse
import csv
import os
import glob

import cv2
import mediapipe as mp
import numpy as np
from scipy.signal import savgol_filter

# ---------------------------------------------------------------------------
# 분석 대상 랜드마크 (6쌍 = 12개 인덱스)
# Pair1: Outer Corner (61-291)  Pair4: Mid-Cheek  (117-346)
# Pair2: Lower Lip   (181-405)  Pair5: Lower-Cheek (50-280)
# Pair3: Upper Lip   (39-269)   Pair6: Side-Cheek  (207-427)
# ---------------------------------------------------------------------------
TARGET_INDICES = [61, 291, 181, 405, 39, 269, 117, 346, 50, 280, 207, 427]

# MediaPipe FaceMesh 초기화 (모듈 수준 1회만)
_face_mesh = mp.solutions.face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    static_image_mode=False,
)

# 정규화 기준: 양안 거리를 이 값(px)으로 맞춤
EYE_DIST_NORM = 200.0


def get_aligned_landmarks(frame: np.ndarray) -> np.ndarray | None:
    """
    프레임 → 정렬·정규화된 랜드마크 배열 반환.

    처리 순서:
    1. MediaPipe로 478개 랜드마크 픽셀 좌표 추출
    2. 양안 중심을 기준으로 얼굴 수평 정렬 (affine rotation)
    3. 양안 거리를 EYE_DIST_NORM(200px)으로 스케일 정규화
       → 피험자 간 카메라 거리 차이에 의한 절대 좌표 편차 제거

    Returns
    -------
    np.ndarray of shape (478, 2) or None (얼굴 미검출 시)
    """
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = _face_mesh.process(rgb)
    if not results.multi_face_landmarks:
        return None

    h, w = frame.shape[:2]
    pts = np.array(
        [(p.x * w, p.y * h) for p in results.multi_face_landmarks[0].landmark],
        dtype=np.float32,
    )

    left_eye  = pts[33]   # 왼쪽 눈 외안각
    right_eye = pts[263]  # 오른쪽 눈 외안각
    eye_center = (left_eye + right_eye) / 2.0

    # 1) 수평 정렬
    angle = np.degrees(
        np.arctan2(right_eye[1] - left_eye[1], right_eye[0] - left_eye[0])
    )
    M_rot = cv2.getRotationMatrix2D(tuple(eye_center), angle, 1.0)
    ones  = np.ones((pts.shape[0], 1), dtype=np.float32)
    pts_rot = (M_rot @ np.hstack([pts, ones]).T).T  # (478, 2)

    # 2) 스케일 정규화 (양안 거리 → EYE_DIST_NORM)
    eye_dist = np.linalg.norm(pts_rot[263] - pts_rot[33])
    if eye_dist < 1e-6:
        return None
    scale = EYE_DIST_NORM / eye_dist
    pts_norm = (pts_rot - pts_rot[33]) * scale  # 왼눈 기준 원점 이동 후 스케일

    return pts_norm


def find_dynamic_interval(
    lm_seq: list, min_peak_frame: int = 10
) -> tuple[int | None, int | None]:
    """
    전체 랜드마크 시퀀스에서 rest 프레임과 peak 프레임 인덱스를 반환.

    - peak: 입꼬리(61-291) 거리가 최대인 프레임 (Savitzky-Golay 스무딩 후)
    - rest: peak 이전 구간에서 프레임 간 변화량이 가장 작은 지점
    - peak가 min_peak_frame 이전이면 유효한 표정 구간 없음 → (None, None)
    """
    dist_series = [
        np.linalg.norm(lm[61] - lm[291]) if lm is not None else 0.0
        for lm in lm_seq
    ]
    dist_series = np.array(dist_series, dtype=np.float32)

    if len(dist_series) < min_peak_frame + 1:
        return None, None

    win = 21 if len(dist_series) >= 21 else len(dist_series) // 2 * 2 + 1
    smoothed = savgol_filter(dist_series, win, 3)

    peak_idx = int(np.argmax(smoothed))
    if peak_idx < min_peak_frame:
        return None, None

    diffs    = np.abs(np.diff(smoothed[:peak_idx]))
    rest_idx = int(np.argmin(diffs))

    return rest_idx, peak_idx


def process_video(video_path: str, save_dir: str) -> None:
    """
    영상 1개를 처리하여 dual_trajectory_analysis.csv 및 landmarks.npy 저장.

    CSV 컬럼 구조 (Pair당 6열):
        P{i}_L_X, P{i}_L_Y, P{i}_R_X, P{i}_R_Y, P{i}_L_Vel, P{i}_R_Vel
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"   > [ERROR] 영상을 열 수 없습니다: {video_path}")
        return

    full_seq = []
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        full_seq.append(get_aligned_landmarks(frame))
    cap.release()

    if not full_seq:
        print(f"   > [SKIP] 프레임 없음: {os.path.basename(video_path)}")
        return

    rest_idx, peak_idx = find_dynamic_interval(full_seq)
    if rest_idx is None:
        print(f"   > [SKIP] 유효한 표정 구간 없음: {os.path.basename(video_path)}")
        return

    lm_seq = full_seq[rest_idx : peak_idx + 1]

    os.makedirs(save_dir, exist_ok=True)
    csv_path = os.path.join(save_dir, "dual_trajectory_analysis.csv")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        header = ["Absolute_Frame"]
        for i in range(1, 7):
            header += [
                f"P{i}_L_X", f"P{i}_L_Y",
                f"P{i}_R_X", f"P{i}_R_Y",
                f"P{i}_L_Vel", f"P{i}_R_Vel",
            ]
        writer.writerow(header)

        for i, curr_lms in enumerate(lm_seq):
            if curr_lms is None:
                continue
            row = [rest_idx + i]
            for p in range(0, 12, 2):
                l_idx, r_idx = TARGET_INDICES[p], TARGET_INDICES[p + 1]
                l_pt = curr_lms[l_idx]
                r_pt = curr_lms[r_idx]

                prev = lm_seq[i - 1] if i > 0 else None
                l_vel = np.linalg.norm(l_pt - prev[l_idx]) if prev is not None else 0.0
                r_vel = np.linalg.norm(r_pt - prev[r_idx]) if prev is not None else 0.0

                row += [l_pt[0], l_pt[1], r_pt[0], r_pt[1], l_vel, r_vel]
            writer.writerow(row)

    np.save(os.path.join(save_dir, "landmarks.npy"), np.array(lm_seq, dtype=object))
    print(f"   > [SUCCESS] {os.path.basename(video_path)}: frames {rest_idx}~{peak_idx}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="얼굴 영상에서 랜드마크 궤적을 추출하여 CSV/NPY로 저장합니다."
    )
    parser.add_argument("--video_root",  required=True, help="입력 영상 루트 폴더")
    parser.add_argument("--output_root", required=True, help="결과 저장 루트 폴더")
    args = parser.parse_args()

    video_files = [
        f for f in glob.glob(os.path.join(args.video_root, "**", "*"), recursive=True)
        if os.path.isfile(f) and f.lower().endswith((".mov", ".mp4", ".avi"))
    ]

    print(f"총 {len(video_files)}개의 영상을 발견했습니다. 분석을 시작합니다.")

    for v_path in video_files:
        person_name = os.path.basename(os.path.dirname(v_path))
        file_name   = os.path.splitext(os.path.basename(v_path))[0]
        save_path   = os.path.join(args.output_root, f"{person_name}_{file_name}")
        process_video(v_path, save_path)

    print("\n✨ 모든 분석이 완료되었습니다!")


if __name__ == "__main__":
    main()
