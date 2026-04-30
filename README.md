# Django Processing Pipeline (Mock)

A clean and minimal Django + Django REST Framework project that models a multi-step processing pipeline:

- scan
- risk
- recommendation
- users
- products
- dashboard

This project intentionally uses mock responses and placeholder flow logic to keep the architecture clear and extensible.

## Tech Stack

- Python 3.13
- Django 6
- Django REST Framework
- SQLite

## Project Structure

```text
App_Django/
  config/                  # Project config (settings, urls)
  users/                   # Custom user model + allergies
  products/                # Product catalog model
  scan/                    # Scan model + scan API endpoint
  risk/                    # Risk API endpoint + persisted mock risk results
  recommendation/          # Recommendation API endpoint + persisted mock recommendations
  dashboard/               # Simple UI + dashboard API summary
  templates/dashboard/     # Dashboard HTML template
  requirements.txt
  .gitignore
  manage.py
```

## Apps and Responsibilities

### users

- `User` custom model (`AUTH_USER_MODEL`)
- `Allergy` list model
- `UserAllergy` mapping table (many-to-many through model)
- API endpoints to list/create users, allergies, and user-allergy mappings

### products

- `Product` model with:
- category (`food`, `cosmetic`)
- extraction method (`lens`, `barcode`)
- ingredients as JSON
- API endpoint to list/create products

### scan

- `Scan` model with optional user and image
- `POST /api/scan/` endpoint:
- creates scan
- generates mock ingredients
- calls internal risk builder
- calls internal recommendation builder
- returns combined response

### risk

- `POST /api/risk/` endpoint
- Input: `scan_id`, `ingredients`
- Output: mock risk list with levels (`low`, `medium`, `high`)
- Persisted placeholders:
- `RiskAssessment`
- `RiskItem`

### recommendation

- `POST /api/recommend/` endpoint
- Input: `scan_id`, `risks`
- Output: mock recommendations (`product`, `reason`)
- Persisted placeholders:
- `RecommendationBatch`
- `RecommendationItem`

### dashboard

- Browser dashboard at `/`
- Shows users, scans, and mock JSON output
- Summary API at `/api/dashboard/summary/`

## Database Schema (High-Level)

- `users.User` 1--* `scan.Scan`
- `users.User` *--* `users.Allergy` through `users.UserAllergy`
- `scan.Scan` 1--1 `risk.RiskAssessment`
- `risk.RiskAssessment` 1--* `risk.RiskItem`
- `scan.Scan` 1--1 `recommendation.RecommendationBatch`
- `recommendation.RecommendationBatch` 1--* `recommendation.RecommendationItem`

This keeps relationships normalized while making future logic expansion straightforward.

## Setup and Run

1. Install dependencies:

```bash
python -m pip install -r requirements.txt
```

1. Create and apply migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

1. Optional: create admin user:

```bash
python manage.py createsuperuser
```

1. Start server:

```bash
python manage.py runserver
```

1. Open:

- Dashboard: `http://127.0.0.1:8000/`
- Admin: `http://127.0.0.1:8000/admin/`

## API Endpoints

- `GET/POST /api/users/`
- `GET/POST /api/users/allergies/`
- `GET/POST /api/users/user-allergies/`
- `GET/POST /api/products/`
- `POST /api/scan/`
- `POST /api/risk/`
- `POST /api/recommend/`
- `GET /api/dashboard/summary/`

## Postman Collection

- Collection file: `postman_collection.json`
- Includes all API endpoints with ready-to-run sample payloads

Import steps:

1. Open Postman and click Import.
1. Select `postman_collection.json`.
1. Ensure `baseUrl` is set to `http://127.0.0.1:8000`.
1. Run requests in this order for quick demo: create user -> create allergy -> create user allergy -> scan pipeline.

### Example: `POST /api/scan/`

Request body (optional fields):

```json
{
  "user": 1
}
```

Response:

```json
{
  "scan_id": 1,
  "ingredients": ["ingredient_1", "ingredient_2", "ingredient_3"],
  "risks": [
    {"ingredient": "ingredient_1", "level": "low"},
    {"ingredient": "ingredient_2", "level": "medium"},
    {"ingredient": "ingredient_3", "level": "high"}
  ],
  "recommendations": [
    {
      "product": "Alternative for ingredient_1",
      "reason": "Mock recommendation generated for low risk ingredient."
    }
  ]
}
```

## Extending Later

- Replace mock generators with domain services in `risk` and `recommendation`
- Add async task queue (Celery/RQ) for heavy pipeline processing
- Introduce versioned API (`/api/v1/`)
- Add authentication and permissions for user-specific scan access
- Add pagination/filtering/search in list endpoints
- Move mock orchestration from views to service layer for richer use cases
