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
        # Cari input prompt box (UI 2026: '+ Ask ChatGPT' div contenteditable / textarea / prompt-textarea)
        composer = None
        selectors = [
            "div[contenteditable='true']",
            "#prompt-textarea",
            "textarea[placeholder*='Ask' i]",
            "textarea[placeholder*='Message' i]",
            "div[role='textbox']",
            "[data-placeholder*='Ask' i]"
        ]
        for s in selectors:
            try:
                loc = page.locator(s)
                if loc.count() > 0 and loc.first.is_visible(timeout=3000):
                    composer = loc.first
                    break
            except Exception:
                pass

        if not composer:
            # Klik pada area '+ Ask ChatGPT' jika masih tertutup
            try:
                ask_placeholder = page.locator("text='Ask ChatGPT', text='Where should we begin'").first
                if ask_placeholder.is_visible(timeout=2000):
                    ask_placeholder.click()
                    time.sleep(1)
                    composer = page.locator("div[contenteditable='true'], #prompt-textarea, textarea").first
            except Exception:
                pass

        if not composer:
            page.screenshot(path="err_no_composer.png")
            return "Gagal menemukan kolom input chat prompt di dashboard."

        composer.click()
        time.sleep(0.5)
        # Gunakan type / fill human-like
        try:
            composer.fill(prompt_text)
        except Exception:
            page.keyboard.type(prompt_text, delay=20)
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

        # Ekstraksi teks jawaban ChatGPT yang akurat di UI 2026:
        last_ans = ""
        # 1. Coba locator markdown atau assistant message
        candidates = page.locator("[data-message-author-role='assistant'], .markdown, [class*='markdown'], article")
        for i in range(candidates.count() - 1, -1, -1):
            t = candidates.nth(i).inner_text().strip()
            if t and prompt_text not in t and len(t) > 10:
                last_ans = t
                break

        # 2. Fallback via evaluate JS untuk mengambil turn assistant
        if not last_ans:
            try:
                res = page.evaluate('''() => {
                    const turns = document.querySelectorAll("[data-message-author-role='assistant'], article, div[data-testid*='conversation-turn']");
                    if (turns && turns.length > 0) {
                        return turns[turns.length - 1].innerText;
                    }
                    const ps = document.querySelectorAll('main p');
                    if (ps && ps.length > 0) {
                        return Array.from(ps).map(p => p.innerText).join('\n');
                    }
                    return '';
                }''')
                if res and res.strip():
                    last_ans = res.strip()
            except Exception as e:
                print(f"JS evaluate extract notice: {e}")

        if last_ans:
            print("==================== [HASIL JAWABAN CHATGPT] ====================")
            print(last_ans)
            print("==================================================================")
            return last_ans

        print("[WARN] Bubble pesan teks tidak cocok dengan selector, jawaban ada di foto screenshot.")
        return "Jawaban berhasil di-generate (screenshot terlampir)."
    except Exception as e:
        print(f"Error in chat engine: {e}")
        return f"Terjadi kesalahan saat memproses jawaban: {e}"
