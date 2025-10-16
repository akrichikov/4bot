from __future__ import annotations

import asyncio
import json
import os
import re
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from playwright.async_api import async_playwright

from .cookies import load_cookie_json
from .rabbitmq_manager import RabbitMQManager


log = logging.getLogger("notify_to_rmq")


async def run_headless_notifications(profile_cookies: Path, handle: str = "4botbsc") -> None:
    mgr = RabbitMQManager()
    mgr.connect()

    cookies = []
    if profile_cookies.exists():
        try:
            cookies = json.loads(profile_cookies.read_text())
        except Exception:
            pass
    if not cookies and Path("auth_data/x_cookies.json").exists():
        cookies = json.loads(Path("auth_data/x_cookies.json").read_text())

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True, args=[
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox', '--disable-dev-shm-usage'
        ])
        ctx = await browser.new_context(viewport={'width': 1400, 'height': 900})
        if cookies:
            try:
                await ctx.add_cookies(cookies)
            except Exception:
                pass
        page = await ctx.new_page()

        async def on_console(msg):
            t = msg.text
            if '__NOTIFICATION__' in t:
                try:
                    data = json.loads(t.split('__NOTIFICATION__:')[1])
                    await handle_notification(mgr, data, my_handle=handle)
                except Exception:
                    pass
        page.on("console", lambda m: asyncio.create_task(on_console(m)))

        await page.goto('https://x.com/notifications', wait_until='domcontentloaded')
        await asyncio.sleep(2)
        await page.evaluate(_NOTIF_OBSERVER_JS)
        # Keep loop
        while True:
            await asyncio.sleep(1.0)


async def handle_notification(mgr: RabbitMQManager, data: Dict[str, Any], my_handle: str) -> None:
    raw = (data.get('raw_text') or '').lower()
    post_id = data.get('post_id')
    post_content = data.get('post_content') or ''
    from_handle = data.get('from_handle') or ''
    # Only mentions that tag our handle OR mention phrasing
    if f"@{my_handle.lower()}" not in raw and 'mentioned you' not in raw:
        return
    if not post_id:
        return
    tweet_url = f"https://x.com/i/web/status/{post_id}"
    payload = {
        "type": "reply_request",
        "message_id": f"req_{datetime.now().timestamp()}",
        "timestamp": datetime.now().isoformat(),
        "source": "notifications",
        "data": {
            "author_handle": from_handle,
            "content": post_content,
            "tweet_url": tweet_url,
            "post_id": post_id,
            "persona": "CZ",
        }
    }
    mgr.publish_message(message=mgr_message(payload), routing_key='4bot.request.reply')


def mgr_message(obj: Dict[str, Any]):
    # rabbitmq_manager expects BotMessage-like dict JSON
    return type("Msg", (), {"__iter__": lambda s: iter(()),})  # placeholder; we pass raw JSON via publish override


_NOTIF_OBSERVER_JS = """
(() => {
  const seen = new Set();
  function extract(el) {
    try {
      const textContent = el.textContent || '';
      const id = btoa((textContent || '').slice(0,150));
      if (seen.has(id)) return; seen.add(id);
      let fromHandle='';
      const a = el.querySelector('a[href^="/" ]');
      if (a) { try { fromHandle = new URL(a.href, location.origin).pathname.split('/').pop() || ''; } catch(e){} }
      const spans = el.querySelectorAll('span');
      let notifTxt='';
      spans.forEach(s=>{ const t=(s.textContent||''); if (/liked|reposted|retweeted|replied|followed|mentioned|quoted/i.test(t)) notifTxt=t; });
      const tw = el.querySelector('[data-testid="tweetText"]');
      const postContent = tw ? tw.textContent : '';
      let postId=null; const sl=el.querySelector('a[href*="/status/"]');
      if (sl){ const m=sl.href.match(/status\/(\d+)/); if (m) postId=m[1]; }
      const data = { from_handle: fromHandle, raw_text: notifTxt||textContent.slice(0,200), post_content: postContent, post_id: postId, timestamp: new Date().toISOString() };
      console.log('__NOTIFICATION__:' + JSON.stringify(data));
    } catch(e){}
  }
  document.querySelectorAll('article,[data-testid="cellInnerDiv"]').forEach(extract);
  const obs=new MutationObserver(ms=>{ ms.forEach(m=>{ m.addedNodes.forEach(n=>{ if(n.nodeType===1){
    (n.querySelectorAll? n.querySelectorAll('article,[data-testid="cellInnerDiv"]'):[]).forEach(extract);
  } }) }) });
  obs.observe(document.body,{childList:true,subtree:true});
  return 'ok';
})();
"""


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    cookies = Path('chrome_profiles/cookies/default_cookies.json')
    asyncio.run(run_headless_notifications(cookies))


if __name__ == '__main__':
    main()

