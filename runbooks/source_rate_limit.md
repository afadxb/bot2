# Source rate-limit breach

1. Check Grafana for spikes in `ingest_errors_total` for the source.
2. Inspect worker logs for HTTP 429 responses.
3. Allow the backoff to recover or reduce poll frequency.
