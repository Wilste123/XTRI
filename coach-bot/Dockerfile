# Build from repo root: docker build -f coach-bot/Dockerfile -t lofoten-coach .
FROM python:3.12-slim

WORKDIR /app/coach-bot

COPY coach-bot/pyproject.toml coach-bot/README.md ./
COPY coach-bot/src ./src
COPY LOFOTEN-2027 /app/LOFOTEN-2027

RUN pip install --no-cache-dir .

ENV REPO_ROOT=/app
ENV PORT=3000
EXPOSE 3000

CMD ["python", "-m", "coach_bot.main"]
