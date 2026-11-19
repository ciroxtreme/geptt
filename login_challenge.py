import os
import sys
import time
import json
import socket
import urllib.request
import urllib.parse
import requests
from playwright.sync_api import sync_playwright
from playwright_stealth import Stealth

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "1936436999")
TARGET_EMAIL = os.environ.get("TARGET_EMAIL", "tuanciroxtreme@gmail.com")
PROMPT_ASK = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PROMPT_ASK", "")

def get_browser_proxy():
    """Cek apakah Cloudflare WARP proxy aktif di port 40000."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(("127.0.0.1", 40000))
        s.close()
        print("✅ Detected Cloudflare WARP SOCKS5 proxy on 127.0.0.1:40000")
        return {"server": "socks5://127.0.0.1:40000"}
    except Exception:
        print("⚠️ WARP proxy on port 40000 not reachable, using direct network.")
        return None

def send_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN:
        print(f"[TELEGRAM SKIP]: {text}")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Telegram send error: {e}")

def send_telegram_photo(photo_path: str, caption: str = ""):
    if not TELEGRAM_BOT_TOKEN:
        print(f"[TELEGRAM PHOTO SKIP]: {caption}")
        return
    if not os.path.exists(photo_path):
        print(f"[PHOTO NOT FOUND]: {photo_path}")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    try:
        with open(photo_path, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": TELEGRAM_CHAT_ID, "caption": caption, "parse_mode": "HTML"}
            requests.post(url, data=data, files=files, timeout=30)
    except Exception as e:
        print(f"Telegram photo send error: {e}")

def wait_and_solve_cloudflare(page, max_wait_sec=25):
    """
    SOP Anti-Cloudflare dari repo xtt:
    Deteksi apakah ada 'challenges.cloudflare.com', 'Just a moment', atau checkbox Turnstile.
    Otomatis klik checkbox secara human-like.
    """
    print("Mengecek proteksi Cloudflare...")
    for sec in range(1, max_wait_sec + 1):
        time.sleep(1)
        title = ""
        try:
            title = (page.title() or "").lower()
        except Exception:
            pass
        body = ""
        try:
            body = (page.locator("body").inner_text() or "").lower()
        except Exception:
            pass

        content = ""
        try:
            content = (page.content() or "").lower()
        except Exception:
            pass

        is_cf = (
            "just a moment" in title or
            "verify you are human" in body or
            "challenges.cloudflare.com" in content or
            "cf-turnstile" in content
        )

        if is_cf:
            print(f"[*] Terdeteksi Cloudflare Gate (detik ke-{sec}), mencari iframe checkbox...")
            try:
                for frame in page.frames:
                    if "challenges.cloudflare.com" in frame.url or "turnstile" in frame.url:
                        cb = frame.query_selector("input[type='checkbox'], #challenge-stage, .ctp-checkbox-label, div[id*='turnstile' i]")
                        if cb:
                            print("[*] Mengklik Turnstile checkbox secara natural...")
                            cb.click()
                            time.sleep(3)
                            break
            except Exception as e:
                print(f"Frame click notice: {e}")
        else:
            if sec >= 3:
                return True
    return False

def wait_for_telegram_otp(timeout_sec: int = 180) -> str:
    """Menunggu Tuan Ciro mengirimkan kode angka OTP ke Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        print("No telegram token, skipping OTP wait.")
        return ""

    print(f"[*] Menunggu balasan OTP dari Telegram Tuan Ciro (maksimal {timeout_sec} detik)...")
    base_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"

    # Dapatkan offset update terakhir agar tidak membaca chat lawas
    last_update_id = 0
    try:
        r = requests.get(base_url, timeout=10).json()
        if r.get("ok") and r.get("result"):
            last_update_id = r["result"][-1]["update_id"]
    except Exception as e:
        print(f"Initial getUpdates error: {e}")

    start_time = time.time()
    while time.time() - start_time < timeout_sec:
        time.sleep(3)
        try:
            params = {"offset": last_update_id + 1, "timeout": 5}
            r = requests.get(base_url, params=params, timeout=10).json()
            if not r.get("ok"):
                continue

            for update in r.get("result", []):
                last_update_id = max(last_update_id, update["update_id"])
                msg = update.get("message", {})
                chat_id = str(msg.get("chat", {}).get("id", ""))
                text = (msg.get("text", "") or "").strip()

                if chat_id == str(TELEGRAM_CHAT_ID) and text:
                    digits = "".join([c for c in text if c.isdigit()])
                    if len(digits) in [6, 8]:
                        print(f"✅ OTP diterima dari Tuan Ciro: {digits}")
                        send_telegram(f"👌 <b>Kode OTP Terdeteksi:</b> <code>{digits}</code>. Memasukkan ke halaman login...")
                        return digits
                    else:
                        print(f"Pesan teks diterima tapi bukan 6/8 digit OTP: {text}")
        except Exception as e:
            print(f"Polling OTP notice: {e}")

    send_telegram("⏱️ <b>Waktu tunggu OTP (3 menit) habis.</b> Tidak menerima kode verifikasi.")
    return ""

