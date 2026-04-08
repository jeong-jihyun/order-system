package com.order.domain.order.controller;

import com.order.common.response.ApiResponse;
import com.order.domain.order.dto.OrderRequest;
import com.order.domain.order.dto.OrderResponse;
import com.order.domain.order.entity.OrderStatus;
import com.order.domain.order.service.command.OrderCommandService;
import com.order.domain.order.service.query.OrderQueryService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/**
 * [CQRS 반영] Command/Query 서비스 분리 주입
 * - 읽기 요청: OrderQueryService
 * - 쓰기 요청: OrderCommandService
 */
@RestController
@RequestMapping("/api/orders")
@RequiredArgsConstructor
@Tag(name = "Order API", description = "주문 관리 API")
public class OrderController {

    private final OrderCommandService orderCommandService;
    private final OrderQueryService orderQueryService;

    @GetMapping
    @Operation(summary = "전체 주문 목록 조회")
    public ApiResponse<List<OrderResponse>> getAllOrders() {
        return ApiResponse.success(orderQueryService.getAllOrders());
    }

    @GetMapping("/{id}")
    @Operation(summary = "단건 주문 조회 (Redis 캐시 적용)")
    public ApiResponse<OrderResponse> getOrder(@PathVariable Long id) {
        return ApiResponse.success(orderQueryService.getOrder(id));
    }

    @GetMapping("/status/{status}")
    @Operation(summary = "상태별 주문 조회")
    public ApiResponse<List<OrderResponse>> getOrdersByStatus(@PathVariable OrderStatus status) {
        return ApiResponse.success(orderQueryService.getOrdersByStatus(status));
    }

    @GetMapping("/pending/sorted")
    @Operation(summary = "PENDING 주문 금액 내림차순 조회")
    public ApiResponse<List<OrderResponse>> getPendingOrdersSortedByPrice() {
        return ApiResponse.success(orderQueryService.getPendingOrdersSortedByPrice());
    }

    @GetMapping("/stats/total-amount")
    @Operation(summary = "전체 주문 총 금액 합산")
    public ApiResponse<BigDecimal> getTotalAmount() {
        return ApiResponse.success(orderQueryService.getOrdersTotalAmount());
    }

    @GetMapping("/stats/count-by-status")
    @Operation(summary = "상태별 주문 건수 집계")
    public ApiResponse<Map<OrderStatus, Long>> getCountByStatus() {
        return ApiResponse.success(orderQueryService.getOrderCountByStatus());
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(summary = "주문 생성 (Kafka 이벤트 발행)")
    public ApiResponse<OrderResponse> createOrder(@RequestBody @Valid OrderRequest request) {
        return ApiResponse.success("주문이 생성되었습니다.", orderCommandService.createOrder(request));
    }

    @PatchMapping("/{id}/status")
    @Operation(summary = "주문 상태 변경 (State Machine 검증)")
    public ApiResponse<OrderResponse> updateStatus(
            @PathVariable Long id,
            @RequestParam OrderStatus status) {
        return ApiResponse.success("주문 상태가 변경되었습니다.", orderCommandService.updateOrderStatus(id, status));
    }
}
