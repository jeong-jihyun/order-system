#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 3: API Gateway (Spring Cloud Gateway/WebFlux) + account-service (JWT/Security)

주의사항:
- Spring Cloud Gateway = WebFlux 기반 → spring-boot-starter-web 제거 필수
- api-gateway: GlobalFilter(JWT), RateLimiter(Redis), 라우팅, CORS, CircuitBreaker
- account-service: Spring Security + BCrypt + JWT 발급/검증, User/Account 도메인
"""
import os

ROOT = r"d:\order-system"

def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"OK  {os.path.relpath(path, ROOT)}")

# ════════════════════════════════════════════════════════════════
# ① API GATEWAY
# ════════════════════════════════════════════════════════════════
GW   = os.path.join(ROOT, "services", "api-gateway")
GWSRC = os.path.join(GW, "src", "main", "java", "com", "exchange", "gateway")
GWRES = os.path.join(GW, "src", "main", "resources")

# api-gateway build.gradle.kts — spring-boot-starter-web 제거 (WebFlux와 충돌)
write(os.path.join(GW, "build.gradle.kts"), """\
plugins {
    java
    id("org.springframework.boot") version "3.2.3"
    id("io.spring.dependency-management") version "1.1.4"
}

group = "com.exchange"
version = "0.0.1-SNAPSHOT"

java { sourceCompatibility = JavaVersion.VERSION_17 }

repositories { mavenCentral() }

dependencyManagement {
    imports {
        mavenBom("org.springframework.boot:spring-boot-dependencies:3.2.3")
        mavenBom("org.springframework.cloud:spring-cloud-dependencies:2023.0.1")
    }
}

dependencies {
    // Spring Cloud Gateway (WebFlux 기반 — spring-boot-starter-web 사용 불가)
    implementation("org.springframework.cloud:spring-cloud-starter-gateway")

    // Redis (Redis Reactive — Rate Limiter용)
    implementation("org.springframework.boot:spring-boot-starter-data-redis-reactive")

    // Actuator
    implementation("org.springframework.boot:spring-boot-starter-actuator")

    // JWT 검증
    implementation("com.auth0:java-jwt:4.4.0")

    // Circuit Breaker
    implementation("org.springframework.cloud:spring-cloud-starter-circuitbreaker-reactor-resilience4j")

    // Jackson (WebFlux에서 JSON)
    implementation("com.fasterxml.jackson.core:jackson-databind")
    implementation("com.fasterxml.jackson.datatype:jackson-datatype-jsr310")

    // Lombok
    compileOnly("org.projectlombok:lombok")
    annotationProcessor("org.projectlombok:lombok")

    // Test
    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("io.projectreactor:reactor-test")
}

tasks.withType<Test> { useJUnitPlatform() }
""")

# application.yml
write(os.path.join(GWRES, "application.yml"), """\
spring:
  application:
    name: api-gateway

  data:
    redis:
      host: ${SPRING_DATA_REDIS_HOST:localhost}
      port: ${SPRING_DATA_REDIS_PORT:6379}

  cloud:
    gateway:
      # 전역 CORS
      globalcors:
        cors-configurations:
          '[/**]':
            allowedOrigins: "*"
            allowedMethods: [GET, POST, PUT, PATCH, DELETE, OPTIONS]
            allowedHeaders: "*"
            maxAge: 3600

      # 기본 필터 (모든 라우트 적용)
      default-filters:
        - name: RequestRateLimiter
          args:
            redis-rate-limiter.replenishRate: 10    # 초당 10 요청 허용
            redis-rate-limiter.burstCapacity: 20    # 순간 최대 20
            redis-rate-limiter.requestedTokens: 1
            key-resolver: "#{@ipKeyResolver}"

      routes:
        # ── account-service (인증 불필요 — public)
        - id: auth-public
          uri: http://localhost:8082
          predicates:
            - Path=/api/v1/auth/**
          filters:
            - name: CircuitBreaker
              args:
                name: account-service-cb
                fallbackUri: forward:/fallback

        # ── account-service (인증 필요)
        - id: account-service
          uri: http://localhost:8082
          predicates:
            - Path=/api/v1/accounts/**
          filters:
            - JwtAuthentication
            - name: CircuitBreaker
              args:
                name: account-service-cb
                fallbackUri: forward:/fallback

        # ── order-service (인증 필요)
        - id: order-service
          uri: http://localhost:8081
          predicates:
            - Path=/api/v1/orders/**
          filters:
            - JwtAuthentication
            - name: CircuitBreaker
              args:
                name: order-service-cb
                fallbackUri: forward:/fallback

        # ── market-data-service (인증 불필요 — 공개 시세)
        - id: market-data-service
          uri: http://localhost:8083
          predicates:
            - Path=/api/v1/market/**

        # ── WebSocket (시세 스트림)
        - id: market-ws
          uri: ws://localhost:8083
          predicates:
            - Path=/ws/**

server:
  port: 8080

management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics,gateway
  endpoint:
    health:
      show-details: always

# Circuit Breaker 설정
resilience4j:
  circuitbreaker:
    instances:
      order-service-cb:
        slidingWindowSize: 10
        failureRateThreshold: 50
        waitDurationInOpenState: 10s
      account-service-cb:
        slidingWindowSize: 10
        failureRateThreshold: 50
        waitDurationInOpenState: 10s

jwt:
  secret: ${JWT_SECRET:order-system-jwt-secret-key-must-be-at-least-256-bits-long}

logging:
  level:
    com.exchange.gateway: DEBUG
    org.springframework.cloud.gateway: WARN
""")

# ApiGatewayApplication.java
write(os.path.join(GWSRC, "ApiGatewayApplication.java"), """\
package com.exchange.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * API Gateway — 모든 클라이언트 요청의 단일 진입점
 * - Port: 8080
 * - Spring Cloud Gateway (Reactive/WebFlux)
 * - JWT 인증, Rate Limiting, Circuit Breaker
 */
