#!/usr/bin/env python3
"""
Twitter Notification to RabbitMQ Bridge
Captures Twitter notifications and publishes them to RabbitMQ
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass
from playwright.async_api import async_playwright
import logging
from dotenv import load_dotenv
from rabbitmq_manager import NotificationPublisher, RabbitMQManager, BotMessage
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

    async def monitor_and_publish(self, duration: int = 60):
        """Monitor Twitter notifications and publish to RabbitMQ"""
        console.print(Panel.fit(
            "[bold cyan]Twitter → RabbitMQ Bridge[/bold cyan]\n"
            "[dim]Publishing notifications to message queue[/dim]",
            border_style="cyan"
        ))

        # Load cookies
        cookie_file = Path("auth_data/x_cookies.json")
        if not cookie_file.exists():
            console.print("[red]❌ No cookie file found![/red]")
            return

        with open(cookie_file) as f:
            cookies = json.load(f)

        console.print(f"[green]✅ Loaded {len(cookies)} cookies[/green]")
        console.print(f"[green]✅ Connected to RabbitMQ[/green]")

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'
            )

            await context.add_cookies(cookies)
            page = await context.new_page()

            # Setup console handler
            page.on("console", lambda msg: self._handle_console(msg))

            console.print("[cyan]📡 Navigating to notifications...[/cyan]")
            await page.goto('https://x.com/notifications', wait_until='domcontentloaded')
            await asyncio.sleep(3)

            # Inject extraction script
            await self._inject_extraction_script(page)

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

    async def _inject_extraction_script(self, page):
        """Inject notification extraction and publishing script"""
        await page.evaluate("""
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
        """)

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
                self.publisher.publish_mention(
                    from_user=from_user,
                    content=data.get('content', ''),
                    post_id=data.get('notification_id', '')
                )
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
    args = parser.parse_args()

    bridge = NotificationRabbitMQBridge()

    try:
        await bridge.monitor_and_publish(args.duration)
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Bridge interrupted[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Bridge error: {e}[/red]")
    finally:
        bridge.close()


if __name__ == "__main__":
    asyncio.run(main())