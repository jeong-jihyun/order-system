# 주문 관리 시스템 (Order System)

> Java Spring Boot + React TypeScript 기반의 실시간 주문 관리 시스템
> 1개월 스터디 프로젝트 — 매일 2시간 실습 중심 학습

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [기술 스택](#2-기술-스택)
3. [아키텍처 설계 방향](#3-아키텍처-설계-방향)
4. [프로젝트 구조](#4-프로젝트-구조)
5. [환경 구축 (Docker)](#5-환경-구축-docker)
6. [백엔드 실행 (로컬)](#6-백엔드-실행-로컬)
7. [프론트엔드 실행 (로컬)](#7-프론트엔드-실행-로컬)
8. [API 명세](#8-api-명세)
9. [학습 로드맵 (4주 플랜)](#9-학습-로드맵-4주-플랜)
10. [변경 관리 (Change Log)](#10-변경-관리-change-log)

---

## 1. 프로젝트 개요

| 항목 | 내용 |
|------|------|
| 목적 | Java + React 실무 핵심 기술 실습 (Kafka, Redis, WebSocket, Generic, Stream 등) |
| 도메인 | 주문 생성 / 상태 변경 / 실시간 현황판 |
| 시작일 | 2026-04-06 |
| 학습 방식 | 매일 2시간 / 주제별 실습 → 누적 통합 |

---

## 2. 기술 스택

### 백엔드

| 기술 | 버전 | 역할 |
|------|------|------|
| Java | 17+ | 언어 |
| Spring Boot | 3.2.x | 웹 프레임워크 |
| Spring Data JPA | - | ORM (MySQL 연동) |
| Spring Data Redis | - | 캐싱 (`@Cacheable`) |
| Spring Kafka | - | 이벤트 발행/소비 |
| Spring WebSocket | - | 실시간 STOMP 통신 |
| SpringDoc (Swagger) | 2.3.x | API 문서 자동화 |
| MySQL | 8.0 | 관계형 DB |
| Redis | 7 | 캐시 서버 |
| Kafka | 7.5.0 | 메시지 브로커 |

### 프론트엔드

| 기술 | 버전 | 역할 |
|------|------|------|
| React | 18+ | UI 라이브러리 |
| TypeScript | 5.x | 타입 안정성 |
| TanStack Query | 5.x | 서버 상태 관리 (로딩/에러 처리) |
| React Router | 6.x | 클라이언트 라우팅 |
| Axios | 1.x | HTTP 클라이언트 |
| STOMP.js | 7.x | WebSocket 클라이언트 |
| Vite | 5.x | 빌드 도구 |
| Vitest | 1.x | 테스트 프레임워크 |

### 인프라

| 기술 | 역할 |
|------|------|
| Docker | 컨테이너 런타임 |
| Docker Compose | 멀티 컨테이너 오케스트레이션 |
| Nginx | 프론트엔드 정적 파일 서빙 + 역방향 프록시 |
| Kafdrop | Kafka 토픽/메시지 모니터링 UI |

---

## 3. 아키텍처 설계 방향

### 왜 이 구조인가?

```
[React 클라이언트]
    │ HTTP REST          │ WebSocket (STOMP)
    ▼                    ▼
[Spring Boot API]  ←→  [STOMP Broker /topic/orders]
    │                    ▲
    │ 저장                │ 이벤트 broadcast
    ▼                    │
 [MySQL DB]         [Kafka Consumer]
    │                    ▲
    │ @Cacheable          │ 이벤트 발행
    ▼                    │
 [Redis Cache]  ←─  [Kafka Producer]
```

### 설계 원칙

| 원칙 | 적용 내용 |
|------|-----------|
| **단일 책임** | Controller → Service → Repository 계층 분리 |
| **제네릭 활용** | `ApiResponse<T>` — 모든 API 응답을 하나의 래퍼로 통일 |
| **비동기 이벤트** | 주문 생성 시 Kafka로 이벤트 발행 → Consumer에서 WebSocket 브로드캐스트 |
| **캐시 전략** | Cache-Aside 패턴: GET은 Redis 우선 조회, 상태 변경 시 `@CacheEvict`로 무효화 |
| **타입 안정성** | 백엔드 `OrderStatus enum` ↔ 프론트 `OrderStatus type` 1:1 대응 |

### 패키지 구조 원칙 (백엔드)

```
도메인 중심 패키지 (Domain-centric package)
  com.order.domain.order   ← 주문 도메인 전체
  com.order.kafka          ← 이벤트 인프라
  com.order.config         ← 기술 설정
  com.order.common         ← 공통 유틸
```

---

## 4. 프로젝트 구조

```
order-system/
├── docker-compose.yml        # 전체 인프라 정의
├── .env                      # 환경변수 (DB 비밀번호 등)
├── README.md
│
├── backend/
│   ├── Dockerfile            # 멀티스테이지 빌드 (Gradle → JRE)
│   ├── build.gradle.kts      # 의존성 관리
│   ├── settings.gradle.kts
│   └── src/main/
│       ├── java/com/order/
│       │   ├── OrderSystemApplication.java   # 진입점, @EnableCaching
│       │   ├── common/
│       │   │   ├── response/ApiResponse.java  # 제네릭 응답 래퍼 <T>
│       │   │   └── exception/GlobalExceptionHandler.java
│       │   ├── config/
│       │   │   ├── KafkaConfig.java           # 토픽 자동 생성
│       │   │   ├── RedisConfig.java           # TTL 30분, JSON 직렬화
│       │   │   └── WebSocketConfig.java       # STOMP /ws 엔드포인트
│       │   ├── domain/order/
│       │   │   ├── entity/Order.java          # JPA 엔티티
│       │   │   ├── entity/OrderStatus.java    # PENDING/PROCESSING/COMPLETED/CANCELLED
│       │   │   ├── dto/OrderRequest.java      # 입력 DTO + @Valid 검증
│       │   │   ├── dto/OrderResponse.java     # 출력 DTO (from() 팩토리)
│       │   │   ├── repository/OrderRepository.java
│       │   │   ├── service/OrderService.java  # @Cacheable, Stream 활용
│       │   │   └── controller/OrderController.java
│       │   └── kafka/
│       │       ├── event/OrderEvent.java      # Kafka 메시지 객체
│       │       ├── producer/OrderEventProducer.java
│       │       └── consumer/OrderEventConsumer.java  # → WebSocket 브로드캐스트
│       └── resources/
│           └── application.yml               # DB/Redis/Kafka 연결 설정
│
└── frontend/
    ├── Dockerfile            # 멀티스테이지 빌드 (Node → Nginx)
    ├── nginx.conf            # 정적 파일 서빙 + API/WS 역방향 프록시
    ├── package.json
    ├── vite.config.ts        # 개발 서버 프록시 설정
    ├── tsconfig.json
    └── src/
        ├── main.tsx          # QueryClient 설정, 앱 진입점
        ├── App.tsx           # Router (목록 / 새 주문)
        ├── types/order.ts    # OrderStatus, Order, ApiResponse<T> 타입
        ├── api/
        │   ├── axiosConfig.ts    # 인터셉터, 타임아웃 설정
        │   └── orderApi.ts       # API 함수 5개
        ├── components/
        │   ├── common/
        │   │   ├── LoadingSpinner.tsx   # 공통 로딩 UI
        │   │   └── ErrorFallback.tsx    # 공통 에러 UI
        │   └── OrderCard.tsx            # 주문 카드 컴포넌트
        ├── pages/
        │   ├── OrderListPage.tsx    # useQuery + useMutation
        │   └── OrderCreatePage.tsx  # 폼 + 유효성 검사
        └── test/
            └── setup.ts            # Vitest + jest-dom 초기화
```

---

## 5. 환경 구축 (Docker)

### 사전 요구사항

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) 설치 및 실행
- 포트 충돌 없을 것: `3000`, `8080`, `3306`, `6379`, `9092`, `9000`

### 실행 명령어

```powershell
# 1. 프로젝트 루트로 이동
cd d:\order-system

# 2. 전체 컨테이너 빌드 + 실행 (첫 실행 시 빌드 포함)
docker compose up -d --build

# 3. 컨테이너 상태 확인
docker compose ps

# 4. Spring 앱 로그 확인
docker compose logs -f spring-app

# 5. 전체 중지
docker compose down

# 6. 전체 중지 + 볼륨 삭제 (DB 초기화 시)
docker compose down -v
```

### 접속 주소

| 서비스 | URL | 설명 |
|--------|-----|------|
| 프론트엔드 | http://localhost:3000 | 주문 목록 / 등록 화면 |
| Swagger UI | http://localhost:8080/swagger-ui.html | API 테스트 |
| Kafdrop | http://localhost:9000 | Kafka 토픽/메시지 확인 |

### 로컬 개발 환경 (Docker 없이)

```
필요 사전 설치: MySQL 8.0, Redis 7, Kafka (또는 Docker로 인프라만 실행)
```

```powershell
# 인프라만 Docker로 실행 (앱은 로컬에서)
docker compose up -d mysql redis kafka zookeeper kafdrop
```

---

## 6. 백엔드 실행 (로컬)

```powershell
cd d:\order-system\backend

# 빌드
.\gradlew.bat build

# 실행
.\gradlew.bat bootRun
```

---

## 7. 프론트엔드 실행 (로컬)

```powershell
cd d:\order-system\frontend

# 의존성 설치 (최초 1회)
npm install

# 개발 서버 실행 (포트 5173)
npm run dev

# 테스트 실행
npm test

# 빌드
npm run build
```

> 개발 서버 실행 중에는 `/api` 요청이 자동으로 `localhost:8080`으로 프록시됩니다.

---

## 8. API 명세

> 상세 명세는 Swagger UI: http://localhost:8080/swagger-ui.html

| Method | URL | 설명 |
|--------|-----|------|
| `GET` | `/api/orders` | 전체 주문 조회 |
| `GET` | `/api/orders/{id}` | 단건 조회 (Redis 캐시 적용) |
| `GET` | `/api/orders/status/{status}` | 상태별 주문 조회 |
| `POST` | `/api/orders` | 주문 생성 (Kafka 이벤트 발행) |
| `PATCH` | `/api/orders/{id}/status?status=` | 상태 변경 (Redis 캐시 무효화) |

### 요청/응답 예시

**주문 생성 요청**
```json
POST /api/orders
{
  "customerName": "홍길동",
  "productName": "노트북",
  "quantity": 1,
  "totalPrice": 1500000
}
```

**응답 (ApiResponse<T> 래퍼)**
```json
{
  "success": true,
  "message": "주문이 생성되었습니다.",
  "data": {
    "id": 1,
    "customerName": "홍길동",
    "productName": "노트북",
    "quantity": 1,
    "totalPrice": 1500000,
    "status": "PENDING",
    "createdAt": "2026-04-06T10:00:00",
    "updatedAt": "2026-04-06T10:00:00"
  }
}
```

### WebSocket 구독

```
연결 엔드포인트: ws://localhost:8080/ws
구독 채널:       /topic/orders
메시지 형식:     OrderEvent JSON (주문 생성/상태 변경 시 수신)
```

---

## 9. 학습 로드맵 (4주 플랜)

| 주차 | 핵심 주제 | 상태 |
|------|-----------|------|
| **Week 1** (04/06 ~) | Docker 환경 + Generic + Stream | 🟡 진행 중 |
| **Week 2** | Redis 캐싱 전략 + Kafka Producer/Consumer | ⬜ 예정 |
| **Week 3** | useReducer + Custom Hook + 로딩/에러 처리 | ⬜ 예정 |
| **Week 4** | WebSocket 실시간 + JUnit5 테스트 + 통합 실습 | ⬜ 예정 |

---

## 10. 변경 관리 (Change Log)

> 규칙: 학습하면서 코드를 수정/추가할 때마다 아래에 기록합니다.
> 형식: `날짜 | 구분 | 파일 | 내용`

---

### 2026-04-06 — Week 1 Day 1 초기 세팅

#### 추가된 파일

| 구분 | 파일 | 설명 |
|------|------|------|
| 인프라 | `docker-compose.yml` | MySQL + Redis + Kafka + Zookeeper + Kafdrop + Spring + Nginx 7개 컨테이너 |
| 인프라 | `.env` | DB 환경변수 분리 |
| 백엔드 | `build.gradle.kts` | Spring Boot 3.2, JPA, Redis, Kafka, WebSocket, Swagger 의존성 |
| 백엔드 | `application.yml` | DB/Redis/Kafka 연결 설정, 로컬/Docker 환경변수 분기 |
| 백엔드 | `Dockerfile` | 멀티스테이지 빌드 (Gradle 8.5 → eclipse-temurin JRE 17) |
| 백엔드 | `ApiResponse<T>` | 제네릭 응답 래퍼 — 성공/실패 팩토리 메서드 패턴 |
| 백엔드 | `GlobalExceptionHandler` | `@RestControllerAdvice`, Stream으로 유효성 오류 수집 |
| 백엔드 | `KafkaConfig` | `order-events` 토픽 자동 생성 (3 파티션) |
| 백엔드 | `RedisConfig` | TTL 30분, JSON 직렬화 `RedisTemplate` + `RedisCacheManager` |
| 백엔드 | `WebSocketConfig` | STOMP `/ws` 엔드포인트, `/topic` 브로커 채널 |
| 백엔드 | `Order` (entity) | JPA 엔티티, `@CreationTimestamp`/`@UpdateTimestamp` |
| 백엔드 | `OrderStatus` | `PENDING / PROCESSING / COMPLETED / CANCELLED` enum |
| 백엔드 | `OrderRequest` | `@Valid` 입력 검증 DTO |
| 백엔드 | `OrderResponse` | `from(Order)` 정적 팩토리 패턴 |
| 백엔드 | `OrderRepository` | `JpaRepository<Order, Long>`, 상태별/고객명 조회 |
| 백엔드 | `OrderService` | `Stream.map()`, `@Cacheable`, `@CacheEvict` |
| 백엔드 | `OrderController` | REST 5개 엔드포인트 + Swagger `@Tag`/`@Operation` |
| 백엔드 | `OrderEvent` | Kafka 메시지 DTO (Entity 의존성 없음) |
| 백엔드 | `OrderEventProducer` | `KafkaTemplate.send()` + 비동기 콜백 로깅 |
| 백엔드 | `OrderEventConsumer` | `@KafkaListener` → `SimpMessagingTemplate`으로 WebSocket 브로드캐스트 |
| 프론트 | `package.json` | React 18 + TanStack Query 5 + STOMP.js + Vitest |
| 프론트 | `vite.config.ts` | `/api`, `/ws` 개발 서버 프록시 설정 |
| 프론트 | `tsconfig.json` | strict 모드, `@/` 경로 alias |
| 프론트 | `Dockerfile` | Node 20 빌드 → Nginx 정적 서빙 |
| 프론트 | `nginx.conf` | SPA 폴백, `/api`, `/ws` 역방향 프록시 |
| 프론트 | `types/order.ts` | `OrderStatus`, `Order`, `OrderRequest`, `ApiResponse<T>` |
| 프론트 | `axiosConfig.ts` | 공통 인터셉터, 타임아웃 10초 |
| 프론트 | `orderApi.ts` | API 함수 5개 |
| 프론트 | `LoadingSpinner.tsx` | 공통 로딩 컴포넌트 |
| 프론트 | `ErrorFallback.tsx` | 공통 에러 컴포넌트 |
| 프론트 | `OrderCard.tsx` | 주문 카드, 상태 변경 버튼 |
| 프론트 | `OrderListPage.tsx` | `useQuery` + `useMutation` + 카드 그리드 |
| 프론트 | `OrderCreatePage.tsx` | 폼 + 클라이언트 유효성 검사 |

#### 설계 결정 사항 (Decision Log)

| # | 결정 | 이유 |
|---|------|------|
| 1 | `ApiResponse<T>` 제네릭 래퍼 사용 | 모든 API 응답 형식 통일, 프론트에서 타입 추론 가능 |
| 2 | Kafka 토픽 파티션 3개 | 컨슈머 그룹 병렬 처리 실습용 (개발 환경) |
| 3 | Redis TTL 30분 | 주문 데이터 빈번한 변경 고려, 너무 길면 데이터 불일치 위험 |
| 4 | `@CacheEvict` + Cache-Aside 패턴 | 상태 변경 후 즉시 캐시 무효화로 데이터 정합성 보장 |
| 5 | 도메인 중심 패키지 구조 | 계층형 패키지(`controller/service/repository`)보다 기능 확장 시 응집도 높음 |
| 6 | `OrderEvent` Entity에서 분리 | Kafka 직렬화 시 JPA Lazy 로딩 문제 방지, 외부 계약 독립 유지 |
| 7 | Vite proxy → Spring API | 개발 시 CORS 설정 불필요, 프로덕션과 동일한 URL 구조 사용 |

---

### 변경 기록 템플릿

아래 형식을 복사해서 학습 진행 중 변경 시 추가하세요.

```markdown
### YYYY-MM-DD — Week N DayN 주제명

#### 변경 내용
| 구분 | 파일 | 변경 내용 |
|------|------|-----------|
| 추가/수정/삭제 | 파일명 | 설명 |

#### 배운 점
- 핵심 개념 1
- 핵심 개념 2

#### 다음 단계
- [ ] 다음에 할 것
```

---

### 2026-04-06 — Week 1 Day 1 (2) Docker 실행 및 동작 확인

#### 발생한 문제 및 해결 과정

---

##### 문제 1 — `version` 속성 경고

**오류 메시지:**
```
the attribute `version` is obsolete, it will be ignored
```

**원인:**  
Docker Compose V2부터 `version: '3.8'` 선언이 불필요해짐. 최신 버전에서는 무시되며 경고 출력.

**해결:**  
`docker-compose.yml` 최상단의 `version: '3.8'` 줄 제거.

```yaml
# 제거 전
version: '3.8'
services:

# 제거 후
services:
```

---

##### 문제 2 — Docker Desktop 미실행 오류

**오류 메시지:**
```
unable to get image 'redis:7-alpine': error during connect:
open //./pipe/dockerDesktopLinuxEngine: The system cannot find the file specified.
```

**원인:**  
Docker 클라이언트는 설치되어 있었지만 **Docker Desktop이 실행되지 않은 상태**였음.  
`//./pipe/dockerDesktopLinuxEngine` 는 Docker Desktop의 Linux 컨테이너 엔진 소켓 경로.

**확인 명령어:**
```powershell
docker version
# → Server 항목이 없으면 데몬 미실행 상태
```

**해결:**  
Docker Desktop 실행 후 `docker version`으로 Server 응답 확인:
```
Server: Docker Desktop 4.47.0 (206054)
 Engine: Version 28.4.0
 OS/Arch: linux/amd64   ← Linux 컨테이너 모드 확인
```

---

##### 문제 3 — 프론트엔드 `npm ci` 실패

**오류 메시지:**
```
Dockerfile:7 — RUN npm ci
process "/bin/sh -c npm ci" did not complete successfully: exit code: 1
```

**원인:**  
`npm ci` 명령은 `package-lock.json` 파일이 **반드시 존재**해야 실행 가능.  
프로젝트 생성 시 `package-lock.json`을 생성하지 않은 상태였음.

> **`npm install` vs `npm ci` 차이점**
> | 명령어 | lock 파일 | 속도 | 용도 |
> |--------|-----------|------|------|
> | `npm install` | 없어도 됨 (생성함) | 느림 | 개발 환경 최초 설치 |
> | `npm ci` | 반드시 필요 | 빠름 | CI/CD, Docker 빌드 |

**해결:**  
로컬에서 `npm install` 실행 → `package-lock.json` 생성 후 Docker 빌드 재시도.

**추가 조치 — `.dockerignore` 추가:**  
`node_modules` 폴더가 Docker 빌드 컨텍스트에 포함되어 전송 속도가 144MB로 느렸음.  
`.dockerignore` 추가로 다음 빌드부터 컨텍스트 크기 대폭 감소.

```
# frontend/.dockerignore
node_modules
dist
.env
```

---

##### 문제 4 — TypeScript 빌드 오류 `Property 'env' does not exist on type 'ImportMeta'`

**오류 메시지:**
```
src/api/axiosConfig.ts(9,24): error TS2339:
Property 'env' does not exist on type 'ImportMeta'.
```

**원인:**  
`import.meta.env`는 Vite 전용 타입으로, TypeScript가 인식하려면  
`/// <reference types="vite/client" />` 선언이 있는 `vite-env.d.ts` 파일이 필요함.  
해당 파일이 누락된 상태였음.

**해결:**  
`src/vite-env.d.ts` 파일 생성:
```typescript
/// <reference types="vite/client" />
```

---

##### 문제 5 — Spring 앱 Gradle 의존성 다운로드 타임아웃

**원인:**  
Docker 빌드 중 `RUN gradle dependencies --no-daemon` 명령이 네트워크 환경에 따라  
오래 걸리거나 타임아웃 발생.

**해결:**  
`--no-watch-fs` 옵션 추가, 테스트 제외 옵션(`-x test`) 추가:
```dockerfile
RUN gradle dependencies --no-daemon --quiet --no-watch-fs 2>/dev/null || true
RUN gradle bootJar --no-daemon --no-watch-fs -x test
```

---

#### 최종 빌드 결과

```
[+] Building 185.9s (33/33) FINISHED
 ✅ spring-app    Built  (Gradle 멀티스테이지)
 ✅ frontend      Built  (Node 20 → Nginx)
```

#### 컨테이너 실행 상태 확인

```powershell
docker compose ps
```

```
NAME              STATUS                    PORTS
order-backend     Up                        0.0.0.0:8080->8080/tcp
order-frontend    Up                        0.0.0.0:3000->80/tcp
order-kafdrop     Up                        0.0.0.0:9000->9000/tcp
order-kafka       Up                        0.0.0.0:9092->9092/tcp
order-mysql       Up (healthy)              0.0.0.0:3306->3306/tcp
order-redis       Up                        0.0.0.0:6379->6379/tcp
order-zookeeper   Up                        2181/tcp
```

#### 동작 확인 — 주문 생성 → Kafka 이벤트 흐름

Swagger UI(`http://localhost:8080/swagger-ui.html`)에서 `POST /api/orders` 테스트 후  
Spring 로그에서 전체 흐름 확인:

```log
# 1단계: DB 저장
INSERT INTO orders (customer_name, product_name, ...) values (?, ?, ?)

# 2단계: Kafka 이벤트 발행 (Producer)
[Kafka] 이벤트 발행 성공 — orderId=2, partition=2, offset=0

# 3단계: Kafka 이벤트 수신 (Consumer)
[Kafka] 이벤트 수신 — orderId=2, status=PENDING
```

Kafdrop(`http://localhost:9000`) → `order-events` 토픽 → **View Messages**에서  
실제 Kafka 메시지 JSON 데이터 확인 완료.

#### 수정된 파일 목록

| 구분 | 파일 | 변경 내용 |
|------|------|-----------|
| 수정 | `docker-compose.yml` | `version: '3.8'` 제거 |
| 수정 | `backend/Dockerfile` | `--no-watch-fs`, `-x test` 옵션 추가 |
| 추가 | `backend/.dockerignore` | `.gradle`, `build` 폴더 빌드 컨텍스트 제외 |
| 추가 | `frontend/.dockerignore` | `node_modules`, `dist` 빌드 컨텍스트 제외 |
| 추가 | `frontend/src/vite-env.d.ts` | `import.meta.env` TypeScript 타입 선언 |
| 추가 | `frontend/package-lock.json` | `npm install` 실행으로 생성 (`npm ci` 사용 가능) |

#### 배운 점

- `npm ci`는 `package-lock.json`이 없으면 실패. Docker 빌드 전 로컬에서 `npm install` 必須
- `.dockerignore`는 빌드 컨텍스트 크기를 줄여 Docker 빌드 속도를 크게 향상시킴 (144MB → 1.15kB)
- `vite-env.d.ts`의 `/// <reference types="vite/client" />` 는 Vite 프로젝트에서 필수 파일
- Docker Desktop은 `docker version` 명령으로 서버 연결 여부를 빠르게 확인 가능
- Kafka Consumer가 메시지를 수신하면 즉시 WebSocket으로 브로드캐스트되는 흐름 실제 확인

#### 다음 단계 (Day 2 예고)

- [ ] `ApiResponse<T>` 제네릭 코드 직접 분석 및 작성 실습
- [ ] `OrderService.java`의 Stream 코드 (`map`, `filter`, `reduce`, `collect`) 직접 작성
- [ ] 총 금액 합산 메서드 `getOrdersSummary()` Stream으로 구현
- [ ] Redis `@Cacheable` 동작 원리 학습 (GET 요청 시 DB 미호출 확인)

---

> **Note:** `.env` 파일은 Git에 커밋하지 마세요. `.gitignore`에 추가 필요.
