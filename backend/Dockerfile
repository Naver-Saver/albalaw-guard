FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY data ./data
# 정기 수집(python -m sync.all)용 — 서버 cron이 컨테이너 안에서 실행한다 (docs/DEPLOY.md)
COPY sync ./sync
COPY samples/raw/wage ./samples/raw/wage
EXPOSE 8000
# Nginx(frontend 컨테이너) 뒤에서 동작하므로 X-Forwarded-* 헤더를 신뢰한다.
# 메모리 캐시·녹음 작업 상태 공유를 위해 워커 1개 (04-data-model)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
