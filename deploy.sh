#!/bin/bash
# deploy.sh — order-system 배포 스크립트 (Linux / macOS)
# 사용법: ./deploy.sh [옵션]
#   ./deploy.sh            — 기본 배포 (앱 컨테이너 시작, Jenkins 포함)
#   ./deploy.sh --all      — 앱 컨테이너 전체 재빌드 (Jenkins 제외)
#   ./deploy.sh --backend  — 백엔드만 재빌드 배포
#   ./deploy.sh --frontend — 프론트엔드만 재빌드 배포
#   ./deploy.sh --jenkins  — Jenkins만 재빌드 및 재시작 (Dockerfile 변경 시)
#   ./deploy.sh --status   — 컨테이너 상태만 확인
#   ./deploy.sh --down     — 전체 종료
#   ./deploy.sh --reset    — 전체 종료 + 볼륨 삭제 (DB 초기화)

set -e

# ─────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
HEALTH_URL="http://localhost:8080/actuator/health"
FRONTEND_URL="http://localhost:3000"
JENKINS_URL="http://localhost:8090"

# ─────────────────────────────────────────────
# 색상 출력 유틸
# ─────────────────────────────────────────────
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

write_header() {
    echo ""
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}========================================${NC}"
}

write_step() {
    echo -e "${YELLOW}[→] $1${NC}"
}

write_success() {
    echo -e "${GREEN}[✓] $1${NC}"
}

write_fail() {
    echo -e "${RED}[✗] $1${NC}"
}

write_info() {
    echo -e "${GRAY}    $1${NC}"
}

# ─────────────────────────────────────────────
# Docker 실행 확인
# ─────────────────────────────────────────────
check_docker() {
    write_step "Docker 상태 확인 중..."
    if ! docker info > /dev/null 2>&1; then
        write_fail "Docker가 실행 중이지 않습니다."
        write_info "Docker를 실행한 후 다시 시도해주세요."
        exit 1
    fi
    write_success "Docker 실행 중"
}

# ─────────────────────────────────────────────
# Kafka NodeExists 오류 방지 처리
# ─────────────────────────────────────────────
fix_kafka() {
    local kafka_status
    kafka_status=$(docker compose ps kafka --format "{{.Status}}" 2>/dev/null || echo "")
    if [[ "$kafka_status" != *"Up"* ]]; then
        write_step "Kafka 재생성 중 (NodeExists 오류 방지)..."
        docker compose rm -f kafka > /dev/null 2>&1 || true
        docker compose up -d kafka > /dev/null 2>&1
        sleep 5
        write_success "Kafka 재생성 완료"
    fi
}

# ─────────────────────────────────────────────
# 백엔드 헬스체크 대기
# ─────────────────────────────────────────────
wait_backend() {
    write_step "백엔드 헬스체크 대기 중..."
    local max_retry=30
    local retry=0
    while [ $retry -lt $max_retry ]; do
        if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
            write_success "백엔드 정상 응답 확인"
            return 0
        fi
        retry=$((retry + 1))
        write_info "대기 중... ($retry/$max_retry)"
        sleep 5
    done
    write_fail "백엔드 헬스체크 실패 — 로그를 확인하세요:"
    write_info "  docker compose logs spring-app --tail=30"
    return 1
}

# ─────────────────────────────────────────────
# 접속 주소 출력
# ─────────────────────────────────────────────
show_urls() {
    echo ""
    echo -e "${CYAN}  서비스 접속 주소${NC}"
    echo -e "${CYAN}  ─────────────────────────────${NC}"
    echo "  프론트엔드  : $FRONTEND_URL"
    echo "  Swagger UI  : http://localhost:8080/swagger-ui.html"
    echo "  Kafdrop     : http://localhost:9000"
    echo "  Jenkins     : $JENKINS_URL"
    echo -e "${CYAN}  ─────────────────────────────${NC}"
    echo ""
}

# ─────────────────────────────────────────────
# 컨테이너 상태 출력
# ─────────────────────────────────────────────
show_status() {
    write_header "컨테이너 상태"
    cd "$PROJECT_DIR"
    docker compose ps
}

# ─────────────────────────────────────────────
# 메인 로직
# ─────────────────────────────────────────────
cd "$PROJECT_DIR"

case "$1" in
    --status)
        show_status
        exit 0
        ;;

    --down)
        write_header "전체 종료"
        write_step "컨테이너 종료 중..."
        docker compose down
        write_success "종료 완료"
        exit 0
        ;;

    --reset)
        write_header "전체 초기화 (DB 데이터 삭제 포함)"
        read -rp "⚠️  DB 데이터가 모두 삭제됩니다. 계속하시겠습니까? (y/N): " confirm
        if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
            echo "취소됐습니다."
            exit 0
        fi
        write_step "컨테이너 및 볼륨 삭제 중..."
        docker compose down -v
        write_success "초기화 완료"
        exit 0
        ;;

    --backend)
        write_header "백엔드 배포"
        check_docker
        write_step "백엔드 이미지 재빌드 중..."
        docker compose up -d --build spring-app
        wait_backend
        write_success "백엔드 배포 완료"
        show_urls
        exit 0
        ;;

    --frontend)
        write_header "프론트엔드 배포"
        check_docker
        write_step "프론트엔드 이미지 재빌드 중..."
        docker compose up -d --build frontend
        write_success "프론트엔드 배포 완료"
        show_urls
        exit 0
        ;;

    --jenkins)
        write_header "Jenkins 재빌드 및 재시작"
        check_docker
        write_step "Jenkins 컨테이너 종료 중..."
        docker compose stop jenkins
        docker compose rm -f jenkins
        write_step "Jenkins 이미지 재빌드 중... (3~5분 소요)"
        docker compose build jenkins
        write_step "Jenkins 시작 중..."
        docker compose up -d jenkins
        write_success "Jenkins 재시작 완료"
        write_info "접속: $JENKINS_URL"
        exit 0
        ;;

    --all)
        write_header "앱 전체 재빌드 배포 (Jenkins 제외)"
        check_docker
        write_step "앱 컨테이너 종료 중 (Jenkins 유지)..."
        docker compose stop mysql redis zookeeper kafka kafdrop spring-app frontend
        docker compose rm -f mysql redis zookeeper kafka kafdrop spring-app frontend
        write_step "앱 이미지 재빌드 및 시작 중..."
        docker compose up -d --build mysql redis zookeeper kafka kafdrop spring-app frontend
        fix_kafka
        wait_backend
        write_header "배포 완료"
        docker compose ps
        show_urls
        exit 0
        ;;

    "")
        # 기본 배포 — 꺼진 컨테이너만 시작
        write_header "order-system 배포"
        check_docker
        write_step "컨테이너 상태 확인 중..."
        docker compose ps
        write_step "중지된 컨테이너 시작 중..."
        docker compose start 2>/dev/null || true
        fix_kafka
        # spring-app 미실행 시 시작
        backend_status=$(docker compose ps spring-app --format "{{.Status}}" 2>/dev/null || echo "")
        if [[ "$backend_status" != *"Up"* ]]; then
            docker compose up -d spring-app > /dev/null 2>&1
        fi
        wait_backend
        write_header "배포 완료"
        docker compose ps
        show_urls
        exit 0
        ;;

    *)
        echo "알 수 없는 옵션: $1"
        echo "사용법: ./deploy.sh [--all|--backend|--frontend|--jenkins|--status|--down|--reset]"
        exit 1
        ;;
esac