@SpringBootApplication
public class ApiGatewayApplication {
    public static void main(String[] args) {
        SpringApplication.run(ApiGatewayApplication.class, args);
    }
}
""")

# JWT 유틸
write(os.path.join(GWSRC, "security", "JwtUtil.java"), """\
package com.exchange.gateway.security;

import com.auth0.jwt.JWT;
import com.auth0.jwt.algorithms.Algorithm;
import com.auth0.jwt.exceptions.JWTVerificationException;
import com.auth0.jwt.interfaces.DecodedJWT;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * JWT 검증 유틸 (Gateway — 발급하지 않고 검증만 수행)
 */
@Component
public class JwtUtil {

    @Value("${jwt.secret}")
    private String secret;

    public DecodedJWT verify(String token) throws JWTVerificationException {
        return JWT.require(Algorithm.HMAC256(secret))
                .withIssuer("exchange")
                .build()
                .verify(token);
    }

    public String extractUsername(String token) {
        return verify(token).getSubject();
    }

    public String extractRole(String token) {
        return verify(token).getClaim("role").asString();
    }
}
""")

# JWT 인증 GlobalFilter
write(os.path.join(GWSRC, "filter", "JwtAuthenticationFilter.java"), """\
package com.exchange.gateway.filter;

import com.auth0.jwt.exceptions.JWTVerificationException;
import com.auth0.jwt.interfaces.DecodedJWT;
import com.exchange.gateway.security.JwtUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilter;
import org.springframework.cloud.gateway.filter.factory.AbstractGatewayFilterFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

/**
 * JWT 인증 GatewayFilterFactory
 *
 * 동작:
 * 1. Authorization: Bearer {token} 헤더 추출
 * 2. JWT 서명/만료 검증
 * 3. 성공 → X-User-Name, X-User-Role 헤더를 하위 서비스에 전달
 * 4. 실패 → 401 Unauthorized 즉시 반환
 *
 * 설정: application.yml 라우트의 filters 에 "JwtAuthentication" 으로 적용
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class JwtAuthenticationFilter
        extends AbstractGatewayFilterFactory<JwtAuthenticationFilter.Config> {

    private final JwtUtil jwtUtil;

    public JwtAuthenticationFilter() {
        super(Config.class);
        this.jwtUtil = null; // Spring이 주입
    }

    @Override
    public GatewayFilter apply(Config config) {
        return (exchange, chain) -> {
            String authHeader = exchange.getRequest()
                    .getHeaders().getFirst(HttpHeaders.AUTHORIZATION);

            if (authHeader == null || !authHeader.startsWith("Bearer ")) {
                return unauthorized(exchange, "Authorization 헤더가 없습니다.");
            }

            String token = authHeader.substring(7);
            try {
                DecodedJWT jwt = jwtUtil.verify(token);
                String username = jwt.getSubject();
                String role     = jwt.getClaim("role").asString();

                // 하위 서비스에 사용자 정보 전달 (헤더 위조 방지: 클라이언트 헤더 제거 후 재설정)
                ServerWebExchange mutated = exchange.mutate()
                        .request(r -> r.headers(headers -> {
                            headers.remove("X-User-Name");
                            headers.remove("X-User-Role");
                            headers.add("X-User-Name", username);
                            headers.add("X-User-Role", role != null ? role : "USER");
                        }))
                        .build();

                log.debug("[Gateway] JWT 인증 성공 — user={}, role={}", username, role);
                return chain.filter(mutated);

            } catch (JWTVerificationException e) {
                log.warn("[Gateway] JWT 인증 실패 — {}", e.getMessage());
                return unauthorized(exchange, "유효하지 않은 토큰입니다.");
            }
        };
    }

    private Mono<Void> unauthorized(ServerWebExchange exchange, String message) {
        exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
        exchange.getResponse().getHeaders().add("Content-Type", "application/json");
        var buffer = exchange.getResponse().bufferFactory()
                .wrap(("{\"success\":false,\"message\":\"" + message + "\"}").getBytes());
        return exchange.getResponse().writeWith(Mono.just(buffer));
    }

    public static class Config {}
}
""")

# Rate Limiter Key Resolver
write(os.path.join(GWSRC, "config", "RateLimiterConfig.java"), """\
package com.exchange.gateway.config;

import org.springframework.cloud.gateway.filter.ratelimit.KeyResolver;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import reactor.core.publisher.Mono;

/**
 * Rate Limiter — IP 기반 키 추출
 * application.yml default-filters.RequestRateLimiter 에서 #{@ipKeyResolver} 참조
 */
