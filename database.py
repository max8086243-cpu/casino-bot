import sqlite3
import random
import json
from datetime import datetime, timedelta

DB_NAME = "casino_xc.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    
    # Таблица пользователей
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            coins INTEGER DEFAULT 0,
            last_spin TEXT,
            booster_luck INTEGER DEFAULT 0,
            booster_speed INTEGER DEFAULT 0,
            booster_magnet INTEGER DEFAULT 0,
            total_spins INTEGER DEFAULT 0,
            total_spent INTEGER DEFAULT 0,
            clan_id INTEGER DEFAULT NULL,
            rank_points INTEGER DEFAULT 0,
            rank_league TEXT DEFAULT 'Железо',
            premium_until TEXT,
            ultra_luck INTEGER DEFAULT 0,
            ultra_speed INTEGER DEFAULT 0,
            legendary_key INTEGER DEFAULT 0,
            booster_reroll INTEGER DEFAULT 0
        )
    ''')
    
    # Таблица карт пользователей
    cur.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            card_name TEXT,
            rarity TEXT,
            image_url TEXT
        )
    ''')
    
    # Таблица шаблонов карт
    cur.execute('''
        CREATE TABLE IF NOT EXISTS card_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            rarity TEXT,
            image_url TEXT
        )
    ''')
    
    # Таблица достижений
    cur.execute('''
        CREATE TABLE IF NOT EXISTS achievements (
            user_id INTEGER,
            achievement TEXT,
            unlocked_at TEXT,
            PRIMARY KEY (user_id, achievement)
        )
    ''')
    
    # Таблица кланов
    cur.execute('''
        CREATE TABLE IF NOT EXISTS clans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE,
            owner_id INTEGER,
            balance INTEGER DEFAULT 0,
            created_at TEXT,
            members TEXT
        )
    ''')
    
    # Таблица обменов
    cur.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_user INTEGER,
            to_user INTEGER,
            from_card_id INTEGER,
            to_card_id INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        )
    ''')
    
    # Добавляем недостающие колонки
    new_columns = [
        ('booster_magnet', 'INTEGER DEFAULT 0'),
        ('total_spins', 'INTEGER DEFAULT 0'),
        ('total_spent', 'INTEGER DEFAULT 0'),
        ('clan_id', 'INTEGER DEFAULT NULL'),
        ('rank_points', 'INTEGER DEFAULT 0'),
        ('rank_league', 'TEXT DEFAULT "Железо"'),
        ('premium_until', 'TEXT'),
        ('ultra_luck', 'INTEGER DEFAULT 0'),
        ('ultra_speed', 'INTEGER DEFAULT 0'),
        ('legendary_key', 'INTEGER DEFAULT 0'),
        ('booster_reroll', 'INTEGER DEFAULT 0')
    ]
    
    for col_name, col_type in new_columns:
        try:
            cur.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"✅ Добавлена колонка: {col_name}")
        except:
            pass
    
    # Добавляем базовые карты-шаблоны, если их нет
    default_cards = [
        ('Калл карта', 'калл', 'https://cdn-icons-png.flaticon.com/512/2933/3933241.png'),
        ('Тьфу блять карта', 'тьфу блять', 'https://cdn-icons-png.flaticon.com/512/2933/3933241.png'),
        ('Среднее карта', 'среднее', 'https://cdn-icons-png.flaticon.com/512/2933/3933241.png'),
        ('Нормалды карта', 'нормалды', 'https://cdn-icons-png.flaticon.com/512/2933/3933241.png'),
        ('Омагад карта', 'омагад', 'https://cdn-icons-png.flaticon.com/512/2933/3933241.png'),
        ('Бог карта', 'бог', 'https://cdn-icons-png.flaticon.com/512/2933/3933241.png'),
        ('Таинственная карта', '???', 'https://cdn-icons-png.flaticon.com/512/2933/3933241.png')
    ]
    
    for name, rarity, url in default_cards:
        cur.execute('SELECT COUNT(*) FROM card_templates WHERE rarity = ?', (rarity,))
        if cur.fetchone()[0] == 0:
            cur.execute('INSERT INTO card_templates (name, rarity, image_url) VALUES (?, ?, ?)',
                       (name, rarity, url))
            print(f"✅ Добавлена карта для редкости: {rarity}")
    
    conn.commit()
    conn.close()

RARITIES = {
    "калл": {"points": 1000, "coins": 3, "weight": 40, "emoji": "💩"},
    "тьфу блять": {"points": 2000, "coins": 5, "weight": 30, "emoji": "🤮"},
    "среднее": {"points": 5000, "coins": 15, "weight": 15, "emoji": "😐"},
    "нормалды": {"points": 6700, "coins": 20, "weight": 8, "emoji": "👍"},
    "омагад": {"points": 8000, "coins": 25, "weight": 4, "emoji": "🤯"},
    "бог": {"points": 15000, "coins": 45, "weight": 3, "emoji": "👑"},
    "???": {"points": 20000, "coins": 200, "weight": 0, "emoji": "❓", "secret": True}
}

def get_random_rarity(luck_boost=False, magnet_boost=False):
    items = list(RARITIES.items())
    weights = []
    for name, data in items:
        if data.get("secret", False):
            weights.append(0)
            continue
        weight = data["weight"]
        if luck_boost and weight <= 8:
            weight = weight * 3
        elif luck_boost:
            weight = weight // 2
        if magnet_boost and name in ["калл", "тьфу блять", "среднее"]:
            weight = 0
        weights.append(max(0, weight))
    if sum(weights) == 0:
        weights = [1, 1, 1]
        items = [("нормалды", RARITIES["нормалды"]), ("омагад", RARITIES["омагад"]), ("бог", RARITIES["бог"])]
    chosen = random.choices(items, weights=weights, k=1)[0]
    return chosen[0], chosen[1]

def safe_get(user, index, default=0):
    if user and index < len(user):
        val = user[index]
        return val if val is not None else default
    return default

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cur.fetchone()
    if not user:
        cur.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cur.fetchone()
    conn.close()
    return user

def update_user(user_id, **kwargs):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    updates = []
    values = []
    for key, value in kwargs.items():
        updates.append(f"{key} = ?")
        values.append(value)
    if updates:
        values.append(user_id)
        cur.execute(f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?", values)
        conn.commit()
    conn.close()

def add_card_to_collection(user_id, card_name, rarity, image_url):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT INTO cards (user_id, card_name, rarity, image_url) VALUES (?, ?, ?, ?)",
                (user_id, card_name, rarity, image_url))
    conn.commit()
    conn.close()

def get_user_cards_count(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM cards WHERE user_id = ?", (user_id,))
    return cur.fetchone()[0]

def get_user_cards(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, card_name, rarity, image_url FROM cards WHERE user_id = ?", (user_id,))
    cards = cur.fetchall()
    conn.close()
    return cards

def get_card_image_by_rarity(rarity_name):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, name, rarity, image_url FROM card_templates WHERE rarity = ?", (rarity_name,))
    templates = cur.fetchall()
    conn.close()
    if templates:
        chosen = random.choice(templates)
        return {"id": chosen[0], "name": chosen[1], "rarity": chosen[2], "image_url": chosen[3]}
    return None

def get_all_card_templates():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, name, rarity, image_url FROM card_templates")
    templates = cur.fetchall()
    conn.close()
    return [{"id": t[0], "name": t[1], "rarity": t[2], "image_url": t[3]} for t in templates]

def get_top_balance(limit=10):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT user_id, balance FROM users ORDER BY balance DESC LIMIT ?", (limit,))
    return cur.fetchall()

def get_top_cards_count(limit=10):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT user_id, COUNT(*) as cnt 
        FROM cards 
        GROUP BY user_id 
        ORDER BY cnt DESC 
        LIMIT ?
    ''', (limit,))
    return cur.fetchall()

