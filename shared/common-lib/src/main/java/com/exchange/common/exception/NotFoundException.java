package com.exchange.common.exception;

public class NotFoundException extends BusinessException {
    public NotFoundException(String resource, Object id) {
        super("NOT_FOUND", resource + " 을(를) 찾을 수 없습니다. id=" + id);
    }
}
