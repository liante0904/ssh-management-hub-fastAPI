-- ============================================================
-- DB 뷰어 테이블/컬럼 코멘트
-- 실행: docker exec -i main-postgres psql -U ssh_reports_hub -d ssh_reports_hub < scripts/table_comments.sql
-- ============================================================

-- ── 테이블 코멘트 ──
COMMENT ON TABLE tbl_consensus_history                IS '한경 컨센서스 이력 - 종목별 실적 컨센서스 추정치';
COMMENT ON TABLE tbl_dart_financial_data              IS 'DART 재무 데이터 - 기업별 재무제표 계정 금액';
COMMENT ON TABLE tbl_dart_insider_tradings            IS 'DART 내부자 거래 내역 - 임원/주요주주 지분 변동';
COMMENT ON TABLE tbl_dart_order_backlogs              IS 'DART 수주잔고 - 기업별 분기별 수주 현황';
COMMENT ON TABLE tbl_fnguide_consensus                IS 'FnGuide 컨센서스 - 증권사별 실적 추정치 통합';
COMMENT ON TABLE tbl_fnguide_report_summaries         IS 'FnGuide 리포트 요약 - 애널리스트 리포트 메타';
COMMENT ON TABLE tbl_investment_notes                 IS '투자 메모 - 사용자별 개인 투자 노트';
COMMENT ON TABLE tbl_market_sentiment_daily_snapshots IS '시장 심리 일간 스냅샷 - 일별 집계 지표';
COMMENT ON TABLE tbl_market_sentiment_indicators      IS '시장 심리 지표 정의 - 지표 메타데이터';
COMMENT ON TABLE tbl_market_sentiment_snapshots       IS '시장 심리 스냅샷 - 수집 시점별 원본 데이터';
COMMENT ON TABLE tbl_report_send_history              IS '레포트 발송 이력 - 텔레그램 알림 발송 기록';
COMMENT ON TABLE tbl_sec_reports                      IS '증권사 레포트 - 수집된 증권사 리포트 원본';
COMMENT ON TABLE tbl_sec_reports_alert_keywords       IS '레포트 알림 키워드 - 사용자별 관심 키워드';
COMMENT ON TABLE tbl_sec_reports_favorites            IS '레포트 즐겨찾기 - 사용자별 저장 레포트';
COMMENT ON TABLE tbl_sec_reports_pdf_archive          IS 'PDF 아카이브 - 레포트 PDF 저장/관리';
COMMENT ON TABLE tbl_sec_reports_telegram_users       IS '텔레그램 유저 - 봇 사용자 계정 정보';
COMMENT ON TABLE tbl_telegram_etf_portfolios          IS '텔레그램 ETF 포트폴리오 - 사용자별 ETF 구성';
COMMENT ON TABLE investment_notes                     IS '투자 노트 (Legacy) - 구버전 투자 메모';
COMMENT ON TABLE tbm_dart_companies                   IS 'DART 기업 마스터 - 종목코드/기업명 매핑';
COMMENT ON TABLE tbm_dart_disclosures                 IS 'DART 공시 마스터 - 공시 요약 및 신호 분석';
COMMENT ON TABLE tbm_sec_firm_board_info              IS '증권사 게시판 마스터 - 증권사별 게시판 유형';
COMMENT ON TABLE tbm_sec_firm_info                    IS '증권사 정보 마스터 - 증권사 기본 정보';

-- ── 컬럼 코멘트 ──

