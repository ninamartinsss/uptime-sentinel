FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY targets.example.json ./targets.json
RUN mkdir /app/data
ENTRYPOINT ["sentinel"]
CMD ["--config", "/app/targets.json", "--db", "/app/data/history.sqlite3"]
