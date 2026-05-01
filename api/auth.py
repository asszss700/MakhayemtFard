from http.server import BaseHTTPRequestHandler
import json, os, hashlib, secrets
from pymongo import MongoClient

MONGO_URI = os.environ.get("MONGO_URI",
    "mongodb+srv://asszss700800_db_user:JrDQGPrLljXGAero@cluster0h.vyl27ln.mongodb.net/?appName=Cluster0h"
)
DB_NAME = os.environ.get("DB_NAME", "makhayem")

def get_db():
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=8000)
    return client[DB_NAME]

def hash_password(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def generate_token():
    return secrets.token_hex(32)

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body   = self.rfile.read(length)
            data   = json.loads(body.decode("utf-8"))

            action   = data.get("action", "")
            username = data.get("username", "").strip().lower()
            password = data.get("password", "")

            if not username or not password:
                self._send(400, {"status": "error", "message": "اسم المستخدم وكلمة السر مطلوبان"})
                return

            db = get_db()

            # ── تسجيل حساب جديد ──
            if action == "register":
                existing = db.users.find_one({"username": username})
                if existing:
                    self._send(409, {"status": "error", "message": "اسم المستخدم موجود مسبقاً"})
                    return

                user_id = generate_token()[:16]
                token   = generate_token()
                db.users.insert_one({
                    "user_id":  user_id,
                    "username": username,
                    "password": hash_password(password),
                    "token":    token
                })
                self._send(200, {
                    "status":   "ok",
                    "message":  "✅ تم إنشاء الحساب بنجاح",
                    "user_id":  user_id,
                    "token":    token,
                    "username": username
                })

            # ── تسجيل دخول ──
            elif action == "login":
                user = db.users.find_one({
                    "username": username,
                    "password": hash_password(password)
                })
                if not user:
                    self._send(401, {"status": "error", "message": "اسم المستخدم أو كلمة السر خاطئة"})
                    return

                # تحديث token عند كل دخول
                new_token = generate_token()
                db.users.update_one(
                    {"username": username},
                    {"$set": {"token": new_token}}
                )
                self._send(200, {
                    "status":   "ok",
                    "message":  "✅ تم تسجيل الدخول",
                    "user_id":  user["user_id"],
                    "token":    new_token,
                    "username": username
                })

            else:
                self._send(400, {"status": "error", "message": "action غير صالح"})

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
