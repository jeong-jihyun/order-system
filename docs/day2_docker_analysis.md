# Day 2 — Docker Compose + Dockerfile 분석 (2026-04-07)

> 주제: 이미 구성된 환경을 직접 읽고 각 설정의 이유 이해하기

---

## 1. docker-compose.yml 핵심 개념

### 이미지 버전 고정

```yaml
image: mysql:8.0      ✅ 권장
image: mysql:latest   ❌ 비권장
```

**이유 — 재현성(Reproducibility)**
- `latest`는 시간이 지나면 다른 버전을 가리킬 수 있음
- 팀원 A는 MySQL 8.0, 팀원 B는 MySQL 9.0이 설치될 수 있음
- 버전 고정 = 모든 환경에서 동일한 동작 보장

---

### depends_on vs condition: service_healthy

```yaml
# ❌ 이것만 쓰면 위험
depends_on:
  - mysql

# ✅ 실무 권장
depends_on:
  mysql:
    condition: service_healthy
```

**차이점:**

| | `depends_on` (단순) | `condition: service_healthy` |
|---|---|---|
| 보장하는 것 | mysql 컨테이너 **시작** 순서 | mysql이 **실제 접속 가능** 상태 |
| spring-app 시작 시점 | mysql 프로세스 시작 직후 | mysql healthcheck 통과 후 |
| 문제 가능성 | DB 초기화 중 접속 시도 → 크래시 | 없음 |

**흐름:**
```
mysql 컨테이너 시작
    → healthcheck 실행 (mysqladmin ping)
    → 성공할 때까지 대기 (interval: 10s, retries: 5)
    → "healthy" 판정
    → 그제서야 spring-app 시작
```

---

### healthcheck

```yaml
mysql:
  healthcheck:
    test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
    interval: 10s      ← 10초마다 검사
    timeout: 5s        ← 5초 안에 응답 없으면 실패
    retries: 5         ← 5번 실패하면 unhealthy 판정
    start_period: 30s  ← 시작 후 30초는 실패해도 무시 (초기화 시간 고려)
```

**역할:** 컨테이너가 정상인지 **주기적으로 검사**하는 방법을 정의

---

### networks

```yaml
networks:
  order-network:
    driver: bridge

services:
  mysql:
    networks:
      - order-network
  spring-app:
    networks:
      - order-network
```

**역할:** 같은 네트워크의 컨테이너끼리 **서비스 이름으로 통신** 가능

```yaml
# application.yml
url: jdbc:mysql://mysql:3306/orderdb
#                 ↑ IP가 아닌 서비스 이름
```

Docker 내부 DNS가 `mysql` → 해당 컨테이너 IP 자동 변환

**없으면?** 각 컨테이너가 격리되어 이름으로 서로를 찾지 못함 → 접속 실패

---

### 3가지 핵심 설정 요약

| 설정 | 역할 한 줄 요약 |
|------|----------------|
| `depends_on` | 컨테이너 **시작 순서**만 보장 |
| `condition: service_healthy` | 컨테이너가 **실제로 준비됐는지** 확인 후 다음 시작 |
| `healthcheck` | 컨테이너 정상 여부를 **주기적으로 검사**하는 방법 정의 |
| `networks` | 컨테이너끼리 **이름으로 찾을 수 있게** 해주는 내부 DNS |

---

## 2. 멀티스테이지 빌드 (Dockerfile)

### 개념

```dockerfile
FROM 이미지A AS 별명   ← Stage 1: 빌드 환경
...빌드 작업...

FROM 이미지B           ← Stage 2: 실행 환경
COPY --from=별명 ...   ← Stage 1에서 결과물만 가져옴
```

**Stage 1의 빌드 도구, 소스코드, 의존성 캐시 → 최종 이미지에 포함되지 않음**

---

### 백엔드 Dockerfile 분석

```dockerfile
# Stage 1: 빌드
FROM gradle:8.5-jdk17-alpine AS builder   ← Gradle + JDK (약 500MB)
WORKDIR /app

COPY build.gradle.kts settings.gradle.kts ./  ← ① 의존성 설정 파일 먼저
RUN gradle dependencies --no-daemon           ← ② 의존성 다운로드 (캐시 레이어)

COPY src ./src                                ← ③ 소스코드 나중에
RUN gradle bootJar --no-daemon --no-watch-fs -x test  ← ④ 빌드

# Stage 2: 실행
FROM eclipse-temurin:17-jre-alpine            ← JRE만 (약 80MB)
COPY --from=builder /app/build/libs/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
```

**이미지 크기 비교:**
```
Stage 1만 사용: ~500MB (Gradle + JDK + 소스 + jar 전부)
멀티스테이지:    ~80MB  (JRE + jar만)
```

---

### 프론트엔드 Dockerfile 분석

