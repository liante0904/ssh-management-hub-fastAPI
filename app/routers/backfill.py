"""Backfill Router — GA 증권사 수동 백필 트리거"""
from __future__ import annotations

import json, logging, os, subprocess, sys, tempfile, time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .admin import get_current_admin

logger = logging.getLogger("management-hub.backfill")

router = APIRouter(prefix="/backfill", tags=["backfill"])

# Scraper repo path
SCRAPER_DIR = Path(os.getenv("SCRAPER_DIR", "/home/ubuntu/workspace/external.reports-hub/apps/scrapers/ssh-reports-scraper"))
SECRETS_PATH = Path(os.path.expanduser("~/secrets/ssh-reports-scraper/secrets.json"))

# Firm → (core_module, core_func, firm_nm, needs_full_cfg)
BACKFILL_FIRMS = {
    "HANA_3":    ("hana_core",    "scrape_hana",    "하나증권",     True),
    "KBsec_4":   ("kb_core",      "scrape_kb",      "KB증권",       True),
    "NHQV_2":    ("nhqv_core",    "scrape_nhqv",    "NH투자증권",   True),
    "MERITZ_20": ("meritz_core",  "scrape_meritz",  "메리츠증권",   True),
    "Samsung_5": ("samsung_core", "scrape_samsung", "삼성증권",     True),
    "Kiwoom_10": ("kiwoom_core",  "scrape_kiwoom",  "키움증권",     True),
    "DAOL_14":   ("daol_core",    "scrape_daol",    "다올투자증권", True),
    "Kyobo_24":  ("kyobo_core",   "scrape_kyobo",   "교보증권",     True),
    "IBKs_25":   ("ibk_core",     "scrape_ibk",     "IBK투자증권",  True),
    "Yuanta_27": ("yuanta_core",  "scrape_yuanta",  "유안타증권",   True),
    "SKS_26":    ("sks_core",     "scrape_sks",     "SK증권",       True),
    "Hmsec_9":   ("hmsec_core",   "scrape_hmsec",   "현대차증권",   True),
    "DBfi_19":   ("dbfi_core",    "scrape_dbfi",    "DB증권",       True),
    "TOSSinvest_15": ("toss_core","scrape_toss",    "토스증권",     True),
    "Sangsanginib_6": ("sangsangin_core","scrape_sangsangin","상상인증권", True),
    "Hygood_22": ("hanyang_core","scrape_hanyang",  "한양증권",     True),
    "Heungkuk_28":("heungkuk_core","scrape_heungkuk","흥국증권",    True),
    "Hanwhawm_21":("hanwha_core","scrape_hanwha",   "한화투자증권", True),
    "Miraeasset_8":("miraeasset_core","scrape_miraeasset","미래에셋증권",True),
    "Leading_16":("leading_core","scrape_leading",   "리딩투자증권", True),
    "Shinyoung_7":("shinyoung_core","scrape_shinyoung","신영증권",   True),
}


def _load_url_config(firm_key: str) -> dict:
    """Load URL list for a firm from secrets.json."""
    with open(SECRETS_PATH) as f:
        secrets = json.load(f)
    return secrets.get("urls", {}).get(firm_key, [])


def _run_scraper(firm_key: str) -> dict:
    """Run a scraper core and return results + stats."""
    mod_name, func_name, firm_nm, needs_cfg = BACKFILL_FIRMS[firm_key]

    # Import core module
    sys.path.insert(0, str(SCRAPER_DIR))
    mod = __import__(f"scrapers.{mod_name}", fromlist=[func_name])
    func = getattr(mod, func_name)

    # Build config
    url_config = _load_url_config(firm_key)
    if needs_cfg:
        cfg = {"urls": url_config} if isinstance(url_config, list) else dict(url_config)
        cfg.setdefault("firm_nm", firm_nm)
    else:
        cfg = url_config

    t0 = time.time()
    try:
        result = func(cfg)
        elapsed = time.time() - t0
    except Exception as e:
        return {"status": "error", "error": str(e), "elapsed_sec": time.time() - t0}

    if not isinstance(result, list):
        return {"status": "error", "error": f"Expected list, got {type(result).__name__}", "elapsed_sec": elapsed}

    # Date stats
    from collections import Counter
    dates = Counter(r.get("reg_dt", "?") for r in result)
    bad_dates = sum(1 for r in result if not str(r.get("reg_dt", "")).isdigit() or len(str(r.get("reg_dt", ""))) != 8)
    missing_key = sum(1 for r in result if not (r.get("report_unique_key") or r.get("key")))

    return {
        "status": "success",
        "articles": len(result),
        "bad_dates": bad_dates,
        "missing_key": missing_key,
        "elapsed_sec": round(elapsed, 1),
        "date_distribution": dict(dates.most_common(20)),
    }


