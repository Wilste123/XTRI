FROM python:3.12-slim

WORKDIR /app

COPY coach-bot/pyproject.toml coach-bot/README.md ./
COPY coach-bot/src ./src
COPY LOFOTEN-2027 /app/LOFOTEN-2027

RUN pip install --no-cache-dir .

ENV PORT=8080
ENV REPO_ROOT=/app/LOFOTEN-2027
ENV STATE_PATH=/data/coach_state.json
ENV SLACK_MODE=socket
ENV TZ=Europe/Oslo

EXPOSE 8080

CMD ["python", "-m", "coach_bot.main"]
