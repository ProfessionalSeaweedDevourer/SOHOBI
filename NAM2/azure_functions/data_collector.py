"""
data_collector.py
모든 데이터 소스에서 지원사업 데이터를 수집하는 모듈

지원 소스:
1. 정부24 공공서비스 API (GOV24_API_KEY)
2. K-Startup 사업공고 조회 API (KSTARTUP_API_KEY) — 창업진흥원
3. 창업공간플랫폼 조회 API (KISED_SPACE_API_KEY) — 창업진흥원
4. 정부지원사업 주관기관 API (KISED_AGENCY_API_KEY) — 창업진흥원
5. 창업에듀 교육과정 API (KISED_EDU_API_KEY) — 창업진흥원
6. 중소벤처24 공고 API (SME24_API_KEY) — 선택
7. 기업마당 API (BIZINFO_API_KEY) — 선택
8. 소진공/신보/고용/외식업 큐레이션 데이터 — 키 불필요
"""

import os
import time
import logging
import requests
from typing import Optional

# ── 공통 ────────────────────────────────────────────

KEYWORDS = [
    "소상공인", "자영업", "외식업", "음식점", "카페",
    "창업", "소공인", "전통시장", "식품", "요식업",
    "프랜차이즈", "배달", "식당", "베이커리", "제과",
    "대출", "융자", "보증", "정책자금", "운전자금",
    "시설자금", "신용보증", "기술보증", "긴급경영",
    "경영안정", "재기지원", "폐업", "전환자금",
    "소상공인진흥", "중소벤처", "소진공",
    "고용지원", "일자리", "인건비", "채용장려",
    "고용안정", "두루누리", "사회보험",
    "경영교육", "컨설팅", "역량강화", "사업정리",
]


def _matches_keywords(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in KEYWORDS)


# ━━━ 1. 정부24 API ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def collect_gov24() -> list[dict]:
    """정부24 공공서비스 API에서 소상공인 관련 지원사업 수집"""
    api_key = os.getenv("GOV24_API_KEY", "")
    if not api_key:
        logging.warning("[gov24] API 키 없음, 스킵")
        return []

    base_url = "https://api.odcloud.kr/api/gov24/v3/serviceList"
    all_items = []
    page = 1

    while True:
        try:
            resp = requests.get(base_url, params={
                "page": page, "perPage": 100, "serviceKey": api_key
            }, timeout=15)
            if resp.status_code != 200:
                logging.warning(f"[gov24] page {page} status {resp.status_code}")
                break

            data = resp.json()
            items = data.get("data", [])
            if not items:
                break

            all_items.extend(items)
            total = data.get("totalCount", 0)
            if len(all_items) >= total:
                break

            page += 1
            time.sleep(0.3)

        except Exception as e:
            logging.warning(f"[gov24] page {page} error: {e}")
            break

    # 키워드 필터링
    filtered = []
    for item in all_items:
        text = " ".join([
            str(item.get("서비스명", "")),
            str(item.get("서비스목적요약", "")),
            str(item.get("지원대상", "")),
            str(item.get("지원내용", "")),
            str(item.get("선정기준", "")),
            str(item.get("서비스분야", "")),
        ])
        if _matches_keywords(text):
            filtered.append({
                "service_id": item.get("서비스ID", ""),
                "program_name": item.get("서비스명", ""),
                "summary": item.get("서비스목적요약", ""),
                "field": item.get("서비스분야", ""),
                "target": item.get("지원대상", ""),
                "criteria": item.get("선정기준", ""),
                "support_content": item.get("지원내용", ""),
                "apply_method": item.get("신청방법", ""),
                "apply_deadline": item.get("신청기한", ""),
                "org_name": item.get("소관기관명", ""),
                "phone": item.get("전화문의", ""),
                "url": item.get("상세조회URL", ""),
                "support_type": item.get("지원유형", ""),
                "source_name": "gov24",
            })

    logging.info(f"[gov24] {len(all_items)}건 조회 → {len(filtered)}건 필터링")
    return filtered


# ━━━ 2. K-Startup 사업공고 조회 (창업진흥원) ━━━━━━━━

