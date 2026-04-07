# Jenkins CI/CD 설정 가이드

> order-system 프로젝트의 Jenkins 파이프라인 설정 전체 과정



## 1. Jenkins 접속 및 초기 설정

### 컨테이너 시작

```powershell
cd d:\order-system
docker compose up -d jenkins

# 초기 Admin 비밀번호 확인
docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

### 초기 설정 순서

**① http://localhost:8090 접속**

**② 비밀번호 입력**  
위 명령으로 출력된 비밀번호를 "Administrator password" 란에 입력

**③ 플러그인 설치**  
"Install suggested plugins" 선택 → 자동 설치 (5~10분 소요)

**④ Admin 계정 생성**

| 항목 | 예시 |
|------|------|
| 사용자 이름 | admin |
| 암호 | (본인 설정) |
| 이름 | Admin |
| 이메일 | admin@order.com |

**⑤ Jenkins URL 확인**  
기본값 `http://localhost:8090/` 그대로 "Save and Finish" 클릭



## 2. 추가 플러그인 설치

Jenkins 관리 → Plugin Manager → Available plugins 탭에서 검색 후 설치:

| 플러그인 | 용도 |
|---------|------|
| `Docker Pipeline` | 파이프라인에서 Docker 명령 사용 |
| `Pipeline` | Jenkinsfile 기반 파이프라인 |
| `Git` | GitHub 연동 |
| `Blue Ocean` | 파이프라인 시각화 UI (선택) |

설치 후 **Jenkins 재시작** 필요:
```
Jenkins 관리 → 플러그인 관리 → 설치 후 재시작 체크 → 다운로드 후 재시작
```



## 3. GitHub Credentials 등록

Jenkins에서 GitHub에 접근하기 위한 인증 정보 등록

**Jenkins 관리 → Credentials → System → Global credentials → Add Credentials**

```
Kind: Username with password
Scope: Global
Username: YOUR_GITHUB_USERNAME
Password: YOUR_GITHUB_TOKEN   ← Personal Access Token (PAT)
ID: github-credentials
Description: GitHub Access Token
```

> **GitHub PAT 발급 방법:**  
> GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)  
> → Generate new token → `repo` 권한 체크



## 4. 파이프라인 생성

### 4-1. New Item 생성

Jenkins 메인 → "새 Item" → 이름 입력(`order-system`) → "Pipeline" 선택 → OK



### 4-2. General 설정

```
✅ GitHub project 체크
Project url: https://github.com/YOUR_USERNAME/order-system
```



### 4-3. Build Triggers 설정 (GitHub 자동 빌드)

```
✅ GitHub hook trigger for GITScm polling 체크
```



### 4-4. Pipeline 설정

```
Definition: Pipeline script from SCM
SCM: Git
Repository URL: https://github.com/YOUR_USERNAME/order-system.git
Credentials: github-credentials (위에서 등록한 것)
Branch Specifier: */main
Script Path: Jenkinsfile
```

→ "저장" 클릭



## 5. Jenkinsfile 파이프라인 구조

```
[GitHub push]
      ↓
[Jenkins 감지]
      ↓
① Checkout      — 소스코드 가져오기
      ↓
② Backend Test  — ./gradlew test
      ↓
③ Frontend Test — npm test
      ↓
④ Docker Build  — 이미지 재빌드
      ↓
⑤ Deploy        — 컨테이너 재시작
      ↓
⑥ Health Check  — /actuator/health 확인
```



## 6. GitHub Webhook 설정 (자동 빌드 트리거)

코드 push 시 Jenkins가 자동으로 빌드를 시작하게 설정



### 로컬 환경 — ngrok으로 외부 URL 생성

```powershell
# ngrok 설치 (https://ngrok.com)
# 설치 후 실행
ngrok http 8090
# → https://abc123.ngrok.io 형태로 외부 URL 발급
```



### GitHub Webhook 등록

```
GitHub 저장소 → Settings → Webhooks → Add webhook

Payload URL: https://abc123.ngrok.io/github-webhook/
Content type: application/json
Secret: (비워도 됨)
Events: Just the push event
✅ Active 체크
```



## 7. 수동 빌드 실행

Webhook 없이 수동으로 파이프라인 실행:

```
Jenkins 메인 → order-system → "지금 빌드" 클릭
```

빌드 결과 확인:
```
빌드 번호 클릭 → Console Output
```



## 8. 빌드 실패 시 주요 해결법

| 에러 | 원인 | 해결 |
|------|------|------|
| `docker: not found` | Jenkins 컨테이너에 Docker CLI 없음 | `docker.sock` 마운트 확인 |
| `Permission denied /var/run/docker.sock` | 권한 문제 | `privileged: true`, `user: root` 설정 확인 |
| `gradlew: Permission denied` | 실행 권한 없음 | `git update-index --chmod=+x gradlew` 후 push |
| `Could not resolve dependencies` | 네트워크 문제 | Jenkins 컨테이너 네트워크 확인 |
| `Health check failed` | spring-app 시작 시간 초과 | `retry(10)`, `sleep(15)` 로 늘리기 |



## 9. Jenkins 관리 명령어

```powershell
# Jenkins 컨테이너 재시작 (플러그인 설치 후)
docker compose restart jenkins

# Jenkins 로그 실시간 확인
docker compose logs -f jenkins

# Jenkins 데이터 볼륨 위치 확인
docker volume inspect order-system_jenkins-data

# Jenkins 컨테이너 내부 접속
docker compose exec jenkins bash

# Jenkins 완전 초기화 (볼륨 삭제)
docker compose down
docker volume rm order-system_jenkins-data
docker compose up -d jenkins
```



## 10. 참고 자료

| 주제 | URL |
|------|-----|
| Jenkins 공식 문서 | https://www.jenkins.io/doc/ |
| Jenkins Pipeline 문법 | https://www.jenkins.io/doc/book/pipeline/syntax/ |
| Docker Pipeline 플러그인 | https://plugins.jenkins.io/docker-workflow/ |
| Blue Ocean 문서 | https://www.jenkins.io/doc/book/blueocean/ |
| ngrok 공식 사이트 | https://ngrok.com |
