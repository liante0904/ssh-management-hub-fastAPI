# 2026-05-29: PDF 아카이브 진단 시스템 구축

> **목표**: PDF 다운로드 실패 원인을 파악하고 98% 완료율을 달성하기 위한 진단 인프라 구축

---

## 오늘 작업 요약

| 순서 | 작업 | 파일 | 목적 |
|------|------|------|------|
| 1 | CI 테스트 실패 수정 | `tests/conftest.py` | PR #45 LEFT JOIN 리팩터링 후 Mock 미업데이트로 11개 테스트 깨짐 |
| 2 | 원본 URL 표시 | `reports.py`, `PdfArchive.jsx`, `api.js` | 실패한 PDF의 원본 기사 URL을 직접 확인 가능 |
| 3 | URL 진단 API | `reports.py` | 서버에서 URL로 HEAD 요청 → HTTP 상태, Content-Type, 응답시간 확인 |
| 4 | 진단 UI | `PdfArchive.jsx` | 🔍 버튼으로 URL 접속 진단 → 결과 패널 표시 |

---

## 1. Mock 테스트 패턴 (conftest.py)

### 문제 상황
PR #45에서 SQL 쿼리가 `SELECT report_id, firm_nm, ...` → `SELECT r.report_id, r.firm_nm, ...`로 바뀌었지만, mock의 문자열 매칭 조건이 업데이트되지 않아 테스트 실패.

### 해결 패턴
```python
# ❌ Before: 정확한 문자열 매칭 — 쿼리 변경에 취약
elif "select report_id, firm_nm, title" in stmt_lower:

# ✅ After: 공백/prefix 제거 후 핵심 패턴 매칭 — 쿼리 변화에 견고
elif "report_id,firm_nm" in stmt_lower.replace(" ", "").replace("r.", ""):
```

### MockDBSession 분기 우선순위
```
1. 테이블명 조건 먼저 (`tbl_sec_reports`, `tbl_sec_reports_pdf_archive`)
2. DML 구분 (`update`, `delete`, `insert`)
3. 집계 쿼리 (`count(*)`, `count(*) filter` + `group by`)
4. 컬럼 패턴 매칭 (SELECT 절 키워드)
5. else → 기본 MockRow 반환
```

### 새 MockRow 추가 시 체크리스트
- [ ] 쿼리에 추가된 컬럼 순서대로 `MockRow(...)` 인자 추가
- [ ] 기존 MockRow도 동일한 개수로 업데이트
- [ ] `response_model` 스키마와 컬럼 수 일치 확인

---

## 2. 진단 API 패턴 (`POST /diagnose`)

### 엔드포인트 설계 원칙
```
POST /api/reports/pdf-archive/{report_id}/diagnose
```
- **POST 선택 이유**: 서버에서 외부 HTTP 요청을 발생시키는 side-effectful 작업
- **경로 위치**: `/pdf-archive/{report_id}/diagnose` — `/pdf-archive/reprocess` 뒤, `/{report_id}` catch-all 앞에 배치 (FastAPI 라우트 우선순위)
- **인증**: `Depends(get_current_admin)` — 관리자만 접근

### 외부 HTTP 호출 패턴 (httpx)
```python
import httpx
import time

try:
    start = time.monotonic()
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        resp = await client.head(url)  # HEAD 요청 — 본문 다운로드 안 함
        elapsed = (time.monotonic() - start) * 1000
        # 응답 분석...
except httpx.TimeoutException:
    # 타임아웃 처리
except httpx.ConnectError as e:
    # 연결 실패 처리
except Exception as e:
    # 기타 오류
```

### DiagnoseResponse 스키마
```python
class DiagnoseResponse(BaseModel):
    report_id: int
    article_url: Optional[str] = None
    reachable: bool = False
    http_status: Optional[int] = None
    content_type: Optional[str] = None
    content_length: Optional[int] = None
    elapsed_ms: Optional[float] = None
    error: Optional[str] = None
```

---

## 3. Frontend-Backend 통합 패턴

### API 함수 추가 (api.js)
```javascript
// 규칙: 메서드 + 경로 + 바디
pdfArchiveDiagnose: (reportId) => req('POST', `/api/reports/pdf-archive/${reportId}/diagnose`),
```
- `req(method, path, body)` — 인증 토큰 자동 포함, 401 시 로그아웃 처리
- **절대로 raw fetch 쓰지 말 것** — `api.js`의 `req()`만 사용

### 테이블 컬럼 추가 (PdfArchive.jsx)
```jsx
// 1. thead에 <th> 추가
<th>원본URL</th>

// 2. tbody에 해당 <td> 추가
<td>
  {r.article_url ? (
    <a href={r.article_url} target="_blank" rel="noopener noreferrer"
      title={r.article_url} style={{color:'var(--accent)'}}>
      🔗
    </a>
  ) : '-'}
</td>
```

