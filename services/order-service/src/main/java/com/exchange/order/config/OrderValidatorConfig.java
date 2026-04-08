package com.exchange.order.config;

import com.exchange.order.domain.order.validator.OrderValidator;
import com.exchange.order.domain.order.validator.PriceValidator;
import com.exchange.order.domain.order.validator.QuantityValidator;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Chain of Responsibility 조립
 * 새 검증 규칙 추가 시 여기서 .andThen() 체인만 연결
 */
@Configuration
public class OrderValidatorConfig {

    @Bean
    public OrderValidator orderValidator(QuantityValidator quantityValidator,
                                         PriceValidator priceValidator) {
        return quantityValidator.andThen(priceValidator);
    }
}
