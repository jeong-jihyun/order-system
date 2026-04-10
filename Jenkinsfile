// ============================================================
// Order Exchange System ? Jenkinsfile (최적화)
//
// 최적화 항목:
//   1. Build&Test: 서비스별 Gradle 6회 → 1회 통합 실행 (--parallel)
//   2. JAR Build:  bootJar도 1회 통합 실행
//   3. Docker:     BuildKit(DOCKER_BUILDKIT=1) 활성화 ? 레이어 캐시 활용
//   4. MySQL 대기: -p exchange 플래그 추가 (올바른 컨테이너 지정)
//   5. Health Check: services.each 순차 → parallel 병렬 확인
// ============================================================
pipeline {
    agent any

    environment {
        REGISTRY        = "${env.DOCKER_REGISTRY ?: 'localhost:5000'}"
        PROJECT         = "exchange"
        COMPOSE_FILE    = "docker-compose.yml"
        COMPOSE_P       = "exchange"
        SERVICES        = "api-gateway order-service account-service market-data-service trading-engine settlement-service"
        DOCKER_BUILDKIT = "1"
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
                    env.IMAGE_TAG = "${env.BRANCH_NAME}-${env.GIT_COMMIT_SHORT}"
                }
                echo "체크아웃 완료 ? branch=${env.BRANCH_NAME}, commit=${env.GIT_COMMIT_SHORT}"
            }
        }

        stage('Prepare') {
            steps {
                sh 'chmod +x gradlew'
            }
        }

        // ③ 통합 테스트 ? JVM 1회 기동, 공통 모듈 중복 컴파일 제거
        stage('Build & Test') {
            steps {
                sh '''
                    ./gradlew \
                        :services:order-service:test \
                        :services:account-service:test \
                        :services:market-data-service:test \
                        :services:trading-engine:test \
                        :services:settlement-service:test \
                        -x :backend:test \
                        --no-daemon \
                        --continue \
                        --parallel
                '''
            }
            post {
                always {
                    junit allowEmptyResults: true,
                          testResults: 'services/*/build/test-results/**/*.xml'
                }
            }
        }

        // ④ 통합 bootJar 빌드 ? 1회 Gradle 실행
        stage('JAR Build') {
            steps {
                sh '''
                    ./gradlew \
                        :services:api-gateway:bootJar \
                        :services:order-service:bootJar \
                        :services:account-service:bootJar \
                        :services:market-data-service:bootJar \
                        :services:trading-engine:bootJar \
                        :services:settlement-service:bootJar \
                        -x test \
                        --no-daemon \
                        --parallel
                '''
            }
        }

        // ⑤ Docker 이미지 병렬 빌드 (BuildKit + cache-from)
        stage('Docker Build') {
            parallel {
                stage('build: api-gateway') {
                    steps {
                        sh """
                            docker build \
                              --build-arg SERVICE_DIR=api-gateway \
                              --build-arg JAR_NAME=api-gateway \
                              --cache-from ${REGISTRY}/${PROJECT}/api-gateway:latest \
                              -f docker/Dockerfile \
                              -t ${REGISTRY}/${PROJECT}/api-gateway:${IMAGE_TAG} \
                              -t ${REGISTRY}/${PROJECT}/api-gateway:latest \
                              .
                        """
                    }
                }
                stage('build: order-service') {
                    steps {
                        sh """
                            docker build \
                              --build-arg SERVICE_DIR=order-service \
                              --build-arg JAR_NAME=order-service \
                              --cache-from ${REGISTRY}/${PROJECT}/order-service:latest \
                              -f docker/Dockerfile \
                              -t ${REGISTRY}/${PROJECT}/order-service:${IMAGE_TAG} \
                              -t ${REGISTRY}/${PROJECT}/order-service:latest \
                              .
                        """
                    }
                }
                stage('build: account-service') {
                    steps {
                        sh """
                            docker build \
                              --build-arg SERVICE_DIR=account-service \
                              --build-arg JAR_NAME=account-service \
                              --cache-from ${REGISTRY}/${PROJECT}/account-service:latest \
                              -f docker/Dockerfile \
                              -t ${REGISTRY}/${PROJECT}/account-service:${IMAGE_TAG} \
                              -t ${REGISTRY}/${PROJECT}/account-service:latest \
                              .
                        """
                    }
                }
                stage('build: market-data-service') {
                    steps {
                        sh """
                            docker build \
                              --build-arg SERVICE_DIR=market-data-service \
                              --build-arg JAR_NAME=market-data-service \
                              --cache-from ${REGISTRY}/${PROJECT}/market-data-service:latest \
                              -f docker/Dockerfile \
                              -t ${REGISTRY}/${PROJECT}/market-data-service:${IMAGE_TAG} \
                              -t ${REGISTRY}/${PROJECT}/market-data-service:latest \
                              .
                        """
                    }
                }
                stage('build: trading-engine') {
                    steps {
                        sh """
                            docker build \
                              --build-arg SERVICE_DIR=trading-engine \
                              --build-arg JAR_NAME=trading-engine \
                              --cache-from ${REGISTRY}/${PROJECT}/trading-engine:latest \
                              -f docker/Dockerfile \
                              -t ${REGISTRY}/${PROJECT}/trading-engine:${IMAGE_TAG} \
                              -t ${REGISTRY}/${PROJECT}/trading-engine:latest \
                              .
                        """
                    }
                }
                stage('build: settlement-service') {
                    steps {
                        sh """
                            docker build \
                              --build-arg SERVICE_DIR=settlement-service \
                              --build-arg JAR_NAME=settlement-service \
                              --cache-from ${REGISTRY}/${PROJECT}/settlement-service:latest \
                              -f docker/Dockerfile \
                              -t ${REGISTRY}/${PROJECT}/settlement-service:${IMAGE_TAG} \
                              -t ${REGISTRY}/${PROJECT}/settlement-service:latest \
                              .
                        """
                    }
                }
            }
        }

        // ⑥ 컨테이너 전체 제거 + 인프라 기동
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
                sh """
                    docker compose -p ${COMPOSE_P} up -d \
                        mysql redis zookeeper kafka kafdrop
                """
                sh """
                    for i in \$(seq 1 12); do
                        docker compose -p ${COMPOSE_P} exec -T mysql \
                            mysqladmin ping -uroot -ppassword --silent 2>/dev/null \
                            && echo "MySQL Ready" && break
                        echo "MySQL 대기 중... (\$i/12)"
                        sleep 5
                    done
                """
            }
        }

        // ⑦ 마이크로서비스 병렬 배포
        stage('Deploy Services') {
            parallel {
                stage('deploy: api-gateway') {
                    steps { sh "docker compose -p ${COMPOSE_P} up -d --no-deps api-gateway" }
                }
                stage('deploy: order-service') {
                    steps { sh "docker compose -p ${COMPOSE_P} up -d --no-deps order-service" }
                }
                stage('deploy: account-service') {
                    steps { sh "docker compose -p ${COMPOSE_P} up -d --no-deps account-service" }
                }
                stage('deploy: market-data-service') {
                    steps { sh "docker compose -p ${COMPOSE_P} up -d --no-deps market-data-service" }
                }
                stage('deploy: trading-engine') {
                    steps { sh "docker compose -p ${COMPOSE_P} up -d --no-deps trading-engine" }
                }
                stage('deploy: settlement-service') {
                    steps { sh "docker compose -p ${COMPOSE_P} up -d --no-deps settlement-service" }
                }
            }
        }

        // ⑧ 헬스체크 ? 6개 서비스 병렬 확인 (순차 60초 → 병렬 약 10~30초)
        stage('Health Check') {
            steps {
                script {
                    def checks = [:]
                    def services = [
                        'api-gateway':         8080,
                        'order-service':       8081,
                        'account-service':     8082,
                        'market-data-service': 8083,
                        'trading-engine':      8084,
                        'settlement-service':  8085
                    ]
                    services.each { name, port ->
                        checks[name] = {
                            retry(6) {
                                sleep(time: 10, unit: 'SECONDS')
                                sh "curl -sf http://localhost:${port}/actuator/health | grep -q '\"status\":\"UP\"' || exit 1"
                            }
                            echo "${name} 헬스체크 통과"
                        }
                    }
                    parallel checks
                }
            }
        }
    }

    post {
        success {
            echo "파이프라인 성공 ? branch=${env.BRANCH_NAME}, tag=${env.IMAGE_TAG}"
        }
        failure {
            echo "파이프라인 실패 ? 로그를 확인하세요."
            sh(script: "docker compose -p exchange logs --tail=50", returnStatus: true)
        }
        always {
            sh 'docker image prune -f || true'
        }
    }
}