### 진단 버튼 + 결과 패널
```jsx
// 버튼 (actions 컬럼)
<button onClick={() => diagnoseSingle(r.report_id)} disabled={diagnosing}
  title="원본 URL 접속 진단">🔍</button>

// 결과 패널 (conditional render)
{diagnoseResult && (
  <div className="card mb1" style={{borderLeft: diagnoseResult.reachable ? '4px solid var(--green)' : '4px solid var(--red)'}}>
    {/* 진단 결과 테이블 */}
  </div>
)}
```

---

## 4. 컬럼 인덱스 Shift 주의

SELECT 절에 새 컬럼을 추가하면 이후 모든 컬럼의 인덱스가 밀린다.

```
Before (18 columns):
r0=r.report_id, r1=firm_nm, r2=title, r3=reg_dt,
r4=author, r5=file_name, r6=file_size, r7=page_count,
r8=archive_status, r9=storage_backend, r10=download_status_yn,
r11=sync_status, r12=pdf_sync_status, r13=retry_count,
r14=has_text, r15=is_encrypted, r16=created_at, r17=updated_at

After (19 columns, article_url inserted at position 4):
r0=report_id, r1=firm_nm, r2=title, r3=reg_dt,
r4=article_url,                          ← NEW
r5=author, r6=file_name, r7=file_size, r8=page_count,
r9=archive_status, r10=storage_backend, r11=download_status_yn,
r12=sync_status, r13=pdf_sync_status, r14=retry_count,
r15=has_text, r16=is_encrypted, r17=created_at, r18=updated_at
```

**변경해야 할 곳 3군데:**
1. SQL SELECT 절 (`reports.py`)
2. 아이템 생성 코드 (`reports.py`)
3. MockRow 생성 코드 (`tests/conftest.py`)

---

## 5. 디버깅 플로우 (실패한 PDF 진단)

```
실패 항목 발견
  │
  ├─ 🔗 클릭 → 원본 기사 URL 직접 열람
  │   └─ 브라우저에서 열리면 URL은 정상
  │
  ├─ 🔍 진단 → 서버에서 HEAD 요청
  │   ├─ 200 + application/pdf → URL 정상, 다운로더 문제
  │   │   └─ Retry (재처리)
  │   ├─ 404 → PDF 삭제됨 → 영구 실패
  │   ├─ 403 → 권한 문제 → URL 패턴 확인
  │   ├─ Timeout → 네트워크 문제 → Retry
  │   └─ Connection Refused → 서버 다운
  │
  └─ Retry 버튼 → sync_status 0으로 초기화
```

---

## 6. 배포 파이프라인

### Backend (FastAPI)
```
push main → GitHub Actions: test → build docker → push GHCR
  → SSH deploy: git checkout SHA → docker pull → docker compose up -d
  → nginx reload
```

### Frontend (React)
```
push main → GitHub Actions: test → (정적 빌드 없음 — dev server 직접 사용)
```
**주의**: 프론트엔드는 현재 CI 테스트만 있고 CD(배포)는 별도 파이프라인 없음.
소스 수정 후 nginx가 서빙하는 디렉토리에 별도 빌드/배포 필요.

---

## 7. 향후 확장 방향

### Phase 2: 실패 원인 자동 분석
- `tbl_sec_reports_pdf_archive`에 `last_error TEXT`, `last_error_at TIMESTAMPTZ` 컬럼 추가
- `GET /pdf-archive/failure-analysis` — 원인별/증권사별 집계 API
- 실패 유형 분류: `NETWORK_TIMEOUT`, `PDF_NOT_FOUND`, `PDF_ENCRYPTED`, `STORAGE_ERROR`

### Phase 3: 스마트 재처리
- `permanent_fail_yn` 플래그 → 영구 실패는 재처리 대상에서 제외
- "재처리 가능한 건만 선택" 필터
- 완료율 = `archived / (total - permanent_fails)` → 현실적 KPI

---

## 관련 파일

| 파일 | 역할 |
|------|------|
| `apps/backend/.../app/routers/reports.py` | PDF Archive API (list, stats, reprocess, diagnose) |
| `apps/backend/.../tests/conftest.py` | MockDBSession — SQL 문자열 매칭 기반 |
| `apps/backend/.../tests/test_reports.py` | 43개 reports 테스트 |
| `apps/frontend/.../src/views/PdfArchive.jsx` | PDF 아카이브 관리 UI |
| `apps/frontend/.../src/lib/api.js` | API 호출 중앙 모듈 |
| `docs/CHANGELOG-2026-05-29.md` | 이 문서 |
