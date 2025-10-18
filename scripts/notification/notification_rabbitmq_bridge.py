#!/usr/bin/env python3
"""
Twitter Notification to RabbitMQ Bridge
Captures Twitter notifications and publishes them to RabbitMQ
"""

import asyncio
import json
from typing import Any as _Moved
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass
from playwright.async_api import async_playwright
import logging
from dotenv import load_dotenv
from xbot.rabbitmq_manager import NotificationPublisher, RabbitMQManager, BotMessage
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

# Load environment
load_dotenv()

console = Console()
logger = logging.getLogger(__name__)


class NotificationRabbitMQBridge:
    """Bridges Twitter notifications to RabbitMQ"""

    def __init__(self):
        self.publisher = NotificationPublisher()
        self.rabbitmq = RabbitMQManager()
        self.rabbitmq.connect()
        self.notifications_captured = 0
        self.notifications_published = 0
        self.seen_ids = set()

    async def monitor_and_publish(self, duration: int = 60, only_handle: str | None = None):
        """Monitor Twitter notifications and publish to RabbitMQ"""
        console.print(Panel.fit(
            "[bold cyan]Twitter → RabbitMQ Bridge[/bold cyan]\n"
            "[dim]Publishing notifications to message queue[/dim]",
            border_style="cyan"
        ))

        # Prefer Playwright storageState from helper; fall back to cookie JSON
        from xbot.profiles import storage_state_path
        profile = os.getenv('PROFILE', '4botbsc')
        sp = storage_state_path(profile)
        storage_state = str(sp) if sp.exists() else None
        cookies = []
        cookie_file = Path("chrome_profiles/cookies/default_cookies.json")
        if not storage_state and cookie_file.exists():
            with open(cookie_file) as f:
                cookies = json.load(f)
        if storage_state:
            console.print(f"[green]✅ Using storageState: {storage_state}[/green]")
        else:
            console.print(f"[yellow]ℹ️ Using cookie JSON: {cookie_file} ({len(cookies)} cookies)\n[tip] Consider exporting Playwright storageState for more reliable auth[/tip]")
        console.print(f"[green]✅ Connected to RabbitMQ[/green]")

        async with async_playwright() as p:
            engine = {'chromium': p.chromium, 'webkit': p.webkit, 'firefox': p.firefox}.get(os.getenv('BROWSER_NAME','chromium').lower(), p.chromium)
            browser = await engine.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )

            context = await browser.new_context(
                storage_state=storage_state,
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
            )

            if cookies:
                await context.add_cookies(cookies)
            page = await context.new_page()

            # Setup console handler
            page.on("console", lambda msg: self._handle_console(msg))

            console.print("[cyan]📡 Navigating to notifications...[/cyan]")
            await page.goto('https://x.com/notifications', wait_until='domcontentloaded')
            await asyncio.sleep(3)

            # Inject extraction script
            await self._inject_extraction_script(page, only_handle=only_handle)

            console.print("[green]✅ Monitoring started[/green]")

            # Monitor with progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:

                task = progress.add_task(
                    f"[cyan]Monitoring for {duration}s...",
                    total=duration
                )

                start_time = datetime.now()
                last_refresh = start_time

                while (datetime.now() - start_time).seconds < duration:
                    elapsed = (datetime.now() - start_time).seconds
                    progress.update(task, completed=elapsed)

                    # Update description
                    progress.update(
                        task,
                        description=f"[cyan]Captured: {self.notifications_captured} | Published: {self.notifications_published}"
                    )

                    # Auto-refresh
                    if (datetime.now() - last_refresh).seconds >= 20:
                        await page.reload(wait_until='domcontentloaded')
                        await asyncio.sleep(3)
                        await self._inject_extraction_script(page)
                        last_refresh = datetime.now()

                    await asyncio.sleep(0.5)

            await browser.close()

        # Display summary
        self._display_summary()

    async def _inject_extraction_script(self, page, only_handle: str | None = None):
        """Inject notification extraction and publishing script"""
        handle_filter = (only_handle or '').lstrip('@') if only_handle else ''
        await page.evaluate(("""
            (() => {
                const processedNotifications = new Set();

                function generateId(text) {
                    let hash = 0;
                    for (let i = 0; i < Math.min(text.length, 200); i++) {
                        hash = ((hash << 5) - hash) + text.charCodeAt(i);
                        hash = hash & hash;
                    }
                    return 'notif_' + Math.abs(hash).toString(36) + '_' + Date.now().toString(36);
                }

                function extractAndPublish(element) {
                    try {
                        const elementText = element.textContent || '';
                        const notifId = generateId(elementText);

                        if (processedNotifications.has(notifId)) return;
                        processedNotifications.add(notifId);

                        // Extract notification data
                        const notifData = {
                            notification_id: notifId,
                            type: 'unknown',
                            timestamp: new Date().toISOString(),
                            from_handle: 'unknown',
                            from_name: '',
                            content: '',
                            mentioned_users: [],
                            raw_text: elementText.substring(0, 500)
                        };

                        // Extract user
                        const userLinks = element.querySelectorAll('a[href^="/"][role="link"]');
                        if (userLinks.length > 0) {
                            const href = userLinks[0].getAttribute('href');
                            if (href && !href.includes('/status/')) {
                                notifData.from_handle = href.split('/').pop() || 'unknown';
                                const nameEl = userLinks[0].querySelector('span');
                                if (nameEl) notifData.from_name = nameEl.textContent;
                            }
                        }

                        // Detect type
                        const textLower = elementText.toLowerCase();
                        if (textLower.includes('liked')) notifData.type = 'like';
                        else if (textLower.includes('retweet')) notifData.type = 'retweet';
                        else if (textLower.includes('replied')) notifData.type = 'reply';
                        else if (textLower.includes('followed')) notifData.type = 'follow';
                        else if (textLower.includes('mentioned')) notifData.type = 'mention';

                        // Extract content
                        const tweetText = element.querySelector('[data-testid="tweetText"]');
                        if (tweetText) notifData.content = tweetText.textContent;

                        // Extract mentions
                        const mentions = elementText.match(/@[a-zA-Z0-9_]+/g);
                        if (mentions) notifData.mentioned_users = [...new Set(mentions)];

                        // Extract status id if present
                        const statusLink = element.querySelector('a[href*="/status/"]');
                        if (statusLink) {
                            const m = (statusLink.getAttribute('href') || statusLink.href || '').match(/status\/(\d+)/);
                            if (m) notifData.post_id = m[1];
                        }

                        // Optional filter: only publish notifications that tag a specific handle
                        const filter = '%HANDLE_FILTER%'.trim();
                        if (filter) {
                            const tag = '@' + filter.toLowerCase();
                            const set = new Set((notifData.mentioned_users || []).map(x => x.toLowerCase()));
                            if (!set.has(tag)) { return; }
                        }

                        // Send to Python
                        console.log('__RABBITMQ_NOTIF__:' + JSON.stringify(notifData));

                    } catch (error) {
                        console.error('Extract error:', error);
                    }
                }

                // Process existing
                document.querySelectorAll('article, [data-testid="cellInnerDiv"]').forEach(extractAndPublish);

                // Monitor new
                const observer = new MutationObserver((mutations) => {
                    mutations.forEach(mutation => {
                        mutation.addedNodes.forEach(node => {
                            if (node.nodeType === 1) {
                                if (node.matches && (node.matches('article') || node.matches('[data-testid="cellInnerDiv"]'))) {
                                    extractAndPublish(node);
                                }
                                if (node.querySelectorAll) {
                                    node.querySelectorAll('article, [data-testid="cellInnerDiv"]').forEach(extractAndPublish);
                                }
                            }
                        });
                    });
                });

                observer.observe(document.body, { childList: true, subtree: true });
            })();
        """).replace('%HANDLE_FILTER%', handle_filter))

    def _handle_console(self, msg):
        """Handle console messages and publish to RabbitMQ"""
        try:
            text = msg.text
            if '__RABBITMQ_NOTIF__:' in text:
                json_str = text.split('__RABBITMQ_NOTIF__:')[1]
                data = json.loads(json_str)

                # Check if already seen
                if data['notification_id'] not in self.seen_ids:
                    self.seen_ids.add(data['notification_id'])
                    self.notifications_captured += 1

                    # Publish to RabbitMQ based on type
                    success = self._publish_notification(data)
                    if success:
                        self.notifications_published += 1
                        console.print(
                            f"[green]✓[/green] Published {data['type']}: @{data['from_handle']}"
                        )
                    else:
                        console.print(
                            f"[red]✗[/red] Failed to publish {data['type']}"
                        )

        except Exception as e:
            pass

    def _publish_notification(self, data: Dict[str, Any]) -> bool:
        """Publish notification to RabbitMQ"""
        try:
            notif_type = data.get('type', 'unknown')
            from_user = data.get('from_handle', 'unknown')
            # If this is a mention and we have a status link, also emit a CZ reply request
            # Try to derive status URL/id from raw_text/content heuristics (JS already tried to extract content)
            post_id = data.get('post_id') or ''
            post_url = f"https://x.com/i/web/status/{post_id}" if post_id else ''

            if notif_type == 'follow':
                self.publisher.publish_follow(
                    from_user=from_user,
                    user_info={"display_name": data.get('from_name', '')}
                )
            elif notif_type == 'like':
                self.publisher.publish_like(
                    from_user=from_user,
                    post_id=data.get('notification_id', '')
                )
            elif notif_type == 'retweet':
                self.publisher.publish_retweet(
                    from_user=from_user,
                    post_id=data.get('notification_id', '')
                )
            elif notif_type == 'reply':
                self.publisher.publish_reply(
                    from_user=from_user,
                    content=data.get('content', ''),
                    post_id=data.get('notification_id', '')
                )
            elif notif_type == 'mention':
                content = data.get('content', '')
                self.publisher.publish_mention(
                    from_user=from_user,
                    content=content,
                    post_id=post_id or data.get('notification_id', '')
                )
                # Send request for CZ generation when a mention targets us (already filtered if only_handle set)
                if post_url:
                    try:
                        self.rabbitmq.publish_cz_reply_request(
                            post_url=post_url,
                            post_id=post_id or data.get('notification_id',''),
                            author_handle=from_user,
                            content=content,
                        )
                    except Exception:
                        pass
            else:
                # Generic notification
                self.rabbitmq.publish_notification(data)

            return True

        except Exception as e:
            logger.error(f"Publish error: {e}")
            return False

    def _display_summary(self):
        """Display summary of bridge operation"""
        table = Table(title="Bridge Summary", border_style="cyan")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Notifications Captured", str(self.notifications_captured))
        table.add_row("Notifications Published", str(self.notifications_published))
        table.add_row("Publish Success Rate",
                     f"{(self.notifications_published/max(1, self.notifications_captured))*100:.1f}%")

        console.print(table)

        console.print(f"\n[bold green]✅ Bridge operation complete![/bold green]")
        console.print(f"[cyan]📊 {self.notifications_published} notifications published to RabbitMQ[/cyan]")

    def close(self):
        """Close connections"""
        self.publisher.close()
        self.rabbitmq.close()


async def main():
    parser = argparse.ArgumentParser(description='Twitter to RabbitMQ notification bridge')
    parser.add_argument('duration', type=int, nargs='?', default=60,
                       help='Duration to monitor in seconds (default: 60)')
    parser.add_argument('--only-handle', type=str, default='4botbsc', help='Filter notifications to those tagging this handle (without @)')
    parser.add_argument('--browser', type=str, default=os.getenv('BROWSER_NAME','chromium'), help='chromium|webkit|firefox')
    args = parser.parse_args()

    bridge = NotificationRabbitMQBridge()

    try:
        await bridge.monitor_and_publish(args.duration, only_handle=args.only_handle)
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Bridge interrupted[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Bridge error: {e}[/red]")
    finally:
        bridge.close()


if __name__ == "__main__":
    asyncio.run(main())
