FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends git gcc nodejs npm && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir fastapi "uvicorn[standard]" python-multipart python-dotenv requests gitpython openai anthropic playwright mysql-connector-python bcrypt PyJWT
RUN pip install --no-cache-dir groq
RUN playwright install chromium --with-deps
COPY . .
RUN mkdir -p auth screenshots reports
EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
