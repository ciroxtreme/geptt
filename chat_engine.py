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

        # Ekstraksi teks jawaban ChatGPT yang akurat di UI 2026 murni Playwright API:
        last_ans = ""
        # 1. Ambil semua paragraf di dalam container pesan assistant / main
        ps = page.locator("main p, [data-message-author-role='assistant'] p, div[data-testid*='conversation-turn'] p")
        p_texts = []
        for i in range(ps.count()):
            try:
                pt = ps.nth(i).inner_text().strip()
                if pt and prompt_text not in pt:
                    p_texts.append(pt)
            except Exception:
                pass

        if p_texts:
            last_ans = "\n\n".join(p_texts).strip()

        # 2. Fallback jika list/bullet points (li)
        if not last_ans or len(p_texts) <= 1:
            lis = page.locator("main li, [data-message-author-role='assistant'] li")
            if lis.count() > 0:
                li_texts = [lis.nth(i).inner_text().strip() for i in range(lis.count()) if lis.nth(i).inner_text().strip()]
                if li_texts:
                    last_ans = last_ans + "\n" + "\n".join(["- " + x for x in li_texts]) if last_ans else "\n".join(["- " + x for x in li_texts])

        # 3. Fallback: ambil inner_text dari turn assistant
        if not last_ans:
            turns = page.locator("[data-message-author-role='assistant'], article")
            if turns.count() > 0:
                try:
                    raw_turn = turns.last.inner_text().strip()
                    if raw_turn and prompt_text not in raw_turn:
                        last_ans = raw_turn
                except Exception:
                    pass

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
