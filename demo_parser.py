from playwright.sync_api import sync_playwright
import sqlite3

def main():
    print("🕷️ Запуск демонстрационного парсера (тренажер quotes.toscrape.com)...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("http://quotes.toscrape.com/js/", wait_until="networkidle")
        
        quotes = page.query_selector_all(".quote")
        print(f"✅ Найдено {len(quotes)} цитат. Сохраняем...")
        
        conn = sqlite3.connect('demo_catalog.db')
        c = conn.cursor()
        
        for quote in quotes:
            text = quote.query_selector(".text").inner_text()
            author = quote.query_selector(".author").inner_text()
            
            # Сохраняем в нашу БД (для демонстрации)
            c.execute("INSERT INTO product_groups (name, description) VALUES (?, ?)", 
                      (author, text))
            
        conn.commit()
        conn.close()
        browser.close()
        print("✅ Данные сохранены в demo_catalog.db")

if __name__ == "__main__":
    main()