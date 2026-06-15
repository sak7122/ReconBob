# Single image serves either HTTP function (webhook or recon_job) via functions-framework.
# The Cloud Run service picks the entry point with FUNCTION_TARGET / FUNCTION_SOURCE env vars.
FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    FUNCTION_TARGET=webhook \
    FUNCTION_SOURCE=src/main.py \
    PORT=8080

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

# Shell form so env vars expand at runtime; exec so signals reach the server.
CMD ["sh", "-c", "exec functions-framework --target=$FUNCTION_TARGET --source=$FUNCTION_SOURCE --host=0.0.0.0 --port=$PORT"]
