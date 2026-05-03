# OverDose Server - Django Processing Pipeline

A Django + Django REST Framework backend that powers a multi-step processing pipeline for scans, risk assessment, and recommendations.

## Overview

This project was developed as part of coursework at Esprit School of Engineering. It provides a structured API for managing users and products, running scans, assessing risks, and returning recommendations through a clear pipeline.

## Features

- User management with custom user and allergy mapping
- Product catalog with categories and extraction methods
- Scan API that orchestrates the pipeline and stores scan data
- Risk assessment API with persisted results
- Recommendation API tied to scans and risks
- Simple dashboard view and summary endpoint

## Tech Stack

- Python 3.13
- Django 6
- Django REST Framework
- SQLite

## GitHub Repository Metadata (Suggested)

**Description:**
Backend Django API for scan, risk, and recommendation pipeline built for a university project.

**Topics:**
python, django, django-rest-framework, api, backend, sqlite, web-development

## Directory Structure

```text
App_Django/
  config/                  # Project config (settings, urls)
  users/                   # Custom user model + allergies
  products/                # Product catalog model
  scan/                    # Scan model + scan API endpoint
  risk/                    # Risk API endpoint + persisted risk results
  recommendation/          # Recommendation API endpoint + persisted recommendations
  dashboard/               # Simple UI + dashboard API summary
  templates/dashboard/     # Dashboard HTML template
  requirements.txt
  manage.py
```

## Apps and Responsibilities

### users

- `User` custom model (`AUTH_USER_MODEL`)
- `Allergy` list model
- `UserAllergy` mapping table (many-to-many through model)
- API endpoints to list/create users, allergies, and user-allergy mappings

### products

- `Product` model with category (`food`, `cosmetic`)
- Extraction method (`lens`, `barcode`)
- Ingredients as JSON
- API endpoint to list/create products

### scan

- `Scan` model with optional user and image
- `POST /api/scan/` endpoint:
  - creates scan
  - builds ingredient list
  - triggers risk assessment
  - triggers recommendation generation
  - returns a combined response

### risk

- `POST /api/risk/` endpoint
- Input: `scan_id`, `ingredients`
- Output: risk list with levels (`low`, `medium`, `high`)
- Persisted models: `RiskAssessment`, `RiskItem`

### recommendation

- `POST /api/recommend/` endpoint
- Input: `scan_id`, `risks`
- Output: recommendations (`product`, `reason`)
- Persisted models: `RecommendationBatch`, `RecommendationItem`

### dashboard

- Browser dashboard at `/`
- Summary API at `/api/dashboard/summary/`

## Database Schema (High-Level)

- `users.User` 1--* `scan.Scan`
- `users.User` *--* `users.Allergy` through `users.UserAllergy`
- `scan.Scan` 1--1 `risk.RiskAssessment`
- `risk.RiskAssessment` 1--* `risk.RiskItem`
- `scan.Scan` 1--1 `recommendation.RecommendationBatch`
- `recommendation.RecommendationBatch` 1--* `recommendation.RecommendationItem`

## Getting Started

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
      "reason": "Recommendation based on the assessed risk level."
    }
  ]
}
```

## Acknowledgments

Completed under academic guidance for coursework at Esprit School of Engineering.