def main():
    print("=== START CHATGPT PLAYWRIGHT STEALTH & CLOUDFLARE WARP ENGINE ===")
    proxy_cfg = get_browser_proxy()
    proxy_label = "Cloudflare WARP SOCKS5 Tunnel (127.0.0.1:40000)" if proxy_cfg else "Direct Cloud IP"
    send_telegram(f"🚀 <b>[TAHAP 1/5]</b> Menjalankan Playwright Chromium via <b>{proxy_label}</b>...")

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
        browser_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--window-size=1280,900"
        ]

        launch_kwargs = {
            "headless": True,
            "args": browser_args
        }
        if proxy_cfg:
            launch_kwargs["proxy"] = proxy_cfg

        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
        )

        if session_loaded and initial_cookies:
            try:
                context.add_cookies(initial_cookies)
                print("Injected existing cookies into browser context.")
            except Exception as e:
                print(f"Inject cookie error: {e}")

        page = context.new_page()

        # Step 1: Buka ChatGPT
        print("Membuka ChatGPT...")
        page.goto("https://chatgpt.com/", timeout=45000, wait_until="load")
        time.sleep(4)
        wait_and_solve_cloudflare(page, max_wait_sec=15)

        page.screenshot(path="01_chatgpt_home.png")
        send_telegram_photo("01_chatgpt_home.png", "📸 <b>[TAHAP 1/5] Halaman Utama ChatGPT</b>\nStatus awal saat browser terbuka via WARP.")

        # Cek apakah sudah login
        is_logged_in = False
        try:
            composer = page.locator("#prompt-textarea, textarea[placeholder*='Message' i], textarea[placeholder*='Kirim pesan' i]")
            if composer.count() > 0 and composer.first.is_visible(timeout=5000):
                is_logged_in = True
        except Exception:
            pass

        # Tutup dialog modal onboarding jika ada (seperti You're all set)
        try:
            from chat_engine import dismiss_onboarding_dialogs
            dismiss_onboarding_dialogs(page)
        except Exception:
            pass

        # Cek ulang setelah dismiss modal
        try:
            composer = page.locator("#prompt-textarea, textarea[placeholder*='Message' i], textarea[placeholder*='Kirim pesan' i]")
            if composer.count() > 0 and composer.first.is_visible(timeout=5000):
                is_logged_in = True
        except Exception:
            pass

        if is_logged_in:
            send_telegram("🎉 <b>Sesi Aktif Ditemukan!</b> Sudah langsung berada di dashboard chat.")
            if PROMPT_ASK:
                from chat_engine import send_prompt_and_extract_answer
                ans = send_prompt_and_extract_answer(page, PROMPT_ASK)
                send_telegram(f"✨ <b>[JAWABAN CHATGPT]:</b>\n\n{ans}")
            browser.close()
            return

        # Step 2: Klik Log in
        login_btn = None
        for sel in ["button:has-text('Log in')", "button:has-text('Masuk')", "[data-testid='login-button']"]:
            try:
                loc = page.locator(sel)
                if loc.count() > 0 and loc.first.is_visible(timeout=3000):
                    login_btn = loc.first
                    break
            except Exception:
                pass

        if login_btn:
            login_btn.click()
            time.sleep(5)
        else:
            page.goto("https://chatgpt.com/auth/login", timeout=30000, wait_until="load")
            time.sleep(5)

        wait_and_solve_cloudflare(page, max_wait_sec=15)
        page.screenshot(path="02_login_options.png")
        send_telegram_photo("02_login_options.png", "📸 <b>[TAHAP 2/5] Menu Opsi Login ChatGPT</b>")

        # Step 3: Isi Email
        email_input = None
        for esel in ["input[name='email']", "input[type='email']", "input[id*='email' i]", "input[placeholder*='email' i]"]:
            try:
                eloc = page.locator(esel)
                if eloc.count() > 0 and eloc.first.is_visible(timeout=3000):
                    email_input = eloc.first
                    break
            except Exception:
                pass

        if not email_input:
            # Tombol 'Continue with email' jika ada
            try:
                cont_email = page.locator("button:has-text('email' i)")
                if cont_email.count() > 0 and cont_email.first.is_visible(timeout=3000):
                    cont_email.first.click()
                    time.sleep(3)
                    email_input = page.locator("input[name='email'], input[type='email']").first
            except Exception:
                pass

        if not email_input:
            page.screenshot(path="err_no_email_box.png")
            send_telegram_photo("err_no_email_box.png", "❌ <b>[GAGAL TAHAP 2]</b> Kolom email tidak ditemukan.")
            browser.close()
            return

        print(f"Mengisi email: {TARGET_EMAIL}")
        email_input.click()
        email_input.fill("")
        email_input.fill(TARGET_EMAIL)
        time.sleep(1)

        page.screenshot(path="03_email_filled.png")
        send_telegram_photo("03_email_filled.png", f"📸 <b>[TAHAP 3/5] Email {TARGET_EMAIL} Terisi</b>\nMenekan tombol Continue form email...")

        # SUBMIT FORM EMAIL STRICT
        submitted = False
        try:
            form_submit = page.locator("form button[type='submit']").first
            if form_submit.is_visible(timeout=2000):
                form_submit.click()
                submitted = True
        except Exception:
            pass

        if not submitted:
            btns = page.locator("button")
            for idx in range(btns.count()):
                b = btns.nth(idx)
                try:
                    txt = (b.inner_text() or "").strip()
                    if txt in ["Continue", "Lanjutkan"] and "phone" not in txt.lower():
                        b.click()
                        submitted = True
                        break
                except Exception:
                    pass

        if not submitted:
            email_input.press("Enter")

        time.sleep(5)
        # Selesaikan Cloudflare jika menghadang di Tahap 4!
        wait_and_solve_cloudflare(page, max_wait_sec=20)

        page.screenshot(path="04_after_email_submit.png")
        send_telegram_photo("04_after_email_submit.png", "📸 <b>[TAHAP 4/5] Status Halaman Setelah Submit Email</b>\nMenganalisis apakah form OTP email muncul...")

        # Step 4: Deteksi Form OTP Email
        page_text = page.locator("body").inner_text().lower()
        if "phone" in page_text and "code" not in page_text:
            send_telegram_photo("04_after_email_submit.png", "❌ <b>[STOP]</b> Halaman ternyata membuka form Phone Number. Berhenti jujur.")
            browser.close()
            return

        otp_field = None
        otp_selectors = [
            "input[autocomplete='one-time-code']",
            "input[name='code']",
            "input[placeholder*='code' i]",
            "input[placeholder*='kode' i]",
            "input[aria-label*='code' i]",
            "input[maxlength='1']"
        ]
        for osel in otp_selectors:
            try:
                oloc = page.locator(osel)
                if oloc.count() > 0 and oloc.first.is_visible(timeout=3000):
                    otp_field = oloc
                    break
            except Exception:
                pass

        if not otp_field:
            try:
                send_code_btn = page.locator("button:has-text('code' i), a:has-text('code' i), button:has-text('email me a code' i)")
                if send_code_btn.count() > 0 and send_code_btn.first.is_visible(timeout=2000):
                    txt_b = send_code_btn.first.inner_text().lower()
                    if "phone" not in txt_b:
                        send_code_btn.first.click()
                        time.sleep(5)
                        wait_and_solve_cloudflare(page, max_wait_sec=15)
                        page.screenshot(path="04_after_email_submit.png")
                        for osel in otp_selectors:
                            oloc = page.locator(osel)
                            if oloc.count() > 0 and oloc.first.is_visible(timeout=3000):
                                otp_field = oloc
                                break
            except Exception:
                pass

        if not otp_field:
            send_telegram_photo("04_after_email_submit.png", "⚠️ <b>[BELUM ADA FORM OTP]</b>\nSilakan periksa foto bukti di atas apakah OpenAI meminta password atau tantangan lain.")
            print("No OTP field detected")
            browser.close()
            return

        send_telegram_photo("04_after_email_submit.png", "🔑 <b>[KODE OTP RESMI TERBUKA!]</b>\nOpenAI telah mengirimkan kode verifikasi ke email Tuan Ciro. Silakan balas chat ini dengan angka OTP-nya!")

        otp_code = wait_for_telegram_otp(timeout_sec=180)
        if not otp_code:
            print("No OTP received, exiting.")
            browser.close()
            return

        print(f"Memasukkan OTP: {otp_code}")
        send_telegram(f"✍️ <b>Memasukkan OTP {otp_code} ke form...</b>")

        if otp_field.count() >= len(otp_code):
            for i, char in enumerate(otp_code):
                otp_field.nth(i).fill(char)
                time.sleep(0.15)
        else:
            otp_field.first.fill(otp_code)

        time.sleep(1)
        page.keyboard.press("Enter")
        time.sleep(10)
        wait_and_solve_cloudflare(page, max_wait_sec=20)

        # Step 4.5: Tangani Konfirmasi Umur / Onboarding ("How old are you?" / "confirm your age")
        time.sleep(3)
        for attempt in range(3):
            try:
                body_text = page.locator("body").inner_text().lower()
                if "how old are you" in body_text or "confirm your age" in body_text or "enter a valid age" in body_text or "birthday" in body_text:
                    print(f"Terdeteksi formulir umur/profil OpenAI (attempt {attempt+1})!")
                    send_telegram("📝 <b>Mengisi formulir konfirmasi umur (25) & profil OpenAI...</b>")

                    # 1. Pastikan nama terisi
                    name_inputs = page.locator("input[name*='name' i], input[id*='name' i], input[aria-label*='name' i]")
                    if name_inputs.count() > 0 and name_inputs.first.is_visible(timeout=1000):
                        if not name_inputs.first.input_value():
                            name_inputs.first.fill("Ciro")
                            time.sleep(0.3)

                    # 2. Tangani input Age (angka umur misal 25) atau Birthday
                    # Cari semua input text/number yang terlihat
                    all_inputs = page.locator("input")
                    for i in range(all_inputs.count()):
                        inp = all_inputs.nth(i)
                        try:
                            if not inp.is_visible(timeout=500):
                                continue
                            placeholder = (inp.get_attribute("placeholder") or "").lower()
                            name_attr = (inp.get_attribute("name") or "").lower()
                            aria_label = (inp.get_attribute("aria-label") or "").lower()
                            val = inp.input_value()

                            # Jika field adalah age / umur
                            if "age" in placeholder or "age" in name_attr or "age" in aria_label:
                                inp.click()
                                inp.fill("25")
                                time.sleep(0.3)
                            elif "birth" in placeholder or "birth" in name_attr or "birth" in aria_label:
                                inp.click()
                                inp.fill("05/12/1998")
                                time.sleep(0.3)
                            elif not val and "name" not in name_attr and "name" not in placeholder:
                                # Input kosong kedua setelah name biasanya adalah Age
                                inp.click()
                                inp.fill("25")
                                time.sleep(0.3)
                        except Exception as ex:
                            pass

                    # 3. Klik Continue
                    cont_btn = page.locator("button:has-text('Continue'), button:has-text('Lanjutkan')").first
                    if cont_btn.is_visible(timeout=2000):
                        cont_btn.click()
                        time.sleep(6)
                        wait_and_solve_cloudflare(page, max_wait_sec=15)
                else:
                    break
            except Exception as e:
                print(f"Age confirm handler notice: {e}")

        # Step 5: Validasi Dashboard
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
            send_telegram(f"🍪 <b>{len(cookies)} Session Cookies Berhasil Diamankan!</b>")

            if PROMPT_ASK:
                from chat_engine import send_prompt_and_extract_answer
                ans = send_prompt_and_extract_answer(page, PROMPT_ASK)
                send_telegram(f"✨ <b>[JAWABAN CHATGPT]:</b>\n\n{ans}")
        else:
            send_telegram_photo("05_final_status.png", "❌ <b>[BELUM BERHASIL LOGIN]</b>\nSetelah memasukkan OTP, layar belum masuk ke dashboard ChatGPT. Lihat bukti foto di atas.")

        browser.close()

if __name__ == "__main__":
    main()
