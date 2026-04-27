"""
sync.py - يحوّل tent.db إلى MongoDB
شغّله مرة واحدة أو كل ما تريد تحديث البيانات

الاستخدام:
  pip install pymongo
  python sync.py --db /path/to/tent.db --uri "mongodb+srv://..."
"""

import sqlite3, sys, os
from pymongo import MongoClient
from datetime import datetime

def sync(db_path: str, mongo_uri: str, db_name: str = "makhayem"):
    print(f"📂 قاعدة البيانات: {db_path}")
    print(f"🔗 MongoDB: {mongo_uri[:40]}...")

    # ── SQLite ───────────────────────────────────────────────────────────
    sql = sqlite3.connect(db_path)
    sql.row_factory = sqlite3.Row

    # ── MongoDB ──────────────────────────────────────────────────────────
    client = MongoClient(mongo_uri)
    mdb    = client[db_name]

    # ── المخيمات ─────────────────────────────────────────────────────────
    camps_rows = sql.execute("SELECT * FROM camps").fetchall()
    camps_map  = {}   # id → dict
    camps_data = []
    for r in camps_rows:
        d = {"camp_id": r["id"], "name": r["name"], "notes": r["notes"] or ""}
        camps_map[r["id"]] = d
        camps_data.append(d)

    mdb.camps.drop()
    if camps_data:
        mdb.camps.insert_many(camps_data)
    print(f"⛺ المخيمات: {len(camps_data)}")

    # ── الزبائن ──────────────────────────────────────────────────────────
    custs_rows = sql.execute("SELECT * FROM customers").fetchall()
    custs_map  = {}
    custs_data = []
    for r in custs_rows:
        d = {"customer_id": r["id"], "name": r["name"], "phone": r["phone"] or ""}
        custs_map[r["id"]] = d
        custs_data.append(d)

    mdb.customers.drop()
    if custs_data:
        mdb.customers.insert_many(custs_data)
    print(f"👥 الزبائن: {len(custs_data)}")

    # ── الحجوزات ─────────────────────────────────────────────────────────
    bookings_rows = sql.execute("SELECT * FROM bookings").fetchall()
    bookings_data = []

    for r in bookings_rows:
        # جلب المخيمات المرتبطة
        bc = sql.execute(
            "SELECT camp_id FROM booking_camps WHERE booking_id = ?",
            (r["id"],)
        ).fetchall()
        booking_camps = [camps_map[row["camp_id"]]
                         for row in bc if row["camp_id"] in camps_map]

        # حساب عدد الأيام
        try:
            d1 = datetime.strptime(r["setup_date"],  "%Y-%m-%d")
            d2 = datetime.strptime(r["remove_date"], "%Y-%m-%d")
            days = (d2 - d1).days + 1
        except:
            days = 0

        cust = custs_map.get(r["customer_id"], {})
        bookings_data.append({
            "booking_id":  r["id"],
            "customer_id": r["customer_id"],
            "customer": {
                "name":  cust.get("name", ""),
                "phone": cust.get("phone", "")
            },
            "setup_date":  r["setup_date"],
            "remove_date": r["remove_date"],
            "days":        days,
            "notes":       r["notes"] or "",
            "camps":       booking_camps
        })

    mdb.bookings.drop()
    if bookings_data:
        mdb.bookings.insert_many(bookings_data)

    # فهرس للبحث السريع بالتاريخ
    mdb.bookings.create_index("setup_date")
    mdb.bookings.create_index("remove_date")

    print(f"📋 الحجوزات: {len(bookings_data)}")
    print("✅ تم الرفع إلى MongoDB بنجاح!")
    sql.close()
    client.close()


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="رفع tent.db إلى MongoDB")
    p.add_argument("--db",  required=True, help="مسار ملف tent.db")
    p.add_argument("--uri", required=True, help="MongoDB connection string")
    p.add_argument("--name", default="makhayem", help="اسم قاعدة البيانات")
    args = p.parse_args()

    if not os.path.exists(args.db):
        print(f"❌ الملف غير موجود: {args.db}")
        sys.exit(1)

    sync(args.db, args.uri, args.name)
