# Carrier Sales

## Carrier Sales: Server

This is a FastAPI-based server to manage carrier sales data. It is deployed on Render.

## Overview

The server provides three main components:

- **Loads API**: Retrieve available loads based on client specifications  
- **Call Data API**: Post call outcomes to the database (final price, sentiment, load origin, etc.)  
- **Dashboard**: A lightweight web UI for viewing call and load information, served at `/dashboard`

All endpoints require authentication via an API key. The key can be passed either in the `x-api-key` header (preferred for API calls) or as a query/path token for browser access to `/dashboard`.

---

## Components

- **API Layer**: FastAPI application (`app.py`) with routes for loads, outcome ingestion, and dashboard rendering  
- **Security**: API key validation using environment variables  
- **Database**: Loads and call outcome data (connected via `DATABASE_URL`)  

---

## Deployment

### API Key

1. Generate an API key:
   ```bash
   python scripts/generate_api_key.py
   ```
2. Store the key as an environment variable:
   - **Local**:  
     ```bash
     export API_KEY="YOUR_GENERATED_KEY"
     ```
   - **Docker run**:  
     ```bash
     docker run -p 8000:8000        -e DATABASE_URL="your_db_url"        -e API_KEY="YOUR_GENERATED_KEY"        carrier-campaign-server
     ```
   - **Production (Render)**: Add environment variable  
     ```
     KEY: API_KEY
     VALUE: YOUR_GENERATED_KEY
     ```

(Optional) You can also set a shorter `DASH_TOKEN` for browser access:
```
KEY: DASH_TOKEN
VALUE: short_random_token
```

---

### Local Development

1. Install Docker  
2. Build and run the service:  
   ```bash
   docker build -t carrier-campaign-server .
   docker run -p 8000:8000      -e DATABASE_URL="your_db_url"      -e API_KEY="YOUR_GENERATED_KEY"      carrier-campaign-server
   ```
3. The API will be available at http://localhost:8000  
4. The dashboard will be available at http://localhost:8000/dashboard  

---

## Accessing Deployment

### API Endpoints

#### Get Loads
```http
GET https://carrier-sales-server.onrender.com/v1/loads/search
Header: x-api-key: YOUR_API_KEY
```

#### Ingest Call Data
```http
POST https://carrier-sales-server.onrender.com/data/outcome
Header: x-api-key: YOUR_API_KEY
```

Request body example:
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

---

### Dashboard Access

The dashboard is hosted as part of the same FastAPI service:  
```
https://carrier-sales-server.onrender.com/dashboard
```

Authentication options:
- API header:  
  `x-api-key: YOUR_API_KEY`
- Query param:  
  `https://carrier-sales-server.onrender.com/dashboard?key=YOUR_API_KEY`  
  or (if you set `DASH_TOKEN`)  
  `https://carrier-sales-server.onrender.com/dashboard?key=YOUR_DASH_TOKEN`
- Path token:  
  `https://carrier-sales-server.onrender.com/dashboard/YOUR_DASH_TOKEN`

---

> **Note**: On Render’s free tier, the instance may take a few moments to spin up after inactivity.
