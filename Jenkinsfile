pipeline {
    agent any

    environment {
        // Docker Hub 또는 로컬 레지스트리 설정
        BACKEND_IMAGE  = "order-system-spring-app"
        FRONTEND_IMAGE = "order-system-frontend"
        COMPOSE_FILE   = "docker-compose.yml"
    }

    stages {

        // ① 소스코드 체크아웃
        stage('Checkout') {
            steps {
                checkout scm
                echo "✅ 소스코드 체크아웃 완료"
            }
        }

        // ② 백엔드 테스트
        stage('Backend Test') {
            steps {
                dir('backend') {
                    sh './gradlew test --no-daemon --no-watch-fs'
                }
                echo "✅ 백엔드 테스트 완료"
            }
            post {
                always {
                    junit allowEmptyResults: true, testResults: 'backend/build/test-results/test/*.xml'
                }
            }
        }

        // ③ 프론트엔드 테스트
        stage('Frontend Test') {
            steps {
                dir('frontend') {
                    sh 'npm ci'
                    sh 'npm test -- --run --passWithNoTests'
                }
                echo "✅ 프론트엔드 테스트 완료"
            }
        }

        // ④ Docker 이미지 빌드
        stage('Docker Build') {
            steps {
                sh """
                    docker compose build spring-app frontend
                """
                echo "✅ Docker 이미지 빌드 완료"
            }
        }

        // ⑤ 배포 (컨테이너 재시작)
        stage('Deploy') {
            steps {
                sh """
                    docker compose up -d --no-deps spring-app frontend
                """
                echo "✅ 배포 완료"
            }
        }

        // ⑥ 헬스체크
        stage('Health Check') {
            steps {
                retry(5) {
                    sleep(time: 10, unit: 'SECONDS')
                    sh 'curl -f http://spring-app:8080/actuator/health || exit 1'
                }
                echo "✅ 헬스체크 통과"
            }
        }
    }

    post {
        success {
            echo "🎉 파이프라인 성공! 배포 완료"
        }
        failure {
            echo "❌ 파이프라인 실패! 로그를 확인하세요."
        }
        always {
            // 빌드 후 불필요한 이미지 정리
            sh 'docker image prune -f'
        }
    }
}
