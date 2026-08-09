import sqlite3

DB_NAME = "shop_database.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # جدول کاربران
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        full_name TEXT,
        balance INTEGER DEFAULT 0,
        is_blocked INTEGER DEFAULT 0,
        referred_by INTEGER DEFAULT NULL,
        last_wheel_claim TIMESTAMP DEFAULT NULL,
        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # جدول سفارشات
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_name TEXT,
        target_type TEXT,
        target_input TEXT,
        price INTEGER,
        status TEXT DEFAULT 'IN_PROGRESS',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    # جدول محصولات دینامیک
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS custom_products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        title TEXT,
        price INTEGER,
        description TEXT
    )
    ''')
    
    # جدول کدهای تخفیف و هدیه
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS discount_codes (
        code TEXT PRIMARY KEY,
        amount_or_percent INTEGER,
        code_type TEXT DEFAULT 'PERCENT', -- 'PERCENT' or 'GIFT_BALANCE'
        is_active INTEGER DEFAULT 1
    )
    ''')
    
    # جدول تنظیمات
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    ''')
    
    defaults = {
        "card_number": "6037-9979-0000-0000",
        "tron_wallet": "TP6b2p7wt5BTX8S6ixkXAqgacvA2F6thxi",
        "ton_wallet": "UQC4W1s4K7FHrZWMs7W9AylPK7_VZrMJTTyr-E0fuTvPq6Ys",
        "stars_per_unit": "1500",
        "ton_price_toman": "350000",
        "trx_price_toman": "15000",
        "text_prem_desc": "👑 **تلگرام پرمیوم (Telegram Premium):**\n\n⚡️ با فعال‌سازی پرمیوم، اکانت خود را به سطح حرفه‌ای ارتقا دهید!\n• ارسال استوری با کیفیت HD و لینک اختصاصی\n• افزایش ۲ برابری تمامی محدودیت‌ها (عضویت در کانال‌ها، پین‌کردن چت‌ها)\n• تبدیل خودکار ویس‌ها و ویدیوپیام‌ها به متن فارسی و انگلیسی\n• استیکرها و ریکشن‌های انحصاری + ایموجی‌های متحرک custom\n• سرعت دانلود فوق‌العاده بالا و حذف کامل تمامی تبلیغات تلگرام",
        "text_stars_desc": "🌟 **تلگرام استارز (Telegram Stars):**\n\n✨ ارز رسمی و درون‌برنامه‌ای تلگرام برای خریدهای دیجیتال!\n• پرداخت در مینی‌آپ‌ها و ربات‌های تلگرامی (مانند Major, Blum, etc.)\n• ارسال هدیه و حمایت از کانال‌ها و تولیدکنندگان محتوا\n• باز کردن قفل محتواها و پست‌های اختصاصی",
        "text_ton_desc": "💎 **ارز تون کوین (TON Coin):**\n\n🚀 سوخت اصلی اکوسیستم بلاکچین تلگرام (TON)!\n• خرید شماره‌های مجازی نایاب و آیدی‌های پریمیوم Fragment\n• پرداخت کارمزد تراکنش‌ها و خرید گیفت‌های NFT\n• نقدشوندگی سریع و امکان سرمایه‌گذاری پر سود",
        "text_trx_desc": "🔴 **ارز ترون (TRX):**\n\n⚡️ سریع‌ترین ارز برای تامین کارمزد شبکه‌های بلاکچینی!\n• صفر کردن کارمزدهای سنگین انتقال تتر (USDT TRC-20)\n• سرعت انتقال فوق‌العاده بالا در چند ثانیه",
        "text_gift_desc": "🎁 **گیفت‌ها و هدیه‌های تلگرام:**\n\n💖 با ارسال گیفت، دوستان خود را شگفت‌زده کنید!\n• نمایش گیفت در پروفایل تلگرام گیرنده به‌صورت دائمی\n• قابلیت تبدیل به استارز یا معامله در بازار NFT"
    }
    for k, v in defaults.items():
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        
    conn.commit()
    conn.close()

def add_or_update_user(user_id, username, full_name, referred_by=None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, username, full_name, referred_by) VALUES (?, ?, ?, ?)",
                       (user_id, username, full_name, referred_by))
    else:
        cursor.execute("UPDATE users SET username = ?, full_name = ? WHERE user_id = ?", (username, full_name, user_id))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_all_user_ids():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE is_blocked = 0")
    users = cursor.fetchall()
    conn.close()
    return [u['user_id'] for u in users]

def set_block_status(user_id, status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_blocked = ? WHERE user_id = ?", (status, user_id))
    conn.commit()
    conn.close()

def update_balance(user_id, amount):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

def get_referral_count(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM users WHERE referred_by = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res["count"] if res else 0

def create_order(user_id, product_name, target_type, target_input, price):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
    INSERT INTO orders (user_id, product_name, target_type, target_input, price)
    VALUES (?, ?, ?, ?, ?)
    ''', (user_id, product_name, target_type, target_input, price))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id

def get_user_orders(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (user_id,))
    orders = cursor.fetchall()
    conn.close()
    return orders

def add_custom_product(category, title, price, description):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO custom_products (category, title, price, description) VALUES (?, ?, ?, ?)",
                   (category, title, price, description))
    conn.commit()
    conn.close()

def get_custom_products(category):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM custom_products WHERE category = ?", (category,))
    prods = cursor.fetchall()
    conn.close()
    return prods

def delete_custom_product(prod_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM custom_products WHERE id = ?", (prod_id,))
    conn.commit()
    conn.close()

def add_discount_code(code, amount_or_percent, code_type='PERCENT'):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO discount_codes (code, amount_or_percent, code_type) VALUES (?, ?, ?)",
                   (code, amount_or_percent, code_type))
    conn.commit()
    conn.close()

def get_discount_code(code):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM discount_codes WHERE code = ? AND is_active = 1", (code,))
    res = cursor.fetchone()
    conn.close()
    return res

def disable_discount_code(code):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE discount_codes SET is_active = 0 WHERE code = ?", (code,))
    conn.commit()
    conn.close()

def get_setting(key):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    res = cursor.fetchone()
    conn.close()
    return res["value"] if res else ""

def update_setting(key, value):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()

def get_stats():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as u FROM users")
    u = cursor.fetchone()['u']
    cursor.execute("SELECT COUNT(*) as o FROM orders")
    o = cursor.fetchone()['o']
    cursor.execute("SELECT SUM(price) as total_sales FROM orders")
    s = cursor.fetchone()['total_sales']
    conn.close()
    return u, o, (s if s else 0)