-- tbl_consensus_history (한경 컨센서스)
COMMENT ON COLUMN tbl_consensus_history.code           IS '종목코드';
COMMENT ON COLUMN tbl_consensus_history.date           IS '컨센서스 기준일';
COMMENT ON COLUMN tbl_consensus_history.target_period  IS '추정 대상 기간 (예: 2025E, 2026E)';
COMMENT ON COLUMN tbl_consensus_history.name           IS '종목명';
COMMENT ON COLUMN tbl_consensus_history.sector         IS '업종';
COMMENT ON COLUMN tbl_consensus_history.current_price  IS '현재 주가';
COMMENT ON COLUMN tbl_consensus_history.market_cap     IS '시가총액';
COMMENT ON COLUMN tbl_consensus_history.per            IS 'PER (주가수익비율)';
COMMENT ON COLUMN tbl_consensus_history.pbr            IS 'PBR (주가순자산비율)';
COMMENT ON COLUMN tbl_consensus_history.roe            IS 'ROE (자기자본이익률, %)';
COMMENT ON COLUMN tbl_consensus_history.dividend_yield IS '배당수익률 (%)';
COMMENT ON COLUMN tbl_consensus_history.operating_profit IS '영업이익';
COMMENT ON COLUMN tbl_consensus_history.net_income     IS '당기순이익';
COMMENT ON COLUMN tbl_consensus_history.sales          IS '매출액';
COMMENT ON COLUMN tbl_consensus_history.eps            IS 'EPS (주당순이익)';
COMMENT ON COLUMN tbl_consensus_history.rev_1m         IS '1개월 수익률 변동 (%)';
COMMENT ON COLUMN tbl_consensus_history.rev_3m         IS '3개월 수익률 변동 (%)';
COMMENT ON COLUMN tbl_consensus_history.updated_at     IS '데이터 업데이트 시각';

-- tbl_dart_financial_data
COMMENT ON COLUMN tbl_dart_financial_data.id          IS 'PK';
COMMENT ON COLUMN tbl_dart_financial_data.corp_code   IS 'DART 기업 고유코드';
COMMENT ON COLUMN tbl_dart_financial_data.year        IS '회계연도';
COMMENT ON COLUMN tbl_dart_financial_data.report_code IS '보고서 코드';
COMMENT ON COLUMN tbl_dart_financial_data.fs_div      IS '재무제표 구분 (CFS/OFS/IS/BS)';
COMMENT ON COLUMN tbl_dart_financial_data.fs_nm       IS '재무제표명';
COMMENT ON COLUMN tbl_dart_financial_data.account_nm  IS '계정명';
COMMENT ON COLUMN tbl_dart_financial_data.amount      IS '금액';
COMMENT ON COLUMN tbl_dart_financial_data.rcept_no    IS '접수번호';
COMMENT ON COLUMN tbl_dart_financial_data.created_at  IS '생성일시';

-- tbl_dart_insider_tradings
COMMENT ON COLUMN tbl_dart_insider_tradings.id                   IS 'PK';
COMMENT ON COLUMN tbl_dart_insider_tradings.corp_code            IS '기업코드';
COMMENT ON COLUMN tbl_dart_insider_tradings.rcept_no             IS '접수번호';
COMMENT ON COLUMN tbl_dart_insider_tradings.report_dt            IS '보고일자';
COMMENT ON COLUMN tbl_dart_insider_tradings.insider_name         IS '내부자명';
COMMENT ON COLUMN tbl_dart_insider_tradings.position             IS '직위';
COMMENT ON COLUMN tbl_dart_insider_tradings.relation             IS '관계';
COMMENT ON COLUMN tbl_dart_insider_tradings.trading_type         IS '거래유형 (매수/매도)';
COMMENT ON COLUMN tbl_dart_insider_tradings.stock_code           IS '종목코드';
COMMENT ON COLUMN tbl_dart_insider_tradings.trading_quantity     IS '거래수량';
COMMENT ON COLUMN tbl_dart_insider_tradings.trading_price        IS '거래단가';
COMMENT ON COLUMN tbl_dart_insider_tradings.trading_amount       IS '거래금액';
COMMENT ON COLUMN tbl_dart_insider_tradings.trade_note           IS '거래비고';
COMMENT ON COLUMN tbl_dart_insider_tradings.after_holding        IS '변동후 보유수량';
COMMENT ON COLUMN tbl_dart_insider_tradings.after_holding_ratio  IS '변동후 보유비율';
COMMENT ON COLUMN tbl_dart_insider_tradings.raw_data             IS '원본 JSON 데이터';
COMMENT ON COLUMN tbl_dart_insider_tradings.created_at           IS '생성일시';

-- tbl_dart_order_backlogs
COMMENT ON COLUMN tbl_dart_order_backlogs.id             IS 'PK';
COMMENT ON COLUMN tbl_dart_order_backlogs.corp_code      IS '기업코드';
COMMENT ON COLUMN tbl_dart_order_backlogs.rcept_no       IS '접수번호';
COMMENT ON COLUMN tbl_dart_order_backlogs.year           IS '회계연도';
COMMENT ON COLUMN tbl_dart_order_backlogs.quarter        IS '분기';
COMMENT ON COLUMN tbl_dart_order_backlogs.backlog_amount IS '수주잔고 금액';
COMMENT ON COLUMN tbl_dart_order_backlogs.description    IS '설명';
COMMENT ON COLUMN tbl_dart_order_backlogs.created_at     IS '생성일시';

