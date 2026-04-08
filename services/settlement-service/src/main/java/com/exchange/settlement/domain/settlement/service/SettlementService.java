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
