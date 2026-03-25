# =====================================================
# vuski/admdongkor GeoJSON → 서울 행정동 GeoJSON 변환
# 실행: python filter_seoul_adm_dong.py
#
# 준비:
#   1. https://github.com/vuski/admdongkor 에서
#      최신 HangJeongDong_ver20XXXXXX.geojson 다운로드
#   2. 이 스크립트와 같은 폴더에 위치
#
# 입력: HangJeongDong_ver20XXXXXX.geojson (자동 탐색)
# 출력: seoul_adm_dong.geojson
# =====================================================

import os
import json
import glob

# ── 상대경로 기준 설정 (파일 위치 기준) ──────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ── 입력 파일 자동 탐색 ──────────────────────────────────────
pattern = os.path.join(BASE_DIR, "HangJeongDong_*.geojson")
matches = glob.glob(pattern)
if not matches:
    raise FileNotFoundError(
        f"HangJeongDong_*.geojson 파일을 찾을 수 없습니다.\n"
        f"경로: {BASE_DIR}\n"
        f"https://github.com/vuski/admdongkor 에서 최신 파일을 다운로드해주세요."
    )
INPUT_PATH  = sorted(matches)[-1]  # 여러 개면 최신
OUTPUT_PATH = os.path.join(BASE_DIR, "seoul_adm_dong.geojson")

print(f"[1] 입력: {os.path.basename(INPUT_PATH)}")

with open(INPUT_PATH, encoding="utf-8") as f:
    gj = json.load(f)

features = gj.get("features", [])
print(f"    전체 {len(features)}개 feature")
if features:
    print(f"    속성 컬럼: {list(features[0]['properties'].keys())}")
    print(f"    샘플: {features[0]['properties']}")

# ── 서울 필터 (adm_cd2 앞 2자리 = 11) ────────────────────────
print(f"\n[2] 서울 필터")
seoul = []
for feat in features:
    p = feat.get("properties", {})
    cd2 = str(p.get("adm_cd2") or p.get("adm_cd") or "")
    if cd2.startswith("11"):
        seoul.append({
            "type": "Feature",
            "properties": {
                "adm_cd": cd2,                                        # 행정안전부 10자리
                "adm_nm": p.get("adm_nm", ""),                       # 행정동명
                "gu_nm":  p.get("sigungu_nm", p.get("sig_nm", "")),  # 구이름
            },
            "geometry": feat["geometry"],
        })

print(f"    서울 행정동 {len(seoul)}개")

# ── GeoJSON 저장 ──────────────────────────────────────────────
print(f"\n[3] 저장: {OUTPUT_PATH}")
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump({"type":"FeatureCollection","features":seoul},
              f, ensure_ascii=False, separators=(",", ":"))

size_kb = os.path.getsize(OUTPUT_PATH) / 1024
print(f"    완료: {len(seoul)}개 / {size_kb:.1f} KB")

# ── 검증 ──────────────────────────────────────────────────────
print(f"\n[4] 검증 (샘플 3개)")
for feat in seoul[:3]:
    p = feat["properties"]
    print(f"    {p['adm_cd']} {p['gu_nm']} {p['adm_nm']}")

print(f"\n✅ 완료: seoul_adm_dong.geojson")
