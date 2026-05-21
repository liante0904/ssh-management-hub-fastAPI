# Management Hub FastAPI — AGENTS.md

## Communication Rules

- **존댓말 사용**: 반말 금지, 항상 존댓말로 응답할 것.
- **인프라 도식화**: 인프라 관련 내용은 반드시 도표/도식으로 시각화 (ASCII diagram, mermaid, table 등)

## Servers

| Server | Hostname | Role | IP (internal) |
|--------|----------|------|---------------|
| oci | arm-instance | Production (Docker, logs, LLM) | 10.0.0.111 |
| oci2 | arm2 | Development (source code, git push) | 10.0.0.164 |

## Workflow Rules

```
oci2 (개발)                        oci (운영)
   │                                  │
   ├─ LLM이 SSH로 붙어서 코딩        ├─ 도커 로그 확인
   ├─ git push ──→ GitHub ──→ CI/CD ──→ docker compose pull / up
```

- **소스 코드 수정 / git 작업 → 무조건 oci2에서** (`ssh oci2`)
- **도커 로그 / 배포 상태 확인 → oci에서** (로컬)
- oci에서 oci2 접속: `ssh oci2` (내부망 10.0.0.164, key: `~/.ssh/id_rsa`)

## Env / Secrets

`.env` 파일은 **절대로 직접 수정하지 않는다.**
시크릿은 `~/secrets/` 디렉터리에 별도 보관되며, Python 스크립트로 `.env`를 생성한다.

```bash
# .env 생성
python3 ~/secrets/generate_env.py management-hub
```

- `.env`는 Git에 포함되지 않음 (`.gitignore`)
- 수정이 필요하면 `~/secrets/` 쪽 원본을 고친 뒤 위 명령어로 재생성

## Repo Structure

```
internal.management-hub/
├── apps/
│   ├── backend/
│   │   └── ssh-management-hub/    ← FastAPI 백엔드 (이 프로젝트)
│   ├── frontend/
│   │   └── system-console/            ← React 프론트엔드 (Netlify 배포)
│   └── scrapers/                      ← (확장 예정)
├── infra/
│   └── management-nginx/              ← Management Hub 전용 nginx
├── AGENTS.md                          ← 레포 루트 AGENTS
└── README.md
```

## Key Containers (on oci)

| Container | Role |
|-----------|------|
| `ssh-management-hub-fastapi-prod` | Management Hub API (이 프로젝트) |
| `management-nginx` | Management Hub 전용 리버스 프록시 |
| `internal-nginx` | 메인 도메인 인그레스 (private-hub 소속) |
| `main-postgres` | 메인 DB (`ssh_reports_hub`) |

## Deploy Flow

1. oci2에서 git push → GitHub Actions (`deploy.yml`) 트리거
2. GHCR에 Docker 이미지 빌드 & 푸시 (`ghcr.io/liante0904/ssh-management-hub`)
3. SSH로 oci 접속 → `docker compose pull && docker compose up -d`
4. `deploy_prepare.py`로 git sync + `.env` 생성 포함
5. Netlify는 프론트엔드 레포 main 푸시 시 자동 배포

## Project Structure

```
ssh-management-hub/
├── app/
│   ├── main.py               ← FastAPI 진입점 (라우터 등록)
│   ├── database.py            ← 공통 DB 세션 (PostgreSQL)
│   └── routers/
│       ├── admin.py           ← 시스템 메트릭 + 로그 브라우징
│       ├── users.py           ← 텔레그램 유저 관리
│       ├── reports.py         ← 레포트 관리 (목록/PDF/FnGuide/발송이력)
│       └── firms.py           ← 증권사 정보 관리
├── tests/
│   ├── conftest.py            ← Mock DB + Auth fixtures
│   ├── test_admin.py          ← 7 tests
│   ├── test_users.py          ← 11 tests
│   ├── test_reports.py        ← 24 tests
│   └── test_firms.py          ← 21 tests
├── docs/
│   ├── AGENTS.md              ← 이 파일
│   └── API_REFERENCE.md       ← API 명세
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── .github/workflows/deploy.yml
```

## Testing

```bash
# 전체 테스트 실행
uv run pytest tests/ -v

# 특정 라우터만
uv run pytest tests/test_admin.py -v
uv run pytest tests/test_users.py -v
```

**테스트 설계 원칙**:
- `dependency_overrides`로 DB / Auth mock 주입 — 실제 PostgreSQL 불필요
- `MockDBSession`이 SQL 패턴 기반으로 응답 반환 (`conftest.py`)
- 새로운 라우터를 추가하면 `tests/` 아래에 `test_{router}.py` 생성
- Mock에 새 테이블 패턴이 필요하면 `conftest.py`의 `MockDBSession.execute()`에 분기 추가

## Safety

- `.env`, `*.db`, `logs/`, `.venv/` 절대 커밋 금지
- `app/main.py`는 라우터 등록만 담당 — 비즈니스 로직은 반드시 `routers/`로 분리
- 새 라우터 추가 시 `app/routers/__init__.py`에 export, `app/main.py`에 `include_router` 등록
- 정적 경로 (`/fnguide`, `/send-history`)는 반드시 파라미터 경로 (`/{report_id}`)보다 앞에 정의
- raw SQL 사용 시 파라미터 바인딩 필수 (`:param`)

## Database

- PostgreSQL (`main-postgres:5432`, DB: `ssh_reports_hub`)
- 공통 세션: `app/database.py` → `get_db()` (모든 라우터가 공유)
- 모든 관리 API는 **읽기 전용 사용자**로 접근 (SELECT 위주)
- 쓰기 작업은 admin 권한 확인 후 수행
