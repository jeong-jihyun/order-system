# Jenkins → GitHub 파이프라인 연동 가이드

> Jenkins가 GitHub에서 소스코드를 Pull하고 자동 빌드하도록 연결하는 단계별 실행 가이드  
> 이 문서를 순서대로 따라가면 `git push` 시 Jenkins 자동 빌드가 됩니다.



## 현재 상황

| 항목 | 상태 |
|------|------|
| Jenkins 컨테이너 | ✅ 실행 중 (port 8090) |
| 초기 Admin 계정 | ✅ 생성 완료 |
| 기본 플러그인 설치 | ✅ 완료 |
| GitHub Credentials 등록 | ❌ 미완료 |
| Pipeline Item 생성 | ❌ 미완료 |
| Git Repository 연결 | ❌ 미완료 |



## STEP 1. Docker CLI 설치 및 권한 확인

`jenkins/jenkins:lts-jdk17` 기본 이미지에는 Docker CLI가 없습니다.  
Docker CLI가 포함된 커스텀 이미지를 빌드해야 합니다.

### 1-1. Jenkins Dockerfile 생성 (`jenkins/Dockerfile`)

```dockerfile
FROM jenkins/jenkins:lts-jdk17

USER root

RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends ca-certificates curl gnupg lsb-release && \
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc && \
    chmod a+r /etc/apt/keyrings/docker.asc && \
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
        https://download.docker.com/linux/debian \
        $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        > /etc/apt/sources.list.d/docker.list && \
    apt-get update -qq && \
    apt-get install -y --no-install-recommends docker-ce-cli && \
    rm -rf /var/lib/apt/lists/*

USER jenkins
```



### 1-2. docker-compose.yml Jenkins 서비스 수정

`image:` 방식 → `build:` 방식으로 변경:

```yaml
jenkins:
  build:
    context: ./jenkins
    dockerfile: Dockerfile
  container_name: order-jenkins
  # ... 나머지 설정은 동일
```



### 1-3. Jenkins 재빌드 및 재시작

```powershell
cd D:\order-system
docker compose stop jenkins
docker compose rm -f jenkins
docker compose build jenkins
docker compose up -d jenkins
```

> `jenkins-data` 볼륨은 유지되므로 기존 Admin 계정과 플러그인 설정은 그대로 남습니다.  
> 빌드는 Docker 이미지 다운로드로 인해 3~5분 소요됩니다.



### 1-4. 확인

```powershell
docker compose exec jenkins docker ps
```

**Exit Code 0 + 컨테이너 목록 출력 → STEP 1 완료**



## STEP 2. 추가 플러그인 설치

`Docker Pipeline` 플러그인이 없으면 Jenkinsfile의 docker 명령이 실패합니다.

1. **Jenkins 메인** → 좌측 **"Jenkins 관리"**
2. **"Plugins"** 클릭
3. 상단 **"Available plugins"** 탭 클릭
4. 검색창에 `Docker Pipeline` 입력
5. 체크박스 선택 → **"Install"** 클릭
6. **"Restart Jenkins when installation is complete and no jobs are running"** 체크

Jenkins 자동 재시작 후 다시 로그인합니다.



## STEP 3. GitHub Personal Access Token (PAT) 발급

Jenkins가 GitHub에 접근할 때 사용하는 토큰입니다.

1. GitHub 접속 → 우측 상단 프로필 사진 클릭 → **"Settings"**
2. 좌측 맨 아래 **"Developer settings"** 클릭
3. **"Personal access tokens"** → **"Tokens (classic)"**
4. **"Generate new token (classic)"** 클릭

**토큰 설정:**

```
Note:       jenkins-order-system
Expiration: 90 days (또는 No expiration)
Scopes:     ✅ repo (하위 항목 전부 자동 체크됨)
```

5. 맨 아래 **"Generate token"** 클릭
6. 생성된 토큰 복사 (`ghp_xxx...` 형태) — **이 화면을 벗어나면 다시 볼 수 없습니다!**



## STEP 4. Jenkins에 GitHub Credentials 등록

1. **Jenkins 메인** → **"Jenkins 관리"**
2. **"Credentials"** 클릭
3. **"System"** → **"Global credentials (unrestricted)"**
4. 좌측 **"Add Credentials"** 클릭

**입력값:**

```
Kind:        Username with password
Scope:       Global
Username:    YOUR_GITHUB_USERNAME   ← GitHub 아이디
Password:    ghp_xxx...             ← STEP 3에서 복사한 PAT
ID:          github-credentials
Description: GitHub PAT for order-system
```

5. **"Create"** 클릭



## STEP 5. Pipeline Item 생성

1. **Jenkins 메인** → 좌측 **"새 Item"**
2. 이름 입력: `order-system-pipeline`
3. **"Pipeline"** 선택 → **"OK"**



## STEP 6. Pipeline 상세 설정 ← 핵심

Item 생성 후 설정 페이지에서 아래 항목들을 입력합니다.



### [General] 섹션

```
✅ "GitHub project" 체크
Project url: https://github.com/YOUR_USERNAME/order-system/
```



### [Build Triggers] 섹션

```
✅ "GitHub hook trigger for GITScm polling" 체크
```

> Webhook을 설정하지 않을 경우 수동 실행만 됩니다. 일단 체크해 두어도 무관합니다.



### [Pipeline] 섹션 ← 가장 중요

