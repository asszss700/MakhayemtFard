from http.server import BaseHTTPRequestHandler
import json, os
from pymongo import MongoClient
from urllib.parse import urlparse, parse_qs
from datetime import datetime

MONGO_URI = os.environ.get("MONGO_URI", "")
DB_NAME   = os.environ.get("DB_NAME", "makhayem")

def get_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    return client[DB_NAME]

def days_between(d1, d2):
    try:
        return (datetime.strptime(d2, "%Y-%m-%d") -
                datetime.strptime(d1, "%Y-%m-%d")).days + 1
    except:
        return 0

def clean_booking(b):
    """أزل _id من MongoDB وأرجع dict نظيف"""
    b.pop("_id", None)
    return b

class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path.rstrip("/")
        params = parse_qs(parsed.query)

        date  = params.get("date",  [None])[0]
        from_ = params.get("from",  [None])[0]
        to_   = params.get("to",    [None])[0]

        try:
            db = get_db()

            # ── / أو /api ────────────────────────────────────────────────
            if path in ("", "/", "/api"):
                self._send(200, {
                    "api":     "مخيمات الفارط",
                    "version": "1.0",
                    "status":  "✅ متصل بـ MongoDB" if MONGO_URI else "⚠️ MONGO_URI غير محدد",
                    "endpoints": {
                        "GET /api/bookings":                              "كل الحجوزات",
                        "GET /api/bookings?date=2026-04-25":              "حجوزات يوم",
                        "GET /api/bookings?from=2026-04-01&to=2026-04-30":"حجوزات فترة",
                        "GET /api/camps":                                 "المخيمات",
                        "GET /api/customers":                             "الزبائن",
                        "GET /api/report?from=...&to=...":                "تقرير + إحصاء"
                    }
                })
                return

            # ── /api/camps ───────────────────────────────────────────────
            if path == "/api/camps":
                camps = list(db.camps.find({}, {"_id": 0}))
                self._send(200, {"count": len(camps), "camps": camps})
                return

            # ── /api/customers ───────────────────────────────────────────
            if path == "/api/customers":
                custs = list(db.customers.find({}, {"_id": 0}))
                self._send(200, {"count": len(custs), "customers": custs})
                return

            # ── /api/bookings ─────────────────────────────────────────────
            if path.startswith("/api/bookings"):
                query = {}
                if date:
                    query = {"setup_date": {"$lte": date}, "remove_date": {"$gte": date}}
                elif from_ and to_:
                    query = {"setup_date": {"$lte": to_},  "remove_date": {"$gte": from_}}

                bookings = list(db.bookings.find(query, {"_id": 0})
                                           .sort("setup_date", -1))
                # أضف عدد الأيام
                for b in bookings:
                    b["days"] = days_between(b.get("setup_date",""),
                                             b.get("remove_date",""))
                self._send(200, {"count": len(bookings), "bookings": bookings})
                return

            # ── /api/report ───────────────────────────────────────────────
            if path == "/api/report":
                if not from_ or not to_:
                    self._send(400, {"error": "مطلوب: ?from=YYYY-MM-DD&to=YYYY-MM-DD"})
                    return

                bookings = list(db.bookings.find(
                    {"setup_date": {"$lte": to_}, "remove_date": {"$gte": from_}},
                    {"_id": 0}
                ).sort("setup_date", 1))

                total_days  = 0
                total_camps = 0
                for b in bookings:
                    d = days_between(b.get("setup_date",""), b.get("remove_date",""))
                    b["days"]    = d
                    total_days  += d
                    total_camps += len(b.get("camps", []))

                self._send(200, {
                    "period":  {"from": from_, "to": to_},
                    "summary": {
                        "total_bookings": len(bookings),
                        "total_days":     total_days,
                        "total_camps":    total_camps
                    },
                    "bookings": bookings
                })
                return

            self._send(404, {"error": "Endpoint غير موجود"})

        except Exception as e:
            self._send(500, {"error": str(e)})

    def _send(self, code, data):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args): pass
