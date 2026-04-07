# 📚 스터디 플랜 — Java Spring + React/TypeScript

> 시작일: 2026-04-06 | 매일 2시간 | 총 28일
> 언어: 피드백은 항상 한국어
> 방식: 개념 설명 → 직접 작성 → 실행 확인 → 코드 리뷰

---

## 규칙 (서로 간의 약속)

| 항목 | 약속 |
|------|------|
| 진행 방식 | 이 파일의 플랜대로만 진행. 임의로 변경하지 않음 |
| 변경 요청 | 플랜을 바꾸고 싶으면 먼저 말씀 후 이 파일을 같이 수정 |
| 실습 방식 | 코드를 먼저 제공하지 않음. 직접 작성 후 리뷰 순서로 진행 |
| 기록 | 매일 학습 후 README.md 변경 관리에 기록 |
| 진행 상태 | 이 파일에 ✅ / 🔲 로 표시하여 관리 |

---

## Week 1 — Docker 이해 + Java 핵심 개념

> 목표: 오늘 만든 환경을 직접 분석하고, Generic/Stream을 직접 작성할 수 있다

### ✅ Day 1 (04/06, 완료)

**한 일:**
- Docker Compose 전체 환경 구축 (MySQL, Redis, Kafka, Spring, React, Nginx, Kafdrop)
- Spring Boot 백엔드 전체 소스 생성 (Order CRUD + Kafka + Redis + WebSocket 설정)
- React 프론트엔드 전체 소스 생성 (TanStack Query + STOMP.js)
- Docker 실행 + 주문 생성 → Kafka 이벤트 발행/수신 동작 확인
- README 변경 관리 기록
- GitHub push 완료

**참고 — Day 1에서 원래 플랜보다 앞서 진행된 것:**
- 원래 Day 1~4 내용(Dockerfile, docker-compose, Redis, Kafka 설정)이 모두 완료됨
- 따라서 Week 1의 나머지 일정을 아래와 같이 재조정함

---

### ✅ Day 2 (04/07, 완료)

**주제: docker-compose.yml + Dockerfile 직접 분석**

| 시간 | 내용 |
|------|------|
| 1교시 (1h) | `docker-compose.yml` 한 줄씩 같이 읽기 — 왜 이 설정이 필요한가? |
| 2교시 (1h) | `backend/Dockerfile`, `frontend/Dockerfile` 분석 — 멀티스테이지 빌드 원리 |

**학습한 내용:**
- 이미지 버전 고정 이유 — 재현성(Reproducibility) 보장
- `depends_on` vs `condition: service_healthy` 차이 — 시작 순서 vs 실제 준비 완료
- `healthcheck` — 컨테이너 정상 여부 주기적 검사
- `networks` — 컨테이너끼리 서비스 이름으로 통신 (내부 DNS)
- 멀티스테이지 빌드 — 빌드 도구 제거로 이미지 크기 대폭 감소
- COPY 순서 분리 — Docker 레이어 캐시 최적화 (빌드 시간 단축)

**학습 노트:** [docs/day2_docker_analysis.md](docs/day2_docker_analysis.md)

---

### ✅ Day 3 (04/07, 완료)

**주제: Java Generic + Stream + Lambda**

| 시간 | 내용 |
|------|------|
| 1교시 (1h) | `ApiResponse<T>` 분석 — 클래스/메서드 레벨 `<T>` 선언 차이, Bounded Wildcard |
| 2교시 (1h) | `OrderService` Stream 직접 작성 — filter/map/collect |

**직접 작성한 코드:**
- `ApiResponse.java` — `<T extends Number> sum(List<T> list)` 추가
- `OrderService.java` — `getPendingOrders()` Stream filter 메서드 추가

**학습한 내용:**
- Generic `<T>` 클래스/메서드 레벨 선언 차이 (static 메서드 이유 포함)
- Primitive 타입 불가 → Wrapper 클래스 사용 (`int` → `Integer`)
- Bounded Wildcard `<T extends Number>` — 타입 범위 제한
- Stream 3단계: 중간 연산(filter/map/sorted) + 최종 연산(collect/count/reduce)
- 메서드 레퍼런스 4가지, 함수형 인터페이스, Optional

**학습 노트:** [docs/day3_generic_stream_lambda.md](docs/day3_generic_stream_lambda.md)

---

### 🔲 Day 4 (04/09)

**주제: Java Stream 직접 작성**

| 시간 | 내용 |
|------|------|
| 1교시 (1h) | `OrderService.getAllOrders()` Stream 코드 분석 + map/filter/collect 원리 |
| 2교시 (1h) | Stream 메서드 직접 작성 실습 |

**실습 과제 (직접 작성 후 OrderService에 추가):**