@Configuration
public class RateLimiterConfig {

    @Bean
    public KeyResolver ipKeyResolver() {
        return exchange -> {
            String ip = exchange.getRequest().getRemoteAddress() != null
                    ? exchange.getRequest().getRemoteAddress().getAddress().getHostAddress()
                    : "unknown";
            return Mono.just(ip);
        };
    }
}
""")

# Fallback Controller (WebFlux)
write(os.path.join(GWSRC, "controller", "FallbackController.java"), """\
package com.exchange.gateway.controller;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.Map;

/**
 * Circuit Breaker Fallback — 하위 서비스 장애 시 기본 응답 반환
 */
@RestController
public class FallbackController {

    @RequestMapping("/fallback")
    public Mono<Map<String, Object>> fallback(ServerWebExchange exchange) {
        exchange.getResponse().setStatusCode(HttpStatus.SERVICE_UNAVAILABLE);
        return Mono.just(Map.of(
                "success", false,
                "message", "서비스가 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해주세요.",
                "status", 503
        ));
    }
}
""")

print("  api-gateway 파일 생성 완료")

# ════════════════════════════════════════════════════════════════
# ② ACCOUNT SERVICE
# ════════════════════════════════════════════════════════════════
ACC  = os.path.join(ROOT, "services", "account-service")
ASRC = os.path.join(ACC, "src", "main", "java", "com", "exchange", "account")
ARES = os.path.join(ACC, "src", "main", "resources")

# build.gradle.kts
write(os.path.join(ACC, "build.gradle.kts"), """\
plugins {
    java
    id("org.springframework.boot") version "3.2.3"
    id("io.spring.dependency-management") version "1.1.4"
}

group = "com.exchange"
version = "0.0.1-SNAPSHOT"

java { sourceCompatibility = JavaVersion.VERSION_17 }

repositories { mavenCentral() }

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.springframework.boot:spring-boot-starter-security")
    implementation("org.springframework.boot:spring-boot-starter-data-redis")
    implementation("org.springframework.boot:spring-boot-starter-cache")

    // MySQL
    runtimeOnly("com.mysql:mysql-connector-j")

    // JWT
    implementation("com.auth0:java-jwt:4.4.0")

    // Kafka
    implementation("org.springframework.kafka:spring-kafka")

    // Jackson
    implementation("com.fasterxml.jackson.core:jackson-databind")
    implementation("com.fasterxml.jackson.datatype:jackson-datatype-jsr310")

    // Swagger
    implementation("org.springdoc:springdoc-openapi-starter-webmvc-ui:2.3.0")

    // Lombok
    compileOnly("org.projectlombok:lombok")
    annotationProcessor("org.projectlombok:lombok")

    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.springframework.security:spring-security-test")
}

tasks.withType<Test> { useJUnitPlatform() }
""")

# application.yml
write(os.path.join(ARES, "application.yml"), """\
spring:
  application:
    name: account-service

  datasource:
    url: ${SPRING_DATASOURCE_URL:jdbc:mysql://localhost:3306/accountdb?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC}
    username: ${SPRING_DATASOURCE_USERNAME:orderuser}
    password: ${SPRING_DATASOURCE_PASSWORD:orderpassword}
    driver-class-name: com.mysql.cj.jdbc.Driver

  jpa:
    hibernate:
      ddl-auto: update
    show-sql: false
    properties:
      hibernate:
        dialect: org.hibernate.dialect.MySQL8Dialect

  data:
    redis:
      host: ${SPRING_DATA_REDIS_HOST:localhost}
      port: ${SPRING_DATA_REDIS_PORT:6379}

  cache:
    type: redis

  kafka:
    bootstrap-servers: ${SPRING_KAFKA_BOOTSTRAP_SERVERS:localhost:9092}
    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.springframework.kafka.support.serializer.JsonSerializer

server:
  port: 8082

management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics
  endpoint:
    health:
      show-details: always

jwt:
  secret: ${JWT_SECRET:order-system-jwt-secret-key-must-be-at-least-256-bits-long}
  expiration-hours: 24

logging:
  level:
    com.exchange.account: DEBUG
    org.springframework.security: WARN
""")

# AccountServiceApplication.java
write(os.path.join(ASRC, "AccountServiceApplication.java"), """\
package com.exchange.account;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * Account Service — 사용자 인증 + 계좌/잔고 관리
 * - Port: 8082
 * - JWT 발급/검증
 * - Spring Security (BCrypt 비밀번호)
 */
@SpringBootApplication
@EnableAsync
public class AccountServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(AccountServiceApplication.class, args);
    }
}
""")

# ── User 도메인 엔티티
write(os.path.join(ASRC, "domain", "user", "entity", "UserRole.java"), """\
package com.exchange.account.domain.user.entity;

