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
