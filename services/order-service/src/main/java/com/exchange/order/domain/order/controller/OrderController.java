package com.exchange.order.domain.order.controller;

import com.exchange.order.common.response.ApiResponse;
import com.exchange.order.domain.order.dto.OrderRequest;
import com.exchange.order.domain.order.dto.OrderResponse;
import com.exchange.order.domain.order.entity.OrderStatus;
import com.exchange.order.domain.order.service.command.OrderCommandService;
import com.exchange.order.domain.order.service.query.OrderQueryService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Tag(name = "Order API", description = "주문 생성/조회/상태 관리")
@RestController
@RequestMapping("/api/v1/orders")
@RequiredArgsConstructor
public class OrderController {

    private final OrderCommandService commandService;
    private final OrderQueryService queryService;

    @Operation(summary = "주문 생성")
    @PostMapping
    public ResponseEntity<ApiResponse<OrderResponse>> createOrder(
            @Valid @RequestBody OrderRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.success("주문이 생성되었습니다.", commandService.createOrder(request)));
    }

    @Operation(summary = "주문 단건 조회")
    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<OrderResponse>> getOrder(@PathVariable Long id) {
        return ResponseEntity.ok(ApiResponse.success(queryService.getOrder(id)));
    }

    @Operation(summary = "전체 주문 목록 조회")
    @GetMapping
    public ResponseEntity<ApiResponse<List<OrderResponse>>> getAllOrders() {
        return ResponseEntity.ok(ApiResponse.success(queryService.getAllOrders()));
    }

    @Operation(summary = "상태별 주문 조회")
    @GetMapping("/status/{status}")
    public ResponseEntity<ApiResponse<List<OrderResponse>>> getOrdersByStatus(
            @PathVariable OrderStatus status) {
        return ResponseEntity.ok(ApiResponse.success(queryService.getOrdersByStatus(status)));
    }

    @Operation(summary = "고객별 주문 조회")
    @GetMapping("/customer/{customerName}")
    public ResponseEntity<ApiResponse<List<OrderResponse>>> getOrdersByCustomer(
            @PathVariable String customerName) {
        return ResponseEntity.ok(ApiResponse.success(queryService.getOrdersByCustomer(customerName)));
    }

    @Operation(summary = "주문 상태 변경")
    @PatchMapping("/{id}/status")
    public ResponseEntity<ApiResponse<OrderResponse>> updateStatus(
            @PathVariable Long id,
            @RequestParam OrderStatus status) {
        return ResponseEntity.ok(ApiResponse.success(commandService.updateOrderStatus(id, status)));
    }

    @Operation(summary = "주문 삭제")
    @DeleteMapping("/{id}")
    public ResponseEntity<ApiResponse<Void>> deleteOrder(@PathVariable Long id) {
        commandService.deleteOrder(id);
        return ResponseEntity.ok(ApiResponse.success(null));
    }

    @Operation(summary = "상태별 주문 통계")
    @GetMapping("/stats")
    public ResponseEntity<ApiResponse<Map<OrderStatus, Long>>> getStats() {
        return ResponseEntity.ok(ApiResponse.success(queryService.getOrderStatsByStatus()));
    }
}
