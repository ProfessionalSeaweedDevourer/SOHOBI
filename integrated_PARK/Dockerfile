# ── 빌드 스테이지 ─────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# 시스템 의존성 (pdfkit → wkhtmltopdf, matplotlib → 폰트 없이 Agg 백엔드)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── 런타임 스테이지 ───────────────────────────────────────────
FROM python:3.12-slim

WORKDIR /app

# wkhtmltopdf (pdfkit 런타임 의존성)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wkhtmltopdf \
    && rm -rf /var/lib/apt/lists/*

# 설치된 패키지 복사
COPY --from=builder /install /usr/local

# 애플리케이션 소스 복사 (.dockerignore로 불필요 파일 제외)
COPY . .

# matplotlib: 디스플레이 없는 환경에서 Agg 백엔드 사용
ENV MPLBACKEND=Agg

# 컨테이너 내부 포트 (Container Apps가 8000을 기본 수신)
EXPOSE 8000

# uvicorn: worker 수는 환경변수로 조정 가능 (기본 1)
CMD ["sh", "-c", "uvicorn api_server:app --host 0.0.0.0 --port 8000 --workers ${UVICORN_WORKERS:-1}"]
