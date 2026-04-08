# ============================================================
# 멀티 스테이지 Dockerfile — 모든 마이크로서비스 공용
# 사용법 (docker-compose.yml에서):
#   build:
#     context: .              ← 프로젝트 루트
#     dockerfile: docker/Dockerfile
#     args:
#       SERVICE_DIR: order-service
#       JAR_NAME: order-service
# ============================================================

# ────────────────────────────────────────
# Stage 1: Build
# ────────────────────────────────────────
FROM eclipse-temurin:17-jdk-alpine AS builder

WORKDIR /workspace

ARG SERVICE_DIR
ARG JAR_NAME

# Gradle Wrapper 복사 (캐시 최적화: 소스보다 먼저)
COPY gradlew gradlew
COPY gradle gradle
COPY build.gradle.kts settings.gradle.kts ./

# 서비스 디렉토리만 복사 (모노레포 — 필요한 서비스만)
COPY services/${SERVICE_DIR} services/${SERVICE_DIR}
COPY shared shared

# 실행 권한 부여 및 빌드 (테스트 제외, 데몬 비활성화)
RUN chmod +x gradlew && \
    ./gradlew :services:${SERVICE_DIR}:bootJar -x test --no-daemon

# 빌드된 JAR 경로를 표준화
RUN cp services/${SERVICE_DIR}/build/libs/${JAR_NAME}*.jar app.jar

# ────────────────────────────────────────
# Stage 2: Runtime
# ────────────────────────────────────────
FROM eclipse-temurin:17-jre-alpine AS runtime

# 보안: non-root 사용자 생성
RUN addgroup -S appgroup && adduser -S appuser -G appgroup

WORKDIR /app

COPY --from=builder /workspace/app.jar app.jar

# 소유권 변경
RUN chown appuser:appgroup app.jar

USER appuser

# JVM 튜닝:
#   -XX:+UseContainerSupport    — Docker 컨테이너 CPU/메모리 자동 감지
#   -XX:MaxRAMPercentage=75.0   — 컨테이너 메모리의 75% 사용
#   -Djava.security.egd=...     — 난수 초기화 속도 개선 (SecureRandom)
ENTRYPOINT ["java", \
    "-XX:+UseContainerSupport", \
    "-XX:MaxRAMPercentage=75.0", \
    "-Djava.security.egd=file:/dev/./urandom", \
    "-jar", "app.jar"]
