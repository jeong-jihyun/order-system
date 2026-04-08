#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 1: 마이크로서비스 뼈대 + shared/common-lib 일괄 생성"""

import os

ROOT = r"d:\order-system"

# ──────────────────────────────────────────────────────────────────
# 유틸
# ──────────────────────────────────────────────────────────────────
def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"OK  {os.path.relpath(path, ROOT)}")


# ──────────────────────────────────────────────────────────────────
# 1. shared/common-lib — 공통 이벤트/DTO/응답 클래스
# ──────────────────────────────────────────────────────────────────
COMMON = os.path.join(ROOT, "shared", "common-lib", "src", "main", "java", "com", "exchange", "common")

write(os.path.join(ROOT, "shared", "common-lib", "build.gradle.kts"), """\
plugins {
    java
    id("org.springframework.boot") version "3.2.3" apply false
    id("io.spring.dependency-management") version "1.1.4"
}

group = "com.exchange"
version = "0.0.1-SNAPSHOT"

java { sourceCompatibility = JavaVersion.VERSION_17 }

repositories { mavenCentral() }

dependencyManagement {
    imports {
        mavenBom("org.springframework.boot:spring-boot-dependencies:3.2.3")
    }
}

dependencies {
    implementation("com.fasterxml.jackson.core:jackson-databind")
    implementation("com.fasterxml.jackson.datatype:jackson-datatype-jsr310")
    compileOnly("org.projectlombok:lombok")
    annotationProcessor("org.projectlombok:lombok")
}
""")

write(os.path.join(COMMON, "event", "BaseEvent.java"), """\
package com.exchange.common.event;

import lombok.Getter;
import java.time.LocalDateTime;
import java.util.UUID;

/**
 * 모든 도메인 이벤트의 기반 클래스
 * - eventId: 멱등성 보장을 위한 고유 ID
 * - occurredAt: 이벤트 발생 시각
 */
@Getter
public abstract class BaseEvent {
    private final String eventId = UUID.randomUUID().toString();
    private final LocalDateTime occurredAt = LocalDateTime.now();
    public abstract String getEventType();
}
""")

write(os.path.join(COMMON, "event", "OrderEvent.java"), """\
package com.exchange.common.event;

import com.exchange.common.enums.OrderStatus;
import com.exchange.common.enums.OrderType;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import java.math.BigDecimal;

/**
 * 서비스 간 공유되는 주문 이벤트 (Kafka 메시지 페이로드)
 * shared/common-lib에 위치해 모든 서비스가 참조
 */
@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OrderEvent extends BaseEvent {

    private Long orderId;
    private String customerName;
    private String productName;
    private Integer quantity;
    private BigDecimal totalPrice;
    private OrderType orderType;
    private OrderStatus status;

    @Override
    public String getEventType() { return "ORDER_EVENT"; }
}
""")

write(os.path.join(COMMON, "enums", "OrderStatus.java"), """\
package com.exchange.common.enums;

public enum OrderStatus {
    PENDING, PROCESSING, COMPLETED, CANCELLED
}
""")

write(os.path.join(COMMON, "enums", "OrderType.java"), """\
package com.exchange.common.enums;

public enum OrderType {
    MARKET, LIMIT, STOP_LOSS, STOP_LIMIT
}
""")