def collect_kstartup() -> list[dict]:
    """창업진흥원 K-Startup 사업공고 + 사업소개 조회 (data.go.kr #15125364)"""
    api_key = os.getenv("KSTARTUP_API_KEY", "")
    if not api_key:
        logging.info("[kstartup] API 키 없음, 스킵")
        return []

    results = []

    # ── (A) 사업공고 (28,000+건, 모집중만 필터) ──
    page = 1
    while True:
        try:
            url = "https://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01"
            resp = requests.get(url, params={
                "serviceKey": api_key,
                "page": page,
                "perPage": 100,
                "returnType": "json",
            }, timeout=20)

            if resp.status_code != 200:
                logging.warning(f"[kstartup-공고] page {page} status {resp.status_code}")
                break

            data = resp.json()
            items = data.get("data", [])
            if not items:
                break

            for item in items:
                # 모집중인 공고만 수집
                if item.get("rcrt_prgs_yn") != "Y":
                    continue
                apply_url = (item.get("aply_mthd_onli_rcpt_istc") or
                             item.get("detl_pg_url") or
                             "https://www.k-startup.go.kr")
                results.append({
                    "service_id": f"kstartup_{item.get('pbanc_sn', '')}",
                    "program_name": item.get("biz_pbanc_nm", ""),
                    "summary": item.get("pbanc_ctnt", ""),
                    "field": item.get("supt_biz_clsfc", "창업지원"),
                    "target": item.get("aply_trgt_ctnt", item.get("aply_trgt", "")),
                    "criteria": item.get("aply_excl_trgt_ctnt", ""),
                    "support_content": item.get("pbanc_ctnt", ""),
                    "apply_method": apply_url,
                    "apply_deadline": item.get("pbanc_rcpt_end_dt", ""),
                    "org_name": item.get("pbanc_ntrp_nm", item.get("sprv_inst", "창업진흥원")),
                    "phone": item.get("prch_cnpl_no", ""),
                    "url": item.get("detl_pg_url", "https://www.k-startup.go.kr"),
                    "support_type": item.get("supt_biz_clsfc", "창업지원"),
                    "source_name": "kstartup",
                })

            total_count = int(data.get("totalCount", 0))
            if page * 100 >= total_count:
                break

            page += 1
            time.sleep(0.3)

        except Exception as e:
            logging.warning(f"[kstartup-공고] page {page} error: {e}")
            break

    logging.info(f"[kstartup-공고] {len(results)}건 (모집중)")

    # ── (B) 사업소개 (1,700+건) ──
    biz_count = 0
    page = 1
    while True:
        try:
            url = "https://apis.data.go.kr/B552735/kisedKstartupService01/getBusinessInformation01"
            resp = requests.get(url, params={
                "serviceKey": api_key,
                "page": page,
                "perPage": 100,
                "returnType": "json",
            }, timeout=20)

            if resp.status_code != 200:
                break

            data = resp.json()
            items = data.get("data", [])
            if not items:
                break

            for item in items:
                results.append({
                    "service_id": f"kstartup_biz_{item.get('id', '')}",
                    "program_name": item.get("supt_biz_titl_nm", ""),
                    "summary": item.get("supt_biz_intrd_info", ""),
                    "field": "창업지원",
                    "target": item.get("biz_supt_trgt_info", ""),
                    "criteria": item.get("supt_biz_chrct", ""),
                    "support_content": item.get("biz_supt_ctnt", ""),
                    "apply_method": item.get("detl_pg_url", "K-Startup 홈페이지"),
                    "apply_deadline": "",
                    "org_name": "창업진흥원",
                    "phone": "",
                    "url": item.get("detl_pg_url", "https://www.k-startup.go.kr"),
                    "support_type": "창업지원",
                    "source_name": "kstartup_biz",
                })
                biz_count += 1

            total_count = int(data.get("totalCount", 0))
            if page * 100 >= total_count:
                break

            page += 1
            time.sleep(0.3)

        except Exception as e:
            logging.warning(f"[kstartup-사업] page {page} error: {e}")
            break

    logging.info(f"[kstartup-사업] {biz_count}건")
    logging.info(f"[kstartup] 총 {len(results)}건 수집")
    return results


# ━━━ 3. 창업공간플랫폼 조회 (창업진흥원) ━━━━━━━━━━━

