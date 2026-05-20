# Facial Motion Asymmetry Analysis
**영상 기반 안면 동적 비대칭 정량화 시스템 — 구안와사 회복 추이 모니터링을 위한 파이프라인**

> EMBC 2025 accepted — *"Dynamic Analysis of Facial Expressions Using Bilateral Asymmetry and Muscle Coordination Metrics"*  
> 박윤희

---

## 연구 개요

안면 비대칭을 보고자 할 때, 보편적으로 정적인 얼굴 사진은 표정의 최종 위치만 담을 뿐, 표정이 형성되는 **동적 과정**에서 나타나는 신경근육 제어 차이를 포착하지 못합니다.

이 프로젝트는 스마트폰 영상 한 편만으로 — 웨어러블 센서 없이 — 좌우 안면 운동의 비대칭을 시계열로 정량화하는 파이프라인을 제안합니다.

핵심 아이디어: 정상적인 얼굴은 표정을 만들 때 좌우가 **시간적으로, 크기 면에서 대칭적으로** 움직입니다. 안면비대칭 또는 구안와사가 있는 사람의 경우, 이 협응이 무너집니다. 따라서 이를 프레임 단위로 좌우 랜드마크 궤적을 비교하면, 육안으로는 보이지 않는 미세한 운동 제어 결함을 관찰할 수 있습니다.

이러한 연구는 스마트폰 카메라만으로 **안면마비 환자의 회복 추이 과정을 추적**하는 것을 목표로 합니다.

---

## 주요 결과

FACS 기반으로 표준화된 두 가지 미소 표정을 8명의 피험자(환자X)에서 비교했습니다.

| 표정 | 근육 제어 | DAA (Pair 1) | Correlation (Pair 1) |
|---|---|---|---|
| Closed-mouth smile | 복잡 (길항근 동시 활성) | 60.34 ± 22.50 | 0.61 ± 0.14 |
| Tooth-showing smile | 상대적으로 단순 | 42.41 ± 30.01 | 0.66 ± 0.29 |

**Closed-mouth smile**은 모든 랜드마크 쌍에서 일관되게 더 큰 비대칭 면적과 낮은 좌우 상관을 보였습니다. 입꼬리 당김근과 안륜근이 동시에 활성화되어야 하는 협응 부담이 더 크기 때문입니다.

Phase portrait 분석에서는 Closed-mouth 조건에서 비선형 궤적 이탈과 미세 가속도 떨림이 더 뚜렷하게 관찰되었으며, 이는 정적 분석으로는 포착할 수 없는 운동 제어 차이를 동적 지표가 담아낸다는 것을 보여줍니다.

---

## 파이프라인

```
영상 입력
    │
    ▼
Acquisition.py          — 랜드마크 추출 · 정렬 · 정규화 · Rest→Peak 구간 탐지
    │
    ├──▶ dynamic_analysis.py          — 6쌍 전체 속도/가속도 그래프 + Phase Portrait
    │
    ├──▶ landmark_Trajectory_test.py  — 입술 3쌍(Pair 1–3) 빠른 확인용 시각화
    │
    └──▶ statistics.py                — 피험자 전체 지표 집계 → 비교 CSV 저장
```

---

## 방법론

### 랜드마크 추출 및 정규화
- **MediaPipe FaceMesh** — 프레임당 478개 랜드마크 픽셀 좌표 추출
- **수평 정렬** — 양안 랜드마크(33, 263) 기준 affine rotation
- **스케일 정규화** — 양안 거리를 200 px로 고정하여 피험자 간 카메라 거리 편차 제거

### Rest → Peak 구간 탐지
- **Rest 프레임** — 표정 형성 이전 구간 중 프레임 간 변화량이 최소인 지점 (Savitzky-Golay 스무딩 적용)
- **Peak 프레임** — 입꼬리 간 거리(landmark 61–291)가 최대인 지점
- Rest → Peak 구간만 분석하여 표정 형성 과정만 포착

### 랜드마크 쌍 구성 (6쌍)
| Pair | 영역 | 랜드마크 |
|---|---|---|
| Pair 1 | Outer corner | 61 – 291 |
| Pair 2 | Lower lip | 181 – 405 |
| Pair 3 | Upper lip | 39 – 269 |
| Pair 4 | Mid-cheek | 117 – 346 |
| Pair 5 | Lower-cheek | 50 – 280 |
| Pair 6 | Side-cheek | 207 – 427 |

