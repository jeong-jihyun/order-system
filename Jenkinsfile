// ============================================================
// Order Exchange System — Jenkinsfile
// 멀티모듈 마이크로서비스 CI/CD 파이프라인
//
// Pipeline:
//   Checkout → 전체 빌드/테스트 → Docker 이미지 병렬 빌드
//           → 인프라 기동 → 6개 서비스 병렬 배포 → 헬스체크
// ============================================================
pipeline {
    agent any

    environment {
        REGISTRY      = "${env.DOCKER_REGISTRY ?: 'localhost:5000'}"
        PROJECT       = "exchange"
        COMPOSE_FILE  = "docker-compose.yml"
        COMPOSE_P     = "exchange"
        // 배포 대상 서비스 목록
        SERVICES      = "api-gateway order-service account-service market-data-service trading-engine settlement-service"
    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 30, unit: 'MINUTES')
        disableConcurrentBuilds()
    }

    stages {

        // ① 소스코드 체크아웃
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
                echo "체크아웃 완료 — branch=${env.BRANCH_NAME}, commit=${env.GIT_COMMIT_SHORT}"
            }
        }

        // ② gradlew 실행 권한 보장 (git checkout 후 Linux 환경 대비)
        stage('Prepare') {
            steps {
                sh 'chmod +x gradlew'
            }
        }

        // ③ 전체 멀티모듈 컴파일 + 테스트 (병렬)
        stage('Build & Test') {
            parallel {

                stage('order-service') {
                    steps {
                        sh './gradlew :services:order-service:test --no-daemon -x :backend:test'
                    }
                    post {
                        always {
                            junit allowEmptyResults: true,
                                  testResults: 'services/order-service/build/test-results/**/*.xml'
                        }
                    }
                }

                stage('account-service') {
                    steps {
                        sh './gradlew :services:account-service:test --no-daemon -x :backend:test'
                    }
                    post {
                        always {
                            junit allowEmptyResults: true,
                                  testResults: 'services/account-service/build/test-results/**/*.xml'
                        }
                    }
                }

                stage('market-data-service') {
                    steps {
                        sh './gradlew :services:market-data-service:test --no-daemon -x :backend:test'
                    }
                    post {
                        always {
                            junit allowEmptyResults: true,
                                  testResults: 'services/market-data-service/build/test-results/**/*.xml'
                        }
                    }
                }

                stage('trading-engine') {
                    steps {
                        sh './gradlew :services:trading-engine:test --no-daemon -x :backend:test'
                    }
                    post {
                        always {
                            junit allowEmptyResults: true,
                                  testResults: 'services/trading-engine/build/test-results/**/*.xml'
                        }
                    }
                }

                stage('settlement-service') {
                    steps {
                        sh './gradlew :services:settlement-service:test --no-daemon -x :backend:test'
                    }
                    post {
                        always {
                            junit allowEmptyResults: true,
                                  testResults: 'services/settlement-service/build/test-results/**/*.xml'
                        }
                    }
                }
            }
        }

        // ④ Docker 이미지 병렬 빌드
        stage('Docker Build') {
            parallel {

                stage('build: api-gateway') {
                    steps {
                        sh """
                            docker build \
                              --build-arg SERVICE_DIR=api-gateway \
                              --build-arg JAR_NAME=api-gateway \
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
                              -f docker/Dockerfile \
                              -t ${REGISTRY}/${PROJECT}/settlement-service:${IMAGE_TAG} \
                              -t ${REGISTRY}/${PROJECT}/settlement-service:latest \
                              .
                        """
                    }
                }
            }
        }

        // ⑤ 인프라 기동 (mysql, redis, kafka 등)
        stage('Infrastructure Up') {
            steps {
                sh """
                    docker compose -p ${COMPOSE_P} up -d --force-recreate \
                        mysql redis zookeeper kafka kafdrop
                """
                // 인프라 Ready 대기 (최대 60초)
                sh '''
                    for i in $(seq 1 12); do
                        docker compose exec -T mysql mysqladmin ping -uroot -ppassword --silent 2>/dev/null \
                            && echo "MySQL Ready" && break
                        echo "MySQL 대기 중... ($i/12)"
                        sleep 5
                    done
                '''
            }
        }

        // ⑥ 마이크로서비스 병렬 배포 (--no-deps: 타 서비스 재시작 방지)
        stage('Deploy Services') {
            parallel {
                stage('deploy: api-gateway') {
                    steps {
                        sh "docker compose -p ${COMPOSE_P} up -d --no-deps api-gateway"
                    }
                }
                stage('deploy: order-service') {
                    steps {
                        sh "docker compose -p ${COMPOSE_P} up -d --no-deps order-service"
                    }
                }
                stage('deploy: account-service') {
                    steps {
                        sh "docker compose -p ${COMPOSE_P} up -d --no-deps account-service"
                    }
                }
                stage('deploy: market-data-service') {
                    steps {
                        sh "docker compose -p ${COMPOSE_P} up -d --no-deps market-data-service"
                    }
                }
                stage('deploy: trading-engine') {
                    steps {
                        sh "docker compose -p ${COMPOSE_P} up -d --no-deps trading-engine"
                    }
                }
                stage('deploy: settlement-service') {
                    steps {
                        sh "docker compose -p ${COMPOSE_P} up -d --no-deps settlement-service"
                    }
                }
            }
        }

        // ⑦ 헬스체크 (6개 서비스 모두 확인)
        stage('Health Check') {
            steps {
                script {
                    def services = [
                        [name: 'api-gateway',        port: 8080],
                        [name: 'order-service',       port: 8081],
                        [name: 'account-service',     port: 8082],
                        [name: 'market-data-service', port: 8083],
                        [name: 'trading-engine',      port: 8084],
                        [name: 'settlement-service',  port: 8085]
                    ]
                    services.each { svc ->
                        retry(6) {
                            sleep(time: 10, unit: 'SECONDS')
                            sh "curl -sf http://localhost:${svc.port}/actuator/health | grep -q '\"status\":\"UP\"' || exit 1"
                        }
                        echo "${svc.name} 헬스체크 통과"
                    }
                }
            }
        }
    }

    post {
        success {
            echo "파이프라인 성공 — branch=${env.BRANCH_NAME}, tag=${env.IMAGE_TAG}"
        }
        failure {
            echo "파이프라인 실패 — 로그를 확인하세요."
            sh(script: "docker compose -p exchange logs --tail=50", returnStatus: true)
        }
        always {
            // 빌드 캐시 최적화 (dangling 이미지 정리)
            sh 'docker image prune -f || true'
        }
    }
}
