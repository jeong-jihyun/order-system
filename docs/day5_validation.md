# Day 5 학습 노트 — GlobalExceptionHandler + @Valid 연결 이해

> 날짜: 2026-04-08 | 주제: 유효성 검사 흐름 + Stream joining 실습

---

## 1. 전체 흐름

```
클라이언트 HTTP 요청 (잘못된 값)
        ↓
OrderController  —  @Valid 어노테이션
        ↓
Spring이 OrderRequest 필드를 자동으로 검사
        ↓
검사 실패 → MethodArgumentNotValidException 발생
        ↓
GlobalExceptionHandler.handleValidation() 에서 잡음
        ↓
Stream으로 오류 메시지 수집 → JSON 응답 반환 (HTTP 400)
```

---

## 2. OrderRequest — 유효성 어노테이션

```java
@NotBlank(message = "고객명은 필수입니다.")
@Size(max = 50, message = "고객명은 50자 이하여야 합니다.")
private String customerName;

@NotBlank(message = "상품명은 필수입니다.")
@Size(max = 100, message = "상품명은 100자 이하여야 합니다.")
private String productName;

@NotNull(message = "수량은 필수입니다.")
@Min(value = 1, message = "수량은 1 이상이어야 합니다.")
private Integer quantity;

@NotNull(message = "금액은 필수입니다.")
@DecimalMin(value = "0.01", message = "금액은 0보다 커야 합니다.")
private BigDecimal totalPrice;
```

---

## 3. @NotNull vs @NotEmpty vs @NotBlank 차이

| 값 | `@NotNull` | `@NotEmpty` | `@NotBlank` |
|----|-----------|-------------|-------------|
| `null` | ❌ 실패 | ❌ 실패 | ❌ 실패 |
| `""` (빈 문자열) | ✅ 통과 | ❌ 실패 | ❌ 실패 |
| `" "` (공백만) | ✅ 통과 | ✅ 통과 | ❌ 실패 |
| `"abc"` | ✅ 통과 | ✅ 통과 | ✅ 통과 |

> **실무 팁:** 문자열 필드에는 항상 `@NotBlank` 사용 — 가장 엄격하게 검사

---

## 4. GlobalExceptionHandler — handleValidation()

### 오늘 직접 작성한 최종 코드

```java
@ExceptionHandler(MethodArgumentNotValidException.class)
public ResponseEntity<ApiResponse<Void>> handleValidation(MethodArgumentNotValidException e) {
    String message = e.getBindingResult().getFieldErrors().stream()
            .map(error -> error.getField() + ": " + error.getDefaultMessage())
            .collect(Collectors.joining(" | "));
    return ResponseEntity
            .status(HttpStatus.BAD_REQUEST)
            .body(ApiResponse.error(message));
}
```

### 각 단계 분석

```java
e.getBindingResult()
// BindingResult — 검사 결과 전체 보관 객체

.getFieldErrors()
// List<FieldError> — 실패한 필드별 오류 목록

.stream()
// Stream<FieldError> — 파이프라인 열기

.map(error -> error.getField() + ": " + error.getDefaultMessage())
// Stream<String> — 각 FieldError를 "필드명: 메시지" 문자열로 변환
// FieldError가 가진 두 값을 조합 → 람다 필수 (메서드 레퍼런스 불가)

.collect(Collectors.joining(" | "))
// String — 모든 메시지를 " | "로 구분하여 하나로 합침
```

---

## 5. 실행 결과 예시

### 요청 (잘못된 값)
```json
{
  "customerName": "",
  "productName": "노트북",
  "quantity": -1,
  "totalPrice": 1500000
}
```

### 응답 (HTTP 400)
```json
{
  "success": false,
  "message": "customerName: 고객명은 필수입니다. | quantity: 수량은 1 이상이어야 합니다."
}
```

---

## 6. 메서드 레퍼런스 vs 람다 선택 기준

| 상황 | 코드 | 형태 |
|------|------|------|
| 하나의 메서드만 호출 | `map(FieldError::getDefaultMessage)` | 메서드 레퍼런스 |
| **두 값 이상 조합** | `map(error -> error.getField() + ": " + error.getDefaultMessage())` | **람다** |

> **규칙:** 변환에 값이 **2개 이상** 필요하면 람다를 써야 한다.

---

## 7. Collectors.joining() 3가지 형태

```java
// 형태 1 — 그냥 붙이기
.collect(Collectors.joining())
// "고객명은 필수입니다.수량은 필수입니다."

// 형태 2 — 구분자
.collect(Collectors.joining(" | "))
// "고객명은 필수입니다. | 수량은 필수입니다."

// 형태 3 — 구분자 + 앞/뒤 감싸기
.collect(Collectors.joining(" | ", "[", "]"))
// "[고객명은 필수입니다. | 수량은 필수입니다.]"
```

---

## 8. @RestControllerAdvice vs @ControllerAdvice

| | `@ControllerAdvice` | `@RestControllerAdvice` |
|---|---|---|
| 응답 형식 | View (HTML) 반환 가능 | JSON 자동 직렬화 |
| 구성 | `@ControllerAdvice` | `@ControllerAdvice` + `@ResponseBody` |
| 사용처 | MVC 웹 앱 | REST API 서버 |

> 현재 프로젝트는 REST API이므로 `@RestControllerAdvice` 사용

---

## 9. 주요 유효성 어노테이션 치트시트

| 어노테이션 | 대상 | 설명 |
|-----------|------|------|
| `@NotNull` | 모든 타입 | null 불가 |
| `@NotEmpty` | String, Collection | null + 빈값 불가 |
| `@NotBlank` | String | null + 빈값 + 공백만 불가 |
| `@Size(min, max)` | String, Collection | 크기 범위 |
| `@Min(value)` | 숫자 | 최솟값 |
| `@Max(value)` | 숫자 | 최댓값 |
| `@DecimalMin(value)` | BigDecimal | 최솟값 (소수 포함) |
| `@Email` | String | 이메일 형식 |
| `@Pattern(regexp)` | String | 정규식 |
| `@Positive` | 숫자 | 양수만 (0 불가) |
| `@PositiveOrZero` | 숫자 | 0 이상 |