def collect_kised_space() -> list[dict]:
    """창업진흥원 창업공간플랫폼 센터목록 조회 (data.go.kr #15125365)"""
    api_key = os.getenv("KISED_SPACE_API_KEY", "")
    if not api_key:
        logging.info("[kised_space] API 키 없음, 스킵")
        return []

    results = []
    page = 1

    while True:
        try:
            url = "https://apis.data.go.kr/B552735/kisedSlpService/getCenterList"
            resp = requests.get(url, params={
                "serviceKey": api_key,
                "page": page,
                "perPage": 100,
                "returnType": "json",
            }, timeout=20)

            if resp.status_code == 403:
                logging.warning("[kised_space] 403 Forbidden — API 활용 승인 필요")
                break
            if resp.status_code != 200:
                logging.warning(f"[kised_space] page {page} status {resp.status_code}")
                break

            data = resp.json()
            items = data.get("data", [])
            if not items:
                break

            for item in items:
                center_name = item.get("cntr_nm", "")
                addr = item.get("addr", item.get("rdnmadr", ""))
                if not center_name:
                    continue
                results.append({
                    "service_id": f"kised_space_{item.get('id', '')}",
                    "program_name": f"창업공간: {center_name}",
                    "summary": f"{center_name} - {addr}. 창업자를 위한 사무공간/보육센터",
                    "field": "창업공간",
                    "target": "예비창업자, 초기창업자, 스타트업",
                    "criteria": "입주 심사",
                    "support_content": f"위치: {addr}. 창업보육센터/코워킹스페이스 제공",
                    "apply_method": "창업공간플랫폼 홈페이지",
                    "apply_deadline": "연중 수시",
                    "org_name": item.get("oper_inst_nm", "창업진흥원"),
                    "phone": item.get("telno", ""),
                    "url": "https://spaces.k-startup.go.kr",
                    "support_type": "현물(공간)",
                    "source_name": "kised_space",
                })

            total_count = int(data.get("totalCount", 0))
            if page * 100 >= total_count:
                break

            page += 1
            time.sleep(0.3)

        except Exception as e:
            logging.warning(f"[kised_space] page {page} error: {e}")
            break

    logging.info(f"[kised_space] {len(results)}건 수집")
    return results


# ━━━ 4. 정부지원사업 주관기관 정보 (창업진흥원) ━━━━━

def collect_kised_agency() -> list[dict]:
    """창업진흥원 정부지원사업 주관기관 정보 (data.go.kr #15125366)
    주관기관 목록 — 추천 시 '어느 기관에 문의하면 되는지' 연결하는 보조 데이터"""
    api_key = os.getenv("KISED_AGENCY_API_KEY", "")
    if not api_key:
        logging.info("[kised_agency] API 키 없음, 스킵")
        return []

    results = []
    page = 1

    while True:
        try:
            url = "https://apis.data.go.kr/B552735/kisedPmsService/getInstitutionInformation"
            resp = requests.get(url, params={
                "serviceKey": api_key,
                "page": page,
                "perPage": 100,
                "returnType": "json",
            }, timeout=20)

            if resp.status_code != 200:
                logging.warning(f"[kised_agency] page {page} status {resp.status_code}")
                break

            data = resp.json()
            items = data.get("data", [])
            if not items:
                break

            for item in items:
                inst_name = item.get("inst_nm", "")
                if not inst_name:
                    continue
                results.append({
                    "service_id": f"kised_agency_{item.get('brno', item.get('id', ''))}",
                    "program_name": f"창업지원 주관기관: {inst_name}",
                    "summary": f"{inst_name} — 창업지원사업 주관/수행기관. 설립: {item.get('fndn_dt', '')}",
                    "field": "창업지원",
                    "target": "예비창업자, 초기창업자, 중소기업",
                    "criteria": "",
                    "support_content": f"기관명: {inst_name}. 영문명: {item.get('inst_eng_nm', '')}. 대표: {item.get('repr_nm', '')}",
                    "apply_method": "K-Startup 홈페이지",
                    "apply_deadline": "",
                    "org_name": inst_name,
                    "phone": "",
                    "url": "https://www.k-startup.go.kr",
                    "support_type": "창업지원기관",
                    "source_name": "kised_agency",
                })

            total_count = int(data.get("totalCount", 0))
            if page * 100 >= total_count:
                break

            page += 1
            time.sleep(0.3)

        except Exception as e:
            logging.warning(f"[kised_agency] page {page} error: {e}")
            break

    logging.info(f"[kised_agency] {len(results)}건 수집")
    return results


