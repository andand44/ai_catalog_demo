import sqlite3
import os

DB_PATH = 'demo_catalog.db'

if os.path.exists(DB_PATH):
    os.remove(DB_PATH)

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Создаем структуру (упрощенная версия вашей)
c.executescript("""
    CREATE TABLE categories (id INTEGER PRIMARY KEY, parent_id INTEGER, name TEXT);
    CREATE TABLE product_groups (group_id INTEGER PRIMARY KEY, name TEXT, description TEXT, category_id INTEGER);
    CREATE TABLE variations (offer_id INTEGER PRIMARY KEY, group_id INTEGER, price INTEGER, available INTEGER, picture TEXT);
    CREATE TABLE attributes (offer_id INTEGER, name TEXT, value TEXT);
    CREATE TABLE all_images (offer_id INTEGER, url TEXT);
    CREATE TABLE bundle_items (bundle_offer_id INTEGER, component_offer_id INTEGER, quantity INTEGER, target_group_id INTEGER, picture TEXT);
    CREATE TABLE manufacturers (group_id INTEGER PRIMARY KEY, name TEXT, description TEXT);
    CREATE TABLE instructions (group_id INTEGER, name TEXT, url TEXT, size TEXT);
    CREATE TABLE tags (tag_id INTEGER PRIMARY KEY, name TEXT, code TEXT); -- ДОБАВИЛИ code
    CREATE TABLE product_tags (group_id INTEGER, tag_id INTEGER);
""")

# Добавляем тестовые данные
c.execute("INSERT INTO categories VALUES (1, 0, 'Тестовая категория')")
c.execute("INSERT INTO product_groups VALUES (100, 'Демо Шкаф', 'Описание шкафа', 1)")
c.execute("INSERT INTO product_groups VALUES (200, 'Демо Кухня', 'Описание кухни', 1)")

c.execute("INSERT INTO variations VALUES (1001, 100, 5000, 1, 'https://via.placeholder.com/600x400?text=Demo+Cabinet')")
c.execute("INSERT INTO variations VALUES (2001, 200, 25000, 1, 'https://via.placeholder.com/600x400?text=Demo+Kitchen')")

c.execute("INSERT INTO attributes VALUES (1001, 'Ширина', '60 см')")
c.execute("INSERT INTO attributes VALUES (2001, 'Ширина', '200 см')")

c.execute("INSERT INTO bundle_items VALUES (2001, 1001, 2, 100, 'https://via.placeholder.com/100x100')")

c.execute("INSERT INTO instructions VALUES (200, 'Инструкция по сборке', 'https://example.com/instruction.pdf', '1.5 Мб')")

# Добавляем тест для тегов (чтобы не падало)
c.execute("INSERT INTO tags VALUES (1, 'Собери в 3D-конструкторе', 'soberi-v-3d')")
c.execute("INSERT INTO product_tags VALUES (200, 1)")

conn.commit()
conn.close()
print("✅ Демо-база demo_catalog.db успешно создана!")