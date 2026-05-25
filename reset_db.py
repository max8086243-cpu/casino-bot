import os
import sqlite3

# Удаляем старую базу
if os.path.exists('casino_xc.db'):
    os.remove('casino_xc.db')
    print('✅ Старая база данных удалена')

# Создаём новую
from database import init_db
init_db()
print('✅ Новая база данных создана со всеми колонками')
print('🎉 Теперь перезапусти бота!')