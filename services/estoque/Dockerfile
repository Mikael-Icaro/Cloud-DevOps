FROM docker.io/library/python:3.12-slim AS base

FROM base AS deps
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM base
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app
COPY --from=deps /root/.local /home/appuser/.local
COPY main.py .
RUN chown -R appuser:appuser /app
USER appuser
ENV PATH=/home/appuser/.local/bin:$PATH
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
