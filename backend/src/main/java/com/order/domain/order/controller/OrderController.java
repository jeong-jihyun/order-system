package com.order.domain.order.controller;

import com.order.common.response.ApiResponse;
import com.order.domain.order.dto.OrderRequest;
import com.order.domain.order.dto.OrderResponse;
import com.order.domain.order.entity.OrderStatus;
import com.order.domain.order.service.OrderService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/orders")
@RequiredArgsConstructor
@Tag(name = "Order API", description = "주문 관리 API")
public class OrderController {

    private final OrderService orderService;

    @GetMapping
    @Operation(summary = "전체 주문 조회")
    public ApiResponse<List<OrderResponse>> getAllOrders() {
        return ApiResponse.success(orderService.getAllOrders());
    }

    @GetMapping("/{id}")
    @Operation(summary = "단건 주문 조회 (Redis 캐시 적용)")
    public ApiResponse<OrderResponse> getOrder(@PathVariable Long id) {
        return ApiResponse.success(orderService.getOrder(id));
    }

    @GetMapping("/status/{status}")
    @Operation(summary = "상태별 주문 조회")
    public ApiResponse<List<OrderResponse>> getOrdersByStatus(@PathVariable OrderStatus status) {
        return ApiResponse.success(orderService.getOrdersByStatus(status));
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(summary = "주문 생성 (Kafka 이벤트 발행)")
    public ApiResponse<OrderResponse> createOrder(@RequestBody @Valid OrderRequest request) {
        return ApiResponse.success("주문이 생성되었습니다.", orderService.createOrder(request));
    }

    @PatchMapping("/{id}/status")
    @Operation(summary = "주문 상태 변경 (Redis 캐시 무효화)")
    public ApiResponse<OrderResponse> updateStatus(
            @PathVariable Long id,
            @RequestParam OrderStatus status) {
        return ApiResponse.success("주문 상태가 변경되었습니다.", orderService.updateOrderStatus(id, status));
    }
}