# ━━━ 5. 창업에듀 교육과정 조회 (창업진흥원) ━━━━━━━━━

def collect_kised_edu() -> list[dict]:
    """창업진흥원 창업에듀 교육과정 조회 서비스 (data.go.kr #15125358)"""
    api_key = os.getenv("KISED_EDU_API_KEY", "")
    if not api_key:
        logging.info("[kised_edu] API 키 없음, 스킵")
        return []

    results = []
    page = 1

    while True:
        try:
            url = "https://apis.data.go.kr/B552735/kisedEduService/getEducationInformation"
            resp = requests.get(url, params={
                "serviceKey": api_key,
                "page": page,
                "perPage": 100,
                "returnType": "json",
            }, timeout=20)

            if resp.status_code != 200:
                logging.warning(f"[kised_edu] page {page} status {resp.status_code}")
                break

            data = resp.json()
            items = data.get("data", [])
            if not items:
                break

            for item in items:
                course_name = item.get("lctr_nm", "")
                if not course_name:
                    continue
                course_url = item.get("lctr_pg_url", "")
                if course_url and not course_url.startswith("http"):
                    course_url = f"https://{course_url}"
                results.append({
                    "service_id": f"kised_edu_{item.get('id', '')}",
                    "program_name": f"창업교육: {course_name}",
                    "summary": item.get("lctr_istc", f"{course_name} — 창업에듀 온라인 교육과정"),
                    "field": "교육·컨설팅",
                    "target": "예비창업자, 초기창업자",
                    "criteria": "누구나 수강 가능",
                    "support_content": f"교육과정: {course_name}. {item.get('lctr_istc', '온라인 창업교육')}. 키워드: {item.get('kywrd', '')}",
                    "apply_method": course_url or "창업에듀 홈페이지",
                    "apply_deadline": "연중 수시 (온라인)",
                    "org_name": "창업진흥원",
                    "phone": "",
                    "url": course_url or "https://edu.k-startup.go.kr",
                    "support_type": "교육",
                    "source_name": "kised_edu",
                })

            total_count = int(data.get("totalCount", 0))
            if page * 100 >= total_count:
                break

            page += 1
            time.sleep(0.3)

        except Exception as e:
            logging.warning(f"[kised_edu] page {page} error: {e}")
            break

    logging.info(f"[kised_edu] {len(results)}건 수집")
    return results


# ━━━ 6. 중소벤처24 API ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def collect_sme24() -> list[dict]:
    """중소벤처24 공고정보 API (smes.go.kr 자체)"""
    api_key = os.getenv("SME24_API_KEY", "")
    if not api_key:
        logging.info("[sme24] API 키 없음, 스킵")
        return []

    results = []
    try:
        url = "https://www.smes.go.kr/fnct/apiReqst/extPblancInfo"
        resp = requests.get(url, params={
            "crtfcKey": api_key,
            "dataType": "json",
            "searchCnt": 200,
        }, timeout=20)

        if resp.status_code != 200:
            logging.warning(f"[sme24] status {resp.status_code}")
            return []

        data = resp.json()
        if "reqErr" in data:
            logging.warning(f"[sme24] API 에러: {data['reqErr']}")
            return []

        items = data.get("jsonArray", data.get("items", []))
        for item in items:
            pblanc_nm = item.get("pblancNm", "")
            if not pblanc_nm:
                continue
            results.append({
                "service_id": f"sme24_{item.get('pblancId', '')}",
                "program_name": pblanc_nm,
                "summary": item.get("bsnsSumryCn", pblanc_nm),
                "field": "중소벤처기업",
                "target": item.get("trgetNm", "중소기업, 소상공인"),
                "criteria": "",
                "support_content": item.get("sporCn", pblanc_nm),
                "apply_method": "중소벤처24 홈페이지",
                "apply_deadline": item.get("endDt", item.get("reqstEndDe", "")),
                "org_name": item.get("jrsdInsttNm", item.get("excInsttNm", "중소벤처기업부")),
                "phone": "국번없이 1357",
                "url": item.get("detailPageUrl", "https://www.smes.go.kr"),
                "support_type": item.get("sporTypeNm", "지원사업"),
                "source_name": "sme24",
            })

        logging.info(f"[sme24] {len(results)}건 수집")
    except Exception as e:
        logging.warning(f"[sme24] error: {e}")

    return results