# ── Schemas ──────────────────────────────────────────────

class BackfillRequest(BaseModel):
    firm: str = Field(..., description="Firm key (e.g. HANA_3, KBsec_4)")
    date_from: Optional[str] = Field(None, pattern=r"^\d{8}$")
    date_to: Optional[str] = Field(None, pattern=r"^\d{8}$")


class BatchBackfillRequest(BaseModel):
    firms: list[str] = Field(..., min_length=1, max_length=29)
    days: int = Field(default=7, ge=1, le=365)


class BackfillResult(BaseModel):
    firm: str
    firm_nm: str
    status: str
    articles: int = 0
    bad_dates: int = 0
    missing_key: int = 0
    elapsed_sec: float = 0
    error: Optional[str] = None
    date_distribution: dict = {}
    scp_sent: bool = False


# ── Endpoints ───────────────────────────────────────────

@router.get("/firms")
async def list_backfill_firms(admin=Depends(get_current_admin)):
    """백필 가능한 증권사 목록."""
    return [
        {"key": k, "name": v[2], "core": v[0]}
        for k, v in BACKFILL_FIRMS.items()
    ]


@router.post("/run", response_model=BackfillResult)
async def run_backfill(req: BackfillRequest, admin=Depends(get_current_admin)):
    """단일 증권사 백필 실행 → SCP 전송."""
    if req.firm not in BACKFILL_FIRMS:
        raise HTTPException(400, f"Unknown firm: {req.firm}")

    firm_nm = BACKFILL_FIRMS[req.firm][2]
    logger.info(f"Backfill start: {req.firm} ({firm_nm})")

    result = _run_scraper(req.firm)

    scp_sent = False
    if result["status"] == "success" and result["articles"] > 0:
        # Save to temp file and SCP
        try:
            scraper_result = _run_scraper_raw(req.firm)
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(scraper_result, f, ensure_ascii=False)
                tmp_path = f.name

            subprocess.run([
                "scp", tmp_path,
                f"ubuntu@10.0.0.111:incoming/ga-scrapes/{req.firm}_backfill_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            ], timeout=30)
            os.unlink(tmp_path)
            scp_sent = True
            logger.info(f"Backfill SCP sent: {req.firm} ({result['articles']} articles)")
        except Exception as e:
            logger.error(f"SCP failed: {e}")

    return BackfillResult(
        firm=req.firm, firm_nm=firm_nm,
        status=result["status"], articles=result.get("articles", 0),
        bad_dates=result.get("bad_dates", 0), missing_key=result.get("missing_key", 0),
        elapsed_sec=result.get("elapsed_sec", 0), error=result.get("error"),
        date_distribution=result.get("date_distribution", {}),
        scp_sent=scp_sent,
    )


@router.post("/run-batch")
async def run_backfill_batch(req: BatchBackfillRequest, admin=Depends(get_current_admin)):
    """여러 증권사 동시 백필."""
    results = []
    for firm in req.firms:
        if firm not in BACKFILL_FIRMS:
            results.append({"firm": firm, "status": "error", "error": "Unknown firm"})
            continue
        firm_nm = BACKFILL_FIRMS[firm][2]
        result = _run_scraper(firm)
        results.append({
            "firm": firm, "firm_nm": firm_nm,
            "status": result["status"], "articles": result.get("articles", 0),
            "elapsed_sec": result.get("elapsed_sec", 0),
            "error": result.get("error"),
        })
    return {"total": len(results), "results": results}


def _run_scraper_raw(firm_key: str) -> list:
    """Run scraper and return raw list (for SCP)."""
    mod_name, func_name, firm_nm, needs_cfg = BACKFILL_FIRMS[firm_key]
    sys.path.insert(0, str(SCRAPER_DIR))
    mod = __import__(f"scrapers.{mod_name}", fromlist=[func_name])
    func = getattr(mod, func_name)
    url_config = _load_url_config(firm_key)
    if needs_cfg:
        cfg = {"urls": url_config} if isinstance(url_config, list) else dict(url_config)
        cfg.setdefault("firm_nm", firm_nm)
    else:
        cfg = url_config
    return func(cfg)
