FROM jenkins/jenkins:lts-jdk17

USER root

# Docker CLI 설치
RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg \
        lsb-release && \
    # Docker 공식 GPG 키 등록
    install -m 0755 -d /etc/apt/keyrings && \
    curl -fsSL https://download.docker.com/linux/debian/gpg -o /etc/apt/keyrings/docker.asc && \
    chmod a+r /etc/apt/keyrings/docker.asc && \
    # Docker apt 저장소 등록
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
        https://download.docker.com/linux/debian \
        $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        > /etc/apt/sources.list.d/docker.list && \
    apt-get update -qq && \
    # Docker CLI만 설치 (dockerd는 불필요, host의 docker.sock 사용)
    apt-get install -y --no-install-recommends docker-ce-cli && \
    # 캐시 정리
    rm -rf /var/lib/apt/lists/*

USER jenkins
