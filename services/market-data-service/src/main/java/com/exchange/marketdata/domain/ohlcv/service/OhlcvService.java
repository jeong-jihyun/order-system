package com.exchange.marketdata.domain.ohlcv.service;

import com.exchange.marketdata.domain.ohlcv.dto.OhlcvDto;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * OHLCV (캔들) 데이터 관리
 * Redis ZSet: ohlcv:{symbol}:{interval}
 * - score = openTime 의 epoch second (시각 순 정렬)
 * - value = OhlcvDto JSON
 * - 각 인터벌별 최대 500개 보관 (LTRIM 방식 유사하게 ZREMRANGEBYRANK)
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class OhlcvService {

    private final StringRedisTemplate stringRedisTemplate;
    private final ObjectMapper objectMapper;

    @Value("${market.redis.ohlcv-prefix:ohlcv:}")
    private String ohlcvPrefix;

    private static final int MAX_CANDLES = 500;

    /**
     * 체결 이벤트 발생 시 해당 인터벌 캔들 업데이트
     */
    public void update(String symbol, String interval,
                       BigDecimal price, Long volume, LocalDateTime time) {
        String key = ohlcvPrefix + symbol + ":" + interval;

        // 현재 진행 중인 캔들 조회 (ZSet 마지막 요소)
        Set<String> last = stringRedisTemplate.opsForZSet().range(key, -1, -1);
        OhlcvDto current = null;
        if (last != null && !last.isEmpty()) {
            current = deserialize(last.iterator().next());
        }

        LocalDateTime candle = truncateToInterval(time, interval);
        double score = candle.toEpochSecond(ZoneOffset.UTC);

        OhlcvDto updated;
        if (current != null && current.getOpenTime().equals(candle)) {
            // 기존 캔들 업데이트
            updated = OhlcvDto.builder()
                    .symbol(symbol)
                    .interval(interval)
                    .open(current.getOpen())
                    .high(current.getHigh().max(price))
                    .low(current.getLow().min(price))
                    .close(price)
                    .volume(current.getVolume() + volume)
                    .openTime(candle)
                    .closeTime(getCloseTime(candle, interval))
                    .build();
            // 기존 점수 제거 후 재삽입
            stringRedisTemplate.opsForZSet().removeRangeByScore(key, score, score);
        } else {
            // 새 캔들 시작
            updated = OhlcvDto.builder()
                    .symbol(symbol)
                    .interval(interval)
                    .open(price).high(price).low(price).close(price)
                    .volume(volume)
                    .openTime(candle)
                    .closeTime(getCloseTime(candle, interval))
                    .build();
        }

        try {
            stringRedisTemplate.opsForZSet().add(key, objectMapper.writeValueAsString(updated), score);
            // 최대 개수 초과 시 오래된 캔들 제거
            Long size = stringRedisTemplate.opsForZSet().zCard(key);
            if (size != null && size > MAX_CANDLES) {
                stringRedisTemplate.opsForZSet().removeRange(key, 0, size - MAX_CANDLES - 1);
            }
        } catch (JsonProcessingException e) {
            log.error("[OHLCV 저장 실패] symbol={}, interval={}", symbol, interval);
        }
    }

    /**
     * 최근 N개 캔들 조회
     */
    public List<OhlcvDto> getCandles(String symbol, String interval, int limit) {
        String key = ohlcvPrefix + symbol + ":" + interval;
        Set<String> raw = stringRedisTemplate.opsForZSet().reverseRange(key, 0, limit - 1);
        if (raw == null) return List.of();

        List<OhlcvDto> result = new ArrayList<>();
        for (String json : raw) {
            OhlcvDto dto = deserialize(json);
            if (dto != null) result.add(dto);
        }
        return result;
    }

    private LocalDateTime truncateToInterval(LocalDateTime time, String interval) {
        return switch (interval) {
            case "1m"  -> time.withSecond(0).withNano(0);
            case "5m"  -> time.withMinute((time.getMinute() / 5) * 5).withSecond(0).withNano(0);
            case "15m" -> time.withMinute((time.getMinute() / 15) * 15).withSecond(0).withNano(0);
            case "1h"  -> time.withMinute(0).withSecond(0).withNano(0);
            case "1d"  -> time.withHour(0).withMinute(0).withSecond(0).withNano(0);
            default    -> time.withSecond(0).withNano(0);
        };
    }

    private LocalDateTime getCloseTime(LocalDateTime open, String interval) {
        return switch (interval) {
            case "1m"  -> open.plusMinutes(1).minusNanos(1);
            case "5m"  -> open.plusMinutes(5).minusNanos(1);
            case "15m" -> open.plusMinutes(15).minusNanos(1);
            case "1h"  -> open.plusHours(1).minusNanos(1);
            case "1d"  -> open.plusDays(1).minusNanos(1);
            default    -> open.plusMinutes(1).minusNanos(1);
        };
    }

    private OhlcvDto deserialize(String json) {
        try {
            return objectMapper.readValue(json, OhlcvDto.class);
        } catch (Exception e) {
            return null;
        }
    }
}
