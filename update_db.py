import sqlite3

conn = sqlite3.connect('casino_xc.db')
cursor = conn.cursor()

# Основные колонки
columns = [
    'booster_magnet INTEGER DEFAULT 0',
    'total_spins INTEGER DEFAULT 0',
    'total_spent INTEGER DEFAULT 0',
    'clan_id INTEGER DEFAULT NULL',
    'rank_points INTEGER DEFAULT 0',
    'rank_league TEXT DEFAULT "Железо"',
    'premium_until TEXT',
    'ultra_luck INTEGER DEFAULT 0',
    'ultra_speed INTEGER DEFAULT 0',
    'legendary_key INTEGER DEFAULT 0',
    'booster_reroll INTEGER DEFAULT 0'
]

for col in columns:
    try:
        cursor.execute(f'ALTER TABLE users ADD COLUMN {col}')
        print(f'✅ Добавлено: {col}')
    except sqlite3.OperationalError as e:
        if 'duplicate column name' in str(e):
            print(f'⚠️ Уже есть: {col}')
        else:
            print(f'❌ Ошибка: {e}')

# Добавляем колонки для дат
date_columns = [
    'reg_date TEXT',
    'last_active TEXT'
]

for col in date_columns:
    try:
        cursor.execute(f'ALTER TABLE users ADD COLUMN {col}')
        print(f'✅ Добавлено: {col}')
    except sqlite3.OperationalError as e:
        if 'duplicate column name' in str(e):
            print(f'⚠️ Уже есть: {col}')
        else:
            print(f'❌ Ошибка: {e}')

conn.commit()
conn.close()
print('🎉 Готово! Теперь можно перезапустить бота.')