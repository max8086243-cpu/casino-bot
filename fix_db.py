import sqlite3

conn = sqlite3.connect('casino_xc.db')
cursor = conn.cursor()

# Проверяем и добавляем reg_date
try:
    cursor.execute('ALTER TABLE users ADD COLUMN reg_date TEXT')
    print('✅ reg_date добавлена')
except Exception as e:
    if 'duplicate column name' in str(e):
        print('⚠️ reg_date уже есть')
    else:
        print(f'❌ Ошибка reg_date: {e}')

# Проверяем и добавляем last_active
try:
    cursor.execute('ALTER TABLE users ADD COLUMN last_active TEXT')
    print('✅ last_active добавлена')
except Exception as e:
    if 'duplicate column name' in str(e):
        print('⚠️ last_active уже есть')
    else:
        print(f'❌ Ошибка last_active: {e}')

conn.commit()
conn.close()

print('🎉 Готово! Теперь перезапусти бота.')