public enum UserRole {
    USER,    // 일반 투자자
    ADMIN,   // 관리자
    TRADER   // 전문 트레이더
}
""")

write(os.path.join(ASRC, "domain", "user", "entity", "User.java"), """\
package com.exchange.account.domain.user.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.LocalDateTime;

@Entity
@Table(name = "users",
       uniqueConstraints = @UniqueConstraint(columnNames = "username"))
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 50)
    private String username;

    @Column(nullable = false)
    private String password; // BCrypt 해시

    @Column(nullable = false, length = 100)
    private String email;

    @Column(nullable = false, length = 100)
    private String fullName;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    @Builder.Default
    private UserRole role = UserRole.USER;

    @Column(nullable = false)
    @Builder.Default
    private boolean enabled = true;

    @CreationTimestamp
    @Column(updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;

    public void changePassword(String encodedPassword) {
        this.password = encodedPassword;
    }
}
""")

# ── Account 도메인 엔티티
write(os.path.join(ASRC, "domain", "account", "entity", "AccountType.java"), """\
package com.exchange.account.domain.account.entity;

public enum AccountType {
    CASH,       // 현금 계좌
    STOCK,      // 주식 계좌
    DERIVATIVE  // 파생 상품 계좌
}
""")

write(os.path.join(ASRC, "domain", "account", "entity", "Account.java"), """\
package com.exchange.account.domain.account.entity;

import com.exchange.account.domain.user.entity.User;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "accounts")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
public class Account {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(nullable = false, unique = true, length = 20)
    private String accountNumber;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    @Builder.Default
    private AccountType accountType = AccountType.CASH;

    @Column(nullable = false, precision = 18, scale = 2)
    @Builder.Default
    private BigDecimal balance = BigDecimal.ZERO;

    @Column(nullable = false, precision = 18, scale = 2)
    @Builder.Default
    private BigDecimal frozenBalance = BigDecimal.ZERO; // 주문 중 동결 금액

    @Column(nullable = false)
    @Builder.Default
    private boolean active = true;

    @CreationTimestamp
    @Column(updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;

    /**
     * 잔고 입금
     */
    public void deposit(BigDecimal amount) {
        if (amount.compareTo(BigDecimal.ZERO) <= 0)
            throw new IllegalArgumentException("입금 금액은 양수여야 합니다.");
        this.balance = this.balance.add(amount);
    }

    /**
     * 잔고 출금 — 가용 잔고(balance - frozenBalance) 기준 검증
     */
    public void withdraw(BigDecimal amount) {
        if (amount.compareTo(BigDecimal.ZERO) <= 0)
            throw new IllegalArgumentException("출금 금액은 양수여야 합니다.");
        BigDecimal available = this.balance.subtract(this.frozenBalance);
        if (available.compareTo(amount) < 0)
            throw new IllegalStateException("잔고가 부족합니다. 가용잔고=" + available);
        this.balance = this.balance.subtract(amount);
    }

    /**
     * 주문용 잔고 동결 (주문 접수 시)
     */
    public void freeze(BigDecimal amount) {
        BigDecimal available = this.balance.subtract(this.frozenBalance);
        if (available.compareTo(amount) < 0)
            throw new IllegalStateException("동결 가능 잔고가 부족합니다.");
        this.frozenBalance = this.frozenBalance.add(amount);
    }

    /**
     * 동결 해제 (주문 취소/체결 완료 시)
     */
    public void unfreeze(BigDecimal amount) {
        if (this.frozenBalance.compareTo(amount) < 0)
            throw new IllegalStateException("동결 잔고보다 큰 금액을 해제할 수 없습니다.");
        this.frozenBalance = this.frozenBalance.subtract(amount);
    }
}
""")

# ── Repository
write(os.path.join(ASRC, "domain", "user", "repository", "UserRepository.java"), """\
package com.exchange.account.domain.user.repository;

import com.exchange.account.domain.user.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByUsername(String username);
    boolean existsByUsername(String username);
    boolean existsByEmail(String email);
}
""")

write(os.path.join(ASRC, "domain", "account", "repository", "AccountRepository.java"), """\
package com.exchange.account.domain.account.repository;

import com.exchange.account.domain.account.entity.Account;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;

import jakarta.persistence.LockModeType;
import java.util.List;
import java.util.Optional;

public interface AccountRepository extends JpaRepository<Account, Long> {
    List<Account> findByUserId(Long userId);
    Optional<Account> findByAccountNumber(String accountNumber);

    /** 잔고 변경 시 비관적 잠금 — 동시 출금 방지 */
    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT a FROM Account a WHERE a.id = :id")
    Optional<Account> findByIdForUpdate(Long id);
}
""")

# ── JWT Provider
write(os.path.join(ASRC, "security", "JwtProvider.java"), """\
package com.exchange.account.security;

import com.auth0.jwt.JWT;
import com.auth0.jwt.algorithms.Algorithm;
import com.auth0.jwt.exceptions.JWTVerificationException;
import com.auth0.jwt.interfaces.DecodedJWT;
import com.exchange.account.domain.user.entity.User;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.Date;

/**
 * JWT 발급 + 검증
 * HMAC256 서명, 24시간 만료, issuer = "exchange"
 */
@Component
public class JwtProvider {

    @Value("${jwt.secret}")
    private String secret;

    @Value("${jwt.expiration-hours:24}")
    private long expirationHours;

    public String generateToken(User user) {
        long now = System.currentTimeMillis();
        return JWT.create()
                .withIssuer("exchange")
                .withSubject(user.getUsername())
                .withClaim("role", user.getRole().name())
                .withClaim("userId", user.getId())
                .withIssuedAt(new Date(now))
                .withExpiresAt(new Date(now + expirationHours * 3600_000L))
                .sign(Algorithm.HMAC256(secret));
    }

    public DecodedJWT verify(String token) throws JWTVerificationException {
        return JWT.require(Algorithm.HMAC256(secret))
                .withIssuer("exchange")
                .build()
                .verify(token);
    }

    public String extractUsername(String token) {
        return verify(token).getSubject();
    }
}
""")

# ── Spring Security 필터
write(os.path.join(ASRC, "security", "JwtAuthenticationFilter.java"), """\
package com.exchange.account.security;

import com.auth0.jwt.exceptions.JWTVerificationException;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;