# ━━━ 7. 기업마당 API ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def collect_bizinfo() -> list[dict]:
    """기업마당(bizinfo) 지원사업 API — bizinfo.go.kr 자체 발급 인증키 사용"""
    api_key = os.getenv("BIZINFO_API_KEY", "")
    if not api_key or api_key.startswith("your-"):
        logging.info("[bizinfo] API 키 없음, 스킵")
        return []

    # 소상공인/창업 관련 분야별로 수집
    categories = ["금융", "창업", "경영", "기술", "인력"]
    results = []

    for category in categories:
        try:
            url = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
            resp = requests.get(url, params={
                "crtfcKey": api_key,
                "dataType": "json",
                "searchCnt": 100,
                "category": category,
            }, timeout=20)

            if resp.status_code != 200:
                logging.warning(f"[bizinfo] category={category} status {resp.status_code}")
                continue

            data = resp.json()
            if "reqErr" in data:
                logging.warning(f"[bizinfo] API 에러: {data['reqErr']}")
                break

            items = data.get("jsonArray", data.get("items", []))
            for item in items:
                pblanc_nm = item.get("pblancNm", "")
                if not pblanc_nm:
                    continue
                results.append({
                    "service_id": f"bizinfo_{item.get('pblancId', '')}",
                    "program_name": pblanc_nm,
                    "summary": item.get("bsnsSumryCn", pblanc_nm),
                    "field": item.get("pldirSportRealmMlsfcCodeNm", category),
                    "target": item.get("trgetNm", "중소기업, 소상공인"),
                    "criteria": item.get("slctnMthdCn", ""),
                    "support_content": item.get("sporCn", pblanc_nm),
                    "apply_method": item.get("rcptMthdCn", "기업마당 홈페이지"),
                    "apply_deadline": item.get("reqstEndDe", item.get("endDt", "")),
                    "org_name": item.get("excInsttNm", item.get("jrsdInsttNm", "")),
                    "phone": item.get("cntctTelno", "국번없이 1357"),
                    "url": item.get("detailPageUrl", f"https://www.bizinfo.go.kr"),
                    "support_type": item.get("sporTypeNm", "지원사업"),
                    "source_name": "bizinfo",
                })

            logging.info(f"[bizinfo] category={category}: {len(items)}건")
            time.sleep(0.3)

        except Exception as e:
            logging.warning(f"[bizinfo] category={category} error: {e}")

    logging.info(f"[bizinfo] 총 {len(results)}건 수집")
    return results


# ━━━ 8. 큐레이션 데이터 (API 키 불필요) ━━━━━━━━━━━━━

