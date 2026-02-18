# 90-Second Demo Script

## 0-20s: Problem framing
"E-commerce teams need near-real-time visibility into price movement and threshold-based alerts."

## 20-60s: API + analytics flow
- Open `/docs`
- Call `/v1/latest` for current snapshot
- Call `/v1/alerts?pct_threshold=5`
- Show returned `count` and top alert records

## 60-80s: Reliability signals
- Show structured response envelope
- Show alert logic tests for spike/drop/noise (`tests/test_alert_logic.py`)

## 80-90s: Hiring close
"This project demonstrates practical analytics APIs, alerting logic, and testable data behavior for production workflows."
