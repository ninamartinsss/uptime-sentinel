# Uptime Sentinel

**A lightweight HTTP availability monitor built with Python and SQLite.**

Uptime Sentinel checks multiple API endpoints concurrently, records response times and status codes in a local SQLite database, calculates historical availability and can notify an n8n webhook when an endpoint fails.

## Features

- Concurrent HTTP endpoint checks using Python's standard library
- Configurable expected status codes and timeouts
- Historical SQLite data with uptime and average latency reports
- Optional n8n webhook for failures (`SENTINEL_WEBHOOK_URL`)
- Continuous monitoring (`--interval`) or one-shot execution
- Automated unit tests, Docker support and GitHub Actions CI
- No required third-party Python runtime packages

## Quick start

Requires Python **3.10+**.

```bash
python -m pip install -e .
cp targets.example.json targets.json
sentinel --config targets.json
sentinel --db sentinel.sqlite3 --report
```

On Windows PowerShell, use `Copy-Item targets.example.json targets.json` instead of `cp` if necessary.

The tool exits with code `1` if any endpoint is down in one-shot mode (useful for CI), and `0` otherwise.

## Continuous monitoring

```bash
sentinel --config targets.json --interval 60
```

The CLI stores samples in `sentinel.sqlite3`. The database file is ignored by Git.

## n8n integration

1. In n8n, create a **Webhook** trigger with the `POST` method.
2. Activate the workflow and copy the **production** webhook URL.
3. Set `SENTINEL_WEBHOOK_URL` in the environment where Sentinel runs.
4. Add downstream n8n nodes (e.g. email, database, Slack).

On a local Docker setup, `localhost` inside a container is not the host machine; use a network-reachable n8n address. Webhook security (authentication, HTTPS and network restrictions) is your responsibility. For public endpoints, use HTTPS and protect tokens as secrets.

## Docker

```bash
docker build -t uptime-sentinel .
docker run --rm -v "$(pwd)/targets.example.json:/app/targets.json:ro" -v "$(pwd)/data:/app/data" uptime-sentinel --config /app/targets.json --db /app/data/history.sqlite3
```

Use an absolute host path or a Docker named volume on Windows when mounting files. The default image runs one check and exits.

## Tests

```bash
python -m unittest discover -s tests -v
```

## Project layout

```text
src/sentinel/       Monitoring and CLI implementation
tests/              Unit tests
targets.example.json Example configuration
Dockerfile          Python container
.github/workflows/  GitHub Actions CI
```

## Roadmap

- [ ] Alert deduplication and recovery notifications
- [ ] CSV export and dashboard visualization
- [ ] Prometheus metrics and configurable retries
- [ ] PostgreSQL adapter for larger deployments

## Security note

Monitor only endpoints you own or are authorized to test. Configured target URLs are trusted operator input: do not accept arbitrary untrusted user-supplied URLs because they can reach internal services. Use low-frequency intervals and reasonable timeouts.

## License

MIT
