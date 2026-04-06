package com.order.config;

import org.apache.kafka.clients.admin.NewTopic;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.config.TopicBuilder;

/**
 * [Week 2 - Kafka 설정]
 * 토픽 이름을 상수로 관리하고 자동 생성 설정
 */
@Configuration
public class KafkaConfig {

    public static final String ORDER_TOPIC = "order-events";

    /**
     * order-events 토픽 자동 생성
     * - partitions: 병렬 처리 단위 (컨슈머 그룹 내 최대 병렬도 = 파티션 수)
     * - replicas: 복제본 수 (개발 환경은 1)
     */
    @Bean
    public NewTopic orderTopic() {
        return TopicBuilder.name(ORDER_TOPIC)
                .partitions(3)
                .replicas(1)
                .build();
    }
}
