# VWorld WFS 응답 샘플 확인용 - 직접 실행해보세요
# python check_wfs.py

import httpx, json

KEY = "BE3AF33A-202E-3D5F-A8AD-63D9EE291ABF"
# 종로구만 (11110) - 소량 샘플
url = (
    f"https://api.vworld.kr/req/wfs"
    f"?SERVICE=WFS&VERSION=2.0.0&REQUEST=GetFeature"
    f"&TYPENAME=lt_c_ademd_info"
    f"&SRSNAME=EPSG:4326"
    f"&CQL_FILTER=sig_cd+LIKE+%2711110%25%27"
    f"&outputFormat=application%2Fjson"
    f"&KEY={KEY}&DOMAIN=localhost"
)
r = httpx.get(url, timeout=30)
data = r.json()
feats = data.get("features", [])
print(f"피처 수: {len(feats)}")
if feats:
    print("\n=== 첫 5개 properties ===")
    for f in feats[:5]:
        p = f["properties"]
        print(json.dumps(p, ensure_ascii=False, indent=2))