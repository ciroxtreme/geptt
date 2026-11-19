import os
import sys
import time
import json
import urllib.request
import urllib.parse
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
TARGET_EMAIL = os.environ.get("TARGET_EMAIL", "tuanciroxtreme@gmail.com")
PROMPT_ASK = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else os.environ.get("PROMPT_ASK", "")

def send_telegram_msg(text: str):
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID):
        print(f"[TG] {text}")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = urllib.parse.urlencode({
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"[TG Error] {e}")

def send_telegram_photo(photo_path: str, caption: str = ""):
    if not (TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID) or not os.path.exists(photo_path):
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    
    with open(photo_path, "rb") as f:
        photo_bytes = f.read()

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
        f"{TELEGRAM_CHAT_ID}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="caption"\r\n\r\n'
        f"{caption}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="photo"; filename="shot.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode("utf-8") + photo_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    req = urllib.request.Request(url, data=body, headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        urllib.request.urlopen(req, timeout=15)
    except Exception as e:
        print(f"[TG Photo Error] {e}")

def wait_for_telegram_otp(timeout_sec: int = 180) -> str:
    """Mendengarkan chat Telegram Tuan Ciro secara realtime untuk menangkap kode OTP."""
    send_telegram_msg(f"⏳ <b>[STANDBY OTP]</b> Bot menunggu Tuan Ciro mengirimkan kode OTP di chat ini (Batas waktu: {timeout_sec} detik)...")
    start_time = time.time()
    last_update_id = 0
    
    try:
        init_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        init_req = urllib.request.urlopen(init_url, timeout=10)
        init_data = json.loads(init_req.read().decode())
        if init_data.get("result"):
            last_update_id = init_data["result"][-1]["update_id"]
    except Exception as e:
        print(f"Notice init getUpdates: {e}")

    while time.time() - start_time < timeout_sec:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=5"
            req = urllib.request.urlopen(url, timeout=10)
            data = json.loads(req.read().decode())
            for upd in data.get("result", []):
                last_update_id = upd["update_id"]
                msg = upd.get("message", {})
                sender = str(msg.get("chat", {}).get("id"))
                if sender == str(TELEGRAM_CHAT_ID):
                    text = msg.get("text", "").strip()
                    import re
                    digits = re.findall(r"\b\d{6}\b", text)
                    if digits:
                        send_telegram_msg(f"🎯 <b>[OTP DITERIMA!]</b> Kode {digits[0]} berhasil ditangkap!")
                        return digits[0]
                    pure_digits = re.sub(r"\D", "", text)
                    if len(pure_digits) >= 6:
                        code = pure_digits[:6]
                        send_telegram_msg(f"🎯 <b>[OTP DITERIMA!]</b> Kode {code} berhasil ditangkap!")
                        return code
        except Exception as e:
            print(f"Polling update error: {e}")
        time.sleep(2)
        
    send_telegram_msg("❌ <b>[TIMEOUT]</b> Waktu tunggu OTP (3 menit) habis.")
    return ""

def main():
    print("=== START CHATGPT LOGIN CHALLENGE & RELAY ===")
    send_telegram_msg(f"🚀 <b>[TAHAP 1/5]</b> Menjalankan Stealth Chromium Browser menuju ChatGPT...")

    session_file = "session_chatgpt.json"
    session_loaded = False
    initial_cookies = []

    if os.path.exists(session_file):
        try:
            with open(session_file, "r") as f:
                initial_cookies = json.load(f)
                if initial_cookies:
                    session_loaded = True
                    print(f"Loaded {len(initial_cookies)} cookies from {session_file}")
        except Exception as e:
            print(f"Failed to load session: {e}")

    with Stealth().use_sync(sync_playwright()) as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-infobars",
                "--window-size=1280,900"
            ]
        )
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-US"
        )
        
        if session_loaded and initial_cookies:
            try:
                context.add_cookies(initial_cookies)
                print("Injected existing cookies into browser context.")
            except Exception as e:
                print(f"Inject cookie error: {e}")

        page = context.new_page()

        # Step 1: Kunjungi ChatGPT
        page.goto("https://chatgpt.com/", timeout=45000, wait_until="load")
        time.sleep(5)
        
        page.screenshot(path="01_chatgpt_home.png")
        send_telegram_photo("01_chatgpt_home.png", "📸 <b>[TAHAP 1/5] Halaman Utama ChatGPT</b>\nStatus awal saat browser terbuka.")

        # Cek apakah sudah login
        is_logged_in = False
        try:
            composer = page.locator("#prompt-textarea, textarea[placeholder*='Message' i], textarea[placeholder*='Kirim pesan' i]")
            if composer.count() > 0 and composer.first.is_visible(timeout=5000):
                is_logged_in = True
        except Exception:
            pass

        if is_logged_in:
            print("Already logged in via session cookies!")
            send_telegram_msg("🎉 <b>Sesi Aktif Ditemukan!</b> Sudah langsung berada di dalam dashboard chat.")
            if PROMPT_ASK:
                from chat_engine import send_prompt_and_extract_answer
                ans = send_prompt_and_extract_answer(page, PROMPT_ASK)
                send_telegram_msg(f"✨ <b>[JAWABAN CHATGPT]:</b>\n\n{ans}")
            return

        # Step 2: Klik Tombol Log in
        print("Mencari tombol Log in...")
        login_btn = None
        selectors = [
            "button:has-text('Log in')",
            "button:has-text('Masuk')",
            "a:has-text('Log in')",
            "a:has-text('Masuk')",
            "[data-testid='login-button']"
        ]
        for sel in selectors:
            try:
                loc = page.locator(sel)
                if loc.count() > 0 and loc.first.is_visible(timeout=3000):
                    login_btn = loc.first
                    break
            except Exception:
                pass

        if login_btn:
            login_btn.click()
            time.sleep(6)
        else:
            page.goto("https://chatgpt.com/auth/login", timeout=30000, wait_until="load")
            time.sleep(5)

        page.screenshot(path="02_login_options.png")
        send_telegram_photo("02_login_options.png", "📸 <b>[TAHAP 2/5] Menu Opsi Login ChatGPT</b>")

        # Step 3: Isi Email
        email_input = None
        email_selectors = [
            "input[name='email']",
            "input[type='email']",
            "input[id*='email' i]",
            "input[placeholder*='email' i]"
        ]
        for esel in email_selectors:
            try:
                eloc = page.locator(esel)
                if eloc.count() > 0 and eloc.first.is_visible(timeout=4000):
                    email_input = eloc.first
                    break
            except Exception:
                pass

        if not email_input:
            try:
                cont_email = page.locator("button:has-text('email' i)")
                if cont_email.count() > 0 and cont_email.first.is_visible(timeout=3000):
                    cont_email.first.click()
                    time.sleep(3)
                    for esel in email_selectors:
                        eloc = page.locator(esel)
                        if eloc.count() > 0 and eloc.first.is_visible(timeout=3000):
                            email_input = eloc.first
                            break
            except Exception:
                pass

        if not email_input:
            page.screenshot(path="err_no_email_box.png")
            send_telegram_photo("err_no_email_box.png", "❌ <b>[GAGAL TAHAP 2]</b> Kolom email tidak ditemukan di layar. Periksa bukti foto di atas.")
            print("Error: email input not found")
            return

        print(f"Mengisi email: {TARGET_EMAIL}")
        email_input.fill(TARGET_EMAIL)
        time.sleep(1)

        page.screenshot(path="03_email_filled.png")
        send_telegram_photo("03_email_filled.png", f"📸 <b>[TAHAP 3/5] Email {TARGET_EMAIL} Terisi</b>\nMenekan tombol Continue...")

        # Tekan Continue / Lanjutkan
        submit_btn = None
        for bsel in ["button[type='submit']", "button:has-text('Continue')", "button:has-text('Lanjutkan')", "button:has-text('Next')"]:
            try:
                bloc = page.locator(bsel)
                if bloc.count() > 0 and bloc.first.is_visible(timeout=3000):
                    submit_btn = bloc.first
                    break
            except Exception:
                pass

        if submit_btn:
            submit_btn.click()
        else:
            page.keyboard.press("Enter")

        time.sleep(7)

        page.screenshot(path="04_after_email_submit.png")
        send_telegram_photo("04_after_email_submit.png", "📸 <b>[TAHAP 4/5] Status Setelah Kirim Email</b>\nMemeriksa apakah form OTP atau challenge muncul...")

        # Step 4: Cek form OTP / Kode
        otp_field = None
        otp_selectors = [
            "input[name='code']",
            "input[autocomplete='one-time-code']",
            "input[placeholder*='code' i]",
            "input[placeholder*='kode' i]",
            "input[maxlength='1']",
            "input[type='number']",
            "input[type='tel']"
        ]
        for osel in otp_selectors:
            try:
                oloc = page.locator(osel)
                if oloc.count() > 0 and oloc.first.is_visible(timeout=5000):
                    otp_field = oloc
                    break
            except Exception:
                pass

        if not otp_field:
            try:
                send_code_btn = page.locator("button:has-text('code' i), a:has-text('code' i), button:has-text('login code' i)")
                if send_code_btn.count() > 0 and send_code_btn.first.is_visible(timeout=3000):
                    send_code_btn.first.click()
                    time.sleep(5)
                    page.screenshot(path="04_after_email_submit.png")
                    for osel in otp_selectors:
                        oloc = page.locator(osel)
                        if oloc.count() > 0 and oloc.first.is_visible(timeout=3000):
                            otp_field = oloc
                            break
            except Exception:
                pass

        if not otp_field:
            send_telegram_photo("04_after_email_submit.png", "⚠️ <b>[PERHATIAN]</b> Form kode OTP belum terdeteksi. Silakan amati screenshot bukti di atas apakah meminta password atau terkena verifikasi lain.")
            print("OTP field not visible")
            return

        send_telegram_photo("04_after_email_submit.png", "🔑 <b>[FORM OTP DITEMUKAN!]</b>\nOpenAI telah mengirimkan kode OTP ke email Tuan Ciro. Silakan balas chat ini dengan angka OTP-nya!")

        otp_code = wait_for_telegram_otp(timeout_sec=180)
        if not otp_code:
            print("No OTP received, exiting.")
            return

        print(f"Memasukkan OTP: {otp_code}")
        send_telegram_msg(f"✍️ <b>Memasukkan OTP {otp_code}...</b>")

        if otp_field.count() >= len(otp_code):
            for i, char in enumerate(otp_code):
                otp_field.nth(i).fill(char)
                time.sleep(0.15)
        else:
            otp_field.first.fill(otp_code)

        time.sleep(1)
        page.keyboard.press("Enter")
        time.sleep(10)

        page.screenshot(path="05_final_status.png")

        final_ok = False
        try:
            final_composer = page.locator("#prompt-textarea, textarea[placeholder*='Message' i], textarea[placeholder*='Kirim pesan' i]")
            if final_composer.count() > 0 and final_composer.first.is_visible(timeout=8000):
                final_ok = True
        except Exception:
            pass

        if final_ok or ("chatgpt.com" in page.url and "/auth/" not in page.url):
            send_telegram_photo("05_final_status.png", "🎉🎉 <b>[LOGIN SUKSES RESMI & TERBUKTI!]</b>\nBrowser telah berhasil masuk ke dashboard ChatGPT!")
            cookies = context.cookies()
            with open(session_file, "w") as f:
                json.dump(cookies, f, indent=2)
            send_telegram_msg(f"🍪 <b>{len(cookies)} Session Cookies Berhasil Diamankan!</b>")

            if PROMPT_ASK:
                from chat_engine import send_prompt_and_extract_answer
                ans = send_prompt_and_extract_answer(page, PROMPT_ASK)
                send_telegram_msg(f"✨ <b>[JAWABAN CHATGPT]:</b>\n\n{ans}")
        else:
            send_telegram_photo("05_final_status.png", "❌ <b>[BELUM BERHASIL LOGIN]</b>\nSetelah memasukkan OTP, layar belum masuk ke dashboard ChatGPT. Lihat bukti foto di atas.")

if __name__ == "__main__":
    main()
