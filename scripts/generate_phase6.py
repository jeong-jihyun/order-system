#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 6: settlement-service — T+2 정산 + 수수료/세금 계산
- 체결 이벤트 수신: Kafka order-status-events → 정산 처리
- 수수료: 매수/매도 각 0.015% (국내 증권사 수준)
- 거래세: 매도 0.2% (양도소득세근거, 실제로는 증권거래세)
- T+2 결제: 체결일 +2 영업일에 실제 잔고 반영 (스케줄러)
- 정산 내역 DB 저장 + 이벤트 발행 (account-service 잔고 업데이트)
- Port: 8085
"""
import os

ROOT = r"d:\order-system"
SS   = os.path.join(ROOT, "services", "settlement-service")
SRC  = os.path.join(SS, "src", "main", "java", "com", "exchange", "settlement")
RES  = os.path.join(SS, "src", "main", "resources")

def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"OK  {os.path.relpath(path, ROOT)}")

# ──────────────────────────────────────────────────────────────────
# 1. build.gradle.kts
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SS, "build.gradle.kts"), """\
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
    implementation("org.springframework.kafka:spring-kafka")
    implementation("com.fasterxml.jackson.core:jackson-databind")
    implementation("com.fasterxml.jackson.datatype:jackson-datatype-jsr310")
    implementation("org.springdoc:springdoc-openapi-starter-webmvc-ui:2.3.0")
    runtimeOnly("com.mysql:mysql-connector-j")
    compileOnly("org.projectlombok:lombok")
    annotationProcessor("org.projectlombok:lombok")
    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("com.h2database:h2")
}

tasks.withType<Test> { useJUnitPlatform() }
""")

# ──────────────────────────────────────────────────────────────────
# 2. application.yml
# ──────────────────────────────────────────────────────────────────
write(os.path.join(RES, "application.yml"), """\
spring:
  application:
    name: settlement-service

  datasource:
    url: ${SPRING_DATASOURCE_URL:jdbc:mysql://localhost:3306/settlement_db?useSSL=false&serverTimezone=Asia/Seoul}
    username: ${SPRING_DATASOURCE_USERNAME:root}
    password: ${SPRING_DATASOURCE_PASSWORD:password}
    driver-class-name: com.mysql.cj.jdbc.Driver

  jpa:
    hibernate:
      ddl-auto: update
    show-sql: false
    properties:
      hibernate.dialect: org.hibernate.dialect.MySQLDialect

  kafka:
    bootstrap-servers: ${SPRING_KAFKA_BOOTSTRAP_SERVERS:localhost:9092}
    consumer:
      group-id: settlement-service-group
      auto-offset-reset: earliest
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.apache.kafka.common.serialization.StringDeserializer
    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.apache.kafka.common.serialization.StringSerializer
      acks: all
      retries: 3
      properties:
        enable.idempotence: true

server:
  port: 8085

management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics

settlement:
  kafka:
    execution-topic: order-status-events     # 수신 (체결 결과)
    settlement-topic: settlement-events       # 발행 (잔고 업데이트 요청)
  fee:
    commission-rate: "0.00015"   # 수수료 0.015% (매수/매도 양측)
    tax-rate: "0.002"            # 거래세 0.2% (매도 시 부과)
  t-plus: 2                      # T+2 정산 일수

logging:
  level:
    com.exchange.settlement: DEBUG
    org.springframework.kafka: WARN
""")

# ──────────────────────────────────────────────────────────────────
# 3. Application 진입점
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "SettlementServiceApplication.java"), """\
package com.exchange.settlement;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Settlement Service — T+2 정산 서비스
 * Port: 8085
 * - 체결 이벤트 수신 → 정산 레코드 생성
 * - 수수료(0.015%) + 거래세(매도 0.2%) 계산
 * - T+2 스케줄러 → 잔고 반영 이벤트 발행
 */
@SpringBootApplication
@EnableAsync
@EnableScheduling
public class SettlementServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(SettlementServiceApplication.class, args);
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 4. 도메인 — 정산 상태
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "settlement", "entity", "SettlementStatus.java"), """\
package com.exchange.settlement.domain.settlement.entity;

/**
 * 정산 상태 머신
 * PENDING → SCHEDULED → COMPLETED
 *                     → FAILED (재시도 후 실패)
 */
public enum SettlementStatus {
    PENDING,     // 체결 완료, 정산 대기
    SCHEDULED,   // T+2 정산일 확정
    COMPLETED,   // 잔고 반영 완료
    FAILED       // 정산 실패 (수동 처리 필요)
}
""")

