from flask import Flask, render_template, request, Response, send_file
from io import BytesIO
import urllib.request
import sqlite3
import json

app = Flask(__name__)
DB_PATH = 'demo_catalog.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/proxy_image')
def proxy_image():
    url = request.args.get('url')
    if not url: return "", 400
    try:
        req = urllib.request.Request(
            url, 
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://example.com/',  # <--- ЗАМЕНИЛИ ЗДЕСЬ
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8'
            }
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            img_data = response.read()
            mime_type = response.headers.get_content_type()
            return send_file(BytesIO(img_data), mimetype=mime_type)
    except Exception as e:
        # Если картинка битая, возвращаем 404
        return "", 404

def get_categories_tree():
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT id, parent_id, name FROM categories ORDER BY name")
    cats = [dict(row) for row in c.fetchall()]
    conn.close()
    
    tree = {}
    for cat in cats:
        tree[cat['id']] = cat
        tree[cat['id']]['children'] = []
        
    root_cats = []
    for cat in cats:
        if cat['parent_id'] and cat['parent_id'] in tree:
            tree[cat['parent_id']]['children'].append(cat)
        else:
            root_cats.append(cat)
    return root_cats

@app.route('/')
def index():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        SELECT g.group_id, g.name, MIN(v.price) as price, 
               COALESCE(
                   MAX(v.picture), 
                   (SELECT i.url FROM all_images i JOIN variations v2 ON i.offer_id = v2.offer_id WHERE v2.group_id = g.group_id LIMIT 1)
               ) as picture
        FROM product_groups g 
        JOIN variations v ON g.group_id = v.group_id 
        GROUP BY g.group_id
        ORDER BY RANDOM() LIMIT 20
    """)
    products = c.fetchall()
    conn.close()
    return render_template('section.html', products=products, categories=get_categories_tree(), current_cat=None)

@app.route('/category/<int:cat_id>')
def category(cat_id):
    conn = get_db()
    c = conn.cursor()
    
    def get_subcats(parent_id):
        subs = []
        c.execute("SELECT id FROM categories WHERE parent_id = ?", (parent_id,))
        for row in c.fetchall():
            subs.append(row['id'])
            subs.extend(get_subcats(row['id']))
        return subs
        
    cat_ids = [cat_id] + get_subcats(cat_id)
    placeholders = ','.join(['?'] * len(cat_ids))
    
    c.execute(f"""
        SELECT g.group_id, g.name, MIN(v.price) as price, 
               COALESCE(
                   MAX(v.picture), 
                   (SELECT i.url FROM all_images i JOIN variations v2 ON i.offer_id = v2.offer_id WHERE v2.group_id = g.group_id LIMIT 1)
               ) as picture
        FROM product_groups g 
        JOIN variations v ON g.group_id = v.group_id 
        WHERE g.category_id IN ({placeholders})
        GROUP BY g.group_id
    """, cat_ids)
    products = c.fetchall()
    
    c.execute("SELECT name FROM categories WHERE id = ?", (cat_id,))
    cat_name = c.fetchone()
    conn.close()
    
    return render_template('section.html', products=products, categories=get_categories_tree(), current_cat=cat_name['name'] if cat_name else '')

@app.route('/product/<int:group_id>')
def product(group_id):
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT * FROM product_groups WHERE group_id = ?", (group_id,))
    group = c.fetchone()
    if not group: return "Товар не найден", 404

    breadcrumb = None
    if group['category_id']:
        c.execute("SELECT name FROM categories WHERE id = ?", (group['category_id'],))
        row = c.fetchone()
        if row: breadcrumb = dict(row)['name']

    c.execute("SELECT * FROM variations WHERE group_id = ? ORDER BY offer_id", (group_id,))
    variations = [dict(row) for row in c.fetchall()]
    
    # 4. Характеристики
    c.execute("""
        SELECT a.name, a.value, v.offer_id
        FROM attributes a
        JOIN variations v ON a.offer_id = v.offer_id
        WHERE v.group_id = ?
    """, (group_id,))
    all_attrs = c.fetchall()
    general_attrs_dict = {}
    for row in all_attrs:
        name_lower = row['name'].strip().lower()
        if not any(x in name_lower for x in ['цвет', 'материал', 'коллекция', 'особенность', 'отделка']):
            general_attrs_dict[row['name'].strip()] = row['value'].strip()
            
    attrs = {}
    for row in all_attrs:
        oid = row['offer_id']
        if oid not in attrs:
            attrs[oid] = [{'name': k, 'value': v} for k, v in general_attrs_dict.items()]
        name_clean = row['name'].strip()
        val_clean = row['value'].strip()
        if name_clean in general_attrs_dict and general_attrs_dict[name_clean] == val_clean:
            continue
        if not any(x['name'] == name_clean and x['value'] == val_clean for x in attrs[oid]):
            attrs[oid].append({'name': name_clean, 'value': val_clean})
            
    for var in variations:
        var['attributes'] = attrs.get(var['offer_id'], [])

    # 5. Картинки (Вывод без дублей)
    c.execute("""
        SELECT i.offer_id, i.url 
        FROM all_images i
        JOIN variations v ON i.offer_id = v.offer_id
        WHERE v.group_id = ?
    """, (group_id,))
    images = {}
    for row in c.fetchall():
        oid = row['offer_id']
        url = row['url']
        if oid not in images: images[oid] = []
        if url not in images[oid]:
            images[oid].append(url)
            
    for var in variations:
        var_imgs = images.get(var['offer_id'], [])
        
        # Если в базе пусто, берем главную картинку этой вариации
        if not var_imgs and var.get('picture'):
            var_imgs = [var['picture']]
            
        var['images'] = var_imgs

    # 6. Комплекты (BOM)
    c.execute("""
        SELECT b.bundle_offer_id, b.component_offer_id, b.quantity, b.picture, b.target_group_id, COALESCE(g.name, 'Модуль') as name
        FROM bundle_items b
        LEFT JOIN product_groups g ON b.target_group_id = g.group_id
        JOIN variations v ON b.bundle_offer_id = v.offer_id
        WHERE v.group_id = ?
    """, (group_id,))
    
    raw_boms = c.fetchall()
    boms = {}
    
    for row in raw_boms:
        bid = row['bundle_offer_id']
        if bid not in boms: 
            boms[bid] = []
            
        item = dict(row)
        comp_offer_id = item['component_offer_id']
        
        # Достаем цвета для конкретной вариации модуля
        c.execute("SELECT value FROM attributes WHERE offer_id = ? AND name LIKE '%Цвет%'", (comp_offer_id,))
        color_rows = c.fetchall()
        color_values = [r['value'] for r in color_rows]
        
        # Убираем дубликаты и склеиваем
        unique_colors = list(dict.fromkeys(color_values))
        item['module_color'] = " / ".join(unique_colors) if unique_colors else ""
        
        boms[bid].append(item)
        
    general_bom = []
    for v_oid in variations:
        if v_oid['offer_id'] in boms:
            general_bom = boms[v_oid['offer_id']]
            break
            
    for var in variations:
        var_bom = boms.get(var['offer_id'], [])
        var['bom'] = var_bom if var_bom else general_bom

    # 7. Остальное
    c.execute("SELECT * FROM manufacturers WHERE group_id = ?", (group_id,))
    manufacturer = c.fetchone()
    c.execute("SELECT * FROM instructions WHERE group_id = ?", (group_id,))
    instructions = [dict(row) for row in c.fetchall()]
    c.execute("SELECT t.name, t.code FROM tags t JOIN product_tags pt ON t.tag_id = pt.tag_id WHERE pt.group_id = ?", (group_id,))
    tags = [dict(row) for row in c.fetchall()]
    
    # 8. В каких комплектах (гарнитурах) состоит этот товар?
    c.execute("""
        SELECT DISTINCT b.bundle_offer_id, v.group_id, g.name, v.picture
        FROM bundle_items b
        JOIN variations v ON b.bundle_offer_id = v.offer_id
        JOIN product_groups g ON v.group_id = g.group_id
        WHERE b.target_group_id = ?
    """, (group_id,))
    raw_kits = c.fetchall()
    
    parent_kits = []
    seen_groups = set()
    
    for row in raw_kits:
        gid = row['group_id']
        if gid in seen_groups:
            continue
        seen_groups.add(gid)
        
        kit = dict(row)
        offer_id = kit['bundle_offer_id']
        
        # ИСПРАВЛЕНИЕ: Берем ВСЕ цвета (и фасада, и корпуса) и склеиваем их
        c.execute("SELECT value FROM attributes WHERE offer_id = ? AND name LIKE '%Цвет%'", (offer_id,))
        color_rows = c.fetchall()
        color_values = [r['value'] for r in color_rows]
        
        # Убираем дубликаты (вдруг названия совпадают) и склеиваем через слэш
        unique_colors = list(dict.fromkeys(color_values))
        kit['variation_name'] = " / ".join(unique_colors) if unique_colors else ""
        
        # Картинка
        if not kit['picture']:
            c.execute("SELECT url FROM all_images WHERE offer_id = ? LIMIT 1", (offer_id,))
            img_row = c.fetchone()
            if img_row:
                kit['picture'] = img_row['url']
                
        parent_kits.append(kit)

    conn.close()

    data_json = json.dumps({
        'variations': variations, 
        'group': dict(group),
        'manufacturer': dict(manufacturer) if manufacturer else None,
        'instructions': instructions, 
        'tags': tags,
        'parent_kits': parent_kits # <--- ДОБАВИЛИ ЭТО
    }, ensure_ascii=False)

    return render_template('product.html', group=group, variations=variations, manufacturer=manufacturer,
                           instructions=instructions, tags=tags, data_json=data_json, breadcrumb=breadcrumb,
                           parent_kits=parent_kits)

if __name__ == '__main__':
    app.run(debug=True, port=5000)