-- tbl_fnguide_consensus
COMMENT ON COLUMN tbl_fnguide_consensus.code               IS '종목코드';
COMMENT ON COLUMN tbl_fnguide_consensus.date               IS '컨센서스 기준일';
COMMENT ON COLUMN tbl_fnguide_consensus.target_period      IS '추정 대상 기간';
COMMENT ON COLUMN tbl_fnguide_consensus.name               IS '종목명';
COMMENT ON COLUMN tbl_fnguide_consensus.sector             IS '업종';
COMMENT ON COLUMN tbl_fnguide_consensus.current_price      IS '현재 주가';
COMMENT ON COLUMN tbl_fnguide_consensus.market_cap         IS '시가총액';
COMMENT ON COLUMN tbl_fnguide_consensus.roe                IS 'ROE (%)';
COMMENT ON COLUMN tbl_fnguide_consensus.dividend_yield     IS '배당수익률 (%)';
COMMENT ON COLUMN tbl_fnguide_consensus.sales              IS '매출액';
COMMENT ON COLUMN tbl_fnguide_consensus.operating_profit   IS '영업이익';
COMMENT ON COLUMN tbl_fnguide_consensus.net_income_equity  IS '지배주주순이익';
COMMENT ON COLUMN tbl_fnguide_consensus.eps                IS 'EPS';
COMMENT ON COLUMN tbl_fnguide_consensus.bps                IS 'BPS (주당순자산)';
COMMENT ON COLUMN tbl_fnguide_consensus.per                IS 'PER';
COMMENT ON COLUMN tbl_fnguide_consensus.pbr                IS 'PBR';
COMMENT ON COLUMN tbl_fnguide_consensus.rev_op_1m          IS '1개월 영업이익 변동률';
COMMENT ON COLUMN tbl_fnguide_consensus.rev_op_3m          IS '3개월 영업이익 변동률';
COMMENT ON COLUMN tbl_fnguide_consensus.rev_op_6m          IS '6개월 영업이익 변동률';
COMMENT ON COLUMN tbl_fnguide_consensus.rev_op_1y          IS '1년 영업이익 변동률';
COMMENT ON COLUMN tbl_fnguide_consensus.avg_target_price   IS '평균 목표주가';
COMMENT ON COLUMN tbl_fnguide_consensus.avg_recommendation IS '평균 투자의견 (1~4)';
COMMENT ON COLUMN tbl_fnguide_consensus.est_inst_cnt       IS '추정기관수';
COMMENT ON COLUMN tbl_fnguide_consensus.source             IS '데이터 출처';
COMMENT ON COLUMN tbl_fnguide_consensus.updated_at         IS '업데이트 시각';

-- tbl_fnguide_report_summaries
COMMENT ON COLUMN tbl_fnguide_report_summaries.summary_id      IS 'PK';
COMMENT ON COLUMN tbl_fnguide_report_summaries.source_page_url IS '원본 페이지 URL';
COMMENT ON COLUMN tbl_fnguide_report_summaries.report_date     IS '리포트 발간일';
COMMENT ON COLUMN tbl_fnguide_report_summaries.company_name    IS '기업명';
COMMENT ON COLUMN tbl_fnguide_report_summaries.company_code    IS '종목코드';
COMMENT ON COLUMN tbl_fnguide_report_summaries.report_title    IS '리포트 제목';
COMMENT ON COLUMN tbl_fnguide_report_summaries.summary_text    IS '요약 텍스트';
COMMENT ON COLUMN tbl_fnguide_report_summaries.opinion         IS '투자의견';
COMMENT ON COLUMN tbl_fnguide_report_summaries.target_price    IS '목표주가';
COMMENT ON COLUMN tbl_fnguide_report_summaries.prev_close      IS '전일 종가';
COMMENT ON COLUMN tbl_fnguide_report_summaries.provider        IS '제공 증권사';
COMMENT ON COLUMN tbl_fnguide_report_summaries.author          IS '작성자';
COMMENT ON COLUMN tbl_fnguide_report_summaries.article_url     IS '기사 URL';
COMMENT ON COLUMN tbl_fnguide_report_summaries.pdf_url         IS 'PDF URL';
COMMENT ON COLUMN tbl_fnguide_report_summaries.report_key      IS '리포트 키 (중복방지)';
COMMENT ON COLUMN tbl_fnguide_report_summaries.item_rank       IS '정렬 순위';
COMMENT ON COLUMN tbl_fnguide_report_summaries.sync_status     IS '동기화 상태 (0=대기, 1=처리중, 2=완료)';
COMMENT ON COLUMN tbl_fnguide_report_summaries.created_at      IS '생성일시';
COMMENT ON COLUMN tbl_fnguide_report_summaries.updated_at      IS '수정일시';

