# ADR-0002: Salesforce VC CRM Schema

**Status:** Accepted  
**Date:** 2025-11-17  

## Context

The vceamless demo project ingests public portfolio data for Salesforce Ventures from the web and stages it in a mini-lake (S3 + local) with enriched JSON for both companies and people:

- `companies_enriched.json`
- `people_enriched.json`

These enriched datasets include:

**Companies** (`companies_enriched.json`):
- Identifiers: `slug`, `name`, `detail_url`
- Status & tags: `status` (active/exited), `status_detail` (Private/Acquired/etc.), `fund_tags`, `theme_tags`
- Marketing & metadata: `description`, `website_url`, `social_links`, `logo_url`, `hero_image_url`
- Leadership: `leadership` array of `{name, role}` (partial, not universal)

**People** (`people_enriched.json`):
- Identifiers: `slug`, `name`, `detail_url`
- Titles: `title` (list), `detail_title` (detail page)
- Bio & location: `bio`, `location`
- Socials: `social_links` (Twitter/X, LinkedIn, email)
- Photos: `photo_url`, `detail_photo_url`
- Portfolio: `portfolio_companies` array of `{slug, name, tags}` for investor-type profiles

The goal of Phase 2 is to load this enriched data into a Salesforce Developer Edition org as a realistic VC CRM that can support:

- Manual exploration in Salesforce UI
- Downstream extraction into Postgres (Phase 3)
- Retool dashboards (Phase 4)
- Slack/Bedrock-based Q&A (Phase 5)

We *do not* have real deal timelines, funding amounts, or non-portfolio prospects, and we explicitly wish to avoid heavy scraping of proprietary data sources (e.g., Crunchbase, PitchBook) or inventing a large mocked deal pipeline at this stage.

## Decision

We will implement a **minimal but expressive VC CRM schema** in Salesforce based on:

- **Standard objects**:
  - `Account` for companies
  - `Contact` for people
- **A custom junction object**:
  - `PersonCompany__c` to model many-to-many relationships between people and companies
- **Custom fields** to capture enriched attributes
- **External IDs** for idempotent upserts from the JSON mini-lake

We intentionally **avoid** modeling detailed deal pipelines, funding amounts, or mock Opportunities for Phase 2, focusing instead on high-quality dimensions and relationships.

### 1. Companies → Account

**Object:** `Account`

**External ID:**

- `Company_Slug__c` (Text, External ID, Unique)  
  - Source: `companies_enriched.slug`  
  - Used for upsert: `sf.Account.upsert("Company_Slug__c/{slug}", payload)`

**Key fields:**

- `Name` (standard) ← `name` / `detail_name`
- `Company_Slug__c` ← `slug`
- `Website` (standard) ← `website_url`
- `Status__c` ← `status` (e.g., "active", "exited")
- `Status_Detail__c` ← `status_detail` (e.g., "Private", "Acquired")
- `Fund_Tags__c` ← `";".join(fund_tags)` (e.g., `"slack-fund"`)
- `Theme_Tags__c` ← `";".join(theme_tags)` (e.g., `"spotlight;security"`)
- `Short_Description__c` ← first sentence/short excerpt of `description`
- `Long_Description__c` ← full `description`
- `Source_URL__c` ← `detail_url`
- `Logo_URL__c` ← `logo_url`
- `Hero_Image_URL__c` ← `hero_image_url`
- `Twitter_URL__c` ← `social_links.twitter` (if present)
- `LinkedIn_URL__c` ← `social_links.linkedin` (if present)
- `Leadership_JSON__c` (Long Text) ← JSON string of the `leadership` array

**Rationale:**

- `Account` is the natural fit for companies in Salesforce.
- Using `Company_Slug__c` as an External ID makes the load idempotent and aligns cleanly with the source slug.
- Leadership is currently only partially modeled and is best preserved as JSON text for now, rather than forcing incomplete Contacts.

### 2. People → Contact

**Object:** `Contact`

**External ID:**

- `Person_Slug__c` (Text, External ID, Unique)  
  - Source: `people_enriched.slug`  
  - Used for upsert: `sf.Contact.upsert("Person_Slug__c/{slug}", payload)`

**Key fields:**

- `Person_Slug__c` ← `slug`
- `FirstName` / `LastName`:
  - Derived from `name` via simple split (last token = `LastName`, rest = `FirstName`)
