import time
import os

def dismiss_onboarding_dialogs(page):
    """Menutup modal atau tombol Continue seperti 'You\'re all set', 'Stay logged in', dsb."""
    for _ in range(3):
        try:
            body = (page.locator("body").inner_text() or "").lower()
            if "you're all set" in body or "stay logged in" in body or "welcome" in body or "continue" in body:
                btns = page.locator("button:has-text('Continue'), button:has-text('Lanjutkan'), button:has-text('Done'), button:has-text('Selesai'), button:has-text('Okay'), button:has-text('Got it')")
                if btns.count() > 0 and btns.first.is_visible(timeout=1500):
                    print("Dismissing onboarding modal: Clicking Continue...")
                    btns.first.click()
                    time.sleep(2)
        except Exception:
            pass

def send_prompt_and_extract_answer(page, prompt_text: str) -> str:
    print(f"Sending prompt to ChatGPT: {prompt_text}")
    dismiss_onboarding_dialogs(page)

    try:
        composer = page.locator("#prompt-textarea, textarea[placeholder*='Message' i], textarea[placeholder*='Kirim pesan' i], div[contenteditable='true']").first
        composer.wait_for(state="visible", timeout=15000)
        composer.click()
        time.sleep(1)
        composer.fill(prompt_text)
        time.sleep(1)

        # Klik tombol kirim atau Enter
        send_btn = page.locator("[data-testid='send-button'], button[aria-label*='Send' i], button[aria-label*='Kirim' i]")
        if send_btn.count() > 0 and send_btn.first.is_enabled():
            send_btn.first.click()
        else:
            page.keyboard.press("Enter")

        print("Prompt sent. Waiting for response to stream...")
        time.sleep(4)

        # Tunggu sampai tombol stop generating hilang
        stop_selectors = [
            "[data-testid='stop-button']",
            "button[aria-label*='Stop' i]",
            "button[aria-label*='Berhenti' i]"
        ]
        
        start_wait = time.time()
        while time.time() - start_wait < 120:
            generating = False
            for s in stop_selectors:
                try:
                    loc = page.locator(s)
                    if loc.count() > 0 and loc.first.is_visible(timeout=500):
                        generating = True
                        break
                except Exception:
                    pass
            if not generating and (time.time() - start_wait > 6):
                print("Generation completed!")
                break
            time.sleep(1.5)

        time.sleep(3)
        page.screenshot(path="06_answer_view.png")

        # Ambil bubble jawaban terakhir
        articles = page.locator("[data-message-author-role='assistant'], article, div.markdown")
        if articles.count() > 0:
            last_ans = articles.last.inner_text()
            return last_ans.strip()

        return "Jawaban berhasil di-generate (screenshot terlampir)."
    except Exception as e:
        print(f"Error in chat engine: {e}")
        return f"Terjadi kesalahan saat memproses jawaban: {e}"