-- tbl_investment_notes / investment_notes
COMMENT ON COLUMN tbl_investment_notes.id            IS 'PK';
COMMENT ON COLUMN tbl_investment_notes.user_id       IS '사용자 ID';
COMMENT ON COLUMN tbl_investment_notes.content       IS '메모 내용';
COMMENT ON COLUMN tbl_investment_notes.color_bg      IS '배경색';
COMMENT ON COLUMN tbl_investment_notes.color_border  IS '테두리색';
COMMENT ON COLUMN tbl_investment_notes.x_pos         IS 'X 위치';
COMMENT ON COLUMN tbl_investment_notes.y_pos         IS 'Y 위치';
COMMENT ON COLUMN tbl_investment_notes.width         IS '너비';
COMMENT ON COLUMN tbl_investment_notes.height        IS '높이';
COMMENT ON COLUMN tbl_investment_notes.z_index       IS 'Z 인덱스 (레이어)';
COMMENT ON COLUMN tbl_investment_notes.parent_id     IS '상위 노트 ID';
COMMENT ON COLUMN tbl_investment_notes.created_at    IS '생성일시';
COMMENT ON COLUMN tbl_investment_notes.updated_at    IS '수정일시';

-- investment_notes (Legacy)
COMMENT ON COLUMN investment_notes.id            IS 'PK';
COMMENT ON COLUMN investment_notes.user_id       IS '사용자 ID';
COMMENT ON COLUMN investment_notes.content       IS '메모 내용';
COMMENT ON COLUMN investment_notes.color_bg      IS '배경색';
COMMENT ON COLUMN investment_notes.color_border  IS '테두리색';
COMMENT ON COLUMN investment_notes.x_pos         IS 'X 위치';
COMMENT ON COLUMN investment_notes.y_pos         IS 'Y 위치';
COMMENT ON COLUMN investment_notes.width         IS '너비';
COMMENT ON COLUMN investment_notes.height        IS '높이';
COMMENT ON COLUMN investment_notes.z_index       IS 'Z 인덱스 (레이어)';
COMMENT ON COLUMN investment_notes.parent_id     IS '상위 노트 ID';
COMMENT ON COLUMN investment_notes.created_at    IS '생성일시';
COMMENT ON COLUMN investment_notes.updated_at    IS '수정일시';

-- tbl_market_sentiment_daily_snapshots
COMMENT ON COLUMN tbl_market_sentiment_daily_snapshots.id              IS 'PK';
COMMENT ON COLUMN tbl_market_sentiment_daily_snapshots.source          IS '데이터 출처';
COMMENT ON COLUMN tbl_market_sentiment_daily_snapshots.snapshot_date   IS '스냅샷 기준일';
COMMENT ON COLUMN tbl_market_sentiment_daily_snapshots.snapshot_ts     IS '스냅샷 시각';
COMMENT ON COLUMN tbl_market_sentiment_daily_snapshots.score           IS '종합 점수';
COMMENT ON COLUMN tbl_market_sentiment_daily_snapshots.rating          IS '등급';
COMMENT ON COLUMN tbl_market_sentiment_daily_snapshots.history_json    IS '과거 데이터 (JSON)';
COMMENT ON COLUMN tbl_market_sentiment_daily_snapshots.indicators_json IS '지표 데이터 (JSON)';
COMMENT ON COLUMN tbl_market_sentiment_daily_snapshots.raw_json        IS '원본 데이터 (JSON)';
COMMENT ON COLUMN tbl_market_sentiment_daily_snapshots.fetched_at      IS '수집 시각';