- `Title` (standard) ← `detail_title` or fallback to `title`
- `Location__c` ← `location` (e.g., "Based in San Francisco, CA")
- `Bio__c` ← full `bio` text (Long Text)
- `Photo_URL__c` ← `photo_url` or `detail_photo_url`
- `Twitter__c` ← `social_links.twitter`
- `LinkedIn__c` ← `social_links.linkedin`
- `PublicEmail__c` ← parsed from `social_links.email` (strip `mailto:` and any `http://`)
- `Source_URL__c` ← `detail_url`

**Rationale:**

- `Contact` is the natural fit for individual people.
- Splitting names heuristically is acceptable for this demo.
- Social and bio fields are persisted explicitly to support UI viewing and analytics.

### 3. Relationships → PersonCompany__c

**Object:** `PersonCompany__c` (custom junction object)

**Fields:**

- `Person__c` (Lookup → `Contact`)
- `Company__c` (Lookup → `Account`)
- `RelationshipType__c` (Picklist)
  - Initial values:
    - `"Investor"` (from `portfolio_companies` arrays)
    - (future: `"Leadership"`, `"Board"`, etc. if desired)
- `PersonCompany_Key__c` (Text, External ID, Unique)
  - Composite key: `"{person_slug}::{company_slug}"`

**Source mapping:**

- From `people_enriched.portfolio_companies`:

  For each person `p` and each `pc` in `p["portfolio_companies"]`:

  - `person_slug = p["slug"]`
  - `company_slug = pc["slug"]`
  - `PersonCompany_Key__c = f"{person_slug}::{company_slug}"`
  - `RelationshipType__c = "Investor"`
  - (Optional) `Tags__c` (if created) ← `";".join(pc["tags"])`

- `Person__c` and `Company__c` lookups are resolved via:
  - `Person_Slug__c` on `Contact`
  - `Company_Slug__c` on `Account`

**Rationale:**

- Many-to-many relationships are central to VC workflows (partners ↔ portfolio companies).
- A dedicated junction object keeps the model clean and easy to extend.
- Using a composite External ID enables idempotent upserts for relationship records.

### 4. What we **are not** modeling (yet)

- Detailed Opportunity-level data:
  - Funding rounds, deal amounts, close dates, pipeline stages, co-investors, etc.
- Non-portfolio prospects / comparables.
- Full enrichment of leadership team as Contacts (due to missing detail pages).

These may be added later as either:

- A small, clearly-marked synthetic dataset (e.g., mock Opportunities), or
- Future integration with another data source.

For Phase 2, we explicitly focus on high-quality company/person dimensions and a realistic relationship model.

## Consequences

- **Simple ETL:** The mapping from JSON → Salesforce is straightforward:
  - `companies_enriched.json` → Accounts (via `Company_Slug__c`)
  - `people_enriched.json` → Contacts (via `Person_Slug__c`)
  - `people_enriched.portfolio_companies` → PersonCompany__c junction records
- **Idempotent loads:** External IDs on Accounts, Contacts, and PersonCompany__c allow safe upserts and re-runs.
- **Good analytics shape:** The eventual warehouse will have:
  - `dim_company` (from Account)
  - `dim_person` (from Contact)
  - `fct_person_company` (from PersonCompany__c)
- **Slack & Retool friendly:**
  - Easy to answer questions like:
    - "Which partners have the most active portfolio companies?"
    - "Which active security companies are associated with a given partner?"
- **Limited scope:** By not modeling full deal pipelines, we avoid:
  - Maintaining fake funding timelines
  - Overcomplicating the Salesforce schema
  - Tightly coupling this demo to external proprietary data sources

## Status and Next Steps

With this schema decision:

- Phase 2.3 (Companies ETL) will:
  - Implement transforms from `companies_enriched.json` to Account payloads.
  - Upsert using `Company_Slug__c` as External ID.
- Phase 2.4 (People & Relationships ETL) will:
  - Implement transforms from `people_enriched.json` to Contact payloads.
  - Upsert using `Person_Slug__c` as External ID.
  - Populate PersonCompany__c from `portfolio_companies`.

Field creation in Salesforce (custom fields and the PersonCompany__c object) will be done manually in the UI for this iteration, and documented in `salesforce/docs/schema_mapping.md` for future reference and potential automation.
