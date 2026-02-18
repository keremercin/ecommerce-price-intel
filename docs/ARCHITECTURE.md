# Architecture

```mermaid
flowchart TD
    A[Collectors / Scrapers] --> B[Normalize + ETL]
    B --> C[(Storage)]
    C --> D[FastAPI Endpoints]
    C --> E[Trend & Delta Logic]
    D --> F[Streamlit Dashboard]
    E --> F
```

## Planned modules
- `collectors/` product source connectors
- `pipeline/` data normalization + enrich
- `api/` serving for dashboard and downstream integrations
- `dashboard.py` quick UI for price trends
