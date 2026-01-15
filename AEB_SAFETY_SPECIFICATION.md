# AEB 시스템 안전 설계 명세서
## Autonomous Emergency Braking Safety Specification

---

**문서 정보**

| 항목 | 내용 |
|------|------|
| 시스템명 | AI 기반 자율 긴급 제동 시스템 (AEB) |
| 버전 | 1.0 |
| 작성일 | 2026년 1월 14일 |
| 안전 무결성 등급 | ASIL-D (ISO 26262) |
| 적용 차량 | 승용차, SUV (Level 2+ 자율주행) |
| 문서 상태 | Draft |

---

## 📑 목차

1. [시스템 개요](#1-시스템-개요)
2. [전략 1: Inherently Safe Design](#전략-1-inherently-safe-design-본질적-안전-설계)
3. [전략 2: 설명가능성 확보](#전략-2-설명가능성explainability-확보)
4. [전략 3: 데이터 기반 위험 분석](#전략-3-데이터-기반-위험-분석)
5. [전략 4: 수동적 및 능동적 안전장치](#전략-4-수동적-및-능동적-안전장치)
6. [전략 5: 제어 가능성 & 인간 중심 설계](#전략-5-제어-가능성--인간-중심-설계)
7. [부록](#부록)

---

## 1. 시스템 개요

### 1.1 AEB 시스템 정의

> **정의:** 자율 긴급 제동(AEB, Autonomous Emergency Braking) 시스템은 차량 전방의 장애물(차량, 보행자, 자전거, 고정 물체)을 감지하고, 충돌이 임박한 경우 자동으로 제동을 작동시켜 충돌을 회피하거나 충돌 속도를 감소시키는 AI 기반 안전 시스템입니다.

### 1.2 시스템 목표

| 우선순위 | 목표 | 설명 |
|----------|------|------|
| 1차 | 충돌 회피 | 속도 0 km/h까지 완전 감속 |
| 2차 | 충돌 속도 감소 | 피해 최소화 (부상 경감) |
| 3차 | 오작동 방지 | 불필요한 제동 최소화 (False Positive < 0.1%) |
| **안전 목표** | **인명 피해 제로** | **시스템 오작동으로 인한 2차 사고 방지** |

### 1.3 운영 환경

#### 환경 조건

| 파라미터 | 범위/조건 |
|----------|-----------|
| **속도 범위** | 0 - 180 km/h |
| **날씨 조건** | 맑음, 비, 눈, 안개 (가시거리 50m 이상) |
| **도로 조건** | 고속도로, 일반도로, 시내도로 |
| **주야간** | 24시간 운영 (주간/야간 모두) |
| **온도 범위** | -20°C ~ +50°C |

### 1.4 센서 구성

#### 멀티 센서 퓨전 아키텍처

```
┌─────────────────┐
│  전방 카메라    │  120° FOV, 150m
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  센서 퓨전      │◄──────┐
│  프로세서       │        │
└────────┬────────┘        │
         │                 │
         ▼                 │
┌─────────────────┐        │
│  AI 의사결정    │        │
│  모듈           │        │
└─────────────────┘        │
                           │
┌─────────────────┐        │
│  레이더 (77GHz) │  200m ─┤
└─────────────────┘        │
                           │
┌─────────────────┐        │
│  라이다 (LiDAR) │  100m ─┤
└─────────────────┘        │
                           │
┌─────────────────┐        │
│  초음파 센서    │  5m   ─┘
└─────────────────┘
```

**센서 상세 스펙**

| 센서 | 사양 | 용도 | 장점 | 한계 |
|------|------|------|------|------|
| 스테레오 카메라 | 120° FOV, 150m | 객체 인식, 분류 | 고해상도, 색상 정보 | 악천후 취약 |
| 밀리미터파 레이더 | 77GHz, 200m | 거리/속도 측정 | 전천후, 장거리 | 해상도 낮음 |
| LiDAR | 100m, 0.1° 각도 | 3D 형상 인식 | 정확한 거리, 형상 | 비용 높음, 악천후 |
| 초음파 | 5m | 근거리 감지 | 저비용, 근접 정밀 | 초단거리만 |
| V2X (선택) | 300m | 통신 기반 정보 | 시야 외 정보 | 인프라 필요 |

---

## 전략 1: Inherently Safe Design (본질적 안전 설계)

### 1.1 설계 철학

> **💡 핵심 원칙:** "불확실하면 제동한다" (Brake when uncertain)
>
> AEB 시스템은 불확실한 상황에서 **보수적 제동**을 기본 동작으로 설정하여, AI의 오판단보다 불필요한 제동이 더 안전한 선택이 되도록 설계합니다.

### 1.2 본질적 안전 요구사항

#### 1.2.1 Safe State 정의

**안전 상태 (Safe State)**

```pseudocode
IF (장애물 존재 확신도 < THRESHOLD_LOW) AND (상황 불확실)
THEN
    상태 = SAFE_DECELERATION
    감속률 = 3 m/s² (승객 불편 최소화)
    경고 = ON
    로그 = "불확실한 상황 감지 - 보수적 제동"
```

**위험 상태 (Unsafe State)**

```pseudocode
IF (장애물 존재 확신도 >= THRESHOLD_HIGH) AND (충돌 시간 < TTC_CRITICAL)
THEN
    상태 = EMERGENCY_BRAKING
    감속률 = 9.8 m/s² (최대 감속)
    경고 = CRITICAL
    로그 = "긴급 상황 - 최대 제동"
```

#### 1.2.2 Fail-Safe 동작

센서 고장 시 안전한 기본 동작으로 전환하는 메커니즘을 구현합니다.

```python
class AEBFailSafeController:
    """센서 고장 시 Fail-Safe 제어"""

    def handle_sensor_failure(self, failed_sensor: SensorType):
        """센서 고장 시 본질적 안전 동작

        Args:
            failed_sensor: 고장난 센서 타입

        Returns:
            None (시스템 상태 직접 변경)
        """

        if failed_sensor == SensorType.CAMERA:
            # 카메라 고장 → 레이더/라이다에 의존
            self.mode = OperatingMode.DEGRADED_VISION
            self.max_speed = 80  # km/h로 제한
            self.warning_distance += 20  # m (경고 거리 증가)
            self.log_event("카메라 고장 - 제한 모드 진입")

        elif failed_sensor == SensorType.RADAR:
            # 레이더 고장 → 카메라/라이다에 의존
            self.mode = OperatingMode.DEGRADED_RANGING
            self.confidence_threshold += 0.2  # 더 보수적 판단
            self.log_event("레이더 고장 - 보수적 모드 진입")

        elif failed_sensor == SensorType.LIDAR:
            # 라이다 고장 → 카메라/레이더로 운영
            self.mode = OperatingMode.DEGRADED_3D
            self.braking_distance += 10  # m (제동 거리 증가)
            self.log_event("라이다 고장 - 제동 거리 증가")

        # 🚨 2개 이상 센서 고장 → 안전 정지
        if self.failed_sensor_count >= 2:
            self.initiate_safe_stop()
            self.notify_driver(AlertLevel.CRITICAL)
            self.log_event("다중 센서 고장 - 안전 정지 시작")
```

#### 1.2.3 불확실성 처리

AI 신뢰도에 따라 제동 강도를 조절하는 계층적 접근 방식을 사용합니다.

**AI 신뢰도 기반 제동 전략**

| AI 신뢰도 | 동작 | 제동 강도 | 감속도 | 운전자 알림 |
|-----------|------|-----------|--------|-------------|
| 🔴 0.95 - 1.0 | 긴급 제동 | 100% | 9.8 m/s² | Critical Alert |
| 🟠 0.80 - 0.95 | 강한 제동 | 70% | 6.9 m/s² | High Warning |
| 🟡 0.60 - 0.80 | 중간 제동 | 40% | 3.9 m/s² | Medium Warning |
| 🟢 0.40 - 0.60 | 약한 제동 | 20% | 2.0 m/s² | Low Warning |
| ⚪ 0.00 - 0.40 | 경고만 | 0% | 0 m/s² | Visual/Audio Alert |

> **📝 Note:** 신뢰도가 0.60 미만인 경우에도 제동을 수행하는 이유는 "불확실하면 제동한다" 원칙에 따른 것입니다. False Positive(불필요한 제동)가 False Negative(충돌 미감지)보다 안전합니다.

#### 1.2.4 최악 시나리오 대비

모든 설계는 최악의 조건을 가정하여 안전 마진을 확보합니다.

```python
class WorstCaseScenario:
    """최악 시나리오 기반 안전 설계"""

    # 물리적 한계 가정
    MAX_DECELERATION = 9.8  # m/s² (건조 노면, 신차 타이어)
    MIN_DECELERATION = 6.0  # m/s² (젖은 노면, 마모된 타이어)

    # 센서 한계 가정
    SENSOR_LATENCY = 100  # ms (최악 지연시간)
    SENSOR_ERROR_RATE = 0.01  # 1% 오탐지율

    # 환경 한계 가정
    WORST_VISIBILITY = 50  # m (안개/폭우)
    WORST_FRICTION = 0.3  # 빙판길 마찰계수

    def calculate_safe_distance(self, velocity: float) -> float:
        """최악 조건 기반 안전 거리 계산

        Args:
            velocity: 현재 속도 (m/s)

        Returns:
            float: 안전 거리 (m)
        """
        # 1. 반응 시간 거리 (센서 지연 포함)
        reaction_time = 0.1 + self.SENSOR_LATENCY / 1000  # 총 200ms
        reaction_distance = velocity * reaction_time

        # 2. 제동 거리 (최악의 감속도 사용)
        braking_distance = (velocity ** 2) / (2 * self.MIN_DECELERATION)

        # 3. 안전 마진 (속도의 50%)
        safety_margin = velocity * 0.5

        # 4. 총 안전 거리
        total_safe_distance = (
            reaction_distance +
            braking_distance +
            safety_margin
        )

        return total_safe_distance
```

**안전 거리 계산 예시**

| 속도 (km/h) | 반응거리 (m) | 제동거리 (m) | 안전마진 (m) | **총 안전거리 (m)** |
|-------------|--------------|--------------|--------------|---------------------|
| 30 | 1.7 | 5.8 | 4.2 | **11.7** |
| 60 | 3.3 | 23.1 | 8.3 | **34.7** |
| 100 | 5.6 | 64.2 | 13.9 | **83.7** |
| 120 | 6.7 | 92.6 | 16.7 | **116.0** |

### 1.3 검증 방법

#### 1.3.1 안전 케이스 검증

**필수 테스트 시나리오**

1. **센서 완전 고장 시나리오**
   - **목적:** Fail-Safe 동작 검증
   - **방법:** 모든 센서 입력 차단
   - **예상 결과:** 안전 정지 수행
   - **합격 기준:** 100% 안전 정지 성공

2. **극한 환경 시나리오**
   - **목적:** 최악 조건 대응 검증
   - **조건:** 폭우 + 야간 + 고속(100 km/h)
   - **방법:** HIL 시뮬레이션 또는 실제 환경
   - **예상 결과:** 보수적 제동 수행
   - **합격 기준:** False Negative Rate < 0.01%

3. **애매한 장애물 시나리오**
   - **목적:** 불확실성 처리 검증
   - **대상:** 비닐봉지, 종이박스, 낙하물 등
   - **방법:** 다양한 크기/형태 물체 배치
   - **예상 결과:** 일단 제동 (보수적 접근)
   - **합격 기준:** 위험한 물체 100% 제동

#### 1.3.2 정량적 안전 목표

| 메트릭 | 목표값 | 측정 방법 |
|--------|--------|-----------|
| MTBF (평균 고장 간격) | > 10,000 시간 | 장기 운영 테스트 |
| False Positive Rate | < 0.1% | 1000회 주행 중 1회 미만 |
| False Negative Rate | < 0.001% | 100,000회 위험 상황 중 1회 미만 |
| Response Time | < 100ms | 장애물 감지부터 제동 명령까지 |
| Availability | > 99.9% | 연간 다운타임 < 8.76시간 |

---

## 전략 2: 설명가능성(Explainability) 확보

### 2.1 XAI 적용 목적

> **⚠️ 중요:** AEB 시스템의 모든 제동 결정은 **설명 가능하고 추적 가능**해야 하며, 사고 발생 시 원인 분석과 책임 소재 판단을 위한 명확한 근거를 제공해야 합니다.

### 2.2 설명가능성 요구사항

#### 2.2.1 실시간 설명 생성

제동 결정 시 모든 관련 데이터를 기록하고 설명을 생성합니다.

```python
from dataclasses import dataclass
from datetime import datetime
from typing import List
import numpy as np

@dataclass
class BrakingDecisionExplanation:
    """제동 결정에 대한 완전한 설명 데이터

    이 데이터 구조는 사고 조사, 시스템 개선, 법적 책임 판단에
    필수적인 모든 정보를 포함합니다.
    """

    # === 시간 정보 ===
    timestamp: datetime
    decision_id: str  # 고유 식별자 (UUID)

    # === 센서 데이터 ===
    camera_confidence: float  # 카메라 객체 인식 신뢰도 [0.0-1.0]
    radar_distance: float  # 레이더 측정 거리 (m)
    lidar_pointcloud: np.ndarray  # 라이다 포인트 클라우드

    # === AI 판단 근거 ===
    object_type: ObjectType  # 차량/보행자/자전거/장애물
    object_confidence: float  # 객체 분류 신뢰도 [0.0-1.0]
    collision_probability: float  # 충돌 확률 [0.0-1.0]
    time_to_collision: float  # 충돌까지 예상 시간 (초)

    # === 결정 과정 ===
    risk_level: RiskLevel  # LOW/MEDIUM/HIGH/CRITICAL
    decision: BrakingDecision  # NO_ACTION/WARNING/BRAKE/EMERGENCY_BRAKE
    braking_force: float  # 제동력 (%)

    # === 대안 평가 ===
    alternative_actions: List[AlternativeAction]  # 고려했던 다른 행동들
    why_chosen: str  # 선택 이유 (자연어)

    # === 환경 정보 ===
    vehicle_speed: float  # 차량 속도 (km/h)
    weather_condition: WeatherType  # 날씨 조건
    road_condition: RoadType  # 도로 조건
    visibility: float  # 가시거리 (m)

    # === 설명 생성 ===
    explanation_summary: str  # 한 문장 요약
    # 예: "전방 20m 보행자 감지, 충돌 1.2초 전, 긴급 제동"

    contributing_factors: List[str]  # 결정에 기여한 요인들
    # 예: ["고속 주행", "야간", "보행자 횡단", "짧은 TTC"]
```

**설명 생성 예시**

```python
explanation = BrakingDecisionExplanation(
    timestamp=datetime.now(),
    decision_id="dec-20260114-154523-abc123",
    camera_confidence=0.92,
    radar_distance=18.5,
    object_type=ObjectType.PEDESTRIAN,
    object_confidence=0.89,
    collision_probability=0.95,
    time_to_collision=1.2,
    risk_level=RiskLevel.CRITICAL,
    decision=BrakingDecision.EMERGENCY_BRAKE,
    braking_force=100.0,
    vehicle_speed=65.0,
    weather_condition=WeatherType.NIGHT_CLEAR,
    explanation_summary="전방 18.5m 보행자 감지 (신뢰도 89%), 충돌 1.2초 전, 긴급 제동 실행",
    contributing_factors=[
        "야간 주행",
        "보행자 갑작스런 횡단",
        "높은 차량 속도 (65 km/h)",
        "짧은 TTC (1.2초)"
    ],
    why_chosen="충돌 확률 95%로 매우 높고 TTC가 1.2초로 매우 짧아 즉각적인 최대 제동 필요"
)
```

#### 2.2.2 Layer-wise Relevance Propagation (LRP)

신경망의 결정 과정을 시각화하여 어떤 입력 영역이 결정에 중요했는지 보여줍니다.

```python
class AEBExplainableNN:
    """설명가능한 AEB 신경망

    LRP (Layer-wise Relevance Propagation)를 사용하여
    신경망의 결정 과정을 역추적하고 시각화합니다.
    """

    def __init__(self):
        self.detection_network = ObjectDetectionNet()
        self.lrp_analyzer = LRPAnalyzer()

    def predict_with_explanation(self, sensor_data: SensorFusion):
        """예측과 설명을 동시에 생성

        Args:
            sensor_data: 센서 퓨전 데이터

        Returns:
            tuple: (탐지 결과, 설명 데이터)
        """

        # 1. 객체 감지 수행
        detections = self.detection_network(sensor_data)

        # 2. LRP로 중요 영역 분석
        relevance_map = self.lrp_analyzer.compute_relevance(
            network=self.detection_network,
            input_data=sensor_data.camera_image
        )

        # 3. 인간이 이해 가능한 설명 생성
        explanation = self._generate_explanation(
            detections=detections,
            relevance_map=relevance_map,
            sensor_data=sensor_data
        )

        return detections, explanation

    def _explain_detection(self, detection, important_regions):
        """개별 탐지에 대한 설명 생성"""
        reasons = []

        # 형태 기반 판단
        if detection.has_feature("wheels"):
            reasons.append("🚗 차량 바퀴 형태 감지")

        # 움직임 기반 판단
        if detection.velocity > 0:
            reasons.append(f"🏃 이동 속도 {detection.velocity:.1f} km/h")

        # 크기 기반 판단
        if detection.size > 100:  # pixels
            reasons.append("📏 대형 물체로 판단 (>100px)")

        # 히트맵 기반 판단
        overlap = self._calculate_overlap(detection.bbox, important_regions)
        if overlap > 0.7:
            reasons.append("🎯 높은 주의 영역에 위치 (70%+ 겹침)")

        return " | ".join(reasons)
```

**LRP 히트맵 시각화 예시**

```
[카메라 이미지]           [LRP 히트맵]           [설명]

 ┌─────────────┐         ┌─────────────┐      "신경망이 이미지의
 │             │         │░░░░░░░░░░░░░│       빨간색 영역에 집중:
 │   🚶 ──►   │   ═►   │░░🔴🔴🔴░░░░░│       - 사람 형태 (머리, 몸통)
 │             │         │░░🔴🔴🔴░░░░░│       - 움직임 패턴
 │    🚗      │         │░░🔴🔴🔴░░░░░│       - 보행자 특징적 자세
 └─────────────┘         └─────────────┘       이를 기반으로 보행자 분류"
```

#### 2.2.3 결정 트리 기반 규칙 추출

복잡한 신경망을 해석 가능한 IF-THEN 규칙으로 변환합니다.

```python
class DecisionTreeExtractor:
    """신경망 동작을 결정 트리로 근사

    블랙박스 신경망을 화이트박스 결정 트리로 변환하여
    명확한 규칙 기반 설명을 제공합니다.
    """

    def extract_rules(self, nn_model, training_data):
        """신경망 동작을 결정 트리로 근사

        Args:
            nn_model: 학습된 신경망 모델
            training_data: 학습 데이터

        Returns:
            List[Rule]: 추출된 규칙 리스트
        """

        # 1. 신경망 예측 수집
        predictions = []
        for data in training_data:
            pred = nn_model.predict(data)
            predictions.append((data.features, pred.label))

        # 2. 결정 트리 학습 (신경망 모방)
        dt_model = DecisionTreeClassifier(
            max_depth=10,
            min_samples_leaf=100
        )
        X = [p[0] for p in predictions]
        y = [p[1] for p in predictions]
        dt_model.fit(X, y)

        # 3. 규칙 추출
        rules = self._tree_to_rules(dt_model)

        return rules
```

**추출된 규칙 예시**

```python
# Rule 1: 긴급 제동
"""
IF distance < 20m
   AND velocity > 50 km/h
   AND object_type = "pedestrian"
   AND TTC < 2.0s
THEN emergency_brake
    (신뢰도: 0.98, 샘플 수: 1,234)
"""

# Rule 2: 강한 제동
"""
IF distance < 50m
   AND TTC < 2.5s
   AND object_type = "vehicle"
   AND confidence > 0.85
THEN strong_brake
    (신뢰도: 0.95, 샘플 수: 5,678)
"""

# Rule 3: 경고만
"""
IF distance > 100m
   OR TTC > 5.0s
   OR confidence < 0.5
THEN warning_only
    (신뢰도: 0.92, 샘플 수: 45,123)
"""
```

#### 2.2.4 블랙박스 데이터 기록

사고 조사를 위한 고해상도 데이터 기록 시스템입니다.

```python
class AEBBlackBox:
    """AEB 블랙박스 데이터 로거

    항공기 블랙박스와 유사하게, 사고 전후의 모든 데이터를
    고해상도로 기록하여 사고 조사에 활용합니다.
    """

    def __init__(self, storage_path: str):
        self.storage = RingBuffer(capacity_gb=32)  # 32GB 순환 버퍼
        self.high_res_recorder = HighResolutionRecorder()

    def _record_high_resolution_event(self, decision):
        """제동 이벤트 고해상도 기록

        제동 전후 10초간의 모든 센서 데이터와 AI 내부 상태를
        저장하여 사고 조사에 활용합니다.
        """

        event_data = {
            # 📹 센서 원시 데이터
            "camera_frames": self._get_camera_history(duration=10),  # 10초
            "radar_traces": self._get_radar_history(duration=10),
            "lidar_scans": self._get_lidar_history(duration=10),

            # 🧠 AI 내부 상태
            "neural_network_activations": self._dump_nn_state(),
            "feature_maps": self._get_feature_maps(),
            "attention_weights": self._get_attention_weights(),

            # 🚗 물리 상태
            "vehicle_dynamics": self._get_dynamics_history(duration=10),
            "brake_pressure": self._get_brake_pressure_history(duration=10),
            "steering_angle": self._get_steering_history(duration=10),

            # 📊 설명 데이터
            "decision_explanation": decision.model_dump(),
            "alternative_scenarios": self._simulate_alternatives(decision)
        }

        # 압축 저장 (사고 조사 시 복원)
        filename = f"event_{decision.timestamp.isoformat()}.aeb"
        self.high_res_recorder.save_compressed(event_data, filename)

    def generate_incident_report(self, event_id: str) -> str:
        """사고 보고서 자동 생성

        Args:
            event_id: 이벤트 ID

        Returns:
            str: 자동 생성된 사고 보고서 (Markdown 형식)
        """

        event = self.high_res_recorder.load(event_id)

        report = f"""
# AEB 사고/이벤트 보고서

## 기본 정보

- **이벤트 ID:** `{event_id}`
- **발생 시각:** {event['timestamp']}
- **차량 번호:** [REDACTED]
- **위치:** GPS {event['location']}

---

## 1. 상황 요약

### 차량 상태
- 차량 속도: **{event['vehicle_state']['speed']} km/h**
- 도로 조건: {event['road_condition']}
- 날씨: {event['weather']}
- 가시거리: {event['visibility']} m

### 장애물 정보
- 종류: **{event['decision_explanation']['object_type']}**
- 거리: **{event['decision_explanation']['radar_distance']} m**
- 충돌까지 시간: **{event['decision_explanation']['time_to_collision']} s**
- AI 신뢰도: {event['decision_explanation']['object_confidence'] * 100:.1f}%

---

## 2. AI 판단 근거

### 결정 과정
{event['decision_explanation']['why_chosen']}

### 기여 요인
{self._format_factors(event['decision_explanation']['contributing_factors'])}

---

## 3. 제동 결과

- **제동력:** {event['decision_explanation']['braking_force']}%
- **최종 속도:** {event['final_speed']} km/h
- **충돌 여부:** {'❌ 발생' if event['collision_occurred'] else '✅ 회피'}
- **제동 거리:** {event['braking_distance']} m

---

## 4. 대안 시나리오 분석

{self._analyze_alternatives(event['alternative_scenarios'])}

---

## 5. 센서 데이터 검증

| 센서 | 상태 | 신뢰도 | 비고 |
|------|------|--------|------|
| 카메라 | {event['camera_status']} | {event['camera_confidence']} | - |
| 레이더 | {event['radar_status']} | {event['radar_signal_strength']} | - |
| 라이다 | {event['lidar_status']} | {event['lidar_point_count']} pts | - |

---

## 6. 결론

{self._generate_conclusion(event)}

---

**보고서 생성 시각:** {datetime.now().isoformat()}
**생성자:** AEB 자동 사고 분석 시스템 v1.0
        """

        return report
```

### 2.3 검증 방법

#### 2.3.1 설명 일관성 검증

| 테스트 | 방법 | 합격 기준 |
|--------|------|-----------|
| 재현성 | 동일 상황 100회 반복 | 동일한 설명 100% 생성 |
| 일관성 | 유사 상황 비교 | 논리적 일관성 > 95% |
| 타당성 | 전문가 평가 (10명) | 평균 타당성 점수 > 4.0/5.0 |

---

## 전략 3: 데이터 기반 위험 분석

### 3.1 학습 데이터 안전성 검증

> **⚠️ 핵심 인사이트:** AEB 시스템의 안전성은 학습 데이터의 품질에 크게 의존합니다. 편향되거나 불완전한 데이터는 시스템 오작동의 근본 원인이 됩니다.

### 3.2 데이터 수집 및 검증 프로토콜

#### 3.2.1 데이터 수집 요구사항

**최소 데이터 볼륨**

| 시나리오 | 최소 샘플 수 | 이유 |
|----------|--------------|------|
| 정상 주행 | 1,000,000 | 기본 동작 학습 |
| 아슬아슬한 상황 (Near-miss) | 100,000 | 경고 시스템 학습 |
| 긴급 제동 상황 | 10,000 | 긴급 대응 학습 |
| 실제 충돌 (시뮬레이션) | 1,000 | 극한 상황 학습 |

**다양성 요구사항**

```python
class DataCollectionRequirements:
    """AEB 학습 데이터 수집 요구사항"""

    DIVERSITY_REQUIREMENTS = {
        "weather": {
            "sunny": 0.40,    # 40% 맑음
            "rainy": 0.25,    # 25% 비
            "snow": 0.15,     # 15% 눈
            "fog": 0.10,      # 10% 안개
            "night": 0.10     # 10% 야간
        },
        "road_type": {
            "highway": 0.30,   # 30% 고속도로
            "urban": 0.40,     # 40% 시내
            "rural": 0.20,     # 20% 시골
            "parking": 0.10    # 10% 주차장
        },
        "object_type": {
            "vehicle": 0.50,      # 50% 차량
            "pedestrian": 0.25,   # 25% 보행자
            "cyclist": 0.15,      # 15% 자전거
            "stationary": 0.10    # 10% 고정 물체
        },
        "speed": {
            "0-30": 0.30,      # 30% 저속
            "30-60": 0.35,     # 35% 중속
            "60-100": 0.25,    # 25% 고속
            "100+": 0.10       # 10% 초고속
        }
    }

    # 🚨 극한 상황 (Edge Cases) 필수 포함
    EDGE_CASES = [
        "아동 돌발 횡단",
        "터널 진입/출구 (급격한 조도 변화)",
        "역광 상황 (해가 카메라 방향)",
        "폭우 + 야간 (복합 악조건)",
        "눈 덮인 도로 + 안개",
        "대형 트럭 끼어들기",
        "갑작스런 정지 차량 (고속도로)",
        "동물 출몰 (사슴, 멧돼지)",
        "낙하물 (타이어, 적재물)",
        "공사 구간 (돌발 장애물)"
    ]
```

#### 3.2.2 데이터 품질 검증

자동화된 검증 파이프라인으로 데이터 품질을 보장합니다.

```python
class DataQualityValidator:
    """학습 데이터 품질 자동 검증 시스템"""

    def validate_dataset(self, dataset: AEBDataset) -> ValidationReport:
        """데이터셋 종합 검증

        Returns:
            ValidationReport: 검증 결과 보고서

        Raises:
            AssertionError: 검증 실패 시
        """

        report = ValidationReport()

        # ✅ 1. 레이블 정확도 검증
        label_accuracy = self._verify_labels(dataset)
        report.add("label_accuracy", label_accuracy)
        assert label_accuracy > 0.95, f"레이블 정확도 부족: {label_accuracy:.2%}"

        # ✅ 2. 센서 데이터 무결성
        sensor_integrity = self._check_sensor_data(dataset)
        report.add("sensor_integrity", sensor_integrity)
        assert sensor_integrity > 0.99, f"센서 데이터 손상: {sensor_integrity:.2%}"

        # ✅ 3. 편향 분석
        bias_report = self._analyze_bias(dataset)
        report.add("bias_analysis", bias_report)
        self._check_bias_thresholds(bias_report)

        # ✅ 4. 다양성 검증
        diversity_score = self._check_diversity(dataset)
        report.add("diversity_score", diversity_score)
        assert diversity_score > 0.8, f"데이터 다양성 부족: {diversity_score:.2f}"

        # ✅ 5. 극한 상황 커버리지
        edge_coverage = self._check_edge_case_coverage(dataset)
        report.add("edge_coverage", edge_coverage)
        assert edge_coverage > 0.9, f"극한 상황 커버리지 부족: {edge_coverage:.2%}"

        return report

    def _check_demographic_bias(self, dataset: AEBDataset) -> Dict:
        """인구통계학적 편향 검사

        보행자 감지에서 인종/성별/연령에 따른 편향이 없는지 검증합니다.
        """

        detection_rates = {
            "skin_tone": {},   # 피부색별 감지율
            "gender": {},      # 성별별 감지율
            "age_group": {}    # 연령대별 감지율
        }

        # ... (이전 코드 동일)

        # 📊 편향 분석 결과
        bias_analysis = {}
        for category, groups in detection_rates.items():
            rates = {
                group: data["detected"] / data["total"]
                for group, data in groups.items()
            }

            max_rate = max(rates.values())
            min_rate = min(rates.values())

            bias_analysis[category] = {
                "rates": rates,
                "max_difference": max_rate - min_rate,
                "is_biased": (max_rate - min_rate) > 0.05  # 5% 차이 = 편향
            }

        return bias_analysis
```

**편향 분석 결과 예시**

```yaml
demographic_bias_report:
  skin_tone:
    light: 0.94  # 94% 감지율
    medium: 0.92 # 92% 감지율
    dark: 0.88   # 88% 감지율 ⚠️
    max_difference: 0.06
    is_biased: true  # 6% 차이는 편향으로 판단

  gender:
    male: 0.91
    female: 0.90
    max_difference: 0.01
    is_biased: false  # 1% 차이는 허용 범위

  age_group:
    child: 0.85   # ⚠️ 아동 감지율 낮음
    adult: 0.93
    elderly: 0.89
    max_difference: 0.08
    is_biased: true
```

### 3.3 편향 완화 전략

발견된 편향을 데이터 증강으로 해결합니다.

```python
class BiasMitigation:
    """데이터 편향 완화 시스템"""

    def mitigate_bias(self, dataset: AEBDataset, bias_report: BiasReport):
        """편향된 데이터 교정

        Args:
            dataset: 원본 데이터셋
            bias_report: 편향 분석 결과

        Returns:
            AEBDataset: 균형 잡힌 데이터셋
        """

        balanced_dataset = dataset.copy()

        for bias_type, bias_info in bias_report.biases.items():

            if bias_type.startswith("object_"):
                # 과소 표현된 객체 증강
                obj_type = bias_type.split("_")[1]
                self._augment_underrepresented_object(
                    balanced_dataset,
                    obj_type,
                    target_ratio=bias_info["expected"]
                )

            elif bias_type == "demographic":
                # 인구통계학적 편향 완화
                self._balance_demographic_representation(
                    balanced_dataset,
                    bias_info
                )

            elif bias_type == "night_driving":
                # 야간 주행 데이터 증강
                self._synthesize_night_driving_data(
                    balanced_dataset,
                    target_ratio=0.3
                )

        # 재검증
        new_bias_report = DataQualityValidator().analyze_bias(balanced_dataset)
        assert new_bias_report.total_bias_count < bias_report.total_bias_count

        return balanced_dataset
```

### 3.4 검증 방법

#### 데이터 품질 메트릭

| 메트릭 | 목표값 | 비고 |
|--------|--------|------|
| 레이블 정확도 | > 95% | 인간 검증자 기준 |
| 센서 데이터 무결성 | > 99% | 손상/누락 없음 |
| 다양성 점수 | > 0.8 | Shannon 엔트로피 기반 |
| 편향 지수 | < 0.1 | 모든 카테고리 |
| 극한 상황 커버리지 | > 90% | 10개 시나리오 모두 포함 |

---

## 부록

### A. 용어 정의

| 용어 | 정의 |
|------|------|
| **TTC** | Time To Collision (충돌까지 예상 시간) |
| **ASIL-D** | Automotive Safety Integrity Level D (최고 안전 등급) |
| **HIL** | Hardware-in-the-Loop (하드웨어 루프 시뮬레이션) |
| **V2X** | Vehicle-to-Everything (차량-사물 통신) |
| **LRP** | Layer-wise Relevance Propagation (계층별 관련성 전파) |
| **MTBF** | Mean Time Between Failures (평균 고장 간격) |

### B. 참고 표준

- ISO 26262: 자동차 기능 안전
- ISO/PAS 21448 (SOTIF): 의도된 기능의 안전성
- ISO 21434: 자동차 사이버 보안
- UN R157: 자동 차선 유지 시스템

### C. 변경 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|-----------|--------|
| 1.0 | 2026-01-14 | 초안 작성 (전략 1-5) | AI System |

---

## 전략 4: 수동적 및 능동적 안전장치

### 4.1 다층 안전 메커니즘

> **💡 핵심 원칙:** 능동적 안전장치(제동)가 실패할 경우를 대비한 수동적 안전장치(에어백, 충격 흡수)를 함께 설계하여 다층 방어 체계를 구축합니다.

### 4.2 능동적 안전장치 (Active Safety)

#### 4.2.1 AEB 시스템 계층

```python
class ActiveSafetySystem:
    """능동적 안전 시스템 - 충돌 회피를 위한 계층적 대응"""

    def __init__(self):
        self.warning_system = DriverWarningSystem()
        self.brake_assist = BrakeAssistSystem()
        self.emergency_brake = EmergencyBrakeSystem()
        self.evasive_steering = EvasiveSteeringSystem()  # 선택적

    def activate_safety_response(self, risk_assessment: RiskAssessment):
        """위험도에 따른 계층적 안전 대응

        Args:
            risk_assessment: 위험 평가 결과
        """

        ttc = risk_assessment.time_to_collision
        collision_prob = risk_assessment.collision_probability

        # 📊 계층 1: 조기 경고 (TTC > 3.0s)
        if 5.0 > ttc > 3.0:
            self.warning_system.activate(
                level=WarningLevel.EARLY,
                message="전방 주의",
                visual=True,
                audio=True
            )

        # 📊 계층 2: 제동 준비 (TTC 2.0-3.0s)
        elif 3.0 >= ttc > 2.0:
            self.brake_assist.prepare_braking()
            self.warning_system.activate(
                level=WarningLevel.MEDIUM,
                message="제동 준비",
                haptic=True  # 진동 경고
            )

        # 📊 계층 3: 부분 제동 (TTC 1.5-2.0s)
        elif 2.0 >= ttc > 1.5:
            self.brake_assist.apply_partial_braking(force=0.3)
            self.warning_system.activate(
                level=WarningLevel.HIGH,
                message="충돌 위험! 제동 중"
            )

        # 📊 계층 4: 긴급 제동 (TTC < 1.5s)
        elif ttc <= 1.5 and collision_prob > 0.8:
            self.emergency_brake.apply_full_braking()
            self.warning_system.activate(
                level=WarningLevel.CRITICAL,
                message="긴급 제동!"
            )

            # 회피 조향 검토 (고급 기능)
            if self.evasive_steering.is_available():
                alternative_path = self.evasive_steering.find_safe_path()
                if alternative_path.is_safer_than_braking():
                    self.evasive_steering.execute(alternative_path)
```

**계층적 대응 전략**

| 계층 | TTC 범위 | 충돌 확률 | 대응 | 목적 |
|------|---------|----------|------|------|
| 1️⃣ 조기 경고 | 3.0s - 5.0s | 20-40% | 시각/청각 경고 | 운전자 주의 환기 |
| 2️⃣ 제동 준비 | 2.0s - 3.0s | 40-60% | 제동 시스템 가압 | 반응 시간 단축 |
| 3️⃣ 부분 제동 | 1.5s - 2.0s | 60-80% | 30% 제동력 | 운전자 개입 유도 |
| 4️⃣ 긴급 제동 | < 1.5s | > 80% | 100% 제동력 | 충돌 회피/경감 |

### 4.3 수동적 안전장치 (Passive Safety)

능동적 안전장치가 충돌을 막지 못한 경우를 대비한 2차 방어선입니다.

#### 4.3.1 충돌 전 대비 (Pre-Crash Preparation)

```python
class PreCrashSystem:
    """충돌 불가피 시 피해 최소화 시스템"""

    def prepare_for_impact(self, ttc: float):
        """충돌 직전 수동적 안전장치 활성화

        Args:
            ttc: Time to collision (초)
        """

        if ttc < 0.5:  # 충돌 0.5초 전
            # 🔒 1. 안전벨트 텐셔너 작동
            self.seatbelt.pre_tension(force=200)  # Newton
            self.log("안전벨트 긴장 완료")

            # 🪟 2. 창문 자동 닫기 (에어백 효율 증대)
            self.windows.close_all(speed="fast")
            self.log("창문 폐쇄 완료")

            # 💺 3. 좌석 위치 조정
            self.seat.adjust_for_crash(
                backrest_angle=110,  # 최적 각도
                headrest_height="max"  # 목 부상 방지
            )
            self.log("좌석 조정 완료")

            # 🎚️ 4. 브레이크 페달 후퇴 (다리 부상 방지)
            self.brake_pedal.retract(distance=50)  # mm
            self.log("페달 후퇴 완료")

            # ⚡ 5. 배터리 차단 (화재 방지)
            if ttc < 0.2:
                self.battery.isolate_high_voltage()
                self.log("고전압 배터리 격리 완료")
```

#### 4.3.2 충돌 시 보호 (During Crash)

**에어백 전개 전략**

| 충돌 유형 | 전개 에어백 | 전개 시점 | 목적 |
|----------|-------------|----------|------|
| 정면 충돌 | 전면 에어백 × 2 | 충돌 후 15ms | 머리/가슴 보호 |
| 측면 충돌 | 측면 에어백 × 2 | 충돌 후 10ms | 흉부/골반 보호 |
| 롤오버 | 커튼 에어백 (전열) | 전복 감지 시 | 머리 보호, 차량 내 유지 |
| 보행자 충돌 | 후드 에어백 | 충돌 후 20ms | 보행자 머리 보호 |

### 4.4 통합 안전 관리

```python
class IntegratedSafetyManager:
    """능동+수동 안전장치 통합 관리자"""

    def __init__(self):
        self.active_safety = ActiveSafetySystem()
        self.passive_safety = PreCrashSystem()
        self.collision_predictor = CollisionPredictor()

    async def monitor_and_respond(self):
        """실시간 위험 모니터링 및 대응"""

        while True:
            # 위험 평가
            risk = await self.collision_predictor.assess_risk()

            # 능동적 대응
            self.active_safety.activate_safety_response(risk)

            # 충돌 불가피 판단
            if risk.collision_inevitable:
                self.passive_safety.prepare_for_impact(risk.ttc)

                # 사고 기록 시작
                self.blackbox.start_high_resolution_recording()

                # 긴급 구조 서비스에 자동 알림
                if risk.ttc < 0.3:
                    await self.emergency_call_system.send_ecall({
                        "location": self.gps.get_location(),
                        "severity": risk.severity,
                        "occupants": self.sensor.detect_occupants()
                    })

            await asyncio.sleep(0.01)  # 100Hz 실행
```

### 4.5 검증 방법

#### 충돌 테스트 프로토콜

| 테스트 | 방법 | 합격 기준 |
|--------|------|-----------|
| Euro NCAP 정면 충돌 | 64 km/h, 40% 오프셋 | ⭐⭐⭐⭐⭐ (5성급) |
| 측면 충돌 | 60 km/h, 측면 장벽 | 흉부 손상 < HIC 700 |
| 보행자 보호 | 40 km/h, 보행자 더미 | 머리 손상 < HIC 1000 |
| AEB 성능 | CCRs, CCRm, CPLA | 충돌 회피율 > 90% |

---

## 전략 5: 제어 가능성 & 인간 중심 설계

### 5.1 설계 철학

> **💡 핵심 원칙:** 시스템이 항상 인간의 통제 하에 있어야 하며, 인간이 시스템의 동작을 이해하고 필요 시 개입할 수 있어야 합니다.

### 5.2 Human-in-the-Loop (HITL)

#### 5.2.1 운전자 개입 메커니즘

```python
class DriverOverrideSystem:
    """운전자 우선 제어 시스템"""

    def __init__(self):
        self.aeb_active = False
        self.driver_input_monitor = DriverInputMonitor()

    def check_driver_override(self) -> bool:
        """운전자의 명시적 개입 감지

        Returns:
            bool: True if driver is overriding
        """

        # 1️⃣ 가속 페달 우선 (Throttle Override)
        if self.driver_input_monitor.throttle_position > 0.2:
            if self.aeb_active:
                self.log_override("accelerator_pressed")
                self.disable_aeb(reason="driver_acceleration")
                return True

        # 2️⃣ 조향 개입 (Steering Override)
        steering_torque = self.driver_input_monitor.steering_torque
        if abs(steering_torque) > 5.0:  # Nm
            if self.aeb_active:
                self.log_override("steering_intervention")
                # 제동은 유지하되, 조향 허용
                self.allow_steering_during_braking()
                return True

        # 3️⃣ 시스템 비활성화 버튼
        if self.driver_input_monitor.aeb_disable_button_pressed:
            self.disable_aeb(reason="manual_disable", duration=10)  # 10초간
            self.show_warning("AEB 일시 비활성화 (10초)")
            return True

        return False

    def disable_aeb(self, reason: str, duration: Optional[float] = None):
        """AEB 시스템 비활성화

        Args:
            reason: 비활성화 이유
            duration: 비활성화 지속 시간 (None = 수동 재활성화까지)
        """

        self.aeb_active = False
        self.log_event({
            "event": "AEB_DISABLED",
            "reason": reason,
            "timestamp": datetime.now(),
            "duration": duration
        })

        # 운전자에게 알림
        self.display.show_message(
            "⚠️ AEB 비활성화됨",
            color="orange",
            duration=5
        )

        # 자동 재활성화 예약
        if duration:
            self.schedule_reactivation(after=duration)
```

**운전자 개입 우선순위**

| 입력 | 우선순위 | AEB 반응 | 비고 |
|------|---------|---------|------|
| 🚗 가속 페달 | 1위 | 즉시 해제 | 운전자 의도 최우선 |
| 🎛️ 조향 휠 | 2위 | 제동 유지, 조향 허용 | 회피 조향 가능 |
| ⏸️ 비활성화 버튼 | 3위 | 10초간 해제 | 임시 비활성화 |
| ⚙️ 메뉴 설정 | 4위 | 영구 해제 | 주의 메시지 표시 |

### 5.3 Human-on-the-Loop (HOTL)

운전자가 시스템을 감독하되 즉각적 제어는 하지 않는 모드입니다.

#### 5.3.1 적응형 제어 권한

```python
class AdaptiveAuthorityManager:
    """상황에 따른 제어 권한 동적 조정"""

    def determine_authority_level(self, context: DrivingContext) -> AuthorityLevel:
        """운전자와 시스템 간 제어 권한 결정

        Args:
            context: 현재 주행 상황

        Returns:
            AuthorityLevel: DRIVER_FULL / SHARED / SYSTEM_FULL
        """

        # 🟢 운전자 완전 제어 (정상 주행)
        if (context.driver_attentiveness > 0.8 and
            context.risk_level == RiskLevel.LOW):
            return AuthorityLevel.DRIVER_FULL

        # 🟡 공유 제어 (주의 필요)
        elif (context.driver_attentiveness > 0.5 and
              context.risk_level == RiskLevel.MEDIUM):
            return AuthorityLevel.SHARED

        # 🔴 시스템 완전 제어 (위급 상황)
        elif (context.driver_attentiveness < 0.3 or
              context.risk_level == RiskLevel.CRITICAL or
              context.ttc < 1.0):
            return AuthorityLevel.SYSTEM_FULL

        # 기본값
        return AuthorityLevel.SHARED
```

**제어 권한 전환 테이블**

| 운전자 주의도 | 위험 수준 | TTC | 제어 모드 | 설명 |
|--------------|----------|-----|----------|------|
| 높음 (>0.8) | 낮음 | >5s | 🟢 운전자 | 정상 주행 |
| 중간 (0.5-0.8) | 중간 | 3-5s | 🟡 공유 | 경고 + 준비 |
| 낮음 (<0.5) | 높음 | <3s | 🟠 시스템 우선 | 개입 준비 |
| 매우 낮음 (<0.3) | 긴급 | <1.5s | 🔴 시스템 완전 | 긴급 제동 |

### 5.4 투명한 시스템 상태 표시

#### 5.4.1 실시간 HMI (Human-Machine Interface)

```python
class AEBHumanInterface:
    """운전자 친화적 인터페이스"""

    def __init__(self):
        self.hud = HeadUpDisplay()
        self.cluster = InstrumentCluster()
        self.haptic = HapticFeedback()

    def display_system_status(self, aeb_state: AEBState):
        """시스템 상태를 명확하게 표시

        Args:
            aeb_state: 현재 AEB 시스템 상태
        """

        # 🖥️ HUD 표시
        if aeb_state.active:
            self.hud.show_icon(
                icon="shield_check",
                color="green",
                text="AEB 활성"
            )

            # 전방 물체 감지 시 거리 표시
            if aeb_state.detected_objects:
                closest = min(aeb_state.detected_objects, key=lambda o: o.distance)
                self.hud.show_distance_warning(
                    distance=closest.distance,
                    ttc=closest.ttc,
                    urgency=self._calculate_urgency(closest.ttc)
                )

        # 📊 계기판 표시
        self.cluster.update_aeb_status(
            status=aeb_state.status,
            confidence=aeb_state.confidence,
            sensor_health=aeb_state.sensor_status
        )

        # 🔊 음향 경고
        if aeb_state.risk_level >= RiskLevel.HIGH:
            self.play_warning_sound(
                urgency=aeb_state.risk_level,
                pattern="increasing_frequency"
            )

        # 📳 햅틱 경고
        if aeb_state.risk_level >= RiskLevel.MEDIUM:
            self.haptic.vibrate_steering_wheel(
                intensity=self._map_risk_to_intensity(aeb_state.risk_level),
                pattern="pulsing"
            )
```

**다중 모달 경고 전략**

| 위험도 | 시각 | 청각 | 촉각 | 목적 |
|--------|------|------|------|------|
| 낮음 | 🟢 아이콘 | 없음 | 없음 | 상태 표시 |
| 중간 | 🟡 깜빡임 | 단일 경고음 | 진동 1회 | 주의 환기 |
| 높음 | 🟠 점멸 + 거리 | 연속 경고음 | 연속 진동 | 즉시 대응 요구 |
| 긴급 | 🔴 전체 화면 | 긴급 알람 | 강한 진동 | 긴급 상황 알림 |

### 5.5 사용자 교육 및 온보딩

#### 5.5.1 초기 설정 가이드

```python
class AEBOnboarding:
    """신규 사용자 온보딩 시스템"""

    def start_onboarding(self):
        """AEB 시스템 사용법 튜토리얼"""

        steps = [
            {
                "title": "AEB 시스템 소개",
                "content": "자동 긴급 제동 시스템은 충돌 위험 시 자동으로 브레이크를 작동합니다.",
                "demo": self._show_intro_video
            },
            {
                "title": "센서 위치 확인",
                "content": "전방 카메라, 레이더, 라이다의 위치와 시야 범위를 확인하세요.",
                "demo": self._show_sensor_locations
            },
            {
                "title": "경고 신호 이해하기",
                "content": "시스템이 위험을 감지하면 경고음, 진동, 화면 표시로 알려줍니다.",
                "demo": self._demonstrate_warnings
            },
            {
                "title": "운전자 개입 방법",
                "content": "가속 페달을 밟거나 비활성화 버튼을 누르면 시스템을 해제할 수 있습니다.",
                "demo": self._practice_override
            },
            {
                "title": "실전 연습",
                "content": "안전한 환경에서 AEB 작동을 체험해보세요.",
                "demo": self._guided_practice_mode
            }
        ]

        for step in steps:
            self.display_step(step)
            step["demo"]()
            self.wait_for_user_confirmation()
```

### 5.6 검증 방법

#### ISO 26262 제어가능성 평가

| 평가 항목 | 목표 | 측정 방법 |
|----------|------|-----------|
| 운전자 개입 시간 | < 0.5s | 실제 측정 |
| 시스템 이해도 | > 80% | 사용자 설문 (5점 척도) |
| Override 성공률 | 100% | 100회 테스트 |
| False Alarm 허용도 | > 70% | 사용자 수용도 조사 |

---

## 전략 6: Fallback (폴백) 및 비상 정지

### 6.1 설계 철학

> **💡 핵심 원칙:** 모든 시스템 구성 요소는 실패할 수 있다고 가정하고, 각 실패 모드에 대한 대안을 사전에 설계합니다.

### 6.2 다층 폴백 전략

#### 6.2.1 센서 폴백 체인

```python
class SensorFallbackChain:
    """센서 고장 시 폴백 체인"""

    def __init__(self):
        self.primary_sensors = [Camera(), Radar(), LiDAR()]
        self.backup_sensors = [UltrasonicArray(), V2XReceiver()]
        self.sensor_health_monitor = SensorHealthMonitor()

    def get_reliable_sensor_data(self) -> SensorData:
        """신뢰할 수 있는 센서 데이터 획득

        Returns:
            SensorData: 폴백을 거친 신뢰 가능한 데이터
        """

        # 1단계: 주 센서 퓨전 (정상 동작)
        if self._all_primary_sensors_healthy():
            return self._fuse_primary_sensors()

        # 2단계: 부분 센서 퓨전 (일부 고장)
        healthy_sensors = self.sensor_health_monitor.get_healthy_sensors()
        if len(healthy_sensors) >= 2:
            return self._fuse_available_sensors(healthy_sensors)

        # 3단계: 단일 센서 모드 (1개만 정상)
        if len(healthy_sensors) == 1:
            return self._single_sensor_mode(healthy_sensors[0])

        # 4단계: 백업 센서 활용
        if self._backup_sensors_available():
            return self._use_backup_sensors()

        # 5단계: 최소 기능 모드 (Safe Stop 준비)
        return self._minimal_functionality_mode()

    def _minimal_functionality_mode(self) -> SensorData:
        """최소 기능 모드 - 안전 정지 준비

        센서가 거의 작동하지 않을 때 차량 속도와 관성만으로
        안전하게 정지할 수 있도록 합니다.
        """

        # 차량 자체 센서(속도, 가속도)만 사용
        current_speed = self.vehicle.get_speed()
        current_accel = self.vehicle.get_acceleration()

        # 안전 정지 프로토콜 시작
        self.initiate_minimal_risk_condition()

        return SensorData(
            mode=OperatingMode.MINIMAL,
            reliability=0.3,
            data={"speed": current_speed, "accel": current_accel},
            recommendation="SAFE_STOP_IMMEDIATELY"
        )
```

**센서 폴백 계층 구조**

```
┌─────────────────────────────────────┐
│  Tier 1: 전체 센서 퓨전             │  ← 정상 동작 (신뢰도 95%)
│  (Camera + Radar + LiDAR)           │
└───────────────┬─────────────────────┘
                │ 센서 고장
                ▼
┌─────────────────────────────────────┐
│  Tier 2: 부분 센서 퓨전             │  ← 성능 저하 (신뢰도 80%)
│  (2개 이상 센서)                    │
└───────────────┬─────────────────────┘
                │ 추가 고장
                ▼
┌─────────────────────────────────────┐
│  Tier 3: 단일 센서                  │  ← 제한 모드 (신뢰도 60%)
│  (1개 센서 + 보수적 판단)           │
└───────────────┬─────────────────────┘
                │ 최종 고장
                ▼
┌─────────────────────────────────────┐
│  Tier 4: 최소 기능 모드             │  ← 안전 정지 (신뢰도 30%)
│  (차량 내부 센서만)                 │
└───────────────┬─────────────────────┘
                │ 즉시 실행
                ▼
┌─────────────────────────────────────┐
│  Emergency: Minimal Risk Condition  │  ← 비상 정지
│  (갓길 정차 or 서서히 정지)         │
└─────────────────────────────────────┘
```

#### 6.2.2 AI 모델 폴백

```python
class AIModelFallback:
    """AI 모델 고장 시 폴백 메커니즘"""

    def __init__(self):
        self.primary_model = NeuralNetworkModel(version="v3.2")
        self.backup_model = NeuralNetworkModel(version="v3.1_stable")
        self.rule_based_fallback = RuleBasedDetector()
        self.model_monitor = ModelHealthMonitor()

    def detect_objects(self, sensor_data: SensorData) -> DetectionResult:
        """객체 감지 (폴백 지원)

        Returns:
            DetectionResult: 감지 결과
        """

        try:
            # 주 모델 실행
            result = self.primary_model.detect(sensor_data)

            # 품질 검증
            if self._is_result_trustworthy(result):
                return result
            else:
                raise ModelOutputException("Low confidence detection")

        except ModelOutputException:
            # 백업 모델로 전환
            self.log_fallback("Switching to backup model")
            result = self.backup_model.detect(sensor_data)

            if self._is_result_trustworthy(result):
                return result
            else:
                # 규칙 기반 시스템으로 최종 폴백
                return self._rule_based_detection(sensor_data)

    def _rule_based_detection(self, sensor_data: SensorData) -> DetectionResult:
        """규칙 기반 감지 (최종 폴백)

        신경망이 신뢰할 수 없을 때 사용하는 간단하지만 안전한 규칙
        """

        detections = []

        # 규칙 1: 레이더 기반 거리 감지
        if sensor_data.radar.distance < 50:  # m
            detections.append(Detection(
                type=ObjectType.UNKNOWN,  # 분류 불가
                distance=sensor_data.radar.distance,
                confidence=0.7,
                source="radar_rule"
            ))

        # 규칙 2: 라이다 포인트 클라우드 밀도
        point_density = sensor_data.lidar.calculate_density()
        if point_density > 100:  # points/m²
            detections.append(Detection(
                type=ObjectType.OBSTACLE,
                distance=sensor_data.lidar.closest_point_distance,
                confidence=0.6,
                source="lidar_rule"
            ))

        # 규칙 3: 카메라 모션 감지
        if sensor_data.camera.motion_detected:
            detections.append(Detection(
                type=ObjectType.MOVING_OBJECT,
                distance=sensor_data.camera.estimate_distance(),
                confidence=0.5,
                source="camera_motion"
            ))

        # 보수적 접근: 의심스러우면 감지로 판단
        return DetectionResult(
            detections=detections,
            fallback_mode=True,
            reliability=0.5
        )
```

### 6.3 Minimal Risk Condition (MRC)

모든 폴백이 실패했을 때의 최종 안전 동작입니다.

#### 6.3.1 안전 정지 프로토콜

```python
class MinimalRiskCondition:
    """최소 위험 조건 - 안전한 정지 절차"""

    def __init__(self):
        self.vehicle_controller = VehicleController()
        self.environment_monitor = EnvironmentMonitor()
        self.emergency_flasher = EmergencyFlasher()

    def initiate_safe_stop(self, reason: str):
        """안전 정지 시작

        Args:
            reason: 정지 이유 (로깅용)
        """

        self.log_critical_event(f"Initiating MRC: {reason}")

        # 1️⃣ 운전자 경고
        self.alert_driver(
            message="⚠️ 시스템 고장 - 안전 정지 중",
            urgency=AlertLevel.CRITICAL,
            audio=True,
            visual=True,
            haptic=True
        )

        # 2️⃣ 환경 평가
        safe_stop_location = self._find_safe_stop_location()

        # 3️⃣ 비상등 작동
        self.emergency_flasher.activate()

        # 4️⃣ 주변 차량 경고
        if self.v2x.is_available():
            self.v2x.broadcast_emergency_message({
                "type": "STOPPING",
                "reason": "SYSTEM_FAILURE",
                "location": self.gps.get_location()
            })

        # 5️⃣ 점진적 감속 시작
        if safe_stop_location.type == "SHOULDER":
            # 갓길로 이동 가능
            self._move_to_shoulder_and_stop(safe_stop_location)
        else:
            # 현재 차선에서 정지
            self._stop_in_lane()

        # 6️⃣ 정지 후 조치
        self._post_stop_actions()

    def _stop_in_lane(self):
        """현재 차선에서 안전하게 정지"""

        # 부드러운 감속 (2.5 m/s² - 승객 안전)
        target_decel = 2.5

        current_speed = self.vehicle_controller.get_speed()
        stop_distance = (current_speed ** 2) / (2 * target_decel)

        self.log(f"Stopping in {stop_distance:.1f}m")

        # 점진적 제동
        self.vehicle_controller.apply_gradual_braking(
            target_deceleration=target_decel,
            until=lambda: self.vehicle_controller.get_speed() == 0
        )

    def _post_stop_actions(self):
        """정지 후 후속 조치"""

        # 1. 주차 브레이크 작동
        self.vehicle_controller.apply_parking_brake()

        # 2. 변속기를 P(주차) 위치로
        self.vehicle_controller.shift_to_park()

        # 3. 비상등 계속 작동
        self.emergency_flasher.keep_active()

        # 4. 자동 긴급 호출
        self.ecall_system.send_emergency_call({
            "type": "SYSTEM_FAILURE",
            "vehicle_stopped": True,
            "location": self.gps.get_location(),
            "occupants": self.sensor.count_occupants()
        })

        # 5. 블랙박스 보존
        self.blackbox.lock_last_n_minutes(minutes=10)

        # 6. 운전자에게 지시
        self.display.show_message(
            "🚨 차량이 안전하게 정지했습니다.\n"
            "1. 비상등이 작동 중입니다.\n"
            "2. 구조 서비스에 자동으로 연락했습니다.\n"
            "3. 차량을 떠나지 마세요.\n"
            "4. 필요시 112에 연락하세요.",
            duration=None  # 무한 표시
        )
```

**안전 정지 시나리오 결정 트리**

```
고장 감지
    │
    ├─ 고속도로 주행 중?
    │   ├─ Yes → 갓길 찾기
    │   │         ├─ 갓길 있음 → 이동 후 정지
    │   │         └─ 갓길 없음 → 비상차로 정지
    │   │
    │   └─ No → 일반 도로
    │             ├─ 교통량 많음 → 좌측/우측 공간 확보
    │             └─ 교통량 적음 → 현재 차선 정지
    │
    └─ 정지 후
        ├─ 비상등 작동
        ├─ 자동 긴급 호출
        └─ 운전자 안내
```

### 6.4 검증 방법

#### 폴백 테스트 시나리오

| 시나리오 | 테스트 방법 | 합격 기준 |
|---------|-----------|-----------|
| 카메라 단독 고장 | SW 주입으로 카메라 비활성화 | 다른 센서로 정상 작동 |
| 2개 센서 동시 고장 | 레이더+라이다 비활성화 | 제한 모드 진입, 경고 표시 |
| 모든 센서 고장 | 전체 센서 차단 | MRC 즉시 실행, 안전 정지 |
| AI 모델 크래시 | Exception 주입 | 백업 모델로 전환, < 100ms |
| 완전 시스템 실패 | 전원 차단 시뮬레이션 | 기계적 브레이크 작동 유지 |

---

## 전략 7: 검증 가능한 행동 정책 (Verifiable Policies)

### 7.1 설계 철학

> **💡 핵심 원칙:** 시스템의 모든 행동은 사전에 정의된 정책을 따르며, 이 정책은 수학적으로 검증 가능해야 합니다.

### 7.2 형식적 정책 정의

#### 7.2.1 제동 결정 정책

```python
from dataclasses import dataclass
from typing import Protocol
import z3  # SMT solver for formal verification

@dataclass
class BrakingPolicy:
    """수학적으로 검증 가능한 제동 정책"""

    # 물리 상수
    MAX_DECELERATION = 9.8  # m/s² (중력 가속도)
    REACTION_TIME = 0.2  # s (시스템 반응 시간)
    SAFETY_MARGIN = 1.5  # 배수 (안전 계수)

    def should_brake(self, state: VehicleState, obstacle: Obstacle) -> bool:
        """제동 결정 정책 (검증 가능)

        이 함수는 형식적 검증을 통해 안전성이 보장됩니다.

        Args:
            state: 차량 상태
            obstacle: 장애물 정보

        Returns:
            bool: True if braking required
        """

        # 1. 충돌 시간 계산
        ttc = self._calculate_ttc(state, obstacle)

        # 2. 최소 제동 거리 계산
        min_brake_distance = self._calculate_min_brake_distance(state.velocity)

        # 3. 안전 거리 계산 (안전 계수 적용)
        safe_distance = min_brake_distance * self.SAFETY_MARGIN

        # 4. 제동 결정 규칙
        decision = (
            obstacle.distance < safe_distance or
            ttc < self.REACTION_TIME + (state.velocity / self.MAX_DECELERATION)
        )

        # 5. 결정 근거 기록
        self._log_decision(
            decision=decision,
            ttc=ttc,
            obstacle_distance=obstacle.distance,
            safe_distance=safe_distance,
            reasoning=f"TTC={ttc:.2f}s, SafeDist={safe_distance:.1f}m"
        )

        return decision

    def _calculate_min_brake_distance(self, velocity: float) -> float:
        """최소 제동 거리 (물리 법칙)

        d = v² / (2 * a) + v * t_react

        Args:
            velocity: 속도 (m/s)

        Returns:
            float: 최소 제동 거리 (m)
        """
        braking_distance = (velocity ** 2) / (2 * self.MAX_DECELERATION)
        reaction_distance = velocity * self.REACTION_TIME
        return braking_distance + reaction_distance
```

#### 7.2.2 형식적 검증 (Formal Verification)

```python
class PolicyVerifier:
    """정책의 안전성을 수학적으로 검증"""

    def verify_braking_policy_safety(self):
        """제동 정책이 항상 안전함을 증명

        Z3 SMT solver를 사용하여 모든 가능한 입력에 대해
        정책이 안전 조건을 만족함을 증명합니다.
        """

        # Z3 변수 선언
        velocity = z3.Real('velocity')
        obstacle_distance = z3.Real('obstacle_distance')
        ttc = z3.Real('ttc')

        # 제약 조건
        constraints = [
            velocity >= 0,
            velocity <= 55.56,  # 200 km/h = 55.56 m/s
            obstacle_distance >= 0,
            ttc >= 0
        ]

        # 안전 조건: 제동하면 충돌 전에 정지 가능
        policy = BrakingPolicy()
        min_brake_dist = (velocity ** 2) / (2 * policy.MAX_DECELERATION)
        safe_dist = min_brake_dist * policy.SAFETY_MARGIN

        safety_condition = z3.Implies(
            obstacle_distance < safe_dist,  # 정책: 안전 거리보다 가까우면 제동
            min_brake_dist < obstacle_distance  # 결과: 제동으로 정지 가능
        )

        # SMT Solver로 검증
        solver = z3.Solver()
        solver.add(constraints)
        solver.add(z3.Not(safety_condition))  # 반례 찾기

        result = solver.check()

        if result == z3.unsat:
            print("✅ 정책 안전성 검증 성공: 모든 경우에 안전합니다.")
            return True
        else:
            print("❌ 정책 안전성 검증 실패: 반례를 발견했습니다.")
            print("반례:", solver.model())
            return False
```

### 7.3 행동 제약 조건

#### 7.3.1 허용 가능한 행동 공간

```python
class ActionConstraints:
    """시스템이 취할 수 있는 행동의 경계"""

    # 물리적 제약
    MAX_LATERAL_ACCEL = 8.0  # m/s² (타이어 한계)
    MAX_LONGITUDINAL_ACCEL = 9.8  # m/s² (마찰 한계)
    MAX_JERK = 10.0  # m/s³ (승객 편의)

    # 규제적 제약
    MUST_OBEY_TRAFFIC_LAWS = True
    MAX_SPEED_LIMIT_VIOLATION = 0  # km/h (위반 불가)

    # 윤리적 제약
    PROTECT_HUMAN_LIFE = Priority.HIGHEST
    MINIMIZE_HARM = True

    def is_action_allowed(self, action: Action) -> tuple[bool, str]:
        """행동이 정책상 허용되는지 검사

        Args:
            action: 제안된 행동

        Returns:
            tuple: (허용 여부, 거부 이유)
        """

        # 물리적 제약 검사
        if abs(action.lateral_accel) > self.MAX_LATERAL_ACCEL:
            return False, f"Lateral acceleration {action.lateral_accel:.1f} exceeds limit"

        if abs(action.longitudinal_accel) > self.MAX_LONGITUDINAL_ACCEL:
            return False, f"Longitudinal acceleration {action.longitudinal_accel:.1f} exceeds limit"

        # 충돌 회피 우선순위
        if action.type == ActionType.EVASIVE_MANEUVER:
            if self._will_cause_secondary_collision(action):
                return False, "Evasive action would cause secondary collision"

        # 승객 안전
        if action.expected_injury_risk > 0.1:  # 10% 부상 위험
            if not self._is_emergency_situation():
                return False, "Action poses unacceptable injury risk"

        # 모든 제약 통과
        return True, "Action allowed"
```

### 7.4 정책 감사 추적 (Audit Trail)

모든 결정에 대한 완전한 추적 기록을 유지합니다.

```python
class PolicyAuditLogger:
    """정책 준수 여부 감사 로거"""

    def log_policy_decision(self, decision: Decision):
        """정책 결정 기록

        Args:
            decision: 시스템이 내린 결정
        """

        audit_record = {
            "timestamp": datetime.now().isoformat(),
            "decision_id": decision.id,

            # 입력 상태
            "input_state": {
                "velocity": decision.vehicle_state.velocity,
                "obstacle_distance": decision.obstacle.distance,
                "ttc": decision.ttc
            },

            # 적용된 정책
            "policy_applied": {
                "name": decision.policy.name,
                "version": decision.policy.version,
                "rule_triggered": decision.rule_id
            },

            # 결정 내용
            "decision": {
                "action": decision.action.type,
                "braking_force": decision.action.braking_force,
                "reasoning": decision.reasoning
            },

            # 제약 검사 결과
            "constraints_checked": decision.constraints_report,

            # 검증 가능성
            "reproducible": True,
            "verification_hash": decision.compute_hash()
        }

        self.audit_log.append(audit_record)

        # 주기적으로 디스크에 영구 저장
        if len(self.audit_log) >= 100:
            self.flush_to_disk()
```

### 7.5 검증 방법

#### 정책 검증 테스트

| 검증 항목 | 방법 | 합격 기준 |
|----------|------|-----------|
| 수학적 정합성 | SMT Solver (Z3) | 반례 없음 |
| 재현 가능성 | 동일 입력 1000회 재실행 | 100% 동일 결과 |
| 정책 준수율 | 10만 건 실제 주행 분석 | > 99.9% 준수 |
| 제약 위반율 | 자동 검사 | 0% (위반 불허) |

---

## 전략 8: 다중 장벽 설계 (Redundancy & Barriers)

### 8.1 설계 철학

> **💡 핵심 원칙:** "스위스 치즈 모델" - 단일 고장점이 사고로 이어지지 않도록 여러 층의 방어막을 구축합니다.

### 8.2 계층적 방어 구조

```
[위험 요소]
     ↓
┌──────────────────────────────────┐
│ Layer 1: 설계 단계 안전성        │  ← 본질적 안전 설계
│ (Inherent Safety)                │
└───────────┬──────────────────────┘
            ↓ 설계 결함 통과
┌──────────────────────────────────┐
│ Layer 2: 센서 다중화             │  ← 센서 퓨전, 크로스 체크
│ (Sensor Redundancy)              │
└───────────┬──────────────────────┘
            ↓ 센서 오류 통과
┌──────────────────────────────────┐
│ Layer 3: AI 검증 계층            │  ← 이중 AI, 규칙 기반 검증
│ (AI Verification)                │
└───────────┬──────────────────────┘
            ↓ AI 오판 통과
┌──────────────────────────────────┐
│ Layer 4: 운전자 개입             │  ← 경고, Override 가능
│ (Human Oversight)                │
└───────────┬──────────────────────┘
            ↓ 운전자 미반응
┌──────────────────────────────────┐
│ Layer 5: 긴급 제동               │  ← 최후 자동 개입
│ (Emergency Brake)                │
└───────────┬──────────────────────┘
            ↓ 충돌 불가피
┌──────────────────────────────────┐
│ Layer 6: 수동적 안전             │  ← 에어백, 크럼플 존
│ (Passive Safety)                 │
└──────────────────────────────────┘
```

### 8.3 센서 다중화 (Sensor Redundancy)

#### 8.3.1 Triple Modular Redundancy

```python
class TripleModularRedundancy:
    """3중 모듈 중복 - 2 out of 3 투표 방식"""

    def __init__(self):
        # 동일 유형 센서 3개
        self.radar_1 = RadarSensor(id="R1", position="center")
        self.radar_2 = RadarSensor(id="R2", position="left")
        self.radar_3 = RadarSensor(id="R3", position="right")

    def get_reliable_distance(self) -> Optional[float]:
        """3개 센서의 투표로 신뢰 가능한 거리 획득

        Returns:
            float: 신뢰 가능한 거리 또는 None
        """

        # 3개 센서 측정
        measurements = [
            self.radar_1.measure_distance(),
            self.radar_2.measure_distance(),
            self.radar_3.measure_distance()
        ]

        # 측정값이 유효한지 확인
        valid_measurements = [m for m in measurements if m is not None]

        if len(valid_measurements) < 2:
            # 2개 미만은 신뢰 불가
            return None

        # Majority voting: 중앙값 사용
        sorted_values = sorted(valid_measurements)
        median_value = sorted_values[len(sorted_values) // 2]

        # 일치도 검사 (±10% 이내)
        agreement = all(
            abs(m - median_value) / median_value < 0.1
            for m in valid_measurements
        )

        if agreement:
            return median_value
        else:
            # 불일치 시 가장 보수적인 값 (최단 거리) 사용
            return min(valid_measurements)
```

#### 8.3.2 이종 센서 크로스 체크

```python
class HeterogeneousSensorCheck:
    """이종 센서 간 상호 검증"""

    def __init__(self):
        self.camera = CameraSensor()
        self.radar = RadarSensor()
        self.lidar = LiDARSensor()

    def detect_with_cross_validation(self) -> Detection:
        """이종 센서 간 크로스 검증

        Returns:
            Detection: 검증된 감지 결과
        """

        # 각 센서의 독립적 감지
        camera_det = self.camera.detect_objects()
        radar_det = self.radar.detect_objects()
        lidar_det = self.lidar.detect_objects()

        # 교집합 찾기 (모든 센서가 감지한 물체)
        confirmed_objects = self._find_common_detections([
            camera_det, radar_det, lidar_det
        ])

        # 2/3 합의 (2개 센서가 동의)
        probable_objects = self._find_majority_detections([
            camera_det, radar_det, lidar_det
        ], threshold=2)

        # 검증 등급 부여
        for obj in confirmed_objects:
            obj.confidence *= 1.3  # 신뢰도 boost (최대 1.0)
            obj.verification_level = VerificationLevel.HIGH

        for obj in probable_objects:
            obj.verification_level = VerificationLevel.MEDIUM

        # 단일 센서만 감지한 물체는 낮은 신뢰도
        single_sensor_objects = self._find_unique_detections([
            camera_det, radar_det, lidar_det
        ])

        for obj in single_sensor_objects:
            obj.confidence *= 0.5  # 신뢰도 감소
            obj.verification_level = VerificationLevel.LOW

        # 통합 결과
        all_detections = confirmed_objects + probable_objects + single_sensor_objects

        return Detection(
            objects=all_detections,
            cross_validated=True
        )
```

### 8.4 AI 모델 다중화

#### 8.4.1 이중 AI 아키텍처

```python
class DualAIArchitecture:
    """2개의 독립적인 AI 모델로 상호 검증"""

    def __init__(self):
        # 주 AI: 고성능 신경망
        self.primary_ai = DeepNeuralNetwork(
            architecture="ResNet-50",
            training_data="full_dataset"
        )

        # 보조 AI: 경량 신경망 (다른 아키텍처)
        self.secondary_ai = DeepNeuralNetwork(
            architecture="MobileNet-V2",
            training_data="critical_scenarios_only"
        )

        # 규칙 기반 검증기
        self.rule_validator = RuleBasedValidator()

    def detect_with_dual_ai(self, sensor_data: SensorData) -> DetectionResult:
        """이중 AI로 감지 및 검증

        Returns:
            DetectionResult: 검증된 결과
        """

        # 두 AI 독립 실행
        primary_result = self.primary_ai.detect(sensor_data)
        secondary_result = self.secondary_ai.detect(sensor_data)

        # 결과 비교
        agreement_score = self._calculate_agreement(
            primary_result, secondary_result
        )

        if agreement_score > 0.9:
            # 높은 일치도 → 신뢰
            final_result = primary_result
            final_result.confidence *= 1.2  # boost
            final_result.verified = True

        elif agreement_score > 0.7:
            # 중간 일치도 → 보수적 판단
            final_result = self._conservative_merge(
                primary_result, secondary_result
            )
            final_result.verified = True

        else:
            # 낮은 일치도 → 규칙 기반 검증기 사용
            final_result = self.rule_validator.arbitrate(
                primary_result, secondary_result, sensor_data
            )
            final_result.verified = False
            final_result.confidence *= 0.7  # penalty

        return final_result
```

### 8.5 기계적 백업 시스템

전자 시스템이 완전히 실패해도 작동하는 기계적 안전장치입니다.

#### 8.5.1 기계식 브레이크 백업

```python
class MechanicalBrakeBackup:
    """전자 시스템 실패 시 기계식 브레이크 작동"""

    def __init__(self):
        self.electronic_brake = ElectronicBrakeSystem()
        self.hydraulic_backup = HydraulicBrakeSystem()
        self.system_monitor = SystemHealthMonitor()

    def apply_braking(self, force: float):
        """제동 시도 (자동 폴백 포함)

        Args:
            force: 제동력 (0.0 - 1.0)
        """

        try:
            # 주 시스템: 전자식 브레이크
            self.electronic_brake.apply(force)

            # 정상 작동 확인
            if not self._verify_braking_applied():
                raise BrakeSystemFailure("Electronic brake not responding")

        except BrakeSystemFailure:
            # 백업: 유압식 브레이크
            self.log_critical("Electronic brake failed, using hydraulic backup")
            self.hydraulic_backup.apply(force)

            # 백업도 실패?
            if not self._verify_braking_applied():
                # 최후 수단: 기계식 주차 브레이크
                self.apply_emergency_parking_brake()
```

### 8.6 검증 방법

#### 다중 장벽 테스트

| 테스트 시나리오 | 방법 | 합격 기준 |
|---------------|------|-----------|
| 단일 센서 고장 | 각 센서를 순차적으로 비활성화 | 나머지 센서로 정상 작동 |
| 2중 센서 고장 | 2개 센서 동시 비활성화 | 제한 모드로 안전 작동 |
| 주 AI 고장 | Primary AI 크래시 주입 | Secondary AI로 즉시 전환 |
| 전자 시스템 고장 | 전원 차단 시뮬레이션 | 기계식 브레이크 작동 |
| 다중 고장 | 여러 시스템 동시 고장 | MRC 실행, 안전 정지 |

---

## 전략 9: 의도치 않은 작동 방지 (Preventing Unintended Operation)

### 9.1 설계 철학

> **💡 핵심 원칙:** "오작동은 발생할 수 있다"는 가정 하에, 오작동으로 인한 피해를 최소화하고 빠르게 감지하여 복구합니다.

### 9.2 오작동 감지 시스템

#### 9.2.1 이상 행동 감지기

```python
class AnomalousBehaviorDetector:
    """시스템의 비정상 동작 감지"""

    def __init__(self):
        self.behavior_model = NormalBehaviorModel()
        self.anomaly_threshold = 0.95  # 상위 5% = 이상

    def detect_anomaly(self, current_behavior: Behavior) -> AnomalyReport:
        """현재 동작이 정상 범위 내인지 검사

        Args:
            current_behavior: 현재 시스템 동작

        Returns:
            AnomalyReport: 이상 감지 결과
        """

        anomalies = []

        # 1. 빈도 이상 감지
        brake_frequency = current_behavior.braking_events_per_minute
        if brake_frequency > 10:  # 분당 10회 이상 = 비정상
            anomalies.append(Anomaly(
                type="EXCESSIVE_BRAKING_FREQUENCY",
                severity=Severity.HIGH,
                description=f"분당 {brake_frequency}회 제동 (정상: < 3회)"
            ))

        # 2. 패턴 이상 감지
        if self._is_oscillating_behavior(current_behavior):
            anomalies.append(Anomaly(
                type="OSCILLATING_BEHAVIOR",
                severity=Severity.CRITICAL,
                description="제동-해제 반복 패턴 감지 (시스템 오작동 의심)"
            ))

        # 3. 컨텍스트 불일치
        if current_behavior.braking and not current_behavior.obstacle_detected:
            anomalies.append(Anomaly(
                type="BRAKING_WITHOUT_OBSTACLE",
                severity=Severity.HIGH,
                description="장애물 없이 제동 (False Positive)"
            ))

        # 4. 물리 법칙 위반
        if current_behavior.reported_deceleration > 12.0:  # m/s²
            anomalies.append(Anomaly(
                type="PHYSICALLY_IMPOSSIBLE",
                severity=Severity.CRITICAL,
                description="물리적으로 불가능한 감속도 (센서 오류)"
            ))

        return AnomalyReport(
            anomalies=anomalies,
            requires_action=len(anomalies) > 0
        )
```

#### 9.2.2 Watchdog 시스템

```python
class AEBWatchdog:
    """AEB 시스템 감시 및 자동 복구"""

    def __init__(self):
        self.aeb_system = AEBSystem()
        self.expected_heartbeat_interval = 0.1  # 100ms
        self.last_heartbeat = time.time()
        self.malfunction_counter = 0

    async def monitor_system(self):
        """시스템 감시 루프"""

        while True:
            await asyncio.sleep(self.expected_heartbeat_interval)

            # 1. Heartbeat 확인
            if not self._received_heartbeat():
                self.log_warning("AEB system not responding")
                self.malfunction_counter += 1

                if self.malfunction_counter >= 3:
                    # 3회 연속 무응답 → 재시작
                    self.restart_aeb_system()

            # 2. 이상 행동 감지
            behavior = self.aeb_system.get_current_behavior()
            anomaly_report = AnomalousBehaviorDetector().detect_anomaly(behavior)

            if anomaly_report.requires_action:
                self.handle_anomaly(anomaly_report)

            # 3. 리소스 사용량 확인
            if self.aeb_system.cpu_usage > 90:
                self.log_warning("AEB CPU usage critical")
                self.optimize_or_throttle()

            if self.aeb_system.memory_usage > 90:
                self.log_warning("AEB memory usage critical")
                self.clear_cache_and_gc()

    def handle_anomaly(self, report: AnomalyReport):
        """이상 행동 처리

        Args:
            report: 이상 감지 보고서
        """

        for anomaly in report.anomalies:
            if anomaly.severity == Severity.CRITICAL:
                # 즉시 시스템 안전 모드 전환
                self.aeb_system.enter_safe_mode()
                self.notify_driver(
                    "⚠️ AEB 시스템 이상 감지 - 안전 모드 진입",
                    urgency=AlertLevel.HIGH
                )

            elif anomaly.severity == Severity.HIGH:
                # 문제가 있는 컴포넌트 비활성화
                self.disable_problematic_component(anomaly)
                self.log_event(f"Disabled component due to: {anomaly.description}")

            # 모든 이상 항목 기록
            self.audit_logger.log_anomaly(anomaly)
```

### 9.3 False Positive 방지

#### 9.3.1 다단계 검증 필터

```python
class FalsePositiveFilter:
    """오탐지 방지 필터"""

    def __init__(self):
        self.temporal_filter = TemporalConsistencyFilter()
        self.spatial_filter = SpatialConsistencyFilter()
        self.physics_validator = PhysicsValidator()

    def filter_detections(self, detections: List[Detection]) -> List[Detection]:
        """여러 필터를 거쳐 오탐지 제거

        Args:
            detections: 원시 감지 결과

        Returns:
            List[Detection]: 필터링된 신뢰 가능한 감지 결과
        """

        # Stage 1: 시간적 일관성 필터
        # 이전 프레임과 비교하여 갑자기 나타난 물체는 의심
        temporal_filtered = self.temporal_filter.apply(detections)

        # Stage 2: 공간적 일관성 필터
        # 물리적으로 불가능한 위치의 물체 제거
        spatial_filtered = self.spatial_filter.apply(temporal_filtered)

        # Stage 3: 물리 법칙 검증
        # 물리 법칙을 위반하는 움직임 제거
        physics_validated = self.physics_validator.apply(spatial_filtered)

        # Stage 4: 통계적 이상치 제거
        statistical_filtered = self._remove_statistical_outliers(physics_validated)

        return statistical_filtered

    def _remove_statistical_outliers(self, detections: List[Detection]) -> List[Detection]:
        """통계적 이상치 제거

        Args:
            detections: 감지 결과

        Returns:
            List[Detection]: 이상치 제거된 결과
        """

        if len(detections) < 3:
            return detections  # 샘플 부족 시 그대로 반환

        # 거리 분포 계산
        distances = [d.distance for d in detections]
        mean_dist = np.mean(distances)
        std_dist = np.std(distances)

        # 3-sigma 규칙: 평균에서 3 표준편차 밖은 이상치
        filtered = [
            d for d in detections
            if abs(d.distance - mean_dist) < 3 * std_dist
        ]

        return filtered
```

### 9.4 Fail-Safe 스위치

물리적 스위치를 통한 시스템 강제 종료 메커니즘입니다.

```python
class EmergencyShutdownSwitch:
    """비상 종료 스위치"""

    def __init__(self):
        self.gpio_pin = GPIO_PIN_EMERGENCY_SWITCH
        self.pressed_duration = 0
        GPIO.setup(self.gpio_pin, GPIO.IN)

    def monitor_switch(self):
        """스위치 모니터링"""

        while True:
            if GPIO.input(self.gpio_pin) == GPIO.HIGH:
                # 스위치 눌림 감지
                self.pressed_duration += 0.1

                if self.pressed_duration >= 2.0:
                    # 2초 이상 누르면 강제 종료
                    self.perform_emergency_shutdown()
                    break
            else:
                self.pressed_duration = 0

            time.sleep(0.1)

    def perform_emergency_shutdown(self):
        """비상 종료 수행"""

        self.log_critical("EMERGENCY SHUTDOWN INITIATED BY USER")

        # 1. AEB 시스템 즉시 비활성화
        self.aeb_system.disable(reason="EMERGENCY_SHUTDOWN")

        # 2. 현재 제동 해제
        self.brake_controller.release_all()

        # 3. 제어권을 완전히 운전자에게 반환
        self.vehicle_controller.return_full_control_to_driver()

        # 4. 시스템 재시작 방지 (수동 재활성화 필요)
        self.aeb_system.lock_until_manual_reset()

        # 5. 운전자에게 알림
        self.display.show_message(
            "🔴 AEB 비상 종료됨\n"
            "재활성화: 차량 정지 후 설정 메뉴에서 재활성화 필요",
            duration=None
        )
```

### 9.5 검증 방법

#### 오작동 방지 테스트

| 테스트 | 방법 | 합격 기준 |
|--------|------|-----------|
| False Positive Rate | 1000 km 정상 주행 | < 0.1% (1회 이하) |
| 오작동 감지 시간 | Watchdog 반응 시간 측정 | < 300ms |
| 비상 종료 스위치 | 물리적 스위치 작동 | 100% 즉시 종료 |
| 이상 행동 감지율 | 인위적 오작동 주입 | > 95% 감지 |

---

## 전략 10: 소프트웨어 업데이트 및 테스트 정책

### 10.1 설계 철학

> **💡 핵심 원칙:** 소프트웨어 업데이트는 새로운 기능을 추가하는 동시에 새로운 위험을 도입할 수 있습니다. 따라서 엄격한 검증 절차와 안전한 롤아웃 전략이 필수입니다.

### 10.2 소프트웨어 업데이트 파이프라인

#### 10.2.1 업데이트 단계

```python
class OTAUpdatePipeline:
    """Over-The-Air (OTA) 업데이트 파이프라인"""

    STAGES = [
        "development",      # 개발 단계
        "internal_test",    # 내부 테스트
        "simulation",       # 시뮬레이션 검증
        "hil_test",        # Hardware-in-the-Loop 테스트
        "field_test",      # 제한적 현장 테스트
        "staged_rollout",  # 단계적 배포
        "full_release"     # 전체 배포
    ]

    def __init__(self):
        self.current_version = "v3.2.1"
        self.candidate_version = None
        self.rollout_percentage = 0

    def initiate_update(self, new_version: str, update_package: bytes):
        """업데이트 시작

        Args:
            new_version: 새 버전 번호
            update_package: 업데이트 패키지
        """

        self.candidate_version = new_version

        # Stage 1: 암호학적 검증
        if not self._verify_signature(update_package):
            raise SecurityError("Update package signature invalid")

        # Stage 2: 버전 호환성 확인
        if not self._check_compatibility(new_version):
            raise CompatibilityError(f"Version {new_version} incompatible")

        # Stage 3: 시뮬레이션 테스트
        sim_result = self._run_simulation_tests(update_package)
        if sim_result.failure_rate > 0.001:
            raise TestFailureError(f"Simulation failure rate too high: {sim_result.failure_rate}")

        # Stage 4: 소수 차량 배포 (Canary Deployment)
        self._deploy_to_canary_fleet(update_package, percentage=1)

        # Stage 5: 모니터링 및 점진적 확대
        self._monitor_and_expand_rollout()

    def _deploy_to_canary_fleet(self, package: bytes, percentage: float):
        """소수 차량에 먼저 배포 (카나리 배포)

        Args:
            package: 업데이트 패키지
            percentage: 배포 비율 (0-100)
        """

        # 카나리 그룹 선정 기준
        canary_criteria = {
            "test_fleet": True,  # 테스트 차량 우선
            "high_telemetry": True,  # 텔레메트리 수집 동의 차량
            "low_risk_environment": True,  # 저위험 환경 (시내 주행)
            "expert_drivers": True  # 숙련 운전자
        }

        canary_vehicles = self._select_canary_vehicles(
            percentage=percentage,
            criteria=canary_criteria
        )

        for vehicle in canary_vehicles:
            self._push_update_to_vehicle(vehicle, package)
            self._monitor_vehicle(vehicle, alert_threshold=0.05)

    def _monitor_and_expand_rollout(self):
        """모니터링 후 점진적 확대"""

        rollout_schedule = [
            (1, 24),    # 1% 차량, 24시간 모니터링
            (5, 48),    # 5%, 48시간
            (10, 72),   # 10%, 72시간
            (25, 96),   # 25%, 96시간
            (50, 120),  # 50%, 120시간
            (100, 0)    # 100% 전체 배포
        ]

        for percentage, monitoring_hours in rollout_schedule:
            self.rollout_percentage = percentage

            # 배포
            self._expand_rollout_to(percentage)

            # 모니터링
            monitoring_result = self._monitor_for_hours(monitoring_hours)

            # 문제 발견 시 롤백
            if monitoring_result.has_critical_issues():
                self._rollback_update()
                raise UpdateFailureError(
                    f"Critical issues detected at {percentage}% rollout"
                )

            # 다음 단계 진행
            self.log(f"Rollout at {percentage}% successful, proceeding")
```

#### 10.2.2 자동 롤백 메커니즘

```python
class AutomaticRollback:
    """문제 감지 시 자동 롤백"""

    def __init__(self):
        self.previous_version = "v3.2.0"
        self.current_version = "v3.2.1"
        self.rollback_threshold = RollbackThreshold()

    def monitor_update_health(self):
        """업데이트 후 시스템 건강도 모니터링"""

        metrics = {
            "false_positive_rate": self._measure_false_positive_rate(),
            "false_negative_rate": self._measure_false_negative_rate(),
            "system_crash_rate": self._measure_crash_rate(),
            "response_time": self._measure_response_time(),
            "user_complaints": self._count_user_complaints()
        }

        # 임계값 초과 확인
        for metric_name, metric_value in metrics.items():
            threshold = self.rollback_threshold.get(metric_name)

            if metric_value > threshold:
                self.log_critical(
                    f"Metric {metric_name} exceeded threshold: "
                    f"{metric_value} > {threshold}"
                )

                # 자동 롤백 시작
                self.initiate_automatic_rollback(reason=f"{metric_name}_threshold_exceeded")
                return

    def initiate_automatic_rollback(self, reason: str):
        """자동 롤백 실행

        Args:
            reason: 롤백 이유
        """

        self.log_critical(f"AUTOMATIC ROLLBACK INITIATED: {reason}")

        # 1. 새 업데이트 차단
        self._stop_new_deployments()

        # 2. 모든 차량에 이전 버전 배포
        self._deploy_previous_version_to_all()

        # 3. 사고 보고서 생성
        incident_report = self._generate_incident_report(reason)
        self._notify_engineering_team(incident_report)

        # 4. 사용자에게 알림
        self._notify_affected_users(
            f"소프트웨어가 안정 버전 ({self.previous_version})으로 복원되었습니다."
        )
```

### 10.3 회귀 테스트 (Regression Testing)

#### 10.3.1 자동화된 테스트 스위트

```python
class AEBRegressionTestSuite:
    """AEB 회귀 테스트 스위트"""

    def __init__(self):
        self.test_scenarios = self._load_test_scenarios()
        self.baseline_performance = self._load_baseline()

    def run_full_regression_test(self, new_software_version: str) -> TestReport:
        """전체 회귀 테스트 실행

        Args:
            new_software_version: 테스트할 새 버전

        Returns:
            TestReport: 테스트 결과 보고서
        """

        report = TestReport(version=new_software_version)

        # 1. 기능 테스트 (모든 기능이 작동하는가?)
        report.functional_tests = self._run_functional_tests()

        # 2. 성능 테스트 (성능이 저하되지 않았는가?)
        report.performance_tests = self._run_performance_tests()

        # 3. 안전 테스트 (안전성이 유지되는가?)
        report.safety_tests = self._run_safety_tests()

        # 4. 엣지 케이스 테스트 (극한 상황 대응)
        report.edge_case_tests = self._run_edge_case_tests()

        # 5. 내구성 테스트 (장기간 안정성)
        report.endurance_tests = self._run_endurance_tests()

        # 베이스라인과 비교
        regression_detected = self._compare_with_baseline(report, self.baseline_performance)

        if regression_detected:
            report.status = TestStatus.FAILED
            report.regressions = regression_detected
        else:
            report.status = TestStatus.PASSED

        return report

    def _run_safety_tests(self) -> SafetyTestResults:
        """안전 테스트 실행"""

        critical_scenarios = [
            "pedestrian_crossing_30kmh",
            "pedestrian_crossing_50kmh",
            "vehicle_sudden_stop_highway",
            "cyclist_sideswipe",
            "stationary_vehicle_night",
            "child_running_from_parked_car",
            "vehicle_cutting_in",
            "animal_on_road",
            "debris_on_highway"
        ]

        results = []

        for scenario in critical_scenarios:
            # 시뮬레이션에서 100회 반복
            scenario_results = []
            for run in range(100):
                result = self.simulator.run_scenario(scenario, run_id=run)
                scenario_results.append(result)

            # 성공률 계산
            success_rate = sum(1 for r in scenario_results if r.collision_avoided) / 100

            results.append(SafetyTestResult(
                scenario=scenario,
                success_rate=success_rate,
                passed=success_rate >= 0.95  # 95% 이상 성공 필요
            ))

        return SafetyTestResults(results=results)
```

### 10.4 버전 관리 및 추적

#### 10.4.1 소프트웨어 Bill of Materials (SBOM)

```python
@dataclass
class SoftwareBillOfMaterials:
    """소프트웨어 구성 요소 명세서"""

    # 버전 정보
    version: str
    build_timestamp: datetime
    git_commit_hash: str

    # AI 모델
    ai_models: List[ModelInfo]  # 각 모델의 버전, 학습 데이터, 성능

    # 의존성
    dependencies: List[Dependency]  # 라이브러리 버전

    # 하드웨어 요구사항
    required_hardware: HardwareRequirement

    # 테스트 결과
    test_results: TestReport

    # 인증 정보
    certifications: List[Certification]  # ISO 26262, SOTIF 등

    def generate_report(self) -> str:
        """SBOM 보고서 생성"""

        report = f"""
# Software Bill of Materials (SBOM)
## AEB System {self.version}

### Version Information
- Version: {self.version}
- Build Time: {self.build_timestamp}
- Git Commit: {self.git_commit_hash}

### AI Models
"""
        for model in self.ai_models:
            report += f"""
- {model.name} v{model.version}
  - Architecture: {model.architecture}
  - Training Data: {model.training_dataset}
  - Performance: {model.performance_metrics}
  - Checksum: {model.checksum}
"""

        report += f"""
### Dependencies
"""
        for dep in self.dependencies:
            report += f"- {dep.name} v{dep.version} (License: {dep.license})\n"

        report += f"""
### Test Results
- Functional Tests: {self.test_results.functional_tests.pass_rate * 100:.1f}%
- Safety Tests: {self.test_results.safety_tests.pass_rate * 100:.1f}%
- Performance Tests: {self.test_results.performance_tests.pass_rate * 100:.1f}%

### Certifications
"""
        for cert in self.certifications:
            report += f"- {cert.standard}: {cert.status} ({cert.date})\n"

        return report
```

### 10.5 검증 방법

#### 업데이트 검증 체크리스트

| 검증 항목 | 방법 | 합격 기준 |
|----------|------|-----------|
| 코드 리뷰 | 2인 이상 리뷰 | 100% 승인 |
| 단위 테스트 | 자동화 테스트 | > 95% 커버리지, 0 실패 |
| 통합 테스트 | CI/CD 파이프라인 | 100% 통과 |
| 시뮬레이션 | 10,000 시나리오 | > 99% 성공 |
| HIL 테스트 | 실제 하드웨어 | 100% 통과 |
| 현장 테스트 | 제한적 배포 (1%) | 24시간 무사고 |
| 보안 감사 | 침투 테스트 | 취약점 0개 (Critical/High) |

---

## 통합 시스템 아키텍처

### 전체 시스템 구조

```
┌────────────────────────────────────────────────────────────────┐
│                      AEB 통합 시스템                            │
└────────────────────────────────────────────────────────────────┘

┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  센서 계층      │  │  AI 계층        │  │  제어 계층      │
├─────────────────┤  ├─────────────────┤  ├─────────────────┤
│ • 카메라 (3x)   │  │ • Primary AI    │  │ • 브레이크      │
│ • 레이더 (3x)   │─▶│ • Secondary AI  │─▶│ • 조향          │
│ • 라이다 (2x)   │  │ • 규칙 검증기   │  │ • 경고 시스템   │
│ • 초음파 (12x)  │  │ • XAI 엔진      │  │ • HMI           │
└─────────────────┘  └─────────────────┘  └─────────────────┘
        ↓                     ↓                     ↓
┌──────────────────────────────────────────────────────────────┐
│                    안전 감시 계층                             │
├──────────────────────────────────────────────────────────────┤
│ • Circuit Breaker  • Watchdog  • Anomaly Detector           │
│ • Policy Validator • Audit Logger • Health Monitor          │
└──────────────────────────────────────────────────────────────┘
        ↓                     ↓                     ↓
┌──────────────────────────────────────────────────────────────┐
│                    복구 계층                                  │
├──────────────────────────────────────────────────────────────┤
│ • Fallback Chain • Rollback Manager • MRC System           │
│ • Backup Systems • Emergency Stop  • Black Box             │
└──────────────────────────────────────────────────────────────┘
```

### 데이터 흐름도

```
[센서 Raw Data]
       ↓
[센서 퓨전 & 전처리]
       ↓
[Triple Redundancy Check] ←─ [Sensor Health Monitor]
       ↓
[AI Object Detection]
       ↓
[Dual AI Verification] ←─────── [Secondary AI]
       ↓
[False Positive Filter]
       ↓
[Risk Assessment & TTC]
       ↓
[Policy Decision Engine] ←───── [Safety Policy Rules]
       ↓
[Action Constraints Check]
       ↓
[Driver Override Check] ←─────── [Driver Input Monitor]
       ↓
[Brake Command] ─────────┬────▶ [Electronic Brake]
                         │
                         ├────▶ [Hydraulic Backup]
                         │
                         └────▶ [Mechanical Backup]
       ↓
[Audit Logging & Explanation]
       ↓
[Black Box Recording]
```

---

## 검증 및 인증

### 인증 로드맵

| 단계 | 인증/표준 | 목표 시기 | 상태 |
|------|----------|----------|------|
| 1 | ISO 26262 ASIL-D (기능 안전) | 2026 Q3 | 진행 중 |
| 2 | ISO/PAS 21448 (SOTIF) | 2026 Q4 | 계획됨 |
| 3 | ISO 21434 (사이버 보안) | 2027 Q1 | 계획됨 |
| 4 | Euro NCAP 5-Star | 2027 Q2 | 계획됨 |
| 5 | UN R157 (ALKS 인증) | 2027 Q3 | 계획됨 |

### 최종 검증 테스트

```python
class FinalVerificationTest:
    """최종 검증 테스트 스위트"""

    def run_final_verification(self) -> CertificationReport:
        """최종 인증 테스트 실행"""

        report = CertificationReport()

        # === 안전성 검증 (ISO 26262) ===
        report.safety = self._verify_safety_goals()
        assert report.safety.asil_level == "D"

        # === 의도된 기능의 안전성 (SOTIF) ===
        report.sotif = self._verify_sotif_compliance()
        assert report.sotif.known_unsafe_scenarios == 0

        # === 사이버 보안 (ISO 21434) ===
        report.security = self._verify_cybersecurity()
        assert report.security.critical_vulnerabilities == 0

        # === 성능 검증 ===
        report.performance = self._verify_performance()
        assert report.performance.false_positive_rate < 0.001
        assert report.performance.false_negative_rate < 0.0001

        # === 설명가능성 검증 ===
        report.explainability = self._verify_explainability()
        assert report.explainability.explanation_coverage > 0.99

        # === 현장 검증 ===
        report.field_test = self._verify_field_performance()
        assert report.field_test.total_test_km > 1_000_000  # 100만 km
        assert report.field_test.incidents == 0

        return report
```

---

## 부록

### A. 용어 정의

| 용어 | 정의 |
|------|------|
| **TTC** | Time To Collision (충돌까지 예상 시간) |
| **ASIL-D** | Automotive Safety Integrity Level D (최고 안전 등급) |
| **HIL** | Hardware-in-the-Loop (하드웨어 루프 시뮬레이션) |
| **V2X** | Vehicle-to-Everything (차량-사물 통신) |
| **LRP** | Layer-wise Relevance Propagation (계층별 관련성 전파) |
| **MTBF** | Mean Time Between Failures (평균 고장 간격) |
| **MRC** | Minimal Risk Condition (최소 위험 조건) |
| **SOTIF** | Safety Of The Intended Functionality (의도된 기능의 안전성) |
| **OTA** | Over-The-Air (무선 업데이트) |
| **SBOM** | Software Bill Of Materials (소프트웨어 구성 명세서) |

### B. 참고 표준

- **ISO 26262**: 자동차 기능 안전
- **ISO/PAS 21448 (SOTIF)**: 의도된 기능의 안전성
- **ISO 21434**: 자동차 사이버 보안
- **UN R157**: 자동 차선 유지 시스템
- **Euro NCAP**: 유럽 신차 안전도 평가
- **SAE J3016**: 자동화 수준 정의

### C. 변경 이력

| 버전 | 날짜 | 변경 내용 | 작성자 |
|------|------|-----------|--------|
| 1.0 | 2026-01-14 | 초안 작성 (전략 1-5) | AI System |
| 1.1 | 2026-01-14 | 전략 6-10 추가, 통합 아키텍처 완성 | AI System |

---

**문서 완료**

✅ **작성 완료된 항목:**
- 전략 1: Inherently Safe Design
- 전략 2: 설명가능성 확보
- 전략 3: 데이터 기반 위험 분석
- 전략 4: 수동적 및 능동적 안전장치
- 전략 5: 제어 가능성 & 인간 중심 설계
- 전략 6: Fallback 및 비상 정지
- 전략 7: 검증 가능한 행동 정책
- 전략 8: 다중 장벽 설계
- 전략 9: 의도치 않은 작동 방지
- 전략 10: 소프트웨어 업데이트 및 테스트 정책
- 통합 시스템 아키텍처
- 검증 및 인증

---

> 📄 **총 문서 길이:** 약 4,000 라인
>
> 💡 **다음 단계 권장사항:**
> 1. 실제 HIL (Hardware-in-the-Loop) 테스트 환경 구축
> 2. AI 모델 학습 데이터 수집 시작 (최소 100만 샘플)
> 3. ISO 26262 인증 프로세스 착수
> 4. 시뮬레이션 환경 구축 (CARLA, PreScan 등)
