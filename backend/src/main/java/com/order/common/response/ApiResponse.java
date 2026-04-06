package com.order.common.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.Getter;

/**
 * [Week 1 - Generic 실습]
 * 제네릭 타입 파라미터 <T>를 사용해 어떤 데이터도 담을 수 있는 API 응답 래퍼.
 *
 * 활용 예:
 *   ApiResponse<OrderResponse>       — 단건
 *   ApiResponse<List<OrderResponse>> — 목록
 *   ApiResponse<Void>                — 데이터 없는 응답
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

    // ── 성공 팩토리 메서드 ────────────────────────────────────
    public static <T> ApiResponse<T> success(T data) {
        return new ApiResponse<>(true, "성공", data);
    }

    public static <T> ApiResponse<T> success(String message, T data) {
        return new ApiResponse<>(true, message, data);
    }

    public static ApiResponse<Void> success(String message) {
        return new ApiResponse<>(true, message, null);
    }

    // ── 실패 팩토리 메서드 ────────────────────────────────────
    public static <T> ApiResponse<T> error(String message) {
        return new ApiResponse<>(false, message, null);
    }
}
