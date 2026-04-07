# deploy.ps1 — order-system 배포 스크립트
# 사용법: .\deploy.ps1 [옵션]
#   .\deploy.ps1           — 기본 배포 (앱 컨테이너 시작, Jenkins 포함)
#   .\deploy.ps1 -All      — 앱 컨테이너 전체 재빌드 (Jenkins 제외)
#   .\deploy.ps1 -Backend  — 백엔드만 재빌드 배포
#   .\deploy.ps1 -Frontend — 프론트엔드만 재빌드 배포
#   .\deploy.ps1 -Jenkins  — Jenkins만 재빌드 및 재시작 (Dockerfile 변경 시)
#   .\deploy.ps1 -Status   — 컨테이너 상태만 확인
#   .\deploy.ps1 -Down     — 전체 종료
#   .\deploy.ps1 -Reset    — 전체 종료 + 볼륨 삭제 (DB 초기화)

param(
    [switch]$All,
    [switch]$Backend,
    [switch]$Frontend,
    [switch]$Jenkins,
    [switch]$Status,
    [switch]$Down,
    [switch]$Reset
)

# ─────────────────────────────────────────────
# 설정
# ─────────────────────────────────────────────
$PROJECT_DIR   = "d:\order-system"
$COMPOSE_FILE  = "$PROJECT_DIR\docker-compose.yml"
$HEALTH_URL    = "http://localhost:8080/actuator/health"
$FRONTEND_URL  = "http://localhost:3000"
$JENKINS_URL   = "http://localhost:8090"

# ─────────────────────────────────────────────
# 유틸 함수
# ─────────────────────────────────────────────
function Write-Header {
    param([string]$Title)
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
}

function Write-Step {
    param([string]$Message)
    Write-Host "[→] $Message" -ForegroundColor Yellow
}

function Write-Success {
    param([string]$Message)
    Write-Host "[✓] $Message" -ForegroundColor Green
}

function Write-Fail {
    param([string]$Message)
    Write-Host "[✗] $Message" -ForegroundColor Red
}

function Write-Info {
    param([string]$Message)
    Write-Host "    $Message" -ForegroundColor Gray
}

# ─────────────────────────────────────────────
# Docker Desktop 실행 확인
# ─────────────────────────────────────────────
function Check-Docker {
    Write-Step "Docker 상태 확인 중..."
    $result = docker info 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Fail "Docker Desktop이 실행 중이지 않습니다."
        Write-Info "Docker Desktop을 실행한 후 다시 시도해주세요."
        exit 1
    }
    Write-Success "Docker 실행 중"
}

# ─────────────────────────────────────────────
# Kafka NodeExists 오류 방지 처리
# ─────────────────────────────────────────────
function Fix-Kafka {
    $kafkaStatus = docker compose ps kafka --format "{{.Status}}" 2>&1
    if ($kafkaStatus -notmatch "Up") {
        Write-Step "Kafka 재생성 중 (NodeExists 오류 방지)..."
        docker compose rm -f kafka | Out-Null
        docker compose up -d kafka | Out-Null
        Start-Sleep -Seconds 5
        Write-Success "Kafka 재생성 완료"
    }
}

# ─────────────────────────────────────────────
# 백엔드 헬스체크
# ─────────────────────────────────────────────
function Wait-Backend {
    Write-Step "백엔드 헬스체크 대기 중..."
    $maxRetry = 30
    $retry = 0
    while ($retry -lt $maxRetry) {
        try {
            $response = Invoke-WebRequest -Uri $HEALTH_URL -TimeoutSec 3 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Success "백엔드 정상 응답 확인"
                return
            }
        } catch {}
        $retry++
        Write-Info "대기 중... ($retry/$maxRetry)"
        Start-Sleep -Seconds 5
    }
    Write-Fail "백엔드 헬스체크 실패 — 로그를 확인하세요:"
    Write-Info "  docker compose logs spring-app --tail=30"
}

