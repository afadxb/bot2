# Database retention

- **Raw snippets (`sentiment_raw`)**: keep 30–90 days.
- **Aggregates (`sentiment_agg`)**: keep 1–3 years.

Use a cron job or MySQL `EVENT` to purge expired rows.
