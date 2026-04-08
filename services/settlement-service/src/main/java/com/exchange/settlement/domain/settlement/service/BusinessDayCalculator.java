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