def get_top_rarest_cards(limit=10):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute('''
        SELECT user_id, SUM(
            CASE 
                WHEN rarity = 'бог' THEN 15000
                WHEN rarity = 'омагад' THEN 8000
                WHEN rarity = 'нормалды' THEN 6700
                WHEN rarity = 'среднее' THEN 5000
                WHEN rarity = 'тьфу блять' THEN 2000
                WHEN rarity = 'калл' THEN 1000
                WHEN rarity = '???' THEN 20000
                ELSE 0
            END
        ) as total_points
        FROM cards
        GROUP BY user_id
        ORDER BY total_points DESC
        LIMIT ?
    ''', (limit,))
    return cur.fetchall()

def get_top_rank_points(limit=10):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT user_id, rank_points FROM users ORDER BY rank_points DESC LIMIT ?", (limit,))
    return cur.fetchall()

def add_achievement(user_id, achievement):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO achievements (user_id, achievement, unlocked_at) VALUES (?, ?, ?)",
                (user_id, achievement, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def check_achievement_exists(user_id, achievement):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM achievements WHERE user_id = ? AND achievement = ?", (user_id, achievement))
    exists = cur.fetchone() is not None
    conn.close()
    return exists

def get_user_achievements(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT achievement, unlocked_at FROM achievements WHERE user_id = ?", (user_id,))
    return cur.fetchall()

def create_clan(clan_name, owner_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO clans (name, owner_id, created_at, members) VALUES (?, ?, ?, ?)",
                    (clan_name, owner_id, datetime.now().isoformat(), json.dumps([owner_id])))
        clan_id = cur.lastrowid
        conn.commit()
        conn.close()
        return clan_id
    except:
        conn.close()
        return None

def get_clan(clan_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM clans WHERE id = ?", (clan_id,))
    return cur.fetchone()

def get_clan_by_name(clan_name):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM clans WHERE name = ?", (clan_name,))
    return cur.fetchone()

def add_to_clan(clan_id, user_id):
    clan = get_clan(clan_id)
    if not clan:
        return False
    members = json.loads(clan[5])
    if user_id in members:
        return False
    members.append(user_id)
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE clans SET members = ? WHERE id = ?", (json.dumps(members), clan_id))
    conn.commit()
    conn.close()
    update_user(user_id, clan_id=clan_id)
    return True

def get_clan_members(clan_id):
    clan = get_clan(clan_id)
    if not clan:
        return []
    return json.loads(clan[5])

def update_clan_balance(clan_id, amount):
    clan = get_clan(clan_id)
    if not clan:
        return False
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE clans SET balance = balance + ? WHERE id = ?", (amount, clan_id))
    conn.commit()
    conn.close()
    return True

def create_trade(from_user, to_user, from_card_id, to_card_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("INSERT INTO trades (from_user, to_user, from_card_id, to_card_id, created_at) VALUES (?, ?, ?, ?, ?)",
                (from_user, to_user, from_card_id, to_card_id, datetime.now().isoformat()))
    trade_id = cur.lastrowid
    conn.commit()
    conn.close()
    return trade_id

def get_trade(trade_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT * FROM trades WHERE id = ?", (trade_id,))
    return cur.fetchone()

def update_trade_status(trade_id, status):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("UPDATE trades SET status = ? WHERE id = ?", (status, trade_id))
    conn.commit()
    conn.close()

def get_pending_trades_for_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT id, from_user, to_user, from_card_id, to_card_id, created_at FROM trades WHERE to_user = ? AND status = 'pending'", (user_id,))
    return cur.fetchall()

def is_premium(user_id):
    user = get_user(user_id)
    if user and len(user) > 13 and user[13]:
        try:
            premium_date = datetime.fromisoformat(user[13])
            if premium_date > datetime.now():
                return True
        except:
            pass
    return False

def activate_premium(user_id, days):
    new_date = datetime.now() + timedelta(days=days)
    update_user(user_id, premium_until=new_date.isoformat())

def get_premium_multiplier(user_id):
    return 1.5 if is_premium(user_id) else 1.0

def get_premium_coin_multiplier(user_id):
    return 2.0 if is_premium(user_id) else 1.0

def add_rank_points(user_id, points):
    user = get_user(user_id)
    current = user[11] if user and len(user) > 11 else 0
    new_points = current + points
    update_user(user_id, rank_points=new_points)
    update_rank_league(user_id)

def update_rank_league(user_id):
    user = get_user(user_id)
    points = user[11] if user and len(user) > 11 else 0
    if points >= 10000:
        league = "Алмаз"
    elif points >= 5000:
        league = "Платина"
    elif points >= 2000:
        league = "Золото"
    elif points >= 1000:
        league = "Серебро"
    elif points >= 500:
        league = "Бронза"
    else:
        league = "Железо"
    update_user(user_id, rank_league=league)