write(os.path.join(COMMON, "response", "ApiResponse.java"), """\
package com.exchange.common.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.Getter;

/**
 * 공통 API 응답 래퍼 - 모든 서비스에서 동일 포맷 사용
 */
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

write(os.path.join(COMMON, "exception", "BusinessException.java"), """\
package com.exchange.common.exception;

import lombok.Getter;

/**
 * 비즈니스 예외 기반 클래스
 * 각 서비스별 구체 예외 클래스로 확장
 */
@Getter
public class BusinessException extends RuntimeException {
    private final String errorCode;

    public BusinessException(String errorCode, String message) {
        super(message);
        this.errorCode = errorCode;
    }
}
""")

write(os.path.join(COMMON, "exception", "NotFoundException.java"), """\
package com.exchange.common.exception;

public class NotFoundException extends BusinessException {
    public NotFoundException(String resource, Object id) {
        super("NOT_FOUND", resource + " 을(를) 찾을 수 없습니다. id=" + id);
    }
}
""")


# ──────────────────────────────────────────────────────────────────
# 2. 각 서비스 build.gradle.kts + Application 뼈대
# ──────────────────────────────────────────────────────────────────
SERVICES = {
    "order-service": {
        "package": "com.exchange.order",
        "class": "OrderServiceApplication",
        "port": "8081",
        "desc": "주문 생성/조회/상태 관리",
        "extra_deps": [
            'implementation("org.springframework.boot:spring-boot-starter-data-jpa")',
            'implementation("org.springframework.boot:spring-boot-starter-data-redis")',
            'implementation("org.springframework.boot:spring-boot-starter-cache")',
            'implementation("org.springframework.kafka:spring-kafka")',
            'runtimeOnly("com.mysql:mysql-connector-j")',
        ],
    },
    "account-service": {
        "package": "com.exchange.account",
        "class": "AccountServiceApplication",
        "port": "8082",
        "desc": "사용자 계좌/잔고/포트폴리오 관리",
        "extra_deps": [
            'implementation("org.springframework.boot:spring-boot-starter-data-jpa")',
            'implementation("org.springframework.boot:spring-boot-starter-data-redis")',
            'implementation("org.springframework.kafka:spring-kafka")',
            'implementation("org.springframework.boot:spring-boot-starter-security")',
            'implementation("com.auth0:java-jwt:4.4.0")',
            'runtimeOnly("com.mysql:mysql-connector-j")',
        ],
    },
    "market-data-service": {
        "package": "com.exchange.marketdata",
        "class": "MarketDataServiceApplication",
        "port": "8083",
        "desc": "실시간 시세/호가창/OHLCV 데이터",
        "extra_deps": [
            'implementation("org.springframework.boot:spring-boot-starter-data-redis")',
            'implementation("org.springframework.boot:spring-boot-starter-websocket")',
            'implementation("org.springframework.kafka:spring-kafka")',
        ],
    },
    "trading-engine": {
        "package": "com.exchange.trading",
        "class": "TradingEngineApplication",
        "port": "8084",
        "desc": "주문 매칭 엔진 - Order Book, 체결 처리",
        "extra_deps": [
            'implementation("org.springframework.boot:spring-boot-starter-data-redis")',
            'implementation("org.springframework.kafka:spring-kafka")',
        ],
    },
    "settlement-service": {
        "package": "com.exchange.settlement",
        "class": "SettlementServiceApplication",
        "port": "8085",
        "desc": "T+2 정산, 세금 계산, 감독기관 리포팅",
        "extra_deps": [
            'implementation("org.springframework.boot:spring-boot-starter-data-jpa")',
            'implementation("org.springframework.kafka:spring-kafka")',
            'runtimeOnly("com.mysql:mysql-connector-j")',
        ],
    },
    "api-gateway": {
        "package": "com.exchange.gateway",
        "class": "ApiGatewayApplication",
        "port": "8080",
        "desc": "API Gateway - 라우팅, JWT 인증, Rate Limiting, Circuit Breaker",
        "extra_deps": [
            'implementation("org.springframework.cloud:spring-cloud-starter-gateway")',
            'implementation("org.springframework.boot:spring-boot-starter-data-redis-reactive")',
            'implementation("com.auth0:java-jwt:4.4.0")',
            'implementation("io.github.resilience4j:resilience4j-spring-boot3:2.2.0")',
        ],
    },
}

for svc_name, cfg in SERVICES.items():
    svc_root = os.path.join(ROOT, "services", svc_name)
    src_main = os.path.join(svc_root, "src", "main")
    pkg_path = os.path.join(src_main, "java", *cfg["package"].split("."))
    resources = os.path.join(src_main, "resources")

    # build.gradle.kts
    is_gateway = svc_name == "api-gateway"
    spring_cloud_dep = """
dependencyManagement {
    imports {
        mavenBom("org.springframework.boot:spring-boot-dependencies:3.2.3")
        mavenBom("org.springframework.cloud:spring-cloud-dependencies:2023.0.1")
    }
}
""" if is_gateway else ""

    extra = "\n".join(f"    {d}" for d in cfg["extra_deps"])
    write(os.path.join(svc_root, "build.gradle.kts"), f"""\
plugins {{
    java
    id("org.springframework.boot") version "3.2.3"
    id("io.spring.dependency-management") version "1.1.4"
}}

group = "com.exchange"
version = "0.0.1-SNAPSHOT"

java {{ sourceCompatibility = JavaVersion.VERSION_17 }}

repositories {{ mavenCentral() }}
{spring_cloud_dep}
dependencies {{
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.springdoc:springdoc-openapi-starter-webmvc-ui:2.3.0")
    compileOnly("org.projectlombok:lombok")
    annotationProcessor("org.projectlombok:lombok")
    // shared common-lib (로컬 의존)
    // implementation(project(":shared:common-lib"))
{extra}
    testImplementation("org.springframework.boot:spring-boot-starter-test")
}}

tasks.withType<Test> {{ useJUnitPlatform() }}
""")

    # Application.java
    write(os.path.join(pkg_path, f"{cfg['class']}.java"), f"""\
package {cfg['package']};

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * {cfg['desc']}
 * Port: {cfg['port']}
 */
@SpringBootApplication
public class {cfg['class']} {{
    public static void main(String[] args) {{
        SpringApplication.run({cfg['class']}.class, args);
    }}
}}
""")

    # application.yml
    write(os.path.join(resources, "application.yml"), f"""\
spring:
  application:
    name: {svc_name}

server:
  port: {cfg['port']}

management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics
  endpoint:
    health:
      show-details: always

springdoc:
  swagger-ui:
    path: /swagger-ui.html
  api-docs:
    path: /api-docs

logging:
  level:
    com.exchange: DEBUG
""")

    print(f"Service [{svc_name}] 뼈대 생성 완료")


# ──────────────────────────────────────────────────────────────────
# 3. 루트 settings.gradle.kts (멀티 모듈 구성)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(ROOT, "settings.gradle.kts"), """\
rootProject.name = "order-system"

// Shared Libraries
include("shared:common-lib")

// Microservices
include("services:order-service")
include("services:account-service")
include("services:market-data-service")
include("services:trading-engine")
include("services:settlement-service")
include("services:api-gateway")

// Legacy monolith (Phase 2에서 order-service로 완전 이전 후 제거 예정)
include("backend")
""")

# ──────────────────────────────────────────────────────────────────
# 4. 루트 build.gradle.kts
# ──────────────────────────────────────────────────────────────────
write(os.path.join(ROOT, "build.gradle.kts"), """\
plugins {
    java
    id("org.springframework.boot") version "3.2.3" apply false
    id("io.spring.dependency-management") version "1.1.4" apply false
}

allprojects {
    repositories { mavenCentral() }
}

subprojects {
    apply(plugin = "java")
    java { sourceCompatibility = JavaVersion.VERSION_17 }
}
""")

print("\n=== Phase 1 완료 ===")
print("생성된 서비스:", list(SERVICES.keys()))
