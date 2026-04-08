rootProject.name = "order-system"

// Shared Libraries
include("shared:common-lib")

// Microservices
include("services:order-service")
include("services:account-service")
include("services:market-data-service")
include("services:trading-engine")
include("services:settlement-service")
include("services:api-gateway")

// Legacy monolith (Phase 2에서 order-service로 완전 이전 후 제거 예정)
include("backend")
