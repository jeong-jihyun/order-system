package com.order.config;

import com.order.domain.order.validator.OrderValidator;
import com.order.domain.order.validator.PriceValidator;
import com.order.domain.order.validator.QuantityValidator;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * [Chain of Responsibility 조립]
 * QuantityValidator -> PriceValidator 순서로 체인 구성
 * 새 검증 규칙 추가 시: 새 Validator 구현 후 체인에 .andThen() 추가
 */
@Configuration
public class OrderValidatorConfig {

    @Bean
    public OrderValidator orderValidator(QuantityValidator qty, PriceValidator price) {
        return qty.andThen(price);
    }
}
