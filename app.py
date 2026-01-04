import json
import uuid
import datetime
import re
import random
import os
import time
import sys

# תיקון עברית בווינדוס
sys.stdout.reconfigure(encoding='utf-8')

from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI 
from woocommerce import API
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# ייבוא המוח של הבוט
from prompts import SYSTEM_PROMPT

app = Flask(__name__)
CORS(app)

# ================= הגדרות אבטחה והגבלה =================
MAX_INPUT_LENGTH = 500  
DAILY_LIMIT = "200 per day" 
MINUTE_LIMIT = "60 per minute" 

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# ================= הגדרות ומפתחות =================
OPENAI_API_KEY = "X" 
OPENAI_MODEL = "gpt-4o-mini" 

# פרטי החנות שלך (בשביל החיבור למוצרים)
WC_URL = "https://YOUR-WEBSITE.co.il" # <--- כתובת האתר שלך
WC_KEY = "X"     # <--- Consumer Key
WC_SECRET = "X"  # <--- Consumer Secret

# ================= אתחול שירותים =================
client = OpenAI(api_key=OPENAI_API_KEY)

wcapi = API(
    url=WC_URL, consumer_key=WC_KEY, consumer_secret=WC_SECRET,
    version="wc/v3", timeout=60 
)

# ================= טעינת המוח (ID Mapping) =================
def load_id_mapping():
    try:
        with open("id_mapping.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"⚠️ Warning: id_mapping.json not found. ({e})")
        return {"categories": {}, "tags": {}}

ID_MAPPING = load_id_mapping()
CAT_NAMES_LIST = ", ".join(ID_MAPPING.get("categories", {}).keys())
TAG_NAMES_LIST = ", ".join(ID_MAPPING.get("tags", {}).keys())

# ================= המאגר החכם =================
SMART_CATALOG = [] 
STORE_METADATA = {
    "categories": [],
    "best_sellers_ids": [], 
    "best_sellers_names": []
}

# מילון מושגים (fallback logic)
CONCEPT_SYNONYMS = {
    "צבעוני": ["פופ ארט", "גרפיטי", "אבסטרקט", "סטריט ארט", "צבעוני", "קולאז", "street art", "pop art", "צבעים", "שמח", "צבע", "colorful"],
    "שמח": ["פופ ארט", "חיות", "צבעוני", "חיוך", "קוף", "אופטימי"],
    "רגוע": ["נוף", "ים", "חוף", "שקיעה", "בז", "פסטל", "מינימליזם", "סקנדינבי", "שקט", "טבע", "בוהו", "boho", "calm"],
    "סולידי": ["שחור לבן", "מינימליזם", "גיאומטרי", "נקי", "קלאסי"],
    "יוקרתי": ["שחור וזהב", "מותגים", "זכוכית", "rolex", "gucci", "זהב", "יוקרה", "יוקרתי", "luxury", "black and gold"],
    "סלון": ["אבסטרקט", "נוף", "גדול", "סט", "שלושה חלקים", "סלון", "living room"],
    "חיות": ["חיות", "animals", "wildlife", "טבע"],
    "ילדים": ["אנימה", "חיות", "ספורט", "גיבורי על", "דיסני", "spiderman", "batman", "ילדים", "נוער", "kids"],
    "אנימה": ["אנימה", "anime", "מנגה", "דרגון בול", "נארוטו", "וואן פיס", "dragon ball", "naruto", "one piece"],
}

def initialize_store_context():
    print("🔄 Initializing Smart Catalog & Intelligence...")
    global SMART_CATALOG
    all_products = []
    page = 1
    try:
        while True:
            batch = wcapi.get("products", params={"per_page": 100, "page": page, "status": "publish"}).json()
            if not batch: break
            all_products.extend(batch)
            page += 1
            if len(all_products) >= 2000: break
        
        SMART_CATALOG = all_products
        print(f"✅ Catalog Loaded: {len(SMART_CATALOG)} products.")

        top_sellers_api = wcapi.get("products", params={"per_page": 20, "orderby": "popularity"}).json()
        STORE_METADATA["best_sellers_ids"] = [p['id'] for p in top_sellers_api]
        STORE_METADATA["best_sellers_names"] = [f"{p['name']}" for p in top_sellers_api[:5]]
        STORE_METADATA["categories"] = list(ID_MAPPING.get("categories", {}).keys())
    except Exception as e:
        print(f"⚠️ Error loading catalog: {e}")

def smart_search_products(query, page=1, limit=12):
    if not SMART_CATALOG: return []
    clean_query = query.lower().strip().replace('"', '').replace("'", "").replace("`", "")
    results = []
    query_words = clean_query.split()
    concept_terms = []
    for concept, synonyms in CONCEPT_SYNONYMS.items():
        if concept in clean_query: concept_terms.extend(synonyms)

    for p in SMART_CATALOG:
        score = 0
        p_name = p.get('name', '').lower()
        p_cats = " ".join([c['name'].lower() for c in p.get('categories', [])])
        p_tags = " ".join([t['name'].lower() for t in p.get('tags', [])])
        full_blob = f"{p_name} {p_cats} {p_tags}"
        
        for term in concept_terms:
            if term in full_blob: score += 10
        matched = 0
        for word in query_words:
            if len(word) < 2: continue 
            if word in full_blob:
                matched += 1
                if word in p_name: score += 30 
        if matched > 0:
            if matched == len(query_words) and len(query_words) > 1: score += 150 
            else: score += (matched * 20)
        if score > 0:
            if p['id'] in STORE_METADATA["best_sellers_ids"]: score += 10 
            results.append((score, p))
    
    results.sort(key=lambda x: x[0], reverse=True)
    start_idx = (page - 1) * limit
    return [item[1] for item in results[start_idx:start_idx + limit]]

# ניהול סשנים בזיכרון
USER_SESSIONS = {}

def log_conversation(session_id, user_msg, bot_msg, meta=None):
    try:
        log_entry = { "timestamp": datetime.datetime.now().isoformat(), "session_id": session_id, "user_message": user_msg, "bot_response": bot_msg, "meta": meta }
        file_path = "chat_logs.json"
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f: json.dump([], f)
        with open(file_path, 'r+', encoding='utf-8') as f:
            content = f.read().strip()
            data = json.loads(content) if content else []
            data.append(log_entry)
            f.seek(0); f.truncate(); json.dump(data, f, ensure_ascii=False, indent=2)
    except: pass

def save_lead(name, phone, context):
    try:
        file_path = "leads.json"
        clean_phone = re.sub(r'\D', '', phone)
        if not (len(clean_phone) == 10 and clean_phone.startswith('05')): return False
        
        leads = []
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if content: leads = json.loads(content)
            except: leads = []

        for lead in leads:
            if re.sub(r'\D', '', lead.get('phone', '')) == clean_phone: return False

        leads.append({ "timestamp": datetime.datetime.now().isoformat(), "phone": phone, "name": name, "context": context })
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(leads, f, ensure_ascii=False, indent=2)
        print(f"✅ SYSTEM: Lead saved: {phone}")
        return True
    except Exception as e:
        print(f"❌ ERROR saving lead: {e}")
        return False

def get_products_html(query, session_data):
    clean_query = query.split("<")[0].replace('`', '').replace("'", "").replace('"', "").replace('.', '').strip()
    products = []
    
    # שימוש בעמוד הנוכחי של הסשן
    current_page = session_data.get('page', 1)

    # 1. חיפוש לפי ID (עם פגינציה)
    cat_id = ID_MAPPING.get("categories", {}).get(clean_query)
    tag_id = ID_MAPPING.get("tags", {}).get(clean_query)

    if cat_id:
        print(f"🎯 Direct Category Match: {clean_query} -> ID {cat_id} (Page {current_page})")
        try: products = wcapi.get("products", params={"category": cat_id, "per_page": 12, "page": current_page, "status": "publish"}).json()
        except: pass
    elif tag_id:
        print(f"🎯 Direct Tag Match: {clean_query} -> ID {tag_id} (Page {current_page})")
        try: products = wcapi.get("products", params={"tag": tag_id, "per_page": 12, "page": current_page, "status": "publish"}).json()
        except: pass

    # 2. חיפוש חכם בזיכרון או רנדומלי
    if not products:
        stop_words = ["משהו", "כזה", "בשביל", "של", "את", "על", "עם", "תמונה", "תמונות", "ציור"]
        words = clean_query.split()
        filtered_words = [w for w in words if w not in stop_words]
        final_text_query = " ".join(filtered_words) if filtered_words else clean_query
        
        print(f"🔍 Smart Text Search: {final_text_query} (Page {current_page})")
        
        if final_text_query.upper() in ["MORE", "עוד", "נוספים"]:
             # אם המשתמש רוצה "עוד", נביא מדגם רחב מהקטלוג בזיכרון
             candidates = random.sample(SMART_CATALOG, min(len(SMART_CATALOG), 60))
             products = candidates
        else:
             products = smart_search_products(final_text_query, page=current_page, limit=12)

    # === מניעת לופים: סינון מוצרים שכבר נצפו ===
    seen = session_data.get('seen_ids', set())
    new_products = [p for p in products if p['id'] not in seen]
    
    # אם שלפנו מוצרים אבל כולם כבר נראו -> נקדם עמוד וננסה שוב (רקורסיה)
    # הגבלה ל-5 עומק רקורסיה כדי לא להיתקע
    if products and not new_products:
        print("⚠️ All fetched products seen. Advancing page...")
        session_data['page'] += 1
        if session_data['page'] > 10: return None # עצירת חירום
        return get_products_html(query, session_data)

    products = new_products
    
    if not products: return None

    # עדכון המוצרים שנצפו והעמוד הבא
    session_data['page'] += 1
    for p in products:
        session_data.setdefault('seen_ids', set()).add(p['id'])

    # 3. יצירת HTML (בחירת מגוון)
    candidates = { "glass": [], "framed": [], "canvas": [], "other": [] }
    for p in products:
        name = p.get('name', '')
        design_match = re.search(r'דגם\s*(\d+)', name)
        design_id = design_match.group(1) if design_match else name 
        item_data = {"product": p, "design_id": design_id}
        
        if "זכוכית" in name: candidates["glass"].append(item_data)
        elif "מסגרת" in name or "ממוסגרת" in name: candidates["framed"].append(item_data)
        elif "קנבס" in name: candidates["canvas"].append(item_data)
        else: candidates["other"].append(item_data)

    selected_items = []
    used_ids = set()
    types_order = ["glass", "framed", "canvas"]
    
    # ניסיון לקחת אחד מכל סוג
    for t in types_order:
        for item in candidates[t]:
            if item["design_id"] not in used_ids:
                selected_items.append(item["product"])
                used_ids.add(item["design_id"])
                break 
    
    # השלמה ל-3 מוצרים
    remaining = candidates["glass"] + candidates["framed"] + candidates["canvas"] + candidates["other"]
    while len(selected_items) < 3 and remaining:
        item = remaining.pop(0)
        if item["design_id"] not in used_ids: 
             selected_items.append(item["product"])
             used_ids.add(item["design_id"])
        elif len(selected_items) == 0:
             selected_items.append(item["product"])

    cards_html = "<div class='products-grid'>"
    for p in selected_items:
        name = p.get('name', 'יצירת אומנות')
        raw_price = p.get('price', '')
        price_display = f"החל מ-{raw_price} ₪" if raw_price else "מחיר באתר"
        link = p.get('permalink', '#')
        img_src = p['images'][0]['src'] if p.get('images') else "https://placehold.co/400x400?text=No+Image"
        
        cards_html += f"""
        <div class="product-card">
            <img src='{img_src}' alt='{name}'>
            <div class="product-info">
                <div class="product-title">{name}</div>
                <div class="product-price">{price_display}</div>
                <a href="{link}" target="_blank" class="buy-btn">לרכישה מהירה 🛒</a>
            </div>
        </div>
        """
    cards_html += "</div>"
    return cards_html

@app.route('/chat', methods=['POST'])
@limiter.limit(MINUTE_LIMIT) 
@limiter.limit(DAILY_LIMIT) 
def chat():
    data = request.json
    user_message = data.get('message') or ""
    
    # הגנה מפני קריסת הטסטר על היסטוריה ריקה
    history = data.get('history')
    if not isinstance(history, list): history = []
    
    session_id = data.get('sessionId')

    if len(user_message) > MAX_INPUT_LENGTH:
        return jsonify({"reply": "ההודעה ארוכה מדי."})

    if not session_id: return jsonify({"error": "No Session ID"}), 400
    
    # אתחול סשן עם סט "מוצרים שנצפו" למניעת כפילויות
    if session_id not in USER_SESSIONS: 
        USER_SESSIONS[session_id] = {
            "page": 1, 
            "last_query": None, 
            "seen_ids": set()
        }
    
    session_data = USER_SESSIONS[session_id]
    
    # שמירת ליד ישיר
    direct_phone_match = re.search(r'05\d[- ]?\d{3}[- ]?\d{4}', user_message)
    if direct_phone_match:
        save_lead("User (Direct)", direct_phone_match.group(0), user_message)
    
    # בניית הפרומפט
    recent_history = history[-10:] if len(history) > 10 else history
    dynamic_context = f"""
    Available Categories: {CAT_NAMES_LIST}
    Available Style Tags: {TAG_NAMES_LIST}
    Top Sellers: {", ".join(STORE_METADATA['best_sellers_names'])}
    """
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT + dynamic_context}]
    for msg in recent_history:
        # המרת תוכן לסטרינג למקרה של תקלה + ניקוי HTML
        content_str = str(msg.get('content', ''))
        clean_content = re.sub(r'<[^>]+>', '', content_str)
        messages.append({"role": "user" if msg.get('sender')=='user' else "assistant", "content": clean_content})
    messages.append({"role": "user", "content": user_message})

    try:
        completion = client.chat.completions.create(model=OPENAI_MODEL, messages=messages, temperature=0.5, max_tokens=300)
        bot_response = completion.choices[0].message.content.strip()
        
        # === הגנה מפני הזיות: ניקוי אגרסיבי ===
        if ("<div" in bot_response or "<img" in bot_response) and "SEARCH_ACTION" not in bot_response:
             bot_response = re.sub(r'<[^>]+>', '', bot_response) 
             bot_response = f"SEARCH_ACTION: {user_message}"

        bot_response = bot_response.replace("```html", "").replace("```", "").strip()
        print(f"🤖 AI: {bot_response}") 
        
        final_html = ""
        
        # ניהול ליד מה-AI
        lead_match = re.search(r"SAVE_LEAD:?\s*([\d\-\s]+)", bot_response, re.IGNORECASE)
        if lead_match:
            save_lead("User (AI)", lead_match.group(1), user_message)
            bot_response = bot_response.replace(lead_match.group(0), "").replace("SAVE_LEAD:", "").strip()
        
        if not bot_response: bot_response = "רשמתי, תודה!"

        # ניהול חיפוש
        search_match = re.search(r"SEARCH_ACTION:\s*(.+)", bot_response)
        if search_match:
            raw_query = search_match.group(1).strip()
            query = raw_query.split('\n')[0].replace('`', '').replace("'", "").replace('"', "").strip()
            
            last_q = session_data.get('last_query')
            if any(k in query.upper() for k in ["MORE", "עוד", "נוספים"]) and last_q:
                query = last_q
            elif query != last_q:
                session_data['last_query'] = query
                session_data['page'] = 1 
                # אם מחליפים שאילתה, מנקים את רשימת הנצפים כדי לאפשר חזרה למוצרים
                session_data['seen_ids'] = set()
            
            products_html = get_products_html(query, session_data)
            text_part = bot_response.split("SEARCH_ACTION")[0].strip()
            if not text_part: text_part = "הנה מה שמצאתי:"

            if products_html: final_html = f"{text_part}<br>{products_html}"
            else: final_html = f"חיפשתי '{query}' אך לא מצאתי תוצאות מדויקות. נסה סגנון אחר?"
        else:
            final_html = bot_response

        log_conversation(session_id, user_message, final_html, meta={"has_products": bool(search_match)})
        return jsonify({"reply": final_html})

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        return jsonify({"reply": "סליחה, נתקלתי בבעיה רגעית. אפשר לנסות שוב?"}), 500

if __name__ == '__main__':
    initialize_store_context()
    print(f"🚀 ArteryBot V4.2 (Anti-Loop & Stable) Running...")
    app.run(port=5000, debug=True)