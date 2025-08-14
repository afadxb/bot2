CREATE TABLE IF NOT EXISTS sentiment_raw (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  ts TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  market ENUM('crypto','stocks') NOT NULL DEFAULT 'crypto',
  symbol VARCHAR(16) NOT NULL,
  source ENUM('news','stocktwits','reddit','fg') NOT NULL,
  text TEXT NOT NULL,
  raw_score DOUBLE,
  quality DOUBLE DEFAULT 1.0,
  meta JSON,
  KEY (market, symbol, ts),
  KEY (source, ts)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS sentiment_agg (
  ts TIMESTAMP NOT NULL,
  market ENUM('crypto','stocks') NOT NULL DEFAULT 'crypto',
  symbol VARCHAR(16) NOT NULL,
  news_score DOUBLE,
  social_score DOUBLE,
  mood_score DOUBLE,
  regime_adj DOUBLE,
  details JSON,
  PRIMARY KEY (market, symbol, ts),
  KEY (ts)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS news_hashes (
  hash CHAR(64) PRIMARY KEY,
  ts TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY (ts)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
