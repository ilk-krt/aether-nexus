import json
import yfinance as yf
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

def get_usd_try():
    try: return float(yf.Ticker("TRY=X").history(period="1d")['Close'].iloc[-1])
    except: return 34.50

def get_tefas_price(fund_code):
    try:
        url = f"https://www.tefas.gov.tr/FonAnaliz.aspx?FonKod={fund_code}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.content, 'html.parser')
        price_str = soup.find('span', string='Son Fiyat').find_next_sibling('span').text
        return float(price_str.replace('.', '').replace(',', '.'))
    except: return 0.0

def run_bot():
    print(f"[{datetime.now()}] Gölge Bot Tetiklendi...")
    
    with open("my_assets.json", "r", encoding="utf-8") as f:
        portfolio = json.load(f)
        
    usd_try = get_usd_try()
    try:
        gold_oz = float(yf.Ticker("GC=F").history(period="1d")['Close'].iloc[-1])
    except:
        gold_oz = 2500.0
    gold_gram_try = (gold_oz / 31.1035) * usd_try
    
    updated_portfolio = []
    
    for item in portfolio:
        sym = item["symbol"]
        ptype = item["type"]
        current_price = item.get("current_price", 0.0)
        
        try:
            if ptype in ["US_STOCK", "TR_STOCK", "CRYPTO", "ETF"]:
                data = yf.Ticker(sym).history(period="1d")
                if not data.empty:
                    current_price = float(data['Close'].iloc[-1])
            elif ptype == "TEFAS":
                price = get_tefas_price(sym)
                if price > 0: current_price = price
            elif ptype == "GOLD":
                current_price = gold_gram_try if item["currency"] == "TRY" else gold_oz
        except Exception as e:
            print(f"Hata ({sym}): {e}")

        item["current_price"] = current_price
        updated_portfolio.append(item)
        print(f"OK: {sym} -> {current_price}")
        time.sleep(0.5)

    data_to_save = {
        "usd_try": usd_try,
        "last_sync": datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "assets": updated_portfolio
    }
    
    with open("portfolio_db.json", "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, indent=4, ensure_ascii=False)

if __name__ == "__main__":
    run_bot()
