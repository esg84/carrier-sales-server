from pydantic import BaseModel
from fastapi import FastAPI, Query, Body, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from typing import Optional, List, Dict
from datetime import datetime
import os

#For Dashboard
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import Integer, String, Boolean, DateTime

# ---------- Pydantic compatibility & helpers ----------
try:
    # Pydantic v2
    from pydantic import BaseModel, field_validator as _validator  # type: ignore
    _P2 = True
except Exception:
    # Pydantic v1
    from pydantic import BaseModel, validator as _validator  # type: ignore
    _P2 = False


def _coerce_int_like(v) -> Optional[int]:
    """
    Accept None, "", "$1,900", "1,900", "1900", 1900, 1900.0.
    Returns int or None. Non-numeric -> None.
    """
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, float):
        try:
            return int(v)
        except Exception:
            return None
    if isinstance(v, str):
        s = v.strip()
        if s == "":
            return None
        digits = "".join(ch for ch in s if ch.isdigit())
        if digits == "":
            return None
        try:
            return int(digits)
        except ValueError:
            return None
    return None
# ------------------------------------------------------

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
    # as before
    call_date: Optional[str] = None
    base_price: Optional[int] = None
    final_price: Optional[int] = None
    load_origin: Optional[str] = None
    call_outcome: Optional[str] = None
    sentiment: Optional[str] = None
    mc_number: Optional[int] = None
    carrier_name: Optional[str] = None

    # add the fields your handler uses (to avoid AttributeError)
    load_destination: Optional[str] = None
    call_duration: Optional[int] = None
    is_negotiated: Optional[bool] = None
    carrier_sentiment: Optional[str] = None

    # ---- forgiving validators (v2 or v1) ----
    if _P2:
        @_validator("mc_number", "base_price", "final_price", "call_duration", mode="before")
        @classmethod
        def _coerce_int_fields_v2(cls, v):
            return _coerce_int_like(v)
    else:
        @_validator("mc_number", "base_price", "final_price", "call_duration", pre=True)  # type: ignore
        def _coerce_int_fields_v1(cls, v):  # type: ignore
            return _coerce_int_like(v)

def _as_int(v):
    try: return int(v)
    except (TypeError, ValueError): return None

def _as_bool(v):
    if isinstance(v, bool): return v
    if isinstance(v, str): return v.strip().lower() in ("true","1","yes","y")
    return None