-- tbl_market_sentiment_indicators
COMMENT ON COLUMN tbl_market_sentiment_indicators.id          IS 'PK';
COMMENT ON COLUMN tbl_market_sentiment_indicators.key         IS '지표 키';
COMMENT ON COLUMN tbl_market_sentiment_indicators.title       IS '지표명';
COMMENT ON COLUMN tbl_market_sentiment_indicators.category    IS '카테고리';
COMMENT ON COLUMN tbl_market_sentiment_indicators.description IS '설명';
COMMENT ON COLUMN tbl_market_sentiment_indicators.value       IS '지표 값';
COMMENT ON COLUMN tbl_market_sentiment_indicators.unit        IS '단위';
COMMENT ON COLUMN tbl_market_sentiment_indicators.score       IS '점수';
COMMENT ON COLUMN tbl_market_sentiment_indicators.status      IS '상태';
COMMENT ON COLUMN tbl_market_sentiment_indicators.source      IS '데이터 출처';
COMMENT ON COLUMN tbl_market_sentiment_indicators.sort_order  IS '정렬 순서';
COMMENT ON COLUMN tbl_market_sentiment_indicators.updated_at  IS '수정일시';

-- tbl_market_sentiment_snapshots
COMMENT ON COLUMN tbl_market_sentiment_snapshots.id              IS 'PK';
COMMENT ON COLUMN tbl_market_sentiment_snapshots.source          IS '데이터 출처';
COMMENT ON COLUMN tbl_market_sentiment_snapshots.snapshot_ts     IS '스냅샷 시각';
COMMENT ON COLUMN tbl_market_sentiment_snapshots.score           IS '종합 점수';
COMMENT ON COLUMN tbl_market_sentiment_snapshots.rating          IS '등급';
COMMENT ON COLUMN tbl_market_sentiment_snapshots.history_json    IS '과거 데이터 (JSON)';
COMMENT ON COLUMN tbl_market_sentiment_snapshots.indicators_json IS '지표 데이터 (JSON)';
COMMENT ON COLUMN tbl_market_sentiment_snapshots.raw_json        IS '원본 데이터 (JSON)';
COMMENT ON COLUMN tbl_market_sentiment_snapshots.fetched_at      IS '수집 시각';

-- tbl_report_send_history
COMMENT ON COLUMN tbl_report_send_history.id        IS 'PK';
COMMENT ON COLUMN tbl_report_send_history.report_id IS '레포트 ID';
COMMENT ON COLUMN tbl_report_send_history.user_id   IS '수신 사용자 ID';
COMMENT ON COLUMN tbl_report_send_history.keyword   IS '매칭 키워드';
COMMENT ON COLUMN tbl_report_send_history.sent_at   IS '발송 시각';

-- tbl_sec_reports
COMMENT ON COLUMN tbl_sec_reports.report_id           IS 'PK';
COMMENT ON COLUMN tbl_sec_reports.sec_firm_order      IS '증권사 순서 (FK)';
COMMENT ON COLUMN tbl_sec_reports.article_board_order IS '게시판 순서 (FK)';
COMMENT ON COLUMN tbl_sec_reports.firm_nm             IS '증권사명';
COMMENT ON COLUMN tbl_sec_reports.article_title       IS '리포트 제목';
COMMENT ON COLUMN tbl_sec_reports.article_url         IS '원문 URL';
COMMENT ON COLUMN tbl_sec_reports.main_ch_send_yn     IS '메인채널 발송 여부 (Y/N)';
COMMENT ON COLUMN tbl_sec_reports.download_status_yn  IS '다운로드 상태 (Y/N)';
COMMENT ON COLUMN tbl_sec_reports.download_url        IS '다운로드 URL';
COMMENT ON COLUMN tbl_sec_reports.save_time           IS '저장 시각';
COMMENT ON COLUMN tbl_sec_reports.reg_dt              IS '등록일 (YYYYMMDD)';
COMMENT ON COLUMN tbl_sec_reports.writer              IS '작성자';
COMMENT ON COLUMN tbl_sec_reports.key                 IS '고유 키 (중복방지)';
COMMENT ON COLUMN tbl_sec_reports.telegram_url        IS '텔레그램 공유 URL';
COMMENT ON COLUMN tbl_sec_reports.mkt_tp              IS '시장구분 (KR/US/etc)';
COMMENT ON COLUMN tbl_sec_reports.gemini_summary      IS 'Gemini AI 요약';
COMMENT ON COLUMN tbl_sec_reports.summary_time        IS '요약 생성 시각';
COMMENT ON COLUMN tbl_sec_reports.summary_model       IS '요약 모델명';
COMMENT ON COLUMN tbl_sec_reports.archive_path        IS '아카이브 경로';
COMMENT ON COLUMN tbl_sec_reports.retry_count         IS '재시도 횟수';
COMMENT ON COLUMN tbl_sec_reports.sync_status         IS '동기화 상태 (0=대기,1=처리중,2=완료,-1=실패)';
COMMENT ON COLUMN tbl_sec_reports.pdf_url             IS 'PDF URL';
COMMENT ON COLUMN tbl_sec_reports.pdf_sync_status     IS 'PDF 동기화 상태';

