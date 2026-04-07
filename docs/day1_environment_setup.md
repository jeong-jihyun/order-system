# Day 1 — 전체 개발 환경 구축 (2026-04-06)

> 주제: Docker Compose + Spring Boot + React 전체 환경 한 번에 구성

---



## 1. 구성한 아키텍처

```
[브라우저]
    │
    ▼
[Nginx :80] ──→ [React :3000]
    │
    ▼
[Spring Boot :8080]
    ├──→ [MySQL :3306]   — 주문 데이터 저장
    ├──→ [Redis :6379]   — 조회 캐싱 (TTL 30분)
    ├──→ [Kafka :9092]   — 주문 이벤트 발행/소비
    └──→ [WebSocket]     — 실시간 상태 변경 브로드캐스트

[Kafdrop :9000]          — Kafka 모니터링 UI
[Zookeeper :2181]        — Kafka 코디네이터
```



## 2. 핵심 소스 요약

### Spring Boot — 계층 구조

```
com.order/
├── common/
│   ├── response/ApiResponse.java       ← Generic<T> 통일 응답 래퍼
│   └── exception/GlobalExceptionHandler.java
├── config/
│   ├── KafkaConfig.java                ← order-events 토픽 3 파티션
│   ├── RedisConfig.java                ← TTL 30분, JSON 직렬화
│   └── WebSocketConfig.java            ← STOMP /ws 엔드포인트
├── domain/order/
│   ├── entity/Order.java
│   ├── dto/OrderRequest.java / OrderResponse.java
│   ├── repository/OrderRepository.java
│   ├── service/OrderService.java       ← @Cacheable, @CacheEvict, Stream
│   └── controller/OrderController.java ← REST 5개 엔드포인트
└── kafka/
    ├── producer/OrderEventProducer.java ← KafkaTemplate 비동기
    └── consumer/OrderEventConsumer.java ← @KafkaListener → WebSocket
```



### Kafka 이벤트 흐름

```
POST /api/orders
    → OrderService.createOrder()
    → OrderEventProducer.send()         ← Kafka 발행
    → OrderEventConsumer.consume()      ← Kafka 소비
    → SimpMessagingTemplate.convertAndSend("/topic/orders")  ← WebSocket 브로드캐스트
```



### React — 핵심 구조

```
src/
├── api/
│   ├── axiosConfig.ts     ← baseURL, 인터셉터
│   └── orderApi.ts        ← 5개 API 함수
├── pages/
│   ├── OrderListPage.tsx  ← useQuery + STOMP WebSocket
│   └── OrderCreatePage.tsx ← useMutation + 폼 유효성 검사
├── components/
│   ├── common/LoadingSpinner.tsx
│   ├── common/ErrorFallback.tsx
│   └── OrderCard.tsx
└── types/order.ts
```



## 3. 실무에서 자주 쓰는 명령어

### Docker

```bash
# 전체 컨테이너 시작 (백그라운드)
docker compose up -d

# 상태 확인
docker compose ps

# 특정 컨테이너 로그 실시간
docker compose logs -f spring-app

# 특정 컨테이너만 재시작
docker compose restart spring-app

# 멈춘 컨테이너 시작
docker compose start spring-app

# 전체 종료 (컨테이너 유지)
docker compose stop

# 전체 종료 + 컨테이너 삭제
docker compose down

# 볼륨까지 삭제 (DB 데이터 초기화)
docker compose down -v

# 이미지 재빌드 후 시작
docker compose up -d --build spring-app
```



### Git

```bash
git init
git add .
git commit -m "feat: 초기 프로젝트 구성"
git remote add origin https://github.com/...
git push -u origin main
```



## 4. Day 1에서 해결한 트러블슈팅

| 문제 | 원인 | 해결 |
|------|------|------|
| `version: '3.8'` 경고 | Docker Compose V2에서 obsolete | `version` 줄 제거 |
| `dockerDesktopLinuxEngine` 오류 | Docker Desktop 미실행 | Docker Desktop 시작 |
| `npm ci` 실패 | `package-lock.json` 없음 | `npm install` 후 lock 파일 생성 |
| 빌드 컨텍스트 144MB | `.dockerignore` 없음 | `.dockerignore` 추가 |
| `import.meta.env` TS 오류 | `vite-env.d.ts` 없음 | `/// <reference types="vite/client" />` 추가 |
| Gradle 타임아웃 | 의존성 다운로드 지연 | `--no-watch-fs -x test` 옵션 추가 |



## 5. 개발 팁

### .env 파일 관리
- `.env`는 반드시 `.gitignore`에 추가 (비밀번호, API 키 포함)
- 팀 공유는 `.env.example` 파일로 키 목록만 공유

```bash
# .env.example
MYSQL_ROOT_PASSWORD=
MYSQL_USER=
MYSQL_PASSWORD=
```



### docker-compose.yml 환경변수 참조

```yaml
environment:
  MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}  ← .env 파일에서 읽음
```



### Spring Boot application.yml 환경변수 기본값 패턴

```yaml
url: ${SPRING_DATASOURCE_URL:jdbc:mysql://localhost:3306/orderdb}
#                              ↑ Docker 환경     ↑ 로컬 개발 기본값
```



### Redis 캐시 전략

```java
@Cacheable(value = "orders", key = "#id")   // 조회 시 캐시 저장
@CacheEvict(value = "orders", key = "#id")  // 수정/삭제 시 캐시 제거
```



### Kafka 토픽 파티션

- 파티션 수 = 동시에 처리할 수 있는 컨슈머 수
- 운영에서는 최소 3개 권장 (고가용성)



## 6. 접속 주소

| 서비스 | URL |
|--------|-----|
| 프론트엔드 | http://localhost:3000 |
| 백엔드 API | http://localhost:8080/swagger-ui.html |
| Kafdrop (Kafka 모니터링) | http://localhost:9000 |
| MySQL | localhost:3306 |
| Redis | localhost:6379 |



## 7-1. Kafka / Redis 상세 설명

> Kafka 토픽/파티션/오프셋 개념, Redis 직렬화/TTL/캐시 무효화 전략 등 상세 내용은 별도 파일 참고

**→ [day1_kafka_redis_setup.md](day1_kafka_redis_setup.md)**



## 7. 참고 자료

| 주제 | URL |
|------|-----|
| Docker Compose 공식 문서 | https://docs.docker.com/compose/ |
| Spring Boot 공식 문서 | https://docs.spring.io/spring-boot/docs/current/reference/html/ |
| Spring Kafka 문서 | https://docs.spring.io/spring-kafka/docs/current/reference/html/ |
| TanStack Query 문서 | https://tanstack.com/query/latest |
| STOMP.js | https://stomp-js.github.io/stomp-websocket/ |
| Kafdrop GitHub | https://github.com/obsidiandynamics/kafdrop |
| SpringDoc OpenAPI | https://springdoc.org/ |
