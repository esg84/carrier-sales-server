# Carrier Sales

## Carrier Sales: Server

This is FastAPI-based server to manage carrier sales data. It is deployed on Render.

## Overview

The server provides two main endpoints:
- Load data retrieval: Used by the agent to get available loads based on client specifications
- Post call data: Used by agent to add 'outcome' produced by the call to the database (i.e. final price, sentiment, load origin, etc...)

All endpoints require API key authentication via the `X-API-Key` header and are served over HTTPS.

## Components

- **API Layer**: FastAPI application with two main routers (loads and data posting)
- **Security**: API key validation using environment variables
- **Data**: Sample loads for challenge demo purposes

## Deployment

### API Key
1. Generate API key using the script:
```bash
python scripts/generate_api_key.py
```
2. Store the generated key:
   - Local: Add to docker run command: `-e API_KEY="YOUR_GENERATED_KEY"`
   - Production: Add to Render environment variables (key: API_KEY)


### Local Development
1. Install Docker
2. Build and run:
```docker build -t carrier-campaign-server .
docker run -p 8000:8000 \
  -e DATABASE_URL="your_db_url" \
  -e API_KEY="YOUR_GENERATED_KEY" \
  carrier-campaign-server

```
## Accessing Deployment: API Endpoints

### Get Loads
```http
GET https://carrier-sales-server.onrender.com/v1/loads/search
Header: X-API-Key: your_api_key
```

### Ingest Call Data
```http
POST https://carrier-sales-server.onrender.com/data/outcome
Header: X-API-Key: your_api_key
```

Request body:
```json
{

  "call_date": "Saturday, September 20, 2025 18:42:40 -0500",
  "base_price": "1400",
  "final_price": "1900",
  "load_origin": "Chicago, IL",
  "call_outcome": "neutral",
  "sentiment": "neutral",
  "mc_number": "323241",
  "carrier_name": "B & J TRUCKING & EXCAVATION"

}
```

> Note: The deployed instance on Render's free tier may take a few moments to spin up after periods of inactivity.

# Carrier Sales Dashboard

A dashboard for visualizing carrier campaign call data, featuring call outcomes, sentiment analysis, and negotiation metrics.


## Deployment

### Local Development

1. Install Docker
2. Build and run:
```docker build -f Dockerfile.dashboard -t carrier-campaign-dashboard .
docker run -p 8501:8501 \
  -e DATABASE_URL="your_db_url" \
  carrier-sales-dashboard
```

The dashboard will be available at http://localhost:8501/


## Access

The dashboard is hosted at: https://carrier-sales-server.onrender.com/dashboard