-- tbl_sec_reports_alert_keywords
COMMENT ON COLUMN tbl_sec_reports_alert_keywords.id         IS 'PK';
COMMENT ON COLUMN tbl_sec_reports_alert_keywords.user_id    IS '사용자 ID';
COMMENT ON COLUMN tbl_sec_reports_alert_keywords.keyword    IS '알림 키워드';
COMMENT ON COLUMN tbl_sec_reports_alert_keywords.is_active  IS '활성화 여부';
COMMENT ON COLUMN tbl_sec_reports_alert_keywords.created_at IS '생성일시';
COMMENT ON COLUMN tbl_sec_reports_alert_keywords.updated_at IS '수정일시';

-- tbl_sec_reports_favorites
COMMENT ON COLUMN tbl_sec_reports_favorites.id         IS 'PK';
COMMENT ON COLUMN tbl_sec_reports_favorites.user_id    IS '사용자 ID';
COMMENT ON COLUMN tbl_sec_reports_favorites.report_id  IS '레포트 ID';
COMMENT ON COLUMN tbl_sec_reports_favorites.created_at IS '생성일시';

-- tbl_sec_reports_pdf_archive
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.report_id         IS '레포트 ID (FK)';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.file_path         IS '파일 경로';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.file_size         IS '파일 크기 (bytes)';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.page_count        IS '페이지 수';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.pdf_url           IS 'PDF URL';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.download_url      IS '다운로드 URL';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.telegram_url      IS '텔레그램 URL';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.key               IS '고유 키';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.archive_status    IS '아카이브 상태 (ARCHIVED/INIT/FAILED)';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.file_name         IS '파일명';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.download_status_yn IS '다운로드 상태';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.sync_status       IS '동기화 상태';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.retry_count       IS '재시도 횟수';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.firm_nm           IS '증권사명';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.title             IS '리포트 제목';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.reg_dt            IS '등록일';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.pdf_sync_status   IS 'PDF 동기화 상태';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.created_at        IS '생성일시';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.updated_at        IS '수정일시';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.pdf_hash          IS 'PDF 해시값 (중복방지)';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.author            IS '작성자';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.has_text          IS '텍스트 추출 가능 여부';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.is_encrypted      IS '암호화 여부';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.storage_backend   IS '스토리지 백엔드 (onedrive/s3)';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.storage_key       IS '스토리지 키';
COMMENT ON COLUMN tbl_sec_reports_pdf_archive.last_accessed_at  IS '마지막 접근 시각';

-- tbl_sec_reports_telegram_users
COMMENT ON COLUMN tbl_sec_reports_telegram_users.id         IS 'PK (텔레그램 user_id)';
COMMENT ON COLUMN tbl_sec_reports_telegram_users.first_name IS '이름';
COMMENT ON COLUMN tbl_sec_reports_telegram_users.last_name  IS '성';
COMMENT ON COLUMN tbl_sec_reports_telegram_users.username   IS '텔레그램 사용자명';
COMMENT ON COLUMN tbl_sec_reports_telegram_users.photo_url  IS '프로필 사진 URL';
COMMENT ON COLUMN tbl_sec_reports_telegram_users.status     IS '상태 (active/blocked/inactive)';
COMMENT ON COLUMN tbl_sec_reports_telegram_users.is_admin   IS '관리자 여부';
COMMENT ON COLUMN tbl_sec_reports_telegram_users.created_at IS '가입일시 (Unix timestamp)';

