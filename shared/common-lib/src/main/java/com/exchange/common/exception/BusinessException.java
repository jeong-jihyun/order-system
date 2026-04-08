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
