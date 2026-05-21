# CI/CD 설정 가이드

> ssh-management-hub GitHub Actions 배포 파이프라인 설정

---

## 1. GitHub Secrets 등록

등록 위치: `https://github.com/liante0904/ssh-management-hub/settings/secrets/actions`

### 등록할 4개 Secrets

| Secret | 값 획득 방법 | 설명 |
|--------|-------------|------|
| `SERVER_HOST` | `10.0.0.111` | oci 서버 내부 IP |
| `SERVER_USER` | `ubuntu` | SSH 접속 계정 |
| `SSH_PRIVATE_KEY` | `cat ~/.ssh/id_rsa` | oci 서버 접속용 비밀키 |
| `GHCR_TOKEN` | `gh auth token` | GitHub Container Registry 푸시 토큰 |

### 등록 방법

```
GitHub 레포 → Settings → Secrets and variables → Actions
→ New repository secret 버튼
```

하나씩 Name / Value 입력 후 **Add secret** 반복.

---

## 2. GHCR_TOKEN 발급 (신규 발급 시)

`gh auth token` 값이 없거나 만료된 경우:

1. https://github.com/settings/tokens → **Tokens (classic)**
2. **Generate new token (classic)**
3. Note: `management-hub-cicd`
4. Expiration: `No expiration`
5. 권한 체크:
   - ✅ `write:packages`
   - ✅ `read:packages`
   - ✅ `delete:packages`
6. **Generate token** → 출력된 `ghp_xxxx...` 복사
7. GitHub Secrets에 `GHCR_TOKEN` 으로 등록

---

## 3. oci 서버 준비

```bash
# oci에 접속
ssh oci

# 디렉토리 생성
mkdir -p /home/ubuntu/workspace/ssh-management-hub
```

---

## 4. secrets/generate_env.py 등록

```bash
# oci2에서
python3 ~/secrets/generate_env.py management-hub
```

---

## 5. internal-nginx 라우팅 추가 (oci에서)

```bash
# oci에서 internal-nginx 설정 편집
# /admin/ → ssh-management-hub-fastapi-prod:8000
```

---

## 6. 배포 확인

```bash
# git push
cd ~/workspace/ssh-management-hub
git push origin main

# GitHub Actions 로그 확인
gh run watch

# oci에서 컨테이너 확인
ssh oci
docker ps | grep management-hub
curl -s http://localhost:8003/health
```

---

## 배포 파이프라인 흐름

```
git push (main)
  │
  ▼
GitHub Actions: Build & Push
  ├── pytest tests/ (PostgreSQL service)
  ├── docker build (linux/arm64)
  └── docker push → ghcr.io/liante0904/ssh-management-hub
  │
  ▼
GitHub Actions: Deploy
  ├── SSH → oci (10.0.0.111)
  ├── git pull (deploy_prepare.py)
  ├── docker compose pull
  └── docker compose up -d --force-recreate
  │
  ▼
oci: ssh-management-hub-fastapi-prod (port 8003)
  └── internal-nginx → /admin/* → :8000
```

## 문제 해결

| 문제 | 확인 |
|------|------|
| GitHub Actions 실패 | `Actions` 탭에서 로그 확인 |
| docker push 거부 | `GHCR_TOKEN` 만료 → 재발급 |
| SSH 접속 실패 | `SSH_PRIVATE_KEY` 라인피드 확인, `SERVER_HOST` IP 확인 |
| 컨테이너 기동 실패 | oci에서 `docker compose logs` 확인, `.env` 누락 확인 |