# ──────────────────────────────────────────────────────────────────
# 5. 도메인 — SettlementRecord 엔티티
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "settlement", "entity", "SettlementRecord.java"), """\
package com.exchange.settlement.domain.settlement.entity;

import jakarta.persistence.*;
import lombok.*;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 체결 1건당 1개의 정산 레코드 생성
 * 매수/매도 각각 별도 레코드 (수수료/세금 계산이 다름)
 */
@Entity
@Table(name = "settlement_records",
       indexes = {
           @Index(name = "idx_order_id",         columnList = "orderId"),
           @Index(name = "idx_settlement_date",   columnList = "settlementDate,status"),
           @Index(name = "idx_username",          columnList = "username")
       })
@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SettlementRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long orderId;

    @Column(nullable = false)
    private Long counterOrderId;     // 상대방 주문 ID

    @Column(nullable = false)
    private String username;

    @Column(nullable = false, length = 20)
    private String symbol;

    @Column(nullable = false, length = 10)
    private String side;             // BUY / SELL

    @Column(nullable = false, precision = 20, scale = 8)
    private BigDecimal executionPrice;

    @Column(nullable = false, precision = 20, scale = 8)
    private BigDecimal executionQuantity;

    @Column(nullable = false, precision = 20, scale = 8)
    private BigDecimal grossAmount;  // 체결 금액 (price * quantity)

    @Column(nullable = false, precision = 20, scale = 8)
    private BigDecimal commission;   // 수수료

    @Column(nullable = false, precision = 20, scale = 8)
    private BigDecimal tax;          // 거래세 (매도만)

    @Column(nullable = false, precision = 20, scale = 8)
    private BigDecimal netAmount;    // 실수령/실지불 금액 (grossAmount ± commission ± tax)

    @Column(nullable = false)
    private LocalDate settlementDate;  // T+2 정산 예정일

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private SettlementStatus status;

    @Column(nullable = false)
    private LocalDateTime executedAt;

    private LocalDateTime settledAt;   // 실제 정산 처리 시각

    public void markScheduled() {
        this.status = SettlementStatus.SCHEDULED;
    }

    public void markCompleted() {
        this.status = SettlementStatus.COMPLETED;
        this.settledAt = LocalDateTime.now();
    }

    public void markFailed() {
        this.status = SettlementStatus.FAILED;
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 6. Repository
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "settlement", "repository", "SettlementRecordRepository.java"), """\
package com.exchange.settlement.domain.settlement.repository;

import com.exchange.settlement.domain.settlement.entity.SettlementRecord;
import com.exchange.settlement.domain.settlement.entity.SettlementStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDate;
import java.util.List;

public interface SettlementRecordRepository extends JpaRepository<SettlementRecord, Long> {

    /**
     * T+2 정산 처리 대상 조회 (오늘 정산일인 SCHEDULED 레코드)
     */
    @Query("SELECT s FROM SettlementRecord s " +
           "WHERE s.settlementDate <= :today AND s.status = :status")
    List<SettlementRecord> findDueSettlements(@Param("today") LocalDate today,
                                              @Param("status") SettlementStatus status);

    List<SettlementRecord> findByUsernameOrderByExecutedAtDesc(String username);

    boolean existsByOrderIdAndSide(Long orderId, String side);
}
""")

# ──────────────────────────────────────────────────────────────────
# 7. 수수료/세금 계산 서비스 (Strategy 패턴)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "settlement", "service", "FeeCalculator.java"), """\
package com.exchange.settlement.domain.settlement.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.math.RoundingMode;

/**
 * 수수료 / 거래세 계산기
 *
 * 수수료: gross × 0.015% (매수/매도 모두)
 * 거래세: gross × 0.2% (매도 시에만 부과 — 코스피 기준)
 * 순수령액:
 *   BUY  → -(grossAmount + commission)          [지출]
 *   SELL → (grossAmount - commission - tax)     [수취]
 */
@Slf4j
@Component
public class FeeCalculator {

    private final BigDecimal commissionRate;
    private final BigDecimal taxRate;

    public FeeCalculator(
            @Value("${settlement.fee.commission-rate:0.00015}") String commissionRate,
            @Value("${settlement.fee.tax-rate:0.002}") String taxRate) {
        this.commissionRate = new BigDecimal(commissionRate);
        this.taxRate = new BigDecimal(taxRate);
    }

