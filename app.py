from pydantic import BaseModel
from fastapi import FastAPI, Query, Body, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict
from datetime import datetime
import os

app = FastAPI(title="Loads API", version="1.0.0")

# allow for calls from browser or other servers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

LOADS = [
  {"load_id":"L-1001","origin":"Chicago, IL","destination":"Dallas, TX",
   "pickup_datetime":"2025-09-23 08:00:00","delivery_datetime":"2025-09-24 18:00:00",
   "equipment_type":"Dry Van","loadboard_rate":1800,"notes":"No pallet exchange",
   "weight":42000,"commodity_type":"Consumer electronics","num_of_pieces":22,"miles":920,"dimensions":"48x40x60"},
  {"load_id":"L-1002","origin":"Reno, NV","destination":"Los Angeles, CA",
   "pickup_datetime":"2025-09-23 10:00:00","delivery_datetime":"2025-09-23 20:00:00",
   "equipment_type":"Reefer","loadboard_rate":1400,"notes":"Temp at 36°F",
   "weight":38000,"commodity_type":"Fresh produce","num_of_pieces":18,"miles":480,"dimensions":"48x40x55"},
  {"load_id":"L-1003","origin":"Atlanta, GA","destination":"Miami, FL",
   "pickup_datetime":"2025-09-24 07:00:00","delivery_datetime":"2025-09-24 19:00:00",
   "equipment_type":"Flatbed","loadboard_rate":2000,"notes":"Tarp required",
   "weight":46000,"commodity_type":"Steel coils","num_of_pieces":10,"miles":660,"dimensions":"60x48x50"},
  {"load_id":"L-1004","origin":"Denver, CO","destination":"Kansas City, MO",
   "pickup_datetime":"2025-09-25 09:00:00","delivery_datetime":"2025-09-25 21:00:00",
   "equipment_type":"Dry Van","loadboard_rate":1300,"notes":"Drop & hook",
   "weight":35000,"commodity_type":"Packaged food","num_of_pieces":25,"miles":600,"dimensions":"40x48x55"},
  {"load_id":"L-1005","origin":"Seattle, WA","destination":"Portland, OR",
   "pickup_datetime":"2025-09-22 06:00:00","delivery_datetime":"2025-09-22 14:00:00",
   "equipment_type":"Reefer","loadboard_rate":900,"notes":"Expedited delivery",
   "weight":20000,"commodity_type":"Frozen seafood","num_of_pieces":12,"miles":180,"dimensions":"48x40x40"},
]

@app.get("/v1/loads/search")
def search_loads(
    origin: Optional[str] = Query(None),
    destination: Optional[str] = Query(None),
    equipment_type: Optional[str] = Query(None),
    min_rate: Optional[int] = Query(None),
):
    rows = LOADS
    if origin:
        rows = [r for r in rows if origin.lower() in r["origin"].lower()]
    if destination:
        rows = [r for r in rows if destination.lower() in r["destination"].lower()]
    if equipment_type:
        rows = [r for r in rows if r["equipment_type"].lower() == equipment_type.lower()]
    if min_rate is not None:
        rows = [r for r in rows if r["loadboard_rate"] >= min_rate]
    return {"data": rows}


##POST step
# in-memory "DB"
EVENTS: List[Dict] = []

# optional simple auth
DASH_TOKEN = os.getenv("DASH_TOKEN", "change-me")

class CallEvent(BaseModel):
    call_date: Optional[str] = None
    base_price: Optional[str] = None
    final_price: Optional[str] = None
    load_origin: Optional[str] = None
    load_destination: Optional[str] = None
    call_outcome: Optional[str] = None
    call_duration: Optional[str] = None
    is_negotiated: Optional[str] = None
    carrier_sentiment: Optional[str] = None
    mc_number: Optional[str] = None
    carrier_name: Optional[str] = None

@app.post("/data/outcome")
def outcome_event(
    payload: CallEvent = Body(...),
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None)
):
    # accept either "Authorization: Bearer <token>" or "X-API-Key: <token>"
    token = (authorization or "").replace("Bearer ", "") or (x_api_key or "")
    if DASH_TOKEN and token != DASH_TOKEN:
        raise HTTPException(status_code=401, detail="invalid token")

    event = payload.model_dump()
    event.setdefault("server_received_at", datetime.utcnow().isoformat() + "Z")
    EVENTS.append(event)
    return {"ok": True, "stored": len(EVENTS)}

@app.get("/data/events")
def list_events():
    return {"data": EVENTS}
