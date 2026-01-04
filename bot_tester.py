import requests
import json
import time
import uuid
import sys
from colorama import init, Fore, Style

# תיקון תצוגת עברית בווינדוס
sys.stdout.reconfigure(encoding='utf-8')

# אתחול צבעים לטרמינל
init(autoreset=True)

# ================= הגדרות =================
BASE_URL = "http://localhost:5000/chat"
SESSION_ID = f"test_session_{uuid.uuid4().hex[:8]}"

def print_header(text):
    print(f"\n{Fore.MAGENTA}{'='*60}")
    print(f"{Fore.MAGENTA}{text.center(60)}")
    print(f"{Fore.MAGENTA}{'='*60}{Style.RESET_ALL}")

def run_test(test_name, message, expected_content=None, unexpected_content=None, history=[]):
    """
    פונקציה גנרית שמריצה טסט בודד ומנתחת את התוצאה
    """
    print(f"{Fore.CYAN}🧪 הרצת בדיקה: {Style.BRIGHT}{test_name}")
    print(f"   📤 שולח: {message[:100]}..." if len(message) > 100 else f"   📤 שולח: {message}")
    
    start_time = time.time()
    
    try:
        payload = {
            "message": message,
            "history": history,
            "sessionId": SESSION_ID
        }
        
        response = requests.post(BASE_URL, json=payload, timeout=20)
        response_time = time.time() - start_time
        
        if response.status_code != 200:
            if response.status_code == 429:
                print(f"   {Fore.YELLOW}⚠️ נחסם עקב Rate Limit (תקין לבדיקות עומס)")
            else:
                print(f"   {Fore.RED}❌ נכשל! שגיאת שרת: {response.status_code}")
            return None

        data = response.json()
        reply = data.get('reply', '')
        
        # --- ניתוח התוצאות ---
        passed = True
        failure_reasons = []

        # 1. בדיקת תוכן מצופה
        if expected_content:
            if isinstance(expected_content, list):
                if not any(x in reply for x in expected_content):
                    passed = False
                    failure_reasons.append(f"אף אחד מהביטויים לא נמצא: {expected_content}")
            elif expected_content not in reply:
                passed = False
                failure_reasons.append(f"לא נמצא התוכן המצופה: '{expected_content}'")

        # 2. בדיקת תוכן אסור
        if unexpected_content:
            check_list = unexpected_content if isinstance(unexpected_content, list) else [unexpected_content]
            for content in check_list:
                if content in reply:
                    passed = False
                    failure_reasons.append(f"נמצא תוכן אסור: '{content}'")

        # --- סיכום הטסט ---
        if passed:
            print(f"   {Fore.GREEN}✅ עבר בהצלחה {Style.DIM}({response_time:.2f}s)")
            # עדכון ההיסטוריה
            if "חסימת" not in test_name:
                history.append({"sender": "user", "content": message})
                history.append({"sender": "bot", "content": reply})
            return history # מחזירים את ההיסטוריה המעודכנת
        else:
            print(f"   {Fore.RED}❌ נכשל!")
            for reason in failure_reasons:
                print(f"   {Fore.YELLOW}סיבה: {reason}")
            print(f"   🤖 תשובת הבוט: {reply[:150]}...") 
            return None # מחזירים None במקרה כישלון

    except requests.exceptions.ConnectionError:
        print(f"   {Fore.RED}❌ שגיאה: השרת לא מגיב. האם app.py רץ?")
        return None
    except Exception as e:
        print(f"   {Fore.RED}❌ שגיאה קריטית בטסטר: {e}")
        return None

def main():
    print_header(f"🚀 BusinessBot V4.0 - בדיקות אינטגרציה מקיפות")
    print(f"Session ID: {SESSION_ID}\n")
    
    history = []

    # פונקציית עזר לניהול ההיסטוריה בצורה בטוחה
    def execute_step(test_func_result):
        nonlocal history
        if test_func_result is not None:
            history = test_func_result
        else:
            print(f"{Fore.RED}⚠️ הטסט נכשל, אך ממשיכים לטסט הבא עם ההיסטוריה הישנה...")

    # ==========================
    # חלק 1: בדיקות בסיסיות
    # ==========================
    execute_step(run_test(
        test_name="בדיקת שפיות (Sanity)",
        message="מי אתה ומה אתה מוכר?",  
        expected_content=["ארטרי", "Business"], 
        history=history
    ))

    # ==========================
    # חלק 2: המוח החדש (ID Mapping)
    # ==========================
    execute_step(run_test(
        test_name="🔍 זיהוי קטגוריה חכמה (ID Mapping)",
        message="בא לי לראות תמונות אנימה",
        expected_content="product-card", 
        history=history
    ))

    execute_step(run_test(
        test_name="🏷️ זיהוי תגית חכמה (Style Tags)",
        message="אני מחפש משהו בסגנון יוקרתי לבית",
        expected_content="product-card", 
        history=history
    ))

    execute_step(run_test(
        test_name="🔄 בדיקת הקשר ודפדוף (More)",
        message="תראה לי עוד תוצאות כאלה",
        expected_content="product-card", 
        history=history
    ))

    # ==========================
    # חלק 3: אבטחה ומניעת הזיות
    # ==========================
    print_header("🛡️ בדיקות אבטחה והגנה")

    # תיקון: הסרנו את "<div" מרשימת האסורים, כי כרטיסי מוצר מכילים div וזה תקין!
    # אנחנו רק רוצים לוודא שאין ```html שמעיד על קוד גולמי
    execute_step(run_test(
        test_name="🔒 מניעת הזיות (Hallucination Check)",
        message="נו תשלח כבר", 
        expected_content="product-card", 
        unexpected_content=["```html"], 
        history=history
    ))

    execute_step(run_test(
        test_name="🛑 חסימת הודעה ארוכה (Input Validation)",
        message="בלה " * 200,
        expected_content="ארוכה מדי", 
        unexpected_content="product-card", 
        history=history
    ))

    # ==========================
    # חלק 4: לידים (CRM)
    # ==========================
    print_header("📞 בדיקות מערכת לידים")

    execute_step(run_test(
        test_name="📝 שמירת ליד תקין",
        message="אשמח שתחזרו אליי למספר 054-1234567",
        expected_content="רשמתי", 
        history=history
    ))

    execute_step(run_test(
        test_name="♻️ מניעת ליד כפול",
        message="בעצם זה המספר שלי 054-1234567, תרשום",
        expected_content="רשמתי", 
        history=history
    ))

    print_header("✨ כל הבדיקות הסתיימו! ✨")

if __name__ == "__main__":

    main()
