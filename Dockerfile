FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git gcc && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y nodejs npm
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" python-multipart python-dotenv requests gitpython openai playwright mysql-connector-python
RUN playwright install chromium --with-deps
COPY dashboard/api/ .
RUN mkdir -p auth screenshots reports
ENV API_TEST_SUITE_PATH=/app/api-tests
EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
