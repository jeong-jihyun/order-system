# ─────────────────────────────────────────────
# 멀티 스테이지 빌드
# Stage 1: Gradle로 빌드
# Stage 2: 경량 JRE 이미지로 실행
# ─────────────────────────────────────────────

FROM gradle:8.5-jdk17-alpine AS builder
WORKDIR /app

# 의존성 레이어 캐싱 최적화 (소스 변경 없으면 캐시 재사용)
COPY build.gradle.kts settings.gradle.kts ./
RUN gradle dependencies --no-daemon --quiet --no-watch-fs 2>/dev/null || true

COPY src ./src
RUN gradle bootJar --no-daemon --no-watch-fs -x test

# ─────────────────────────────────────────────
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app

COPY --from=builder /app/build/libs/*.jar app.jar

EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
