from http.server import BaseHTTPRequestHandler
import json, os
from urllib.parse import urlparse, parse_qs
from pymongo import MongoClient

MONGO_URI = os.environ.get("MONGO_URI",
    "mongodb+srv://asszss700800_db_user:JrDQGPrLljXGAero@cluster0h.vyl27ln.mongodb.net/?appName=Cluster0h"
)
DB_NAME = os.environ.get("DB_NAME", "makhayem")

def get_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
    return client[DB_NAME]

def verify_token(db, user_id, token):
    if not user_id or not token:
        return False
    user = db.users.find_one({"user_id": user_id, "token": token})
    return user is not None

class handler(BaseHTTPRequestHandler):

    # ══ GET - استعادة البيانات ══════════════════════════════════════════════
    def do_GET(self):
        try:
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            user_id = params.get("user_id", [None])[0]
            token   = params.get("token",   [None])[0]

            db = get_db()

            # إذا فيه user_id، تحقق من الـ token وأرجع بياناته فقط
            if user_id:
                if not verify_token(db, user_id, token):
                    self._send(401, {"status": "error", "message": "غير مصرح - سجل دخولك أولاً"})
                    return
                query = {"user_id": user_id}
            else:
                # بدون user_id - للتوافق مع النسخة القديمة
                query = {}

            camps     = list(db.camps.find(query,     {"_id": 0, "user_id": 0}))
            customers = list(db.customers.find(query, {"_id": 0, "user_id": 0}))
            bookings  = list(db.bookings.find(query,  {"_id": 0, "user_id": 0}))

            self._send(200, {
                "status":    "ok",
                "camps":     camps,
                "customers": customers,
                "bookings":  bookings
            })

        except Exception as e:
            self._send(500, {"status": "error", "message": str(e)})

    # ══ POST - رفع البيانات ═════════════════════════════════════════════════
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            data   = json.loads(body.decode("utf-8"))

            db      = get_db()
            user_id = data.get("user_id", "")
            token   = data.get("token",   "")

            # تحقق من الـ token إذا موجود
            if user_id and token:
                if not verify_token(db, user_id, token):
                    self._send(401, {"status": "error", "message": "غير مصرح"})
                    return

            camps     = data.get("camps",     [])
            customers = data.get("customers", [])
            bookings  = data.get("bookings",  [])

            if user_id:
                # حذف بيانات هذا المستخدم فقط
                db.camps.delete_many({"user_id": user_id})
                db.customers.delete_many({"user_id": user_id})
                db.bookings.delete_many({"user_id": user_id})

                # أضف user_id لكل سجل
                for c in camps:     c["user_id"] = user_id
                for c in customers: c["user_id"] = user_id
                for b in bookings:  b["user_id"] = user_id
            else:
                # للتوافق مع النسخة القديمة بدون حسابات
                db.camps.drop()
                db.customers.drop()
                db.bookings.drop()

            if camps:     db.camps.insert_many(camps)
            if customers: db.customers.insert_many(customers)
            if bookings:
                db.bookings.insert_many(bookings)
                db.bookings.create_index([("user_id", 1), ("setup_date", 1)])

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
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
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