```java
// 과제 1: 전체 주문 총 금액 합산
public BigDecimal getOrdersTotalAmount() { ... }

// 과제 2: 상태별 주문 건수 집계
public Map<OrderStatus, Long> getOrderCountByStatus() { ... }

// 과제 3: PENDING 상태만 필터링 후 금액 내림차순 정렬
public List<OrderResponse> getPendingOrdersSortedByPrice() { ... }
```

실행 확인: Swagger에서 API 호출 후 결과 검증

---

### 🔲 Day 5 (04/10)

**주제: GlobalExceptionHandler + @Valid 연결 이해**

| 시간 | 내용 |
|------|------|
| 1교시 (1h) | `@Valid`, `@NotBlank`, `MethodArgumentNotValidException` 흐름 분석 |
| 2교시 (1h) | Stream으로 오류 메시지 수집하는 코드 직접 작성 |

**실습 과제:**
- Swagger에서 잘못된 값으로 요청 → 어떤 오류 메시지가 나오는지 확인
- Stream의 `collect(Collectors.joining(", "))` 직접 작성

---

### 🔲 Day 6 (04/11)

**주제: Week 1 복습 + 직접 설명하기**

| 시간 | 내용 |
|------|------|
| 1교시 (1h) | Generic + Stream 복습 — 코드 없이 직접 설명해보기 |
| 2교시 (1h) | docker-compose 전체 구조를 직접 재현해보기 (빈 파일에서 시작) |

---

### 🔲 Day 7 (04/12)

**주제: Week 1 최종 점검**

| 시간 | 내용 |
|------|------|
| 1교시 (1h) | Week 1 전체 퀴즈 (10문항 직접 답하기) |
| 2교시 (1h) | 틀린 부분 보완 + Week 2 예습 (Redis 개념) |

---

## Week 2 — 백엔드 심화 (Redis / Kafka)

> 목표: Redis 캐싱 전략과 Kafka Producer/Consumer를 직접 구현하고 동작을 확인한다

### 🔲 Day 8 (04/13) — Redis @Cacheable / @CacheEvict 직접 작성
### 🔲 Day 9 (04/14) — Redis TTL 설정 + Cache-Aside 패턴 실습
### 🔲 Day 10 (04/15) — Kafka Producer 직접 작성 + 파티션/직렬화 이해
### 🔲 Day 11 (04/16) — Kafka Consumer 직접 작성 + DLQ 개념
### 🔲 Day 12 (04/17) — Stream 심화 + Generic 유틸 조합 실습
### 🔲 Day 13 (04/18) — Kafka + Redis 통합 실습 (주문 이벤트 → 캐시 갱신)
### 🔲 Day 14 (04/19) — Week 2 복습 + Swagger 문서화

---

## Week 3 — 프론트엔드 심화 (React + TypeScript)

> 목표: useReducer, Custom Hook, 로딩/에러 처리를 직접 구현한다

### 🔲 Day 15 (04/20) — useState vs useReducer 차이 분석 + TypeScript action 타입 정의
### 🔲 Day 16 (04/21) — Reducer 심화: 장바구니 상태 모델링
### 🔲 Day 17 (04/22) — Custom Hook 기초: useFetch, useDebounce 직접 작성
### 🔲 Day 18 (04/23) — Custom Hook 심화: useInfiniteScroll, useLocalStorage
### 🔲 Day 19 (04/24) — 로딩 처리: Suspense + 스켈레톤 UI
### 🔲 Day 20 (04/25) — 에러 처리: ErrorBoundary + TanStack Query 에러 핸들링
### 🔲 Day 21 (04/26) — Week 3 복습 + Custom Hook으로 API 추상화 완성

---

## Week 4 — 통합 실습 (WebSocket + 테스트 + 미니 프로젝트)

> 목표: WebSocket 실시간 연동, 테스트 작성, 전체 스택 통합 실행

### 🔲 Day 22 (04/27) — Spring WebSocket STOMP 서버 직접 분석
### 🔲 Day 23 (04/28) — React useWebSocket Custom Hook 직접 작성
### 🔲 Day 24 (04/29) — JUnit5 + Mockito 단위 테스트 직접 작성
### 🔲 Day 25 (04/30) — Vitest + React Testing Library 테스트 직접 작성
### 🔲 Day 26 (05/01) — 미니 프로젝트 Day 1: 실시간 주문 현황판 구현
### 🔲 Day 27 (05/02) — 미니 프로젝트 Day 2: Redis 캐싱 + 에러처리 통합
### 🔲 Day 28 (05/03) — 최종 회고 + 다음 단계 로드맵

---

## 진행 현황

| 주차 | 완료 | 전체 | 진행률 |
|------|------|------|--------|
| Week 1 | 1 | 7 | 14% |
| Week 2 | 0 | 7 | 0% |
| Week 3 | 0 | 7 | 0% |
| Week 4 | 0 | 7 | 0% |
| **전체** | **1** | **28** | **4%** |
