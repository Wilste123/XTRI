FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

ENV PORT=3000
EXPOSE 3000

CMD ["python", "-m", "coach_bot.main"]
