# AEB System Safety Specification

AI 기반 자율 긴급 제동(AEB, Autonomous Emergency Braking) 시스템의 안전 설계 명세서입니다.

## 🌐 온라인 문서

📖 **[웹 버전 보기](https://jsyssdsh.github.io/AEB_plan/)**

HTML 버전으로 보기 좋게 포맷팅된 전체 명세서를 확인할 수 있습니다.

## 📑 문서 정보

| 항목 | 내용 |
|------|------|
| 시스템명 | AI 기반 자율 긴급 제동 시스템 (AEB) |
| 버전 | 1.1 |
| 작성일 | 2026년 1월 14일 |
| 안전 무결성 등급 | ASIL-D (ISO 26262) |
| 적용 차량 | 승용차, SUV (Level 2+ 자율주행) |

## 📂 파일 구조

```
AEB_plan/
├── AEB_SAFETY_SPECIFICATION.md  # 전체 안전 설계 명세서 (마크다운)
├── index.html                    # 웹 버전 문서
├── README.md                     # 프로젝트 소개 (현재 파일)
└── SPECIFICATION.md              # 추가 명세서
```

## 📋 목차

명세서는 다음과 같은 10가지 안전 전략을 다룹니다:

1. **Inherently Safe Design (본질적 안전 설계)**
   - Safe State 정의
   - Fail-Safe 동작
   - 불확실성 처리

2. **설명가능성(Explainability) 확보**
   - XAI 적용
   - Layer-wise Relevance Propagation (LRP)
   - 블랙박스 데이터 기록

3. **데이터 기반 위험 분석**
   - 학습 데이터 안전성 검증
   - 편향 완화 전략

4. **수동적 및 능동적 안전장치**
   - 계층적 제동 전략
   - Pre-Crash 시스템

5. **제어 가능성 & 인간 중심 설계**
   - Human-in-the-Loop (HITL)
   - 운전자 개입 메커니즘

6. **Fallback 및 비상 정지**
   - 센서/AI 폴백 체인
   - Minimal Risk Condition (MRC)

7. **검증 가능한 행동 정책**
   - 형식적 정책 정의
   - SMT Solver 검증

8. **다중 장벽 설계 (Redundancy & Barriers)**
   - 센서 다중화
   - 이중 AI 아키텍처

9. **의도치 않은 작동 방지**
   - 이상 행동 감지
   - Watchdog 시스템

10. **소프트웨어 업데이트 및 테스트 정책**
    - OTA 업데이트 파이프라인
    - 자동 롤백 메커니즘

## 🎯 시스템 목표

| 우선순위 | 목표 | 설명 |
|----------|------|------|
| 1차 | 충돌 회피 | 속도 0 km/h까지 완전 감속 |
| 2차 | 충돌 속도 감소 | 피해 최소화 (부상 경감) |
| 3차 | 오작동 방지 | 불필요한 제동 최소화 (False Positive < 0.1%) |
| **안전 목표** | **인명 피해 제로** | **시스템 오작동으로 인한 2차 사고 방지** |

## 🔧 센서 구성

- **스테레오 카메라**: 120° FOV, 150m (객체 인식, 분류)
- **밀리미터파 레이더**: 77GHz, 200m (거리/속도 측정)
- **LiDAR**: 100m, 0.1° 각도 (3D 형상 인식)
- **초음파 센서**: 5m (근거리 감지)
- **V2X (선택)**: 300m (통신 기반 정보)

## 📊 안전 메트릭

| 메트릭 | 목표값 |
|--------|--------|
| MTBF (평균 고장 간격) | > 10,000 시간 |
| False Positive Rate | < 0.1% |
| False Negative Rate | < 0.001% |
| Response Time | < 100ms |
| Availability | > 99.9% |

## 🏆 인증 로드맵

| 인증/표준 | 목표 시기 | 상태 |
|----------|----------|------|
| ISO 26262 ASIL-D (기능 안전) | 2026 Q3 | 진행 중 |
| ISO/PAS 21448 (SOTIF) | 2026 Q4 | 계획됨 |
| ISO 21434 (사이버 보안) | 2027 Q1 | 계획됨 |
| Euro NCAP 5-Star | 2027 Q2 | 계획됨 |
| UN R157 (ALKS 인증) | 2027 Q3 | 계획됨 |

## 📖 문서 읽는 방법

### 온라인으로 보기
가장 권장하는 방법입니다:
- **웹 버전**: https://jsyssdsh.github.io/AEB_plan/
  - 문법 강조, 목차, 반응형 디자인
  - 브라우저에서 바로 확인

### 로컬에서 보기

1. **마크다운 뷰어 사용**:
   ```bash
   # VSCode에서 열기
   code AEB_SAFETY_SPECIFICATION.md
   # Ctrl+Shift+V (미리보기)
   ```

2. **HTML 버전**:
   ```bash
   # 웹 브라우저로 열기
   open index.html  # macOS
   xdg-open index.html  # Linux
   ```

## 🔗 관련 표준

- **ISO 26262**: 자동차 기능 안전
- **ISO/PAS 21448 (SOTIF)**: 의도된 기능의 안전성
- **ISO 21434**: 자동차 사이버 보안
- **UN R157**: 자동 차선 유지 시스템
- **Euro NCAP**: 유럽 신차 안전도 평가
- **SAE J3016**: 자동화 수준 정의

## 📝 용어 정의

| 용어 | 정의 |
|------|------|
| **TTC** | Time To Collision (충돌까지 예상 시간) |
| **ASIL-D** | Automotive Safety Integrity Level D (최고 안전 등급) |
| **HIL** | Hardware-in-the-Loop (하드웨어 루프 시뮬레이션) |
| **V2X** | Vehicle-to-Everything (차량-사물 통신) |
| **LRP** | Layer-wise Relevance Propagation (계층별 관련성 전파) |
| **MTBF** | Mean Time Between Failures (평균 고장 간격) |
| **MRC** | Minimal Risk Condition (최소 위험 조건) |
| **SOTIF** | Safety Of The Intended Functionality |
| **OTA** | Over-The-Air (무선 업데이트) |

## 📄 라이선스

이 문서는 교육 및 연구 목적으로 작성되었습니다.

## 🤝 기여

문서 개선을 위한 이슈나 풀 리퀘스트를 환영합니다.

## 📧 문의

이슈나 질문이 있으시면 GitHub Issues를 통해 연락주세요.

---

**문서 버전**: 1.1
**마지막 업데이트**: 2026년 1월 15일