def _infer_is_negotiated(base: Optional[int], final: Optional[int], explicit: Optional[bool]) -> Optional[bool]:
    """
    If explicit flag provided, use it.
    Otherwise infer: True when both prices exist and differ; else None.
    """
    if explicit is not None:
        return explicit
    if base is not None and final is not None:
        return base != final
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

    # --- normalize inputs and infer negotiation flag ---
    bp = _as_int(payload.base_price)
    fp = _as_int(payload.final_price)
    explicit_neg = _as_bool(payload.is_negotiated)
    neg_flag = _infer_is_negotiated(bp, fp, explicit_neg)

    row = EventRow(
        call_date = payload.call_date,
        base_price = bp,
        final_price = fp,
        load_origin = payload.load_origin,
        load_destination = payload.load_destination,
        call_outcome = payload.call_outcome,
        call_duration = _as_int(payload.call_duration),
        is_negotiated = neg_flag,
        carrier_sentiment = (payload.sentiment or payload.carrier_sentiment),
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

        # ---- Outcomes (fixed categories) ----
        outcome_counts = {"Success": 0, "No MC": 0, "Unsuccessful": 0}
        for k, v in s.execute(text("""
            SELECT call_outcome, COUNT(*) 
            FROM call_events 
            GROUP BY call_outcome
        """)):
            if not k:
                continue
            k_norm = str(k).strip()
            if k_norm in outcome_counts:
                outcome_counts[k_norm] = int(v)

        # ---- Sentiments (fixed categories) ----
        sentiment_counts = {"Negative": 0, "Neutral": 0, "Positive": 0}
        for k, v in s.execute(text("""
            SELECT carrier_sentiment, COUNT(*) 
            FROM call_events 
            GROUP BY carrier_sentiment
        """)):
            if not k:
                continue
            k_norm = str(k).strip().capitalize()  # normalize "negative" -> "Negative"
            if k_norm in sentiment_counts:
                sentiment_counts[k_norm] = int(v)

        # Negotiation rate
        neg_count = s.execute(text("""
    SELECT COUNT(*) FROM call_events
    WHERE COALESCE(
        is_negotiated,
        CASE
            WHEN base_price IS NOT NULL AND final_price IS NOT NULL AND base_price <> final_price
            THEN TRUE ELSE FALSE
        END
    ) = TRUE
""")).scalar() or 0

        negotiation_rate = (neg_count / total) if total else 0.0

        # Averages (ignore NULLs)
        avg_base = s.execute(text("SELECT AVG(base_price) FROM call_events")).scalar() or 0
        avg_final = s.execute(text("SELECT AVG(final_price) FROM call_events")).scalar() or 0

    return {
        "total_calls": int(total),
        "outcomes": outcome_counts,          # {"Success": x, "No MC": y, "Unsuccessful": z}
        "sentiments": sentiment_counts,      # {"Negative": a, "Neutral": b, "Positive": c}
        "negotiation_rate": float(negotiation_rate),
        "avg_base_price": float(avg_base),
        "avg_final_price": float(avg_final),
    }


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
    .cards{display:grid;grid-template-columns:repeat(4,minmax(240px,1fr));gap:16px;margin:16px 0 32px}
    .card{padding:16px;border:1px solid #e5e7eb;border-radius:12px;box-shadow:0 1px 2px rgba(0,0,0,.04)}
    .label{color:#6b7280;margin-bottom:6px}
    .num{font-size:28px;font-weight:700}
    @media (max-width:1100px){ .cards{grid-template-columns:repeat(auto-fit,minmax(240px,1fr));} }
    canvas{max-height:360px}
  </style>
</head>
<body>
  <h1 style="margin-bottom:8px;">Carrier Sales Dashboard</h1>
  <div class="cards">
    <div class="card">
      <div class="label">Total calls</div>
      <div id="total" class="num">0</div>
    </div>
    <div class="card">
      <div class="label">Negotiation rate</div>
      <div id="negRate" class="num">0%</div>
    </div>
    <div class="card">
      <div class="label">Avg negotiation price</div>
      <div id="avgPrice" class="num">$0</div>
    </div>
    <div class="card">
      <div class="label">Overall Sentiment</div>
      <div id="overallSentiment" class="num">–</div>
    </div>
  </div>

  <div class="cards" style="grid-template-columns:1fr 1fr;">
    <div class="card"><canvas id="outcomes"></canvas></div>
    <div class="card"><canvas id="sentiments"></canvas></div>
  </div>

  <script>
  async function loadMetrics() {
    const res = await fetch('/dashboard/metrics');
    const m = await res.json();

    // KPIs
    const total = m.total_calls || 0;
    const negRate = ((m.negotiation_rate || 0) * 100).toFixed(0) + '%';
    const avgPrice = '$' + Math.round(m.avg_final_price || 0); // use avg_final_price; swap to avg_base_price if you prefer

    document.getElementById('total').textContent = total;
    document.getElementById('negRate').textContent = negRate;
    document.getElementById('avgPrice').textContent = avgPrice;

    // Fixed categories
    const outcomeLabels = ['Success', 'No MC', 'Unsuccessful'];
    const sentimentLabels = ['Negative', 'Neutral', 'Positive'];

    // Counts with safe defaults
    const outcomesObj = m.outcomes || {};
    const sentimentsObj = m.sentiments || {};
    const outcomeCounts = outcomeLabels.map(k => Number(outcomesObj[k] || 0));
    const sentimentCounts = sentimentLabels.map(k => Number(sentimentsObj[k] || 0));

    // Dominant sentiment for the KPI card
    const totalSent = sentimentCounts.reduce((a,b) => a+b, 0);
    const maxIdx = sentimentCounts.indexOf(Math.max(...sentimentCounts, 0));
    const dominant = totalSent > 0 ? sentimentLabels[maxIdx] : '–';
    document.getElementById('overallSentiment').textContent = dominant;

    // Outcomes bar (no legend)
    new Chart(document.getElementById('outcomes'), {
      type: 'bar',
      data: {
        labels: outcomeLabels,
        datasets: [{
          label: 'Outcomes',
          data: outcomeCounts,
          backgroundColor: ['#22c55e', '#9ca3af', '#f59e0b'] // green, gray, amber
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { precision: 0 } }
        }
      }
    });

    // Sentiments pie
    new Chart(document.getElementById('sentiments'), {
      type: 'pie',
      data: {
        labels: sentimentLabels,
        datasets: [{
          label: 'Sentiment',
          data: sentimentCounts,
          backgroundColor: ['#ef4444', '#f59e0b', '#22c55e'] // red, amber, green
        }]
      }
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
