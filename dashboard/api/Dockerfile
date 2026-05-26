FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git gcc && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y nodejs npm
<<<<<<< HEAD
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" python-multipart python-dotenv requests gitpython openai anthropic playwright mysql-connector-python bcrypt PyJWT google-generativeai
RUN playwright install chromium --with-deps
COPY . .
=======
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" python-multipart python-dotenv requests gitpython openai playwright mysql-connector-python bcrypt PyJWT
RUN playwright install chromium --with-deps
COPY dashboard/api/ .
>>>>>>> 0764c65d1ac09d5a7e653b3324863c23e1c43dae
RUN mkdir -p auth screenshots reports
ENV API_TEST_SUITE_PATH=/app/api-tests
EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