### 정량화 지표
| 지표 | 설명 |
|---|---|
| **DAA** | Dynamic Asymmetry Area — 좌우 속도 곡선 사이의 적분 면적 |
| **Corr** | 좌우 속도 시계열의 Pearson 상관계수 |
| **TimeLag** | 교차상관 기반 좌우 움직임 시작 시점 차이 (프레임 단위) |
| **AAI** | Acceleration Asymmetry Index — 가속도 표준편차의 정규화 차이 |
| **PEI** | Path Efficiency Index — 실제 경로 길이 / 직선 변위 |

---

## 데이터 수집 프로토콜

- **카메라**: 스마트폰, 30 FPS, 고정 거리
- **조명**: 링라이트 최대 밝기, 벽에서 약 80 cm
- **배경**: 흰 벽
- **자세**: 척추 보조 쿠션으로 상체 고정
- **표정** (FACS 기반 표준화):
  1. Closed-mouth smile (AU12 + orbicularis oris)
  2. Tooth-showing smile (AU12 주도)
- **피험자**: 건강한 성인 8명 (연구실 구성원)
- 모든 표정은 무표정 → 표정 전환 방식으로 영상 촬영

---

## 설치

```bash
pip install opencv-python mediapipe numpy scipy pandas matplotlib
```

Python 3.9 이상 권장.

---

## 사용법

### 1. 랜드마크 추출
```bash
python Acquisition.py \
    --video_root  ./data/videos \
    --output_root ./data/output_results
```

### 2. 동적 분석 시각화 (6쌍 전체)
```bash
python dynamic_analysis.py \
    --root_dir ./data/output_results
```

### 2-alt. 입술 3쌍만 빠르게 확인
```bash
python landmark_Trajectory_test.py \
    --root_dir ./data/output_results
```

### 3. 피험자 전체 통계 집계
```bash
python statistics.py \
    --root_dir  ./data/output_results \
    --keyword_a "6. Closed-mouth" \
    --keyword_b "7. Mouth stretch" \
    --output    ./data/Expression_Comparison.csv
```

> **폴더 네이밍 규칙** (`statistics.py`의 키워드 매칭 기준):  
> `{피험자명}_{표정라벨}` — 예: `yunhee_6. Closed-mouth smile`

---

## 출력 구조

```
output_results/
└── {피험자}_{표정}/
    ├── dual_trajectory_analysis.csv   # 프레임별 랜드마크 좌표 및 속도
    ├── landmarks.npy                  # 랜드마크 시퀀스 원본 (numpy object array)
    ├── Pair_1_Analysis.png            # 속도 & 가속도 그래프
    ├── Pair_1_Smooth_Phase.png        # Phase portrait (변위–속도)
    ├── Pair_2_Analysis.png
    ├── Pair_2_Smooth_Phase.png
    └── ...
```


## 한계 및 향후 연구

- **표본 수**: 건강한 피험자 8명으로 임상 데이터(실제 구안와사 환자) 미포함
- **MediaPipe 추정 오차**: 표정이 작은 경우 및 표정형성 과정의 개개인의 차이 등으로 랜드마크 추정 노이즈가 신호처럼 보일 수 있음 — 절대값보다 상대 지표(Corr, AAI, nDAA)가 더 강건함
- **2D 분석**: 깊이 정보 미반영 — 3D 재구성은 향후 과제
- **임상 검증**: 구안와사 환자의 주 단위 회복 추이 종단 추적이 최우선 후속 과제

---


## References

[1] N. Mueller et al., "High-resolution surface electromyographic activities of facial muscles during mimic movements in healthy adults: A prospective observational study," *Front. Hum. Neurosci.*, vol. 16, Art. no. 1029415, 2022.

[2] M. F. Valstar and M. Pantic, "Fully automatic recognition of the temporal phases of facial actions," *IEEE Trans. Syst., Man, Cybern. B (Cybern.)*, vol. 42, no. 1, pp. 28–43, Feb. 2012.

[3] T. S. Kim, H. S. Lee, and K. J. Park, "Quantitative analysis of movements in facial nerve palsy with surface electromyography and kinematic analysis," *Clin. Biomech.*, vol. 18, no. 7, pp. 605–615, 2003.

---



## Citation

```

```

---

## 감사의 말


