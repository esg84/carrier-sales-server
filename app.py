from pydantic import BaseModel
from fastapi import FastAPI, Query, Body, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict
from datetime import datetime
import os

#For Dashboard
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import Integer, String, Boolean, DateTime

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
DATABASE_URL = os.getenv("DATABASE_URL")  # set this in Render
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL env var not set (Render Postgres).")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

class EventRow(Base):
    __tablename__ = "call_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    server_received_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    call_date: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    base_price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    final_price: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    load_origin: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    load_destination: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    call_outcome: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    call_duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_negotiated: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    carrier_sentiment: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    mc_number: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    carrier_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

# create table if it doesn't exist
with engine.begin() as conn:
    Base.metadata.create_all(conn)

# optional simple auth
DASH_TOKEN = os.getenv("DASH_TOKEN", "eleni-happy-robot")

class CallEvent(BaseModel):
    call_date: Optional[str] = None
    base_price: Optional[int] = None
    final_price: Optional[int] = None
    load_origin: Optional[str] = None
    call_outcome: Optional[str] = None
    sentiment: Optional[str] = None
    mc_number: Optional[int] = None
    carrier_name: Optional[str] = None

def _as_int(v):
    try: return int(v)
    except (TypeError, ValueError): return None

def _as_bool(v):
    if isinstance(v, bool): return v
    if isinstance(v, str): return v.strip().lower() in ("true","1","yes","y")
    return None

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

    row = EventRow(
        call_date = payload.call_date,
        base_price = _as_int(payload.base_price),
        final_price = _as_int(payload.final_price),
        load_origin = payload.load_origin,
        load_destination = payload.load_destination,
        call_outcome = payload.call_outcome,
        call_duration = _as_int(payload.call_duration),
        is_negotiated = _as_bool(payload.is_negotiated),
        carrier_sentiment = payload.carrier_sentiment,
        mc_number = payload.mc_number,
        carrier_name = payload.carrier_name,
        server_received_at = datetime.utcnow()
    )
    with SessionLocal() as s:
        s.add(row)
        s.commit()
        s.refresh(row)
        stored = s.query(EventRow).count()
    return {"ok": True, "id": row.id, "stored": stored}

    @app.get("/data/events")
def list_events(limit: int = 100, offset: int = 0):
    with SessionLocal() as s:
        q = s.query(EventRow).order_by(EventRow.id.desc()).offset(offset).limit(limit)
        rows = q.all()
        def to_dict(r: EventRow):
            return {
                "id": r.id,
                "server_received_at": r.server_received_at.isoformat() + "Z",
                "call_date": r.call_date,
                "base_price": r.base_price,
                "final_price": r.final_price,
                "load_origin": r.load_origin,
                "load_destination": r.load_destination,
                "call_outcome": r.call_outcome,
                "call_duration": r.call_duration,
                "is_negotiated": r.is_negotiated,
                "carrier_sentiment": r.carrier_sentiment,
                "mc_number": r.mc_number,
                "carrier_name": r.carrier_name,
            }
        return {"data": [to_dict(r) for r in rows]}

    
@app.get("/dashboard/metrics")
def dashboard_metrics():
    with SessionLocal() as s:
        total = s.query(EventRow).count()

        # outcomes
        outcomes = dict((k, v) for k, v in s.execute(
            text("SELECT call_outcome, COUNT(*) FROM call_events GROUP BY call_outcome")
        ))

        # sentiments
        sentiments = dict((k, v) for k, v in s.execute(
            text("SELECT carrier_sentiment, COUNT(*) FROM call_events GROUP BY carrier_sentiment")
        ))

        # negotiation rate
        neg_count = s.execute(text("SELECT COUNT(*) FROM call_events WHERE is_negotiated = TRUE")).scalar() or 0
        negotiation_rate = (neg_count / total) if total else 0

        # averages (ignore NULLs)
        avg_base = s.execute(text("SELECT AVG(base_price) FROM call_events")).scalar() or 0
        avg_final = s.execute(text("SELECT AVG(final_price) FROM call_events")).scalar() or 0

    return {
        "total_calls": total,
        "outcomes": outcomes,
        "sentiments": sentiments,
        "negotiation_rate": negotiation_rate,
        "avg_base_price": float(avg_base),
        "avg_final_price": float(avg_final),
    }

## DASHBOARD HTML

DASHBOARD_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Carrier Sales Dashboard</title>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:24px}
    .cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;margin:16px 0 32px}
    .card{padding:16px;border:1px solid #e5e7eb;border-radius:12px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
    .num{font-size:28px;font-weight:700}
    canvas{max-height:320px}
  </style>
</head>
<body>
  <h1>Carrier Sales Dashboard</h1>
  <div class="cards">
    <div class="card"><div>Total calls</div><div id="total" class="num">–</div></div>
    <div class="card"><div>Negotiation rate</div><div id="negRate" class="num">–</div></div>
    <div class="card"><div>Avg base price</div><div id="avgBase" class="num">–</div></div>
    <div class="card"><div>Avg final price</div><div id="avgFinal" class="num">–</div></div>
  </div>
  <div class="cards">
    <div class="card"><canvas id="outcomes"></canvas></div>
    <div class="card"><canvas id="sentiments"></canvas></div>
  </div>
<script>
async function loadMetrics(){
  const res = await fetch('/dashboard/metrics'); const m = await res.json();
  document.getElementById('total').textContent = m.total_calls;
  document.getElementById('negRate').textContent = (m.negotiation_rate*100).toFixed(0) + '%';
  document.getElementById('avgBase').textContent = '$' + Math.round(m.avg_base_price);
  document.getElementById('avgFinal').textContent = '$' + Math.round(m.avg_final_price);

  new Chart(document.getElementById('outcomes'), {
    type:'bar',
    data:{ labels:Object.keys(m.outcomes||{}),
           datasets:[{ label:'Outcomes', data:Object.values(m.outcomes||{}) }] },
    options:{ plugins:{ legend:{ display:false } } }
  });
  new Chart(document.getElementById('sentiments'), {
    type:'pie',
    data:{ labels:Object.keys(m.sentiments||{}),
           datasets:[{ label:'Sentiment', data:Object.values(m.sentiments||{}) }] }
  });
}
loadMetrics();
</script>
</body>
</html>
"""

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    return HTMLResponse(content=DASHBOARD_HTML)
