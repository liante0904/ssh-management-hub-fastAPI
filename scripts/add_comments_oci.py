#!/usr/bin/env python3
"""OCI PostgreSQL에 테이블/컬럼 코멘트 적용 (postgres superuser로 실행)"""
import subprocess, sys

table_descs = {
    "tbl_consensus_history": "한경 컨센서스 이력 - 종목별 실적 컨센서스 추정치",
    "tbl_dart_business_contents": "DART 사업보고서 내용",
    "tbl_dart_disclosures": "DART 공시 정보",
    "tbl_dart_financial_data": "DART 재무 데이터 - 기업별 재무제표",
    "tbl_dart_insider_tradings": "DART 내부자 거래 내역 - 임원/주요주주 지분 변동",
    "tbl_dart_macro_indicators": "DART 거시경제 지표",
    "tbl_dart_major_shareholdings": "DART 주요주주 현황",
    "tbl_dart_order_backlogs": "DART 수주잔고 - 기업별 분기별 수주 현황",
    "tbl_fnguide_consensus": "FnGuide 컨센서스 - 증권사별 실적 추정치 통합",
    "tbl_fnguide_report_summaries": "FnGuide 리포트 요약 - 애널리스트 리포트 메타",
    "tbl_investment_notes": "투자 메모 - 사용자별 개인 투자 노트",
    "tbl_kofia_credit_balance": "KOFIA 신용잔고",
    "tbl_kofia_trading_amount": "KOFIA 거래대금",
    "tbl_market_sentiment_daily_snapshots": "시장 심리 일간 스냅샷 - 일별 집계 지표",
    "tbl_market_sentiment_indicators": "시장 심리 지표 정의 - 지표 메타데이터",
    "tbl_market_sentiment_snapshots": "시장 심리 스냅샷 - 수집 시점별 원본 데이터",
    "tbl_report_send_history": "레포트 발송 이력 - 텔레그램 알림 발송 기록",
    "tbl_sec_reports": "증권사 레포트 - 수집된 증권사 리포트 원본",
    "tbl_sec_reports_alert_keywords": "레포트 알림 키워드 - 사용자별 관심 키워드",
    "tbl_sec_reports_favorites": "레포트 즐겨찾기 - 사용자별 저장 레포트",
    "tbl_sec_reports_pdf_archive": "PDF 아카이브 - 레포트 PDF 저장/관리",
    "tbl_sec_reports_telegram_users": "텔레그램 유저 - 봇 사용자 계정 정보",
    "tbl_telegram_etf_portfolios": "텔레그램 ETF 포트폴리오 - 사용자별 ETF 구성",
    "tbm_dart_companies": "DART 기업 마스터 - 종목코드/기업명 매핑",
    "tbm_dart_disclosures": "DART 공시 마스터 - 공시 요약 및 신호 분석",
    "tbm_sec_firm_board_info": "증권사 게시판 마스터 - 증권사별 게시판 유형",
    "tbm_sec_firm_info": "증권사 정보 마스터 - 증권사 기본 정보",
}

def psql(sql):
    """Run a SQL command via docker exec as postgres superuser"""
    return subprocess.run([
        "docker", "exec", "main-postgres", "psql",
        "-U", "postgres", "-d", "ssh_reports_hub",
        "-c", sql
    ], capture_output=True, text=True)

# Get all tables and columns
result = subprocess.run([
    "docker", "exec", "main-postgres", "psql",
    "-U", "postgres", "-d", "ssh_reports_hub",
    "-tAc",
    "SELECT table_name, column_name FROM information_schema.columns "
    "WHERE table_schema='public' ORDER BY table_name, ordinal_position"
], capture_output=True, text=True)

success = 0
errors = 0
seen_tables = set()

for line in result.stdout.strip().split("\n"):
    line = line.strip()
    if not line:
        continue
    parts = line.split("|")
    if len(parts) < 2:
        continue
    table, col = parts[0].strip(), parts[1].strip()
    
    # Table comment (once per table)
    if table not in seen_tables:
        desc = table_descs.get(table, table)
        r = psql(f"COMMENT ON TABLE {table} IS '{desc}'")
        if r.returncode == 0:
            success += 1
        else:
            print(f"ERR table: {table} - {r.stderr.strip()[:80]}", file=sys.stderr)
            errors += 1
        seen_tables.add(table)
    
    # Column comment
    r = psql(f"COMMENT ON COLUMN {table}.{col} IS '{col}'")
    if r.returncode == 0:
        success += 1
    else:
        errors += 1

print(f"Done: {success} comments applied, {errors} errors")