    public FeeResult calculate(BigDecimal grossAmount, String side) {
        BigDecimal commission = grossAmount.multiply(commissionRate)
                .setScale(2, RoundingMode.HALF_UP);

        BigDecimal tax = "SELL".equalsIgnoreCase(side)
                ? grossAmount.multiply(taxRate).setScale(2, RoundingMode.HALF_UP)
                : BigDecimal.ZERO;

        BigDecimal netAmount = "SELL".equalsIgnoreCase(side)
                ? grossAmount.subtract(commission).subtract(tax)
                : grossAmount.add(commission).negate();

        log.debug("[FeeCalculator] gross={}, commission={}, tax={}, net={}",
                grossAmount, commission, tax, netAmount);
        return new FeeResult(commission, tax, netAmount);
    }

    public record FeeResult(BigDecimal commission, BigDecimal tax, BigDecimal netAmount) {}
}
""")

# ──────────────────────────────────────────────────────────────────
# 8. 영업일 계산 유틸 (T+2 계산)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "settlement", "service", "BusinessDayCalculator.java"), """\
package com.exchange.settlement.domain.settlement.service;

import org.springframework.stereotype.Component;

import java.time.DayOfWeek;
import java.time.LocalDate;
import java.util.Set;

/**
 * 영업일 계산기 (주말 제외, 공휴일은 간단 처리)
 * 실제 운영 시 공휴일 DB 연동 필요
 */
@Component
public class BusinessDayCalculator {

    // 간이 공휴일 (yyyy-MM-dd 형식, 필요 시 DB/Config로 관리)
    private static final Set<LocalDate> HOLIDAYS = Set.of(
        LocalDate.of(2025, 1, 1),   // 신정
        LocalDate.of(2025, 3, 1),   // 삼일절
        LocalDate.of(2025, 5, 5),   // 어린이날
        LocalDate.of(2025, 8, 15),  // 광복절
        LocalDate.of(2025, 10, 3),  // 개천절
        LocalDate.of(2025, 12, 25)  // 성탄절
    );

    /**
     * 기준일에서 n 영업일 후 날짜 반환
     */
    public LocalDate addBusinessDays(LocalDate base, int days) {
        LocalDate result = base;
        int count = 0;
        while (count < days) {
            result = result.plusDays(1);
            if (isBusinessDay(result)) count++;
        }
        return result;
    }

