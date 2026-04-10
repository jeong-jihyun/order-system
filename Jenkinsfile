// ============================================================
// Order Exchange System — Jenkinsfile (변경 감지 최적화)
//
// 최적화 항목:
//   1. 변경 감지: git diff로 변경된 서비스만 빌드/배포
//   2. Build&Test: 변경 서비스만 Gradle 테스트
//   3. JAR Build:  변경 서비스만 bootJar
//   4. Docker:     변경 서비스만 이미지 빌드 (dynamic parallel)
//   5. Deploy:     변경 서비스만 컨테이너 재시작 (dynamic parallel)
//   6. 공유 파일(docker/, build.gradle, Jenkinsfile 등) 변경 시 전체 빌드
// ============================================================
pipeline {
    agent any

    environment {
        REGISTRY     = "${env.DOCKER_REGISTRY ?: 'localhost:5000'}"
        PROJECT      = "exchange"
        COMPOSE_FILE = "docker-compose.yml"
        COMPOSE_P    = "exchange"
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    stages {

        stage('Checkout') {
            steps {
                checkout scm
                script {
                    env.GIT_COMMIT_SHORT = sh(
                        script: 'git rev-parse --short HEAD',
                        returnStdout: true
                    ).trim()
                    env.IMAGE_TAG = "${env.BRANCH_NAME ?: 'main'}-${env.GIT_COMMIT_SHORT}"
                }
                echo "체크아웃 완료 — branch=${env.BRANCH_NAME}, commit=${env.GIT_COMMIT_SHORT}"
            }
        }

        stage('Prepare') {
            steps {
                sh 'chmod +x gradlew'
            }
        }

        // 변경된 서비스 감지 — 이후 모든 스테이지는 CHANGED_SERVICES만 처리
        stage('Detect Changes') {
            steps {
                script {
                    def changedFiles = sh(
                        script: 'git diff --name-only HEAD~1 HEAD 2>/dev/null | tr "\\n" " " || echo "ALL"',
                        returnStdout: true
                    ).trim()

                    echo "변경 파일: ${changedFiles}"

                    def allServices = [
                        'api-gateway',
                        'order-service',
                        'account-service',
                        'market-data-service',
                        'trading-engine',
                        'settlement-service'
                    ]

                    // 공유 파일 변경 시 전체 재빌드
                    def rebuildAll = changedFiles == 'ALL' ||
                        changedFiles.contains('docker/') ||
                        changedFiles.contains('build.gradle') ||
                        changedFiles.contains('settings.gradle') ||
                        changedFiles.contains('gradle/') ||
                        changedFiles.contains('Jenkinsfile')

                    def changed = []
                    if (rebuildAll) {
                        changed = allServices
                        echo "공유 파일 변경 → 전체 빌드"
                    } else {
                        allServices.each { svc ->
                            if (changedFiles.contains("services/${svc}")) {
                                changed << svc
                            }
                        }
                        if (changed.isEmpty()) {
                            changed = allServices
                            echo "변경 감지 없음 → 안전을 위해 전체 빌드"
                        }
                    }

                    env.CHANGED_SERVICES = changed.join(',')
                    echo "빌드 대상: ${env.CHANGED_SERVICES}"
                }
            }
        }

        // 변경된 서비스만 테스트 (api-gateway 제외)
        stage('Build & Test') {
            steps {
                script {
                    def changed = env.CHANGED_SERVICES.split(',').toList()
                    def tasks = changed
                        .findAll { it != 'api-gateway' }
                        .collect { ":services:${it}:test" }
                        .join(' ')

                    if (tasks) {
                        sh """
                            ./gradlew ${tasks} \
                                --no-daemon \
                                --continue \
                                --parallel
                        """
                    } else {
                        echo "테스트 대상 없음 — 스킵"
                    }
                }
            }
            post {
                always {
                    junit allowEmptyResults: true,
                          testResults: 'services/*/build/test-results/**/*.xml'
                }
            }
        }

        // 변경된 서비스만 bootJar 빌드
        stage('JAR Build') {
            steps {
                script {
                    def changed = env.CHANGED_SERVICES.split(',').toList()
                    def tasks = changed.collect { ":services:${it}:bootJar" }.join(' ')
                    sh """
                        ./gradlew ${tasks} \
                            -x test \
                            --no-daemon \
                            --parallel
                    """
                }
            }
        }

        // 변경된 서비스만 Docker 이미지 빌드 (dynamic parallel)
        stage('Docker Build') {
            steps {
                script {
                    def changed = env.CHANGED_SERVICES.split(',').toList()
                    def builds = [:]
                    changed.each { svc ->
                        def s = svc
                        builds["build: ${s}"] = {
                            sh """
                                docker build \
                                  --build-arg SERVICE_DIR=${s} \
                                  --build-arg JAR_NAME=${s} \
                                  -f docker/Dockerfile.runtime \
                                  -t ${REGISTRY}/${PROJECT}/${s}:${IMAGE_TAG} \
                                  -t ${REGISTRY}/${PROJECT}/${s}:latest \
                                  .
                            """
                        }
                    }
                    parallel builds
                }
            }
        }

        // 인프라(MySQL, Redis, Kafka 등) 기동
        stage('Infrastructure Up') {
            steps {
                sh """
                    docker rm -f \
                        exchange-zookeeper exchange-kafka exchange-redis \
                        exchange-mysql exchange-kafdrop \
                        exchange-api-gateway exchange-order-service \
                        exchange-account-service exchange-market-data \
                        exchange-trading-engine exchange-settlement-service \
                        2>/dev/null || true
                """
                // Kafka/Zookeeper 볼륨 제거 → ClusterID 불일치 방지 (InconsistentClusterIdException)
                sh "docker volume rm exchange_kafka-data exchange_zookeeper-data exchange_zookeeper-log 2>/dev/null; true"
                sh """
                    docker compose -p ${COMPOSE_P} up -d \
                        mysql redis zookeeper kafka kafdrop
                """
                sh """
                    for i in \$(seq 1 12); do
                        docker compose -p ${COMPOSE_P} exec -T mysql \
                            mysqladmin ping -uroot -ppassword --silent 2>/dev/null \
                            && echo "MySQL Ready" && break
                        echo "MySQL 대기... (\$i/12)"
                        sleep 5
                    done
                """
            }
        }

        // 변경된 서비스만 배포 (dynamic parallel)
        stage('Deploy Services') {
            steps {
                script {
                    def changed = env.CHANGED_SERVICES.split(',').toList()
                    def deploys = [:]
                    changed.each { svc ->
                        def s = svc
                        deploys["deploy: ${s}"] = {
                            sh "docker compose -p ${COMPOSE_P} up -d --no-deps ${s}"
                        }
                    }
                    parallel deploys
                }
            }
        }

        // Jenkins 컨테이너를 exchange 네트워크에 연결 (Health Check용)
        stage('Network Connect') {
            steps {
                sh "docker network connect ${COMPOSE_P}_exchange-net exchange-jenkins 2>/dev/null || true"
            }
        }

        // 변경된 서비스만 헬스체크 (dynamic parallel)
        stage('Health Check') {
            steps {
                script {
                    def portMap = [
                        'api-gateway':         [host: 'api-gateway',        port: 8080],
                        'order-service':       [host: 'order-service',      port: 8081],
                        'account-service':     [host: 'account-service',    port: 8082],
                        'market-data-service': [host: 'market-data',        port: 8083],
                        'trading-engine':      [host: 'trading-engine',     port: 8084],
                        'settlement-service':  [host: 'settlement-service', port: 8085]
                    ]
                    def changed = env.CHANGED_SERVICES.split(',').toList()
                    def checks = [:]
                    changed.each { svc ->
                        def info = portMap[svc]
                        if (info) {
                            def svcHost = info.host
                            def svcPort = info.port
                            checks[svc] = {
                                retry(6) {
                                    sleep(time: 10, unit: 'SECONDS')
                                    sh "curl -sf http://exchange-${svcHost}:${svcPort}/actuator/health | grep -q '\"status\":\"UP\"' || exit 1"
                                }
                                echo "${svc} 헬스체크 성공"
                            }
                        }
                    }
                    parallel checks
                }
            }
        }
    }

    post {
        success {
            echo "빌드 성공 — branch=${env.BRANCH_NAME}, tag=${env.IMAGE_TAG}, 서비스=${env.CHANGED_SERVICES}"
        }
        failure {
            echo "빌드 실패 — 로그를 확인하세요."
            sh(script: "docker compose -p exchange logs --tail=50", returnStatus: true)
        }
        always {
            sh 'docker image prune -f || true'
        }
    }
}
