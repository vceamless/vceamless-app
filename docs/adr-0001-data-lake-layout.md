# ADR-0001: Local vs S3 "Mini Lake" Layout

**Status:** Accepted  
**Date:** 2025-11-17

## Context

The vceamless demo project ingests Salesforce Ventures portfolio and people data via web scraping, stages it locally for exploratory work, and mirrors a subset to S3 as the "source of truth" for downstream pipelines (Salesforce load, dbt, analytics, Slackbot).

We want:
- A simple local directory structure for ad hoc exploration.
- A consistent S3 prefix layout that mirrors the logical layers (raw_landing, bronze).
- Minimal nesting to avoid path bloat and refactor pain.
- Clear mapping between local and S3 so code can be refactored safely.

## Decision

1. **Local layout (repo):**

   ```text
   data_staging/
     raw_landing/
       companies_list_page.html
       people_list_page.html
       company_pages/
         <slug>.html
       person_pages/
         <slug>.html

     bronze/
       companies_list.json
       people_list.json
       companies_enriched.json      (Phase 1C)
       people_enriched.json         (optional later)

2. **Base path substitutions (aws):**

    ```
    RAW_LOCAL_BASE = Path("data_staging/raw_landing")
    RAW_S3_BASE = "sf_ventures/raw_landing"

    BRONZE_LOCAL_BASE = Path("data_staging/bronze")
    BRONZE_S3_BASE = "sf_ventures/bronze"
    ```