def get_curated_data() -> list[dict]:
    """소진공 정책자금, 신용보증, 고용지원, 외식업 특화 등 수동 큐레이션 데이터"""
    programs = [
        # ── 소진공 정책자금 ──
        {"service_id": "curated_001", "program_name": "소상공인 일반경영안정자금", "summary": "경영애로를 겪는 소상공인에게 저금리 운전자금 대출 지원", "field": "정책자금", "target": "업력 제한 없는 소상공인 (상시근로자 5인 미만)", "criteria": "소상공인확인서 발급 가능 업체", "support_content": "대출한도: 업체당 7천만원 이내, 대출금리: 정책자금 기준금리(분기별 변동), 대출기간: 5년(거치 2년 포함)", "apply_method": "소진공 홈페이지 온라인 신청", "apply_deadline": "연중 수시", "org_name": "소상공인시장진흥공단", "phone": "1357", "url": "https://www.semas.or.kr", "support_type": "융자(대출)", "source_name": "curated"},
        {"service_id": "curated_002", "program_name": "소상공인 긴급경영안정자금", "summary": "재난, 경기침체 등 긴급 경영위기 소상공인 긴급 자금 지원", "field": "긴급자금", "target": "재난·재해 피해 소상공인, 경영위기 업종 소상공인", "criteria": "피해사실 확인서 또는 경영위기 업종 확인", "support_content": "대출한도: 업체당 7천만원 이내, 우대금리 적용, 대출기간: 5년(거치 2년 포함)", "apply_method": "소진공 홈페이지", "apply_deadline": "연중 수시", "org_name": "소상공인시장진흥공단", "phone": "1357", "url": "https://www.semas.or.kr", "support_type": "융자(대출)", "source_name": "curated"},
        {"service_id": "curated_003", "program_name": "소상공인 성장촉진자금", "summary": "사업 확장, 시설 투자가 필요한 소상공인 지원", "field": "정책자금", "target": "사업 확장·시설 투자가 필요한 소상공인", "criteria": "사업성 평가, 시설투자 계획서", "support_content": "대출한도: 업체당 5억원 이내(시설자금), 대출기간: 8년(거치 3년 포함)", "apply_method": "소진공 홈페이지", "apply_deadline": "연중 수시", "org_name": "소상공인시장진흥공단", "phone": "1357", "url": "https://www.semas.or.kr", "support_type": "융자(대출)", "source_name": "curated"},
        {"service_id": "curated_004", "program_name": "소상공인 재도전 특별자금", "summary": "폐업 후 재창업하는 소상공인의 사업 재개 지원", "field": "재기지원", "target": "폐업 경험이 있는 재창업 소상공인", "criteria": "재창업교육 이수, 폐업사실증명", "support_content": "대출한도: 업체당 7천만원 이내, 우대금리, 대출기간: 5년(거치 2년 포함)", "apply_method": "소진공 홈페이지", "apply_deadline": "연중 수시", "org_name": "소상공인시장진흥공단", "phone": "1357", "url": "https://www.semas.or.kr", "support_type": "융자(대출)", "source_name": "curated"},
        {"service_id": "curated_005", "program_name": "소상공인 전환자금", "summary": "업종전환을 원하는 소상공인 지원 대출", "field": "업종전환", "target": "업종전환을 희망하는 소상공인", "criteria": "업종전환 계획서, 전환교육 이수", "support_content": "대출한도: 업체당 7천만원 이내, 대출기간: 5년(거치 2년 포함)", "apply_method": "소진공 홈페이지", "apply_deadline": "연중 수시", "org_name": "소상공인시장진흥공단", "phone": "1357", "url": "https://www.semas.or.kr", "support_type": "융자(대출)", "source_name": "curated"},

        # ── 신용보증 ──
        {"service_id": "curated_010", "program_name": "신용보증기금 소상공인 신용보증", "summary": "담보력 부족 소상공인의 대출을 위한 신용보증서 발급", "field": "금융지원", "target": "소상공인, 자영업자", "criteria": "사업자등록 후 6개월 이상, 신용등급 평가", "support_content": "보증한도: 업체당 최대 2억원, 보증비율: 85~100%, 보증료: 연 0.5~1.5%", "apply_method": "신용보증기금 지점 방문", "apply_deadline": "연중 수시", "org_name": "신용보증기금", "phone": "1588-6565", "url": "https://www.kodit.co.kr", "support_type": "신용보증", "source_name": "curated"},
        {"service_id": "curated_011", "program_name": "기술보증기금 소상공인 기술보증", "summary": "기술력이 있는 소상공인의 사업자금 대출을 위한 기술보증", "field": "금융지원", "target": "기술력 보유 소상공인, 기술창업자", "criteria": "기술사업 영위, 기술평가 통과", "support_content": "보증한도: 업체당 최대 3억원, 보증비율 85~100%", "apply_method": "기술보증기금 지점 방문", "apply_deadline": "연중 수시", "org_name": "기술보증기금", "phone": "1544-1120", "url": "https://www.kibo.or.kr", "support_type": "기술보증", "source_name": "curated"},
        {"service_id": "curated_012", "program_name": "지역신용보증재단 소상공인 보증", "summary": "각 지역 신용보증재단의 소상공인 보증 지원", "field": "금융지원", "target": "해당 지역 소재 소상공인", "criteria": "해당 지역 사업장, 소상공인확인서", "support_content": "보증한도: 업체당 최대 8천만원, 보증비율 85~100%, 저보증료", "apply_method": "지역 재단 방문", "apply_deadline": "연중 수시", "org_name": "지역신용보증재단", "phone": "각 지역 재단", "url": "", "support_type": "신용보증", "source_name": "curated"},
        {"service_id": "curated_013", "program_name": "서울신용보증재단 소상공인 특별보증", "summary": "서울 소재 소상공인 경영안정을 위한 특별보증", "field": "금융지원", "target": "서울시 소재 소상공인", "criteria": "서울시 소재 사업장, 소상공인확인서", "support_content": "보증한도: 최대 1억원, 보증비율 95~100%, 보증료 면제 또는 감면", "apply_method": "서울신보 지점 방문", "apply_deadline": "연중 수시", "org_name": "서울신용보증재단", "phone": "1577-6119", "url": "https://www.seoulshinbo.co.kr", "support_type": "신용보증", "source_name": "curated"},

        # ── 고용지원 ──
        {"service_id": "curated_020", "program_name": "두루누리 사회보험료 지원사업", "summary": "소규모 사업장 근로자·사업주의 사회보험료 지원", "field": "고용지원", "target": "근로자 10인 미만 사업장, 월보수 260만원 미만", "criteria": "10인 미만 사업장, 월보수 260만원 미만", "support_content": "신규가입자 사회보험료 80% 지원", "apply_method": "4대보험 포털사이트", "apply_deadline": "연중 수시", "org_name": "근로복지공단", "phone": "1588-0075", "url": "https://www.4insure.or.kr", "support_type": "보험료지원", "source_name": "curated"},
        {"service_id": "curated_021", "program_name": "고용촉진장려금", "summary": "취업취약계층 채용 시 사업주에게 인건비 지원", "field": "고용지원", "target": "취업취약계층을 신규 채용한 사업주", "criteria": "6개월 이상 고용 유지", "support_content": "월 60만원씩 최대 1년간 지원", "apply_method": "고용센터 신청", "apply_deadline": "연중 수시", "org_name": "고용노동부", "phone": "1350", "url": "https://www.ei.go.kr", "support_type": "현금(인건비)", "source_name": "curated"},
        {"service_id": "curated_022", "program_name": "청년추가고용장려금", "summary": "청년 정규직 채용 시 인건비 지원", "field": "고용지원", "target": "5인 이상 중소·중견기업", "criteria": "청년 정규직 신규 채용, 기존 근로자 수 유지", "support_content": "청년 1인당 연 최대 900만원, 최대 3년간", "apply_method": "고용센터 신청", "apply_deadline": "연중 수시", "org_name": "고용노동부", "phone": "1350", "url": "https://www.ei.go.kr", "support_type": "현금(인건비)", "source_name": "curated"},

        # ── 창업 지원 ──
        {"service_id": "curated_030", "program_name": "예비창업패키지", "summary": "예비창업자에게 사업화 자금, 교육, 멘토링 지원", "field": "창업지원", "target": "예비창업자(사업자등록 전 또는 3년 이내)", "criteria": "사업계획서 평가, 발표평가", "support_content": "사업화 자금 최대 1억원, 창업교육, 전담멘토링", "apply_method": "K-Startup 홈페이지", "apply_deadline": "연 1~2회 공고", "org_name": "중소벤처기업부/창업진흥원", "phone": "1357", "url": "https://www.k-startup.go.kr", "support_type": "보조금+교육", "source_name": "curated"},
        {"service_id": "curated_031", "program_name": "초기창업패키지", "summary": "3년 이내 초기 창업기업에 사업화 자금 지원", "field": "창업지원", "target": "업력 3년 이내 창업기업", "criteria": "사업계획서 평가", "support_content": "사업화 자금 최대 1억원, 창업보육 입주", "apply_method": "K-Startup 홈페이지", "apply_deadline": "연 1~2회 공고", "org_name": "중소벤처기업부/창업진흥원", "phone": "1357", "url": "https://www.k-startup.go.kr", "support_type": "보조금", "source_name": "curated"},

        # ── 외식업 특화 ──
        {"service_id": "curated_040", "program_name": "외식업 경영주 아카데미", "summary": "외식업 경영주를 위한 전문 경영 교육", "field": "교육·컨설팅", "target": "외식업 경영주 및 예비 외식 창업자", "criteria": "외식업 종사자", "support_content": "메뉴개발, 원가관리, 마케팅, 위생관리, 배달앱 최적화 등 무료 교육", "apply_method": "온라인 신청", "apply_deadline": "연중 수시", "org_name": "식품의약품안전처", "phone": "1577-1255", "url": "", "support_type": "교육", "source_name": "curated"},
        {"service_id": "curated_041", "program_name": "소상공인 배달·택배비 지원사업", "summary": "배달·택배 이용 소상공인에게 비용 일부 지원", "field": "소상공인지원", "target": "연 매출 3억원 이하 소상공인", "criteria": "소상공인 확인, 배달 이용 실적", "support_content": "배달·택배비 연간 최대 30만원 지원", "apply_method": "소진공 홈페이지", "apply_deadline": "연중 수시", "org_name": "소상공인시장진흥공단", "phone": "1357", "url": "https://www.semas.or.kr", "support_type": "현금", "source_name": "curated"},
        {"service_id": "curated_042", "program_name": "소상공인 폐업지원(희망리턴패키지)", "summary": "폐업 예정·폐업 후 소상공인 재취업·재창업 지원", "field": "재기지원", "target": "폐업 예정이거나 폐업한 소상공인", "criteria": "폐업사실증명 또는 폐업 예정 확인서", "support_content": "폐업 정리 컨설팅, 점포 원상복구비 최대 250만원, 재취업 교육", "apply_method": "소진공 홈페이지", "apply_deadline": "연중 수시", "org_name": "소상공인시장진흥공단", "phone": "1357", "url": "https://www.semas.or.kr", "support_type": "현금+교육", "source_name": "curated"},
        {"service_id": "curated_043", "program_name": "서울시 공유주방 입주 지원", "summary": "예비 외식업 창업자를 위한 공유주방 입주 및 교육", "field": "창업지원", "target": "서울시 외식업 예비창업자", "criteria": "서울시 거주 또는 사업 예정", "support_content": "공유주방 3~6개월 입주, 메뉴개발 컨설팅, 배달앱 입점 지원", "apply_method": "서울시 자영업지원센터", "apply_deadline": "공고별 상이", "org_name": "서울시 자영업지원센터", "phone": "02-2133-5538", "url": "", "support_type": "현물+교육", "source_name": "curated"},
        {"service_id": "curated_044", "program_name": "HACCP 인증 지원사업", "summary": "중소 식품업체 HACCP 인증 취득 컨설팅 및 시설 지원", "field": "식품안전", "target": "HACCP 인증 희망 중소 식품업체", "criteria": "식품 제조·가공업 영위", "support_content": "HACCP 컨설팅 무료, 시설 개보수비 최대 1억원(융자), 인증 수수료 지원", "apply_method": "식약처 홈페이지", "apply_deadline": "연중 수시", "org_name": "식품의약품안전처", "phone": "1577-1255", "url": "", "support_type": "컨설팅+융자", "source_name": "curated"},
    ]

    logging.info(f"[curated] {len(programs)}건 로드")
    return programs


# ━━━ 통합 수집 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def collect_all_sources() -> dict:
    """모든 소스에서 데이터 수집 + 중복 제거"""
    all_data = []
    source_stats = {}

    collectors = [
        ("gov24", collect_gov24),
        ("kstartup", collect_kstartup),
        ("kised_space", collect_kised_space),
        ("kised_agency", collect_kised_agency),
        ("kised_edu", collect_kised_edu),
        ("sme24", collect_sme24),
        ("bizinfo", collect_bizinfo),
        ("curated", get_curated_data),
    ]

    for name, collector in collectors:
        try:
            data = collector()
            source_stats[name] = len(data)
            all_data.extend(data)
        except Exception as e:
            logging.error(f"[{name}] 수집 실패: {e}")
            source_stats[name] = 0

    # 중복 제거 (program_name 기준)
    seen = set()
    unique = []
    for item in all_data:
        key = item.get("program_name", "").strip().replace(" ", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(item)

    logging.info(f"[총합] {len(all_data)}건 수집 → {len(unique)}건 (중복 제거)")

    return {
        "data": unique,
        "total": len(unique),
        "source_stats": source_stats,
    }
