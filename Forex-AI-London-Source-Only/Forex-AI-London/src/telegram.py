import os,requests
def send_telegram(message):
    token=os.getenv("TELEGRAM_BOT_TOKEN"); chat=os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat: raise RuntimeError("Missing Telegram secrets")
    r=requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
      data={"chat_id":chat,"text":message,"disable_web_page_preview":True},timeout=30)
    r.raise_for_status(); result=r.json()
    if not result.get("ok"): raise RuntimeError(str(result))
