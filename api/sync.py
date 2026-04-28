from http.server import BaseHTTPRequestHandler
import json, os
from pymongo import MongoClient

MONGO_URI = os.environ.get("MONGO_URI",
    "mongodb+srv://asszss700800_db_user:JrDQGPrLljXGAero@cluster0h.vyl27ln.mongodb.net/?appName=Cluster0h"
)
DB_NAME = os.environ.get("DB_NAME", "makhayem")

def get_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
    return client[DB_NAME]

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            data   = json.loads(body.decode("utf-8"))

            db = get_db()

            # امسح القديم وأدخل الجديد
            camps     = data.get("camps",     [])
            customers = data.get("customers", [])
            bookings  = data.get("bookings",  [])

            db.camps.drop()
            db.customers.drop()
            db.bookings.drop()

            if camps:     db.camps.insert_many(camps)
            if customers: db.customers.insert_many(customers)
            if bookings:
                db.bookings.insert_many(bookings)
                db.bookings.create_index("setup_date")
                db.bookings.create_index("remove_date")

            self._send(200, {
                "status":    "ok",
                "message":   "✅ تم رفع البيانات بنجاح",
                "camps":     len(camps),
                "customers": len(customers),
                "bookings":  len(bookings)
            })

        except Exception as e:
            self._send(500, {"status": "error", "message": str(e)})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def _send(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args): pass