    public boolean isBusinessDay(LocalDate date) {
        DayOfWeek day = date.getDayOfWeek();
        return day != DayOfWeek.SATURDAY
            && day != DayOfWeek.SUNDAY
            && !HOLIDAYS.contains(date);
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 9. 정산 핵심 서비스
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "settlement", "service", "SettlementService.java"), """\
package com.exchange.settlement.domain.settlement.service;

import com.exchange.settlement.domain.settlement.entity.SettlementRecord;
import com.exchange.settlement.domain.settlement.entity.SettlementStatus;
import com.exchange.settlement.domain.settlement.repository.SettlementRecordRepository;
import com.exchange.settlement.infrastructure.kafka.SettlementEventProducer;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

/**
 * 체결 이벤트 수신 → 정산 레코드 생성 → T+2 정산 처리
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class SettlementService {

    private final SettlementRecordRepository settlementRepo;
    private final FeeCalculator feeCalculator;
    private final BusinessDayCalculator businessDayCalc;
    private final SettlementEventProducer eventProducer;

    @Value("${settlement.t-plus:2}")
    private int tPlus;

    /**
     * 체결 이벤트 → 정산 레코드 2건 생성 (매수/매도 각각)
     */
    @Transactional
    public void processExecution(Long buyOrderId, Long sellOrderId,
                                  String symbol, BigDecimal executionPrice,
                                  BigDecimal executionQuantity, LocalDateTime executedAt,
                                  String buyerUsername, String sellerUsername) {
        LocalDate settlementDate = businessDayCalc.addBusinessDays(executedAt.toLocalDate(), tPlus);
        BigDecimal grossAmount = executionPrice.multiply(executionQuantity)
                .setScale(2, RoundingMode.HALF_UP);

        // 매수 정산 레코드
        if (!settlementRepo.existsByOrderIdAndSide(buyOrderId, "BUY")) {
            FeeCalculator.FeeResult buyFee = feeCalculator.calculate(grossAmount, "BUY");
            SettlementRecord buyRecord = SettlementRecord.builder()
                    .orderId(buyOrderId)
                    .counterOrderId(sellOrderId)
                    .username(buyerUsername)
                    .symbol(symbol)
                    .side("BUY")
                    .executionPrice(executionPrice)
                    .executionQuantity(executionQuantity)
                    .grossAmount(grossAmount)
                    .commission(buyFee.commission())
                    .tax(buyFee.tax())
                    .netAmount(buyFee.netAmount())
                    .settlementDate(settlementDate)
                    .status(SettlementStatus.SCHEDULED)
                    .executedAt(executedAt)
                    .build();
            settlementRepo.save(buyRecord);
            log.info("[정산 등록] BUY — 주문={}, 금액={}, 수수료={}, 정산일={}",
                    buyOrderId, grossAmount, buyFee.commission(), settlementDate);
        }

        // 매도 정산 레코드
        if (!settlementRepo.existsByOrderIdAndSide(sellOrderId, "SELL")) {
            FeeCalculator.FeeResult sellFee = feeCalculator.calculate(grossAmount, "SELL");
            SettlementRecord sellRecord = SettlementRecord.builder()
                    .orderId(sellOrderId)
                    .counterOrderId(buyOrderId)
                    .username(sellerUsername)
                    .symbol(symbol)
                    .side("SELL")
                    .executionPrice(executionPrice)
                    .executionQuantity(executionQuantity)
                    .grossAmount(grossAmount)
                    .commission(sellFee.commission())
                    .tax(sellFee.tax())
                    .netAmount(sellFee.netAmount())
                    .settlementDate(settlementDate)
                    .status(SettlementStatus.SCHEDULED)
                    .executedAt(executedAt)
                    .build();
            settlementRepo.save(sellRecord);
            log.info("[정산 등록] SELL — 주문={}, 금액={}, 세금={}, 정산일={}",
                    sellOrderId, grossAmount, sellFee.tax(), settlementDate);
        }
    }

    /**
     * T+2 정산 스케줄러 — 매일 오전 7시 실행 (개장 전)
     * 정산 예정일이 오늘 이전인 SCHEDULED 레코드를 처리
     */
    @Scheduled(cron = "0 0 7 * * MON-FRI")
    @Transactional
    public void processScheduledSettlements() {
        List<SettlementRecord> dueRecords =
                settlementRepo.findDueSettlements(LocalDate.now(), SettlementStatus.SCHEDULED);

        if (dueRecords.isEmpty()) return;

        log.info("[T+{} 정산 스케줄러] {} 건 처리 시작", tPlus, dueRecords.size());

        for (SettlementRecord record : dueRecords) {
            try {
                eventProducer.publishSettlementComplete(record);
                record.markCompleted();
                log.info("[정산 완료] id={}, 주문={}, 실수령={}",
                        record.getId(), record.getOrderId(), record.getNetAmount());
            } catch (Exception e) {
                record.markFailed();
                log.error("[정산 실패] id={}, 주문={}, 오류={}", record.getId(),
                        record.getOrderId(), e.getMessage());
            }
        }
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 10. Kafka Consumer (체결 이벤트 수신)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "infrastructure", "kafka", "ExecutionEventConsumer.java"), """\
package com.exchange.settlement.infrastructure.kafka;

import com.exchange.settlement.domain.settlement.service.SettlementService;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Map;

/**
 * Kafka Consumer — order-status-events (체결 결과) 수신
 * buyFilled=true && sellFilled=true → 완전 체결로 간주하여 정산 처리
 * 부분 체결은 누적 관리 필요 (현재 간략 구현)
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class ExecutionEventConsumer {

    private final SettlementService settlementService;
    private final ObjectMapper objectMapper;

    @KafkaListener(topics = "${settlement.kafka.execution-topic:order-status-events}",
                   groupId = "settlement-service-group")
    public void consume(String message) {
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> payload = objectMapper.readValue(message, Map.class);

            Long buyOrderId  = Long.valueOf(payload.get("buyOrderId").toString());
            Long sellOrderId = Long.valueOf(payload.get("sellOrderId").toString());
            String symbol    = (String) payload.get("symbol");
            BigDecimal price = new BigDecimal(payload.get("executionPrice").toString());
            BigDecimal qty   = new BigDecimal(payload.get("executionQuantity").toString());
            LocalDateTime executedAt = LocalDateTime.parse(payload.get("executedAt").toString());

            // username은 별도 조회 필요 — 현재는 orderId를 임시 사용 (account-service 연동 예정)
            String buyerUsername  = "user-" + buyOrderId;
            String sellerUsername = "user-" + sellOrderId;

            settlementService.processExecution(
                    buyOrderId, sellOrderId, symbol, price, qty, executedAt,
                    buyerUsername, sellerUsername);

        } catch (Exception e) {
            log.error("[ExecutionEventConsumer] 처리 실패: {}", e.getMessage(), e);
        }
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 11. Kafka Producer (정산 완료 이벤트 발행)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "infrastructure", "kafka", "SettlementEventProducer.java"), """\
package com.exchange.settlement.infrastructure.kafka;

import com.exchange.settlement.domain.settlement.entity.SettlementRecord;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * 정산 완료 이벤트 발행
 * account-service가 수신하여 실제 잔고 반영 처리
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class SettlementEventProducer {

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    @Value("${settlement.kafka.settlement-topic:settlement-events}")
    private String settlementTopic;

    public void publishSettlementComplete(SettlementRecord record) {
        try {
            Map<String, Object> payload = Map.of(
                "settlementId",  record.getId(),
                "orderId",       record.getOrderId(),
                "username",      record.getUsername(),
                "symbol",        record.getSymbol(),
                "side",          record.getSide(),
                "netAmount",     record.getNetAmount(),
                "settlementDate",record.getSettlementDate().toString()
            );
            String json = objectMapper.writeValueAsString(payload);
            kafkaTemplate.send(settlementTopic, record.getUsername(), json);
            log.info("[SettlementProducer] 정산 이벤트 발행 — id={}, username={}, netAmount={}",
                    record.getId(), record.getUsername(), record.getNetAmount());
        } catch (JsonProcessingException e) {
            log.error("[SettlementProducer] 직렬화 실패: {}", e.getMessage());
            throw new RuntimeException("정산 이벤트 발행 실패", e);
        }
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 12. REST Controller — 정산 내역 조회
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "settlement", "controller", "SettlementController.java"), """\
package com.exchange.settlement.domain.settlement.controller;

import com.exchange.settlement.common.response.ApiResponse;
import com.exchange.settlement.domain.settlement.entity.SettlementRecord;
import com.exchange.settlement.domain.settlement.repository.SettlementRecordRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Tag(name = "Settlement API", description = "정산 내역 조회")
@RestController
@RequestMapping("/api/v1/settlements")
@RequiredArgsConstructor
public class SettlementController {

    private final SettlementRecordRepository settlementRepo;

    @Operation(summary = "내 정산 내역 조회")
    @GetMapping("/me")
    public ResponseEntity<ApiResponse<List<SettlementRecord>>> getMySettlements(
            @RequestHeader("X-User-Name") String username) {
        List<SettlementRecord> records =
                settlementRepo.findByUsernameOrderByExecutedAtDesc(username);
        return ResponseEntity.ok(ApiResponse.success(records));
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 13. 공통 응답/예외
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "common", "response", "ApiResponse.java"), """\
package com.exchange.settlement.common.response;

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

    public static <T> ApiResponse<T> error(String message) {
        return new ApiResponse<>(false, message, null);
    }
}
""")

write(os.path.join(SRC, "common", "exception", "GlobalExceptionHandler.java"), """\
package com.exchange.settlement.common.exception;

import com.exchange.settlement.common.response.ApiResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ApiResponse<Void>> handleIllegalArgument(IllegalArgumentException e) {
        return ResponseEntity.badRequest().body(ApiResponse.error(e.getMessage()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Void>> handleGeneral(Exception e) {
        log.error("[서버 오류]", e);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ApiResponse.error("서버 내부 오류가 발생했습니다."));
    }
}
""")

print()
print("=== Phase 6 생성 완료 ===")
print("핵심 클래스:")
print("  - SettlementRecord: JPA 엔티티 (T+2 정산 레코드)")
print("  - FeeCalculator: 수수료(0.015%) + 거래세(매도 0.2%)")
print("  - BusinessDayCalculator: 영업일 계산 (주말/공휴일 제외)")
print("  - SettlementService: 체결→정산 레코드 생성 + T+2 스케줄러")
print("  - ExecutionEventConsumer: order-status-events 수신")
print("  - SettlementEventProducer: settlement-events 발행")
print("다음: ./gradlew.bat :services:settlement-service:compileJava")
