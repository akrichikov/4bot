#!/usr/bin/env python3
"""
Working Notification JSON Parser
Uses proven extraction patterns that successfully captured notifications before
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
from playwright.async_api import async_playwright
import logging
import argparse
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text

console = Console()


@dataclass
class NotificationData:
    """Structured notification data"""
    notification_id: str
    type: str
    timestamp: str
    from_handle: str
    from_name: str
    action_text: str
    content: str
    mentioned_users: List[str]
    raw_text: str


class NotificationJSONParser:
    def __init__(self):
        self.notifications: List[NotificationData] = []
        self.seen_ids = set()

    async def parse_notifications(self, duration: int = 60):
        """Parse notifications for specified duration"""
        console.print("[bold cyan]🔄 Starting Notification JSON Parser[/bold cyan]")

        # Setup directories
        log_dir = Path("notification_json_logs")
        log_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_file = log_dir / f"notifications_{timestamp}.json"

        # Load cookies
        cookie_file = Path("auth_data/x_cookies.json")
        if not cookie_file.exists():
            console.print("[red]❌ No cookie file found![/red]")
            return

        with open(cookie_file) as f:
            cookies = json.load(f)

        console.print(f"[green]✅ Loaded {len(cookies)} cookies[/green]")

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

            # Setup console message handler
            page.on("console", lambda msg: self._handle_console(msg))

            console.print("[cyan]📡 Navigating to notifications...[/cyan]")
            await page.goto('https://x.com/notifications', wait_until='domcontentloaded')
            await asyncio.sleep(3)

            # Inject enhanced extraction script
            await page.evaluate("""
                (() => {
                    const processedNotifications = new Set();
                    let notificationCount = 0;

                    function extractNotificationData(element) {
                        try {
                            // Create unique ID from element content
                            const elementText = element.textContent || '';
                            const notifId = btoa(elementText.substring(0, 200)).replace(/[^a-zA-Z0-9]/g, '');

                            if (processedNotifications.has(notifId)) return;
                            processedNotifications.add(notifId);
                            notificationCount++;

                            // Initialize notification data
                            let notifData = {
                                notification_id: notifId,
                                type: 'unknown',
                                timestamp: new Date().toISOString(),
                                from_handle: 'unknown',
                                from_name: '',
                                action_text: '',
                                content: '',
                                mentioned_users: [],
                                raw_text: elementText.substring(0, 500)
                            };

                            // Extract user information
                            const userLinks = element.querySelectorAll('a[href^="/"][role="link"]');
                            if (userLinks.length > 0) {
                                const firstLink = userLinks[0];
                                const href = firstLink.getAttribute('href');
                                if (href && !href.includes('/status/')) {
                                    notifData.from_handle = href.split('/').pop() || 'unknown';

                                    // Get display name
                                    const nameSpan = firstLink.querySelector('span');
                                    if (nameSpan) {
                                        notifData.from_name = nameSpan.textContent || '';
                                    }
                                }
                            }

                            // Detect notification type from text patterns
                            const textLower = elementText.toLowerCase();
                            if (textLower.includes('liked your')) {
                                notifData.type = 'like';
                                notifData.action_text = 'liked your post';
                            } else if (textLower.includes('retweeted') || textLower.includes('reposted')) {
                                notifData.type = 'retweet';
                                notifData.action_text = 'retweeted your post';
                            } else if (textLower.includes('replied to')) {
                                notifData.type = 'reply';
                                notifData.action_text = 'replied to you';
                            } else if (textLower.includes('followed you')) {
                                notifData.type = 'follow';
                                notifData.action_text = 'followed you';
                            } else if (textLower.includes('mentioned you')) {
                                notifData.type = 'mention';
                                notifData.action_text = 'mentioned you';
                            } else if (textLower.includes('quoted your')) {
                                notifData.type = 'quote';
                                notifData.action_text = 'quoted your post';
                            } else if (textLower.includes('replying to')) {
                                notifData.type = 'reply';
                                notifData.action_text = 'replied';
                            }

                            // Extract tweet content if present
                            const tweetText = element.querySelector('[data-testid="tweetText"]');
                            if (tweetText) {
                                notifData.content = tweetText.textContent || '';
                            }

                            // Extract mentioned users
                            if (elementText.includes('Replying to')) {
                                const mentions = elementText.match(/@[a-zA-Z0-9_]+/g) || [];
                                notifData.mentioned_users = [...new Set(mentions)];
                            }

                            // Send to Python
                            console.log('__NOTIFICATION_JSON__:' + JSON.stringify(notifData));
                            return notifData;

                        } catch (error) {
                            console.error('Extraction error:', error);
                            return null;
                        }
                    }

                    // Process existing notifications
                    const existingNotifs = document.querySelectorAll('article, [data-testid="cellInnerDiv"]');
                    console.log(`Processing ${existingNotifs.length} existing notifications`);
                    existingNotifs.forEach(extractNotificationData);

                    // Monitor for new notifications
                    const observer = new MutationObserver((mutations) => {
                        mutations.forEach(mutation => {
                            mutation.addedNodes.forEach(node => {
                                if (node.nodeType === Node.ELEMENT_NODE) {
                                    if (node.matches && (node.matches('article') || node.matches('[data-testid="cellInnerDiv"]'))) {
                                        extractNotificationData(node);
                                    }
                                    if (node.querySelectorAll) {
                                        const notifs = node.querySelectorAll('article, [data-testid="cellInnerDiv"]');
                                        notifs.forEach(extractNotificationData);
                                    }
                                }
                            });
                        });
                    });

                    observer.observe(document.body, {
                        childList: true,
                        subtree: true
                    });

                    console.log('Notification JSON extractor active');
                    return notificationCount;
                })();
            """)

            console.print("[green]✅ Extraction script injected[/green]")
            console.print(f"[cyan]⏱️ Monitoring for {duration} seconds...[/cyan]")

            # Create live display
            with Live(console=console, refresh_per_second=1) as live:
                start_time = datetime.now()
                last_refresh = start_time

                while (datetime.now() - start_time).seconds < duration:
                    # Create status table
                    table = Table(title="Notification Monitor Status")
                    table.add_column("Metric", style="cyan")
                    table.add_column("Value", style="green")

                    elapsed = (datetime.now() - start_time).seconds
                    remaining = duration - elapsed

                    table.add_row("Elapsed", f"{elapsed}s")
                    table.add_row("Remaining", f"{remaining}s")
                    table.add_row("Total Captured", str(len(self.notifications)))

                    # Add type breakdown
                    type_counts = {}
                    for notif in self.notifications:
                        type_counts[notif.type] = type_counts.get(notif.type, 0) + 1

                    for notif_type, count in type_counts.items():
                        table.add_row(f"  - {notif_type}", str(count))

                    # Show last notification
                    if self.notifications:
                        last_notif = self.notifications[-1]
                        table.add_row("Last Notification", "")
                        table.add_row("  From", f"@{last_notif.from_handle}")
                        table.add_row("  Type", last_notif.type)
                        table.add_row("  Action", last_notif.action_text)

                    live.update(table)

                    # Auto-refresh every 15 seconds
                    if (datetime.now() - last_refresh).seconds >= 15:
                        console.print("[dim]🔄 Refreshing page...[/dim]")
                        await page.reload(wait_until='domcontentloaded')
                        await asyncio.sleep(3)

                        # Re-inject script
                        await page.evaluate("""
                            // Re-inject extraction script after refresh
                            (() => {
                                const processedNotifications = new Set();

                                function extractNotificationData(element) {
                                    const elementText = element.textContent || '';
                                    const notifId = btoa(elementText.substring(0, 200)).replace(/[^a-zA-Z0-9]/g, '');

                                    if (processedNotifications.has(notifId)) return;
                                    processedNotifications.add(notifId);

                                    let notifData = {
                                        notification_id: notifId,
                                        type: 'unknown',
                                        timestamp: new Date().toISOString(),
                                        from_handle: 'unknown',
                                        from_name: '',
                                        action_text: '',
                                        content: '',
                                        mentioned_users: [],
                                        raw_text: elementText.substring(0, 500)
                                    };

                                    const userLinks = element.querySelectorAll('a[href^="/"]');
                                    if (userLinks.length > 0) {
                                        const href = userLinks[0].getAttribute('href');
                                        if (href && !href.includes('/status/')) {
                                            notifData.from_handle = href.split('/').pop() || 'unknown';
                                        }
                                    }

                                    const textLower = elementText.toLowerCase();
                                    if (textLower.includes('liked')) notifData.type = 'like';
                                    else if (textLower.includes('retweet') || textLower.includes('repost')) notifData.type = 'retweet';
                                    else if (textLower.includes('replied')) notifData.type = 'reply';
                                    else if (textLower.includes('followed')) notifData.type = 'follow';
                                    else if (textLower.includes('mentioned')) notifData.type = 'mention';

                                    console.log('__NOTIFICATION_JSON__:' + JSON.stringify(notifData));
                                }

                                document.querySelectorAll('article, [data-testid="cellInnerDiv"]').forEach(extractNotificationData);

                                const observer = new MutationObserver((mutations) => {
                                    mutations.forEach(m => {
                                        m.addedNodes.forEach(node => {
                                            if (node.nodeType === 1) {
                                                if (node.matches && (node.matches('article') || node.matches('[data-testid="cellInnerDiv"]'))) {
                                                    extractNotificationData(node);
                                                }
                                                if (node.querySelectorAll) {
                                                    node.querySelectorAll('article, [data-testid="cellInnerDiv"]').forEach(extractNotificationData);
                                                }
                                            }
                                        });
                                    });
                                });

                                observer.observe(document.body, { childList: true, subtree: true });
                            })();
                        """)

                        last_refresh = datetime.now()

                    await asyncio.sleep(1)

            await browser.close()

        # Save results to JSON
        self._save_json(json_file)

        console.print(f"\n[bold green]✅ Complete![/bold green]")
        console.print(f"[cyan]📊 Total notifications captured: {len(self.notifications)}[/cyan]")
        console.print(f"[cyan]📁 JSON saved to: {json_file}[/cyan]")

        # Show summary
        if self.notifications:
            self._print_summary()

    def _handle_console(self, msg):
        """Handle console messages from browser"""
        try:
            text = msg.text
            if '__NOTIFICATION_JSON__:' in text:
                json_str = text.split('__NOTIFICATION_JSON__:')[1]
                notif_data = json.loads(json_str)

                # Create NotificationData object
                notification = NotificationData(
                    notification_id=notif_data.get('notification_id', ''),
                    type=notif_data.get('type', 'unknown'),
                    timestamp=notif_data.get('timestamp', ''),
                    from_handle=notif_data.get('from_handle', 'unknown'),
                    from_name=notif_data.get('from_name', ''),
                    action_text=notif_data.get('action_text', ''),
                    content=notif_data.get('content', ''),
                    mentioned_users=notif_data.get('mentioned_users', []),
                    raw_text=notif_data.get('raw_text', '')
                )

                # Only add if not seen before
                if notification.notification_id not in self.seen_ids:
                    self.seen_ids.add(notification.notification_id)
                    self.notifications.append(notification)

                    # Print notification
                    console.print(f"[green]📬 New notification:[/green] @{notification.from_handle} - {notification.type}")

        except Exception as e:
            pass  # Silently ignore non-notification messages

    def _save_json(self, filepath: Path):
        """Save notifications to JSON file"""
        output = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_notifications": len(self.notifications),
                "types": {}
            },
            "notifications": []
        }

        # Count types
        type_counts = {}
        for notif in self.notifications:
            type_counts[notif.type] = type_counts.get(notif.type, 0) + 1
        output["metadata"]["types"] = type_counts

        # Add notifications
        for notif in self.notifications:
            output["notifications"].append(asdict(notif))

        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)

    def _print_summary(self):
        """Print summary of captured notifications"""
        table = Table(title="Notification Summary")
        table.add_column("Type", style="cyan")
        table.add_column("Count", style="green")
        table.add_column("Example From", style="yellow")

        type_examples = {}
        for notif in self.notifications:
            if notif.type not in type_examples:
                type_examples[notif.type] = {
                    'count': 0,
                    'example': f"@{notif.from_handle}"
                }
            type_examples[notif.type]['count'] += 1

        for notif_type, data in type_examples.items():
            table.add_row(notif_type, str(data['count']), data['example'])

        console.print(table)


async def main():
    parser = argparse.ArgumentParser(description='Parse X/Twitter notifications to JSON')
    parser.add_argument('duration', type=int, nargs='?', default=60,
                       help='Duration to monitor in seconds (default: 60)')
    args = parser.parse_args()

    parser_instance = NotificationJSONParser()
    await parser_instance.parse_notifications(args.duration)


if __name__ == "__main__":
    asyncio.run(main())