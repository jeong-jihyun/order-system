// ============================================================
// Order Exchange System ? Jenkinsfile (����ȭ)
//
// ����ȭ �׸�:
//   1. Build&Test: ���񽺺� Gradle 6ȸ �� 1ȸ ���� ���� (--parallel)
//   2. JAR Build:  bootJar�� 1ȸ ���� ����
//   3. Docker:     BuildKit(DOCKER_BUILDKIT=1) Ȱ��ȭ ? ���̾� ĳ�� Ȱ��
//   4. MySQL ���? -p exchange �÷��� �߰� (�ùٸ� �����̳� ����)
//   5. Health Check: services.each ���� �� parallel ���� Ȯ��
// ============================================================
pipeline {
    agent any

    environment {
        REGISTRY        = "${env.DOCKER_REGISTRY ?: 'localhost:5000'}"
        PROJECT         = "exchange"
        COMPOSE_FILE    = "docker-compose.yml"
        COMPOSE_P       = "exchange"
        SERVICES        = "api-gateway order-service account-service market-data-service trading-engine settlement-service"
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
                echo "üũ�ƿ� �Ϸ� ? branch=${env.BRANCH_NAME}, commit=${env.GIT_COMMIT_SHORT}"
            }
        }

        stage('Prepare') {
            steps {
                sh 'chmod +x gradlew'
            }
        }

        // �� ���� �׽�Ʈ ? JVM 1ȸ �⵿, ���� ���?�ߺ� ������ ����
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

        // �� ���� bootJar ���� ? 1ȸ Gradle ����
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

        // �� Docker �̹��� ���� ���� (BuildKit + cache-from)
        stage('Docker Build') {
            parallel {
                stage('build: api-gateway') {
                    steps {
                        sh """
                            docker build \
                              --build-arg SERVICE_DIR=api-gateway \
                              --build-arg JAR_NAME=api-gateway \
                              --cache-from ${REGISTRY}/${PROJECT}/api-gateway:latest \
                              -f docker/Dockerfile.runtime \
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
                              -f docker/Dockerfile.runtime \
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
                              -f docker/Dockerfile.runtime \
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
                              -f docker/Dockerfile.runtime \
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
                              -f docker/Dockerfile.runtime \
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
                              -f docker/Dockerfile.runtime \
                              -t ${REGISTRY}/${PROJECT}/settlement-service:${IMAGE_TAG} \
                              -t ${REGISTRY}/${PROJECT}/settlement-service:latest \
                              .
                        """
                    }
                }
            }
        }

        // �� �����̳� ��ü ���� + ������ �⵿
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
                // Kafka/Zookeeper 볼륨 ?�거 ??ClusterID 불일�?방�? (InconsistentClusterIdException)
                // zookeeper-data/log???�께 ??��?�야 kafka-data?� ClusterID가 ?�치
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
                        echo "MySQL ���?��... (\$i/12)"
                        sleep 5
                    done
                """
            }
        }

        // �� ����ũ�μ��� ���� ����
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

        // �� �ｺüũ ? 6�� ���� ���� Ȯ�� (���� 60�� �� ���� �� 10~30��)
        stage('Health Check') {
            steps {
                script {
                    def checks = [:]
                    // key = ?�제 컨테?�너�??��???exchange-{key}), value = ?�트
                    def services = [
                        'api-gateway':     8080,
                        'order-service':   8081,
                        'account-service': 8082,
                        'market-data':     8083,
                        'trading-engine':  8084,
                        'settlement-service': 8085
                    ]
                    services.each { name, port ->
                        def svcName = name
                        def svcPort = port
                        checks[svcName] = {
                            retry(6) {
                                sleep(time: 10, unit: 'SECONDS')
                                sh "curl -sf http://exchange-${svcName}:${svcPort}/actuator/health | grep -q '\"status\":\"UP\"' || exit 1"
                            }
                            echo "${svcName} ?�스체크 ?�과"
                        }
                    }
                    parallel checks
                }
            }
        }
    }

    post {
        success {
            echo "���������� ���� ? branch=${env.BRANCH_NAME}, tag=${env.IMAGE_TAG}"
        }
        failure {
            echo "���������� ���� ? �α׸� Ȯ���ϼ���."
            sh(script: "docker compose -p exchange logs --tail=50", returnStatus: true)
        }
        always {
            sh 'docker image prune -f || true'
        }
    }
}