# ─────────────────────────────────────────────
# 최종 접속 정보 출력
# ─────────────────────────────────────────────
function Show-Urls {
    Write-Host ""
    Write-Host "  서비스 접속 주소" -ForegroundColor Cyan
    Write-Host "  ─────────────────────────────" -ForegroundColor Cyan
    Write-Host "  프론트엔드  : $FRONTEND_URL" -ForegroundColor White
    Write-Host "  Swagger UI  : http://localhost:8080/swagger-ui.html" -ForegroundColor White
    Write-Host "  Kafdrop     : http://localhost:9000" -ForegroundColor White
    Write-Host "  Jenkins     : $JENKINS_URL" -ForegroundColor White
    Write-Host "  ─────────────────────────────" -ForegroundColor Cyan
    Write-Host ""
}

# ─────────────────────────────────────────────
# 컨테이너 상태 출력
# ─────────────────────────────────────────────
function Show-Status {
    Write-Header "컨테이너 상태"
    Set-Location $PROJECT_DIR
    docker compose ps
}

# ─────────────────────────────────────────────
# 메인 로직
# ─────────────────────────────────────────────
Set-Location $PROJECT_DIR

# 상태만 확인
if ($Status) {
    Show-Status
    exit 0
}

# 전체 종료
if ($Down) {
    Write-Header "전체 종료"
    Write-Step "컨테이너 종료 중..."
    docker compose down
    Write-Success "종료 완료"
    exit 0
}

# 전체 초기화 (볼륨 삭제)
if ($Reset) {
    Write-Header "전체 초기화 (DB 데이터 삭제 포함)"
    $confirm = Read-Host "⚠️  DB 데이터가 모두 삭제됩니다. 계속하시겠습니까? (y/N)"
    if ($confirm -ne "y") {
        Write-Host "취소됐습니다."
        exit 0
    }
    Write-Step "컨테이너 및 볼륨 삭제 중..."
    docker compose down -v
    Write-Success "초기화 완료"
    exit 0
}

# ─────────────────────────────────────────────
# 배포 시작
# ─────────────────────────────────────────────
Write-Header "order-system 배포"
Check-Docker

# 백엔드만 배포
if ($Backend) {
    Write-Step "백엔드 이미지 재빌드 중..."
    docker compose up -d --build spring-app
    Wait-Backend
    Write-Success "백엔드 배포 완료"
    Show-Urls
    exit 0
}

# 프론트엔드만 배포
if ($Frontend) {
    Write-Step "프론트엔드 이미지 재빌드 중..."
    docker compose up -d --build frontend
    Write-Success "프론트엔드 배포 완료"
    Show-Urls
    exit 0
}

# Jenkins만 재빌드 및 재시작 (Dockerfile 변경 시에만 사용)
if ($Jenkins) {
    Write-Header "Jenkins 재빌드 및 재시작"
    Write-Step "Jenkins 컨테이너 종료 중..."
    docker compose stop jenkins
    docker compose rm -f jenkins

    Write-Step "Jenkins 이미지 재빌드 중... (3~5분 소요)"
    docker compose build jenkins

    Write-Step "Jenkins 시작 중..."
    docker compose up -d jenkins

    Write-Success "Jenkins 재시작 완료"
    Write-Info "접속: $JENKINS_URL"
    exit 0
}

# 전체 재빌드 배포 (앱 컨테이너만, Jenkins 제외)
if ($All) {
    Write-Step "앱 컨테이너 종료 중 (Jenkins 유지)..."
    docker compose stop mysql redis zookeeper kafka kafdrop spring-app frontend
    docker compose rm -f mysql redis zookeeper kafka kafdrop spring-app frontend

    Write-Step "앱 이미지 재빌드 및 시작 중..."
    docker compose up -d --build mysql redis zookeeper kafka kafdrop spring-app frontend

    Fix-Kafka
    Wait-Backend

    Write-Header "배포 완료"
    docker compose ps
    Show-Urls
    exit 0
}

# 기본 배포 — 꺼진 컨테이너만 시작
Write-Step "컨테이너 상태 확인 중..."
docker compose ps

Write-Step "중지된 컨테이너 시작 중..."
docker compose start 2>&1 | Out-Null

Fix-Kafka

Write-Step "spring-app 시작 확인 중..."
$backendStatus = docker compose ps spring-app --format "{{.Status}}" 2>&1
if ($backendStatus -notmatch "Up") {
    docker compose up -d spring-app | Out-Null
}

Wait-Backend

Write-Header "배포 완료"
docker compose ps
Show-Urls