```
Definition:        Pipeline script from SCM
SCM:               Git
Repository URL:    https://github.com/YOUR_USERNAME/order-system.git
Credentials:       github-credentials     ← STEP 4에서 등록한 것
Branch Specifier:  */main
Script Path:       Jenkinsfile
```

> `Repository URL` 입력 후 `Credentials` 드롭다운에서 선택하면  
> "Validated credentials" 메시지가 나오면 정상입니다.  
> 빨간 오류가 나오면 GitHub URL 또는 PAT 권한을 다시 확인하세요.

→ 맨 아래 **"저장"** 클릭



## STEP 7. 수동 빌드로 테스트

1. `order-system-pipeline` 페이지에서 좌측 **"지금 빌드"** 클릭
2. 좌측 "Build History"에 `#1` 생성됨
3. `#1` 클릭 → **"Console Output"** 클릭

**정상 로그 예시:**

```
Started by user admin
[Pipeline] Start of Pipeline
[Pipeline] stage: Checkout
...
Cloning the remote Git repository
...
[Pipeline] stage: Backend Test
...
BUILD SUCCESSFUL
...
[Pipeline] stage: Health Check
...
{"status":"UP","groups":["liveness","readiness"]}
[Pipeline] End of Pipeline
Finished: SUCCESS
```



## STEP 8. 빌드 결과 확인

파이프라인 페이지에서 각 Stage 상태를 확인할 수 있습니다:

```
Checkout → Backend Test → Frontend Test → Docker Build → Deploy → Health Check
   ✅           ✅             ✅              ✅           ✅          ✅
```

> Blue Ocean UI로 시각화하려면:  
> 플러그인에서 `Blue Ocean` 설치 → 파이프라인 페이지 → "Open Blue Ocean" 클릭



## STEP 9. GitHub Webhook 설정 (자동 빌드)

`git push` 시 Jenkins가 자동으로 빌드를 시작하게 합니다.  
로컬 PC에서 실행 중이므로 ngrok으로 외부 URL을 만들어야 합니다.



### ngrok 설치 및 실행

```powershell
# ngrok 공식 사이트 https://ngrok.com 에서 다운로드
# 계정 생성 후 authtoken 설정
ngrok config add-authtoken YOUR_NGROK_AUTHTOKEN

# Jenkins 포트(8090) 터널 생성
ngrok http 8090
```

출력 예시:
```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8090
```



### GitHub Webhook 등록

GitHub 저장소 → **Settings** → **Webhooks** → **"Add webhook"**

```
Payload URL:  https://abc123.ngrok-free.app/github-webhook/
Content type: application/json
Secret:       (비워도 됨)
Events:       ✅ Just the push event
Active:       ✅ 체크
```

→ **"Add webhook"** 클릭

등록 후 GitHub에서 test ping을 보내면 Jenkins가 응답합니다.  
이후 `git push` 할 때마다 Jenkins 빌드가 자동 시작됩니다.



## STEP 10. Jenkinsfile 수정이 필요한 경우

현재 Jenkinsfile의 Health Check 단계:

```groovy
stage('Health Check') {
    steps {
        retry(5) {
            sleep(10)
            sh 'curl -f http://spring-app:8080/actuator/health'
        }
    }
}
```

> Jenkins 컨테이너와 spring-app 컨테이너가 같은 Docker 네트워크(`order-network`)에 있어야  
> `http://spring-app:8080`으로 접근 가능합니다.

**네트워크 확인:**

```powershell
# spring-app이 order-network에 연결되어 있는지 확인
docker network inspect order-system_order-network
```



## 빌드 실패 시 트러블슈팅

| 증상 | 원인 | 해결 방법 |
|------|------|----------|
| `docker: not found` | docker.sock 마운트 안 됨 | docker-compose.yml 볼륨 설정 확인 |
| `Permission denied /var/run/docker.sock` | 권한 없음 | `chmod 666 /var/run/docker.sock` |
| `gradlew: Permission denied` | 실행 권한 없음 | `git update-index --chmod=+x backend/gradlew` 후 push |
| `invalid credentials` | PAT 만료 또는 잘못됨 | PAT 재발급 → Credentials 업데이트 |
| `Repository URL` 빨간 오류 | URL 오타 또는 repo 없음 | GitHub URL 복사 후 재입력 |
| `Health check failed` | spring-app 기동 시간 초과 | retry 값을 `retry(10)`, sleep을 `sleep(20)`으로 증가 |
| `Branch not found` | Branch 이름 불일치 | `*/main` vs `*/master` 확인 |
| Console Output에서 Checkout 후 멈춤 | Git shallow clone 시간 초과 | 네트워크 확인 또는 토큰 재확인 |



## 완료 체크리스트

```
□ STEP 1: docker ps 정상 실행 확인
□ STEP 2: Docker Pipeline 플러그인 설치
□ STEP 3: GitHub PAT 발급 및 복사
□ STEP 4: Jenkins Credentials 등록 (ID: github-credentials)
□ STEP 5: Pipeline Item 생성 (order-system-pipeline)
□ STEP 6: Pipeline 설정 — Pipeline script from SCM 완료
□ STEP 7: 수동 빌드 → Console Output 확인
□ STEP 8: 모든 Stage GREEN 확인
□ STEP 9: (선택) Webhook 설정 → git push 자동 빌드 확인
```
