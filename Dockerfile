FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git gcc && rm -rf /var/lib/apt/lists/*
COPY dashboard/api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && playwright install chromium --with-deps
COPY dashboard/api/ .
RUN mkdir -p auth screenshots reports
EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
# force rebuild Mon Apr 27 12:52:07 PKT 2026
