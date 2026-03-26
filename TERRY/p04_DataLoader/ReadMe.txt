p04_DataLoader/
│
├── load_store_csv.py              ← 소상공인 상권정보 → STORE_SEOUL
├── load_sangkwon_sales_csv.py     ← 상권 매출 → SANGKWON_SALES
├── load_sangkwon_store_csv.py     ← 점포수 → SANGKWON_STORE
├── insert_law_adm.py              ← 법정동↔행정동 매핑
├── filter_seoul_adm_dong.py       ← GeoJSON 추출
│
├── csv/
│   ├── mapping/                   ← 소형 (GitHub 포함)
│   │   ├── law_adm_map_new.csv
│   │   └── svc_induty_map.csv
│   │
│   ├── sangkwon_sales/            ← 상권 매출 (gitignore)
│   │   ├── sangkwon_2019_utf8/
│   │   ├── sangkwon_2020_utf8/
│   │   ├── sangkwon_2021_utf8/
│   │   ├── sangkwon_2022_utf8/
│   │   ├── sangkwon_2023_utf8/
│   │   ├── sangkwon_2024_utf8/
│   │   └── sangkwon_2025_utf8/
│   │
│   ├── sangkwon_store/            ← 점포수 (gitignore)
│   │   └── SANGKWON_STORE_*.csv
│   │
│   └── location_csv/                  ← 소상공인 상권정보 (gitignore)
│       ├── 소상공인_서울_202512.csv
│       ├── 소상공인_경기_202512.csv
│       ├── 소상공인_강원_202512.csv
│       └── ...
│
└── geojson/                       ← gitignore
    └── HangJeongDong_ver20260201.geojson_*.geojson