```dockerfile
# Stage 1: 빌드
FROM node:20-alpine AS builder              ← Node.js (약 180MB)
WORKDIR /app

COPY package*.json ./                       ← ① package.json 먼저
RUN npm ci                                  ← ② 의존성 설치 (캐시 레이어)

COPY . .                                    ← ③ 소스코드 나중에
RUN npm run build                           ← ④ Vite 빌드 → /dist 생성

# Stage 2: 서빙
FROM nginx:1.25-alpine                      ← Nginx (약 25MB)
COPY --from=builder /app/dist /usr/share/nginx/html  ← 정적 파일만
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

**React 앱의 핵심:**  
빌드하면 HTML/CSS/JS 파일만 남음 → Node.js 필요 없음 → Nginx로 충분

---

### COPY 순서가 중요한 이유 — Docker 레이어 캐시

**Docker는 각 명령어를 레이어로 저장하고, 변경이 없으면 캐시 재사용**

```
❌ 비효율적 방식:
COPY . .               ← 소스 한 줄 수정 → 이 레이어 무효화
RUN npm ci             ← 매번 의존성 새로 설치 (2~5분)
RUN npm run build

✅ 캐시 최적화 방식:
COPY package*.json ./  ← package.json 변경 없으면 캐시 유지
RUN npm ci             ← 캐시 재사용! (0초)
COPY . .               ← 소스코드 변경
RUN npm run build      ← 빌드만 실행 (30초)
```

**빌드 시간 비교:**

| 상황 | 비효율 방식 | 캐시 최적화 방식 |
|------|------------|----------------|
| 소스 코드 수정 후 빌드 | 3~5분 | **30초** |
| package.json 수정 후 빌드 | 3~5분 | 3~5분 |

---

## 3. 실무에서 자주 쓰는 명령어

### Docker 이미지 관련

```bash
# 이미지 목록 확인
docker images

# 이미지 크기 확인 (멀티스테이지 효과 확인)
docker image inspect nginx:1.25-alpine --format='{{.Size}}'

# 미사용 이미지 정리
docker image prune

# 빌드 캐시 확인
docker buildx du

# 빌드 캐시 삭제 (캐시 초기화할 때)
docker builder prune
```

### Docker 로그/디버깅

```bash
# 실시간 로그
docker compose logs -f spring-app

# 최근 50줄만
docker compose logs --tail=50 spring-app

# 컨테이너 내부 접속
docker compose exec mysql bash
docker compose exec mysql mysql -u root -p

# Redis CLI 접속
docker compose exec redis redis-cli

# 컨테이너 리소스 사용량 모니터링
docker stats
```

### Dockerfile 빌드 단독 테스트

```bash
# 특정 이미지만 빌드 (docker-compose 없이)
docker build -t my-backend ./backend
docker build -t my-frontend ./frontend

# 빌드 + 바로 실행 테스트
docker run -p 8080:8080 my-backend
```

---

## 4. 개발 팁

### alpine 이미지를 쓰는 이유
- `alpine` = 경량 Linux 배포판 (약 5MB)
- `ubuntu` 기반보다 이미지 크기 대폭 감소
- 단, 일부 라이브러리(glibc 등) 호환성 문제가 생길 수 있음
- 문제 발생 시 `eclipse-temurin:17-jre` (slim 버전)으로 교체

### `npm ci` vs `npm install`

| | `npm ci` | `npm install` |
|---|---|---|
| 사용 상황 | CI/CD, Docker 빌드 | 로컬 개발 |
| `package-lock.json` | 필수 (없으면 실패) | 없어도 됨 |
| 속도 | 빠름 (lock 파일 그대로 설치) | 느림 (의존성 해석) |
| `node_modules` | 항상 새로 설치 | 있으면 업데이트 |

### `gradle bootJar` 주요 옵션

```bash
--no-daemon      # Gradle 데몬 비활성화 (Docker/CI 환경 필수)
--no-watch-fs    # 파일 시스템 감시 비활성화 (컨테이너 내부 성능 향상)
-x test          # 테스트 스킵 (빌드 속도 향상)
--quiet          # 로그 최소화
```

### `.dockerignore` 필수 항목

```
# 백엔드
.gradle/
build/
*.class

# 프론트엔드
node_modules/
dist/
.env
```

→ 빌드 컨텍스트 크기를 144MB → 1MB 수준으로 감소 가능

---

## 5. 참고 자료

| 주제 | URL |
|------|-----|
| Docker 멀티스테이지 빌드 공식 문서 | https://docs.docker.com/build/building/multi-stage/ |
| Docker Compose healthcheck | https://docs.docker.com/compose/compose-file/05-services/#healthcheck |
| Docker 레이어 캐시 최적화 | https://docs.docker.com/build/cache/ |
| Gradle 빌드 옵션 | https://docs.gradle.org/current/userguide/command_line_interface.html |
| Nginx alpine 이미지 | https://hub.docker.com/_/nginx |
| eclipse-temurin JRE | https://hub.docker.com/_/eclipse-temurin |
| npm ci 공식 문서 | https://docs.npmjs.com/cli/v10/commands/npm-ci |