-- tbl_telegram_etf_portfolios
COMMENT ON COLUMN tbl_telegram_etf_portfolios.id            IS 'PK';
COMMENT ON COLUMN tbl_telegram_etf_portfolios.telegram_id   IS '텔레그램 사용자 ID';
COMMENT ON COLUMN tbl_telegram_etf_portfolios.portfolio_name IS '포트폴리오명';
COMMENT ON COLUMN tbl_telegram_etf_portfolios.etf_code      IS 'ETF 종목코드';
COMMENT ON COLUMN tbl_telegram_etf_portfolios.quantity      IS '보유 수량';
COMMENT ON COLUMN tbl_telegram_etf_portfolios.created_at    IS '생성일시';
COMMENT ON COLUMN tbl_telegram_etf_portfolios.updated_at    IS '수정일시';

-- tbm_dart_companies
COMMENT ON COLUMN tbm_dart_companies.id          IS 'PK';
COMMENT ON COLUMN tbm_dart_companies.corp_code   IS 'DART 기업 고유코드';
COMMENT ON COLUMN tbm_dart_companies.corp_name   IS '기업명';
COMMENT ON COLUMN tbm_dart_companies.stock_code  IS '종목코드';
COMMENT ON COLUMN tbm_dart_companies.modify_date IS '최종 수정일';
COMMENT ON COLUMN tbm_dart_companies.created_at  IS '생성일시';

-- tbm_dart_disclosures
COMMENT ON COLUMN tbm_dart_disclosures.id               IS 'PK';
COMMENT ON COLUMN tbm_dart_disclosures.source           IS '데이터 출처';
COMMENT ON COLUMN tbm_dart_disclosures.published_at      IS '공시 게시일시';
COMMENT ON COLUMN tbm_dart_disclosures.company_name      IS '기업명';
COMMENT ON COLUMN tbm_dart_disclosures.company_code      IS '기업코드';
COMMENT ON COLUMN tbm_dart_disclosures.disclosure_title  IS '공시 제목';
COMMENT ON COLUMN tbm_dart_disclosures.disclosure_type   IS '공시 유형';
COMMENT ON COLUMN tbm_dart_disclosures.insider_name      IS '내부자명';
COMMENT ON COLUMN tbm_dart_disclosures.insider_role      IS '내부자 역할';
COMMENT ON COLUMN tbm_dart_disclosures.transaction_type  IS '거래 유형';
COMMENT ON COLUMN tbm_dart_disclosures.shares            IS '주식수';
COMMENT ON COLUMN tbm_dart_disclosures.amount            IS '거래금액';
COMMENT ON COLUMN tbm_dart_disclosures.avg_price         IS '평균단가';
COMMENT ON COLUMN tbm_dart_disclosures.ownership_after   IS '거래후 보유비율';
COMMENT ON COLUMN tbm_dart_disclosures.signal_score      IS '신호 점수';
COMMENT ON COLUMN tbm_dart_disclosures.summary_text      IS '요약 텍스트';
COMMENT ON COLUMN tbm_dart_disclosures.dart_url          IS 'DART 원문 URL';
COMMENT ON COLUMN tbm_dart_disclosures.telegram_url      IS '텔레그램 공유 URL';
COMMENT ON COLUMN tbm_dart_disclosures.tags_json         IS '태그 (JSON)';
COMMENT ON COLUMN tbm_dart_disclosures.fetched_at        IS '수집 시각';

-- tbm_sec_firm_board_info
COMMENT ON COLUMN tbm_sec_firm_board_info.sec_firm_order      IS '증권사 순서 (FK)';
COMMENT ON COLUMN tbm_sec_firm_board_info.article_board_order IS '게시판 순서';
COMMENT ON COLUMN tbm_sec_firm_board_info.board_nm            IS '게시판명 (원본)';
COMMENT ON COLUMN tbm_sec_firm_board_info.board_cd            IS '게시판 코드';
COMMENT ON COLUMN tbm_sec_firm_board_info.label_nm            IS '표시 라벨명';

-- tbm_sec_firm_info
COMMENT ON COLUMN tbm_sec_firm_info.sec_firm_order     IS 'PK - 증권사 순서';
COMMENT ON COLUMN tbm_sec_firm_info.firm_nm            IS '증권사명';
COMMENT ON COLUMN tbm_sec_firm_info.telegram_update_yn IS '텔레그램 업데이트 여부 (Y/N)';
COMMENT ON COLUMN tbm_sec_firm_info."COMMENT_PDF_URL"  IS 'PDF URL 코멘트';