/**
 * account-service 내부용 JWT 필터
 * API Gateway를 통한 요청은 X-User-Name 헤더로 사용자 식별 (재검증 불필요 가능)
 * 직접 호출 시에는 Bearer 토큰으로 검증
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtProvider jwtProvider;

    @Override
    protected void doFilterInternal(HttpServletRequest request,
                                    HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        // Gateway에서 전달한 X-User-Name 헤더 우선 처리
        String gatewayUser = request.getHeader("X-User-Name");
        String gatewayRole = request.getHeader("X-User-Role");
        if (gatewayUser != null) {
            String role = gatewayRole != null ? "ROLE_" + gatewayRole : "ROLE_USER";
            UsernamePasswordAuthenticationToken auth =
                    new UsernamePasswordAuthenticationToken(
                            gatewayUser, null, List.of(new SimpleGrantedAuthority(role)));
            SecurityContextHolder.getContext().setAuthentication(auth);
            chain.doFilter(request, response);
            return;
        }

        // 직접 호출 시 Bearer 토큰 검증
        String header = request.getHeader("Authorization");
        if (header != null && header.startsWith("Bearer ")) {
            try {
                String token = header.substring(7);
                String username = jwtProvider.extractUsername(token);
                String roleClaim = jwtProvider.verify(token).getClaim("role").asString();
                UsernamePasswordAuthenticationToken auth =
                        new UsernamePasswordAuthenticationToken(
                                username, null,
                                List.of(new SimpleGrantedAuthority("ROLE_" + roleClaim)));
                SecurityContextHolder.getContext().setAuthentication(auth);
            } catch (JWTVerificationException e) {
                log.warn("[AccountService] JWT 검증 실패: {}", e.getMessage());
                SecurityContextHolder.clearContext();
            }
        }
        chain.doFilter(request, response);
    }
}
""")

# ── Security Config
write(os.path.join(ASRC, "config", "SecurityConfig.java"), """\
package com.exchange.account.config;

import com.exchange.account.security.JwtAuthenticationFilter;
import lombok.RequiredArgsConstructor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
@EnableWebSecurity
@RequiredArgsConstructor
public class SecurityConfig {

    private final JwtAuthenticationFilter jwtAuthenticationFilter;

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(csrf -> csrf.disable())
            .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                .requestMatchers("/api/v1/auth/**").permitAll()
                .requestMatchers("/actuator/**").permitAll()
                .requestMatchers("/swagger-ui/**", "/api-docs/**").permitAll()
                .anyRequest().authenticated()
            )
            .addFilterBefore(jwtAuthenticationFilter,
                             UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
""")

# ── Redis Config
write(os.path.join(ASRC, "config", "RedisConfig.java"), """\
package com.exchange.account.config;

import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.cache.RedisCacheManager;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import java.time.Duration;

@EnableCaching
@Configuration
public class RedisConfig {

    @Bean
    public RedisCacheManager cacheManager(RedisConnectionFactory factory) {
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofMinutes(30))
                .serializeKeysWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(new StringRedisSerializer()))
                .serializeValuesWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(new GenericJackson2JsonRedisSerializer()));
        return RedisCacheManager.builder(factory).cacheDefaults(config).build();
    }
}
""")

# ── DTOs
write(os.path.join(ASRC, "domain", "user", "dto", "SignUpRequest.java"), """\
package com.exchange.account.domain.user.dto;

import jakarta.validation.constraints.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class SignUpRequest {

    @NotBlank(message = "사용자명은 필수입니다")
    @Size(min = 3, max = 50, message = "사용자명은 3~50자여야 합니다")
    @Pattern(regexp = "^[a-zA-Z0-9_]+$", message = "사용자명은 영문/숫자/_만 가능합니다")
    private String username;

    @NotBlank(message = "비밀번호는 필수입니다")
    @Size(min = 8, max = 100, message = "비밀번호는 8자 이상이어야 합니다")
    private String password;

    @NotBlank(message = "이메일은 필수입니다")
    @Email(message = "유효한 이메일 형식이어야 합니다")
    private String email;

    @NotBlank(message = "이름은 필수입니다")
    @Size(max = 100, message = "이름은 100자 이하여야 합니다")
    private String fullName;
}
""")

write(os.path.join(ASRC, "domain", "user", "dto", "LoginRequest.java"), """\
package com.exchange.account.domain.user.dto;

import jakarta.validation.constraints.NotBlank;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class LoginRequest {

    @NotBlank(message = "사용자명은 필수입니다")
    private String username;

    @NotBlank(message = "비밀번호는 필수입니다")
    private String password;
}
""")

write(os.path.join(ASRC, "domain", "user", "dto", "AuthResponse.java"), """\
package com.exchange.account.domain.user.dto;

import com.exchange.account.domain.user.entity.UserRole;
import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class AuthResponse {
    private String accessToken;
    private String tokenType;
    private Long userId;
    private String username;
    private UserRole role;
    private long expiresIn; // 초 단위

    public static AuthResponse of(String token, Long userId, String username, UserRole role) {
        return AuthResponse.builder()
                .accessToken(token)
                .tokenType("Bearer")
                .userId(userId)
                .username(username)
                .role(role)
                .expiresIn(86400L) // 24시간
                .build();
    }
}
""")

write(os.path.join(ASRC, "domain", "account", "dto", "AccountResponse.java"), """\
package com.exchange.account.domain.account.dto;

import com.exchange.account.domain.account.entity.Account;
import com.exchange.account.domain.account.entity.AccountType;
import lombok.Builder;
import lombok.Getter;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Getter
@Builder
public class AccountResponse {
    private Long id;
    private String accountNumber;
    private AccountType accountType;
    private BigDecimal balance;
    private BigDecimal frozenBalance;
    private BigDecimal availableBalance;
    private boolean active;
    private LocalDateTime createdAt;

    public static AccountResponse from(Account account) {
        return AccountResponse.builder()
                .id(account.getId())
                .accountNumber(account.getAccountNumber())
                .accountType(account.getAccountType())
                .balance(account.getBalance())
                .frozenBalance(account.getFrozenBalance())
                .availableBalance(account.getBalance().subtract(account.getFrozenBalance()))
                .active(account.isActive())
                .createdAt(account.getCreatedAt())
                .build();
    }
}
""")

write(os.path.join(ASRC, "domain", "account", "dto", "BalanceRequest.java"), """\
package com.exchange.account.domain.account.dto;

import jakarta.validation.constraints.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.math.BigDecimal;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class BalanceRequest {

    @NotNull(message = "금액은 필수입니다")
    @DecimalMin(value = "0.01", message = "금액은 0.01 이상이어야 합니다")
    @DecimalMax(value = "1000000000", message = "금액은 10억 이하여야 합니다")
    private BigDecimal amount;
}
""")

# ── AuthService
write(os.path.join(ASRC, "domain", "user", "service", "AuthService.java"), """\
package com.exchange.account.domain.user.service;

import com.exchange.account.domain.account.entity.Account;
import com.exchange.account.domain.account.entity.AccountType;
import com.exchange.account.domain.account.repository.AccountRepository;
import com.exchange.account.domain.user.dto.AuthResponse;
import com.exchange.account.domain.user.dto.LoginRequest;
import com.exchange.account.domain.user.dto.SignUpRequest;
import com.exchange.account.domain.user.entity.User;
import com.exchange.account.domain.user.repository.UserRepository;
import com.exchange.account.security.JwtProvider;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

/**
 * 회원가입 + 로그인 서비스
 * 회원 생성 시 기본 CASH 계좌 자동 생성
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional
public class AuthService {

    private final UserRepository userRepository;
    private final AccountRepository accountRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtProvider jwtProvider;

    public AuthResponse signUp(SignUpRequest request) {
        if (userRepository.existsByUsername(request.getUsername())) {
            throw new IllegalArgumentException("이미 사용 중인 사용자명입니다: " + request.getUsername());
        }
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new IllegalArgumentException("이미 사용 중인 이메일입니다.");
        }

        User user = User.builder()
                .username(request.getUsername())
                .password(passwordEncoder.encode(request.getPassword()))
                .email(request.getEmail())
                .fullName(request.getFullName())
                .build();
        User saved = userRepository.save(user);

        // 기본 현금 계좌 자동 생성
        Account account = Account.builder()
                .user(saved)
                .accountNumber(generateAccountNumber())
                .accountType(AccountType.CASH)
                .build();
        accountRepository.save(account);

        log.info("[회원가입] userId={}, username={}", saved.getId(), saved.getUsername());
        String token = jwtProvider.generateToken(saved);
        return AuthResponse.of(token, saved.getId(), saved.getUsername(), saved.getRole());
    }

    @Transactional(readOnly = true)
    public AuthResponse login(LoginRequest request) {
        User user = userRepository.findByUsername(request.getUsername())
                .orElseThrow(() -> new IllegalArgumentException("사용자를 찾을 수 없습니다."));

        if (!user.isEnabled()) {
            throw new IllegalStateException("비활성화된 계정입니다.");
        }
        if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            throw new IllegalArgumentException("비밀번호가 일치하지 않습니다.");
        }

        log.info("[로그인] userId={}, username={}", user.getId(), user.getUsername());
        String token = jwtProvider.generateToken(user);
        return AuthResponse.of(token, user.getId(), user.getUsername(), user.getRole());
    }

    private String generateAccountNumber() {
        // ACC + 8자리 UUID 앞부분
        return "ACC" + UUID.randomUUID().toString().replace("-", "").substring(0, 8).toUpperCase();
    }
}
""")

# ── AccountService
write(os.path.join(ASRC, "domain", "account", "service", "AccountService.java"), """\
package com.exchange.account.domain.account.service;

import com.exchange.account.domain.account.dto.AccountResponse;
import com.exchange.account.domain.account.dto.BalanceRequest;
import com.exchange.account.domain.account.repository.AccountRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
@Transactional
public class AccountService {

    private final AccountRepository accountRepository;

    @Transactional(readOnly = true)
    public List<AccountResponse> getMyAccounts(Long userId) {
        return accountRepository.findByUserId(userId).stream()
                .map(AccountResponse::from)
                .toList();
    }

    @Transactional(readOnly = true)
    public AccountResponse getAccount(Long accountId) {
        return accountRepository.findById(accountId)
                .map(AccountResponse::from)
                .orElseThrow(() -> new IllegalArgumentException("계좌를 찾을 수 없습니다. id=" + accountId));
    }

    public AccountResponse deposit(Long accountId, BalanceRequest request) {
        var account = accountRepository.findByIdForUpdate(accountId)
                .orElseThrow(() -> new IllegalArgumentException("계좌를 찾을 수 없습니다."));
        account.deposit(request.getAmount());
        log.info("[입금] accountId={}, amount={}", accountId, request.getAmount());
        return AccountResponse.from(accountRepository.save(account));
    }

    public AccountResponse withdraw(Long accountId, BalanceRequest request) {
        var account = accountRepository.findByIdForUpdate(accountId)
                .orElseThrow(() -> new IllegalArgumentException("계좌를 찾을 수 없습니다."));
        account.withdraw(request.getAmount());
        log.info("[출금] accountId={}, amount={}", accountId, request.getAmount());
        return AccountResponse.from(accountRepository.save(account));
    }
}
""")

# ── 공통 응답
write(os.path.join(ASRC, "common", "response", "ApiResponse.java"), """\
package com.exchange.account.common.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.Getter;

@Getter
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ApiResponse<T> {
    private final boolean success;
    private final String message;
    private final T data;

    private ApiResponse(boolean success, String message, T data) {
        this.success = success;
        this.message = message;
        this.data = data;
    }

    public static <T> ApiResponse<T> success(T data) {
        return new ApiResponse<>(true, "성공", data);
    }

    public static <T> ApiResponse<T> success(String message, T data) {
        return new ApiResponse<>(true, message, data);
    }

    public static <T> ApiResponse<T> error(String message) {
        return new ApiResponse<>(false, message, null);
    }
}
""")

# ── 공통 예외 핸들러
write(os.path.join(ASRC, "common", "exception", "GlobalExceptionHandler.java"), """\
package com.exchange.account.common.exception;

import com.exchange.account.common.response.ApiResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ApiResponse<Void>> handleIllegalArgument(IllegalArgumentException e) {
        return ResponseEntity.badRequest().body(ApiResponse.error(e.getMessage()));
    }

    @ExceptionHandler(IllegalStateException.class)
    public ResponseEntity<ApiResponse<Void>> handleIllegalState(IllegalStateException e) {
        return ResponseEntity.badRequest().body(ApiResponse.error(e.getMessage()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<Void>> handleValidation(MethodArgumentNotValidException e) {
        String msg = e.getBindingResult().getFieldErrors().stream()
                .map(fe -> fe.getField() + ": " + fe.getDefaultMessage())
                .findFirst().orElse("유효성 검사 실패");
        return ResponseEntity.badRequest().body(ApiResponse.error(msg));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Void>> handleGeneral(Exception e) {
        log.error("[서버 오류]", e);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ApiResponse.error("서버 내부 오류가 발생했습니다."));
    }
}
""")

# ── Controllers
write(os.path.join(ASRC, "domain", "user", "controller", "AuthController.java"), """\
package com.exchange.account.domain.user.controller;

import com.exchange.account.common.response.ApiResponse;
import com.exchange.account.domain.user.dto.AuthResponse;
import com.exchange.account.domain.user.dto.LoginRequest;
import com.exchange.account.domain.user.dto.SignUpRequest;
import com.exchange.account.domain.user.service.AuthService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@Tag(name = "Auth API", description = "회원가입 / 로그인")
@RestController
@RequestMapping("/api/v1/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @Operation(summary = "회원가입")
    @PostMapping("/signup")
    public ResponseEntity<ApiResponse<AuthResponse>> signUp(
            @Valid @RequestBody SignUpRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.success("회원가입이 완료되었습니다.", authService.signUp(request)));
    }

    @Operation(summary = "로그인")
    @PostMapping("/login")
    public ResponseEntity<ApiResponse<AuthResponse>> login(
            @Valid @RequestBody LoginRequest request) {
        return ResponseEntity.ok(
                ApiResponse.success("로그인 성공", authService.login(request)));
    }
}
""")

write(os.path.join(ASRC, "domain", "account", "controller", "AccountController.java"), """\
package com.exchange.account.domain.account.controller;

import com.exchange.account.common.response.ApiResponse;
import com.exchange.account.domain.account.dto.AccountResponse;
import com.exchange.account.domain.account.dto.BalanceRequest;
import com.exchange.account.domain.account.service.AccountService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Tag(name = "Account API", description = "계좌/잔고 관리")
@RestController
@RequestMapping("/api/v1/accounts")
@RequiredArgsConstructor
public class AccountController {

    private final AccountService accountService;

    @Operation(summary = "내 계좌 목록 조회")
    @GetMapping("/me")
    public ResponseEntity<ApiResponse<List<AccountResponse>>> getMyAccounts(
            @RequestHeader("X-User-Name") String username,
            @RequestHeader(value = "X-User-Role", defaultValue = "USER") String role) {
        // Gateway에서 X-User-Name 헤더로 전달된 userId 기반 조회
        // Phase 3에서는 username → userId 조회 구현 예정
        return ResponseEntity.ok(ApiResponse.success(List.of()));
    }

    @Operation(summary = "계좌 단건 조회")
    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<AccountResponse>> getAccount(@PathVariable Long id) {
        return ResponseEntity.ok(ApiResponse.success(accountService.getAccount(id)));
    }

    @Operation(summary = "입금")
    @PostMapping("/{id}/deposit")
    public ResponseEntity<ApiResponse<AccountResponse>> deposit(
            @PathVariable Long id,
            @Valid @RequestBody BalanceRequest request) {
        return ResponseEntity.ok(ApiResponse.success("입금 완료", accountService.deposit(id, request)));
    }

    @Operation(summary = "출금")
    @PostMapping("/{id}/withdraw")
    public ResponseEntity<ApiResponse<AccountResponse>> withdraw(
            @PathVariable Long id,
            @Valid @RequestBody BalanceRequest request) {
        return ResponseEntity.ok(ApiResponse.success("출금 완료", accountService.withdraw(id, request)));
    }
}
""")

print("  account-service 파일 생성 완료")
print()
print("=== Phase 3 생성 완료 ===")
print("다음 단계:")
print("  1. ./gradlew.bat :services:api-gateway:compileJava")
print("  2. ./gradlew.bat :services:account-service:compileJava")
