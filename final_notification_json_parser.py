#!/usr/bin/env python3
"""
Final Notification JSON Parser with Unicode Support
Captures all X/Twitter notifications with comprehensive detail extraction
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict, field
from playwright.async_api import async_playwright
import logging
import argparse
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler('notification_parser.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class NotificationUser:
    """User involved in notification"""
    handle: str
    display_name: str = ""
    avatar_url: str = ""
    verified: bool = False


@dataclass
class PostContent:
    """Content of a post in notification"""
    text: str = ""
    has_media: bool = False
    media_count: int = 0
    quoted_post: Optional[str] = None
    urls: List[str] = field(default_factory=list)
    hashtags: List[str] = field(default_factory=list)


@dataclass
class NotificationMetrics:
    """Engagement metrics if available"""
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    views: int = 0


@dataclass
class ParsedNotification:
    """Complete parsed notification data"""
    notification_id: str
    type: str  # like, retweet, reply, mention, follow, quote
    timestamp_captured: str
    timestamp_event: Optional[str] = None
    actor: Optional[NotificationUser] = None
    target_post: Optional[PostContent] = None
    new_content: Optional[PostContent] = None
    metrics: Optional[NotificationMetrics] = None
    mentioned_users: List[str] = field(default_factory=list)
    raw_text: str = ""


class NotificationJSONParser:
    def __init__(self):
        self.notifications: List[ParsedNotification] = []
        self.seen_ids = set()
        self.stats = {
            'total': 0,
            'likes': 0,
            'retweets': 0,
            'replies': 0,
            'mentions': 0,
            'follows': 0,
            'quotes': 0,
            'unknown': 0
        }

    async def parse_notifications(self, duration: int = 60):
        """Parse notifications for specified duration"""
        console.print(Panel.fit(
            "[bold cyan]X/Twitter Notification JSON Parser[/bold cyan]\n"
            "[dim]Extracting comprehensive notification data[/dim]",
            border_style="cyan"
        ))

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
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process'
                ]
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )

            await context.add_cookies(cookies)
            page = await context.new_page()

            # Setup console message handler
            page.on("console", lambda msg: self._handle_console(msg))

            console.print("[cyan]📡 Navigating to notifications...[/cyan]")
            await page.goto('https://x.com/notifications', wait_until='domcontentloaded')
            await asyncio.sleep(3)

            # Inject comprehensive extraction script
            await self._inject_extraction_script(page)

            console.print("[green]✅ Extraction script injected[/green]")

            # Monitor with progress display
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                TimeElapsedColumn(),
                console=console
            ) as progress:

                task = progress.add_task(
                    f"[cyan]Monitoring notifications for {duration}s...",
                    total=duration
                )

                start_time = datetime.now()
                last_refresh = start_time
                last_count = 0

                while (datetime.now() - start_time).seconds < duration:
                    elapsed = (datetime.now() - start_time).seconds
                    progress.update(task, completed=elapsed)

                    # Update description with count
                    if len(self.notifications) != last_count:
                        progress.update(
                            task,
                            description=f"[cyan]Captured {len(self.notifications)} notifications..."
                        )
                        last_count = len(self.notifications)

                    # Auto-refresh every 20 seconds
                    if (datetime.now() - last_refresh).seconds >= 20:
                        console.print(f"[dim]🔄 Refreshing page (captured {len(self.notifications)} so far)...[/dim]")
                        await page.reload(wait_until='domcontentloaded')
                        await asyncio.sleep(3)
                        await self._inject_extraction_script(page)
                        last_refresh = datetime.now()

                    await asyncio.sleep(0.5)

            await browser.close()

        # Save results
        self._save_json(json_file)
        self._save_human_readable(log_dir / f"notifications_{timestamp}.txt")

        # Display summary
        self._display_summary()

        console.print(f"\n[bold green]✅ Complete![/bold green]")
        console.print(f"[cyan]📊 Total notifications: {len(self.notifications)}[/cyan]")
        console.print(f"[cyan]📁 JSON: {json_file}[/cyan]")

    async def _inject_extraction_script(self, page):
        """Inject the notification extraction JavaScript"""
        await page.evaluate("""
            (() => {
                const processedNotifications = new Set();
                let notificationCount = 0;

                // Simple hash function for Unicode-safe ID generation
                function generateId(text) {
                    let hash = 0;
                    for (let i = 0; i < Math.min(text.length, 200); i++) {
                        const char = text.charCodeAt(i);
                        hash = ((hash << 5) - hash) + char;
                        hash = hash & hash; // Convert to 32bit integer
                    }
                    return 'notif_' + Math.abs(hash).toString(36) + '_' + Date.now().toString(36);
                }

                function extractNotificationData(element) {
                    try {
                        const elementText = element.textContent || '';
                        const notifId = generateId(elementText);

                        if (processedNotifications.has(notifId)) return;
                        processedNotifications.add(notifId);
                        notificationCount++;

                        // Build comprehensive notification object
                        const notifData = {
                            notification_id: notifId,
                            type: 'unknown',
                            timestamp_captured: new Date().toISOString(),
                            timestamp_event: null,
                            actor: {
                                handle: 'unknown',
                                display_name: '',
                                avatar_url: '',
                                verified: false
                            },
                            target_post: null,
                            new_content: null,
                            metrics: null,
                            mentioned_users: [],
                            raw_text: elementText.substring(0, 1000)
                        };

                        // Extract user information from links
                        const userLinks = element.querySelectorAll('a[href^="/"][role="link"]');
                        userLinks.forEach((link, index) => {
                            const href = link.getAttribute('href');
                            if (href && !href.includes('/status/') && index === 0) {
                                notifData.actor.handle = href.split('/').pop() || 'unknown';

                                // Get display name
                                const nameElement = link.querySelector('span > span');
                                if (nameElement) {
                                    notifData.actor.display_name = nameElement.textContent || '';
                                }

                                // Check for verification badge
                                const verifiedBadge = link.querySelector('[data-testid="icon-verified"]');
                                if (verifiedBadge) {
                                    notifData.actor.verified = true;
                                }
                            }
                        });

                        // Extract avatar
                        const avatar = element.querySelector('img[src*="profile_images"]');
                        if (avatar) {
                            notifData.actor.avatar_url = avatar.src;
                        }

                        // Detect notification type with better patterns
                        const textLower = elementText.toLowerCase();
                        const textPatterns = {
                            'like': ['liked your', 'liked a post', 'likes your'],
                            'retweet': ['retweeted', 'reposted', 'retweets your'],
                            'reply': ['replied to', 'replying to', 'replied'],
                            'follow': ['followed you', 'follows you', 'started following'],
                            'mention': ['mentioned you', 'tagged you', 'mentions you'],
                            'quote': ['quoted your', 'quote tweeted', 'quoted']
                        };

                        for (const [type, patterns] of Object.entries(textPatterns)) {
                            if (patterns.some(pattern => textLower.includes(pattern))) {
                                notifData.type = type;
                                break;
                            }
                        }

                        // Extract post content if present
                        const tweetTextElement = element.querySelector('[data-testid="tweetText"]');
                        if (tweetTextElement) {
                            const postContent = {
                                text: tweetTextElement.textContent || '',
                                has_media: false,
                                media_count: 0,
                                quoted_post: null,
                                urls: [],
                                hashtags: []
                            };

                            // Check for media
                            const mediaElements = element.querySelectorAll('[data-testid="tweetPhoto"], [data-testid="videoPlayer"], [data-testid="card.wrapper"]');
                            if (mediaElements.length > 0) {
                                postContent.has_media = true;
                                postContent.media_count = mediaElements.length;
                            }

                            // Extract hashtags
                            const hashtagRegex = /#[\\w]+/g;
                            const hashtags = postContent.text.match(hashtagRegex);
                            if (hashtags) {
                                postContent.hashtags = hashtags;
                            }

                            // Extract URLs
                            const urlElements = element.querySelectorAll('a[href^="http"]');
                            urlElements.forEach(urlEl => {
                                const url = urlEl.getAttribute('href');
                                if (url) {
                                    postContent.urls.push(url);
                                }
                            });

                            notifData.new_content = postContent;
                        }

                        // Extract metrics if available
                        const likeButton = element.querySelector('[data-testid="like"]');
                        const retweetButton = element.querySelector('[data-testid="retweet"]');
                        const replyButton = element.querySelector('[data-testid="reply"]');

                        if (likeButton || retweetButton || replyButton) {
                            notifData.metrics = {
                                likes: 0,
                                retweets: 0,
                                replies: 0,
                                views: 0
                            };

                            // Parse metric values
                            [likeButton, retweetButton, replyButton].forEach(btn => {
                                if (btn) {
                                    const valueEl = btn.querySelector('span');
                                    if (valueEl && valueEl.textContent) {
                                        const value = parseInt(valueEl.textContent.replace(/[^0-9]/g, '')) || 0;
                                        if (btn === likeButton) notifData.metrics.likes = value;
                                        else if (btn === retweetButton) notifData.metrics.retweets = value;
                                        else if (btn === replyButton) notifData.metrics.replies = value;
                                    }
                                }
                            });
                        }

                        // Extract mentioned users
                        const mentions = elementText.match(/@[a-zA-Z0-9_]+/g);
                        if (mentions) {
                            notifData.mentioned_users = [...new Set(mentions)];
                        }

                        // Extract timestamp if available
                        const timeElement = element.querySelector('time');
                        if (timeElement) {
                            notifData.timestamp_event = timeElement.getAttribute('datetime');
                        }

                        // Send to Python
                        console.log('__NOTIF_JSON__:' + JSON.stringify(notifData));
                        return notifData;

                    } catch (error) {
                        console.error('Extraction error:', error.message);
                        return null;
                    }
                }

                // Process existing notifications
                const existingNotifs = document.querySelectorAll('article, [data-testid="cellInnerDiv"]');
                console.log(`Processing ${existingNotifs.length} existing elements`);
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
                                    const elements = node.querySelectorAll('article, [data-testid="cellInnerDiv"]');
                                    elements.forEach(extractNotificationData);
                                }
                            }
                        });
                    });
                });

                observer.observe(document.body, {
                    childList: true,
                    subtree: true
                });

                console.log('Notification extractor active with Unicode support');
                return notificationCount;
            })();
        """)

    def _handle_console(self, msg):
        """Handle console messages from browser"""
        try:
            text = msg.text
            if '__NOTIF_JSON__:' in text:
                json_str = text.split('__NOTIF_JSON__:')[1]
                data = json.loads(json_str)

                # Create ParsedNotification from the data
                notification = ParsedNotification(
                    notification_id=data['notification_id'],
                    type=data['type'],
                    timestamp_captured=data['timestamp_captured'],
                    timestamp_event=data.get('timestamp_event'),
                    actor=NotificationUser(**data['actor']) if data.get('actor') else None,
                    target_post=PostContent(**data['target_post']) if data.get('target_post') else None,
                    new_content=PostContent(**data['new_content']) if data.get('new_content') else None,
                    metrics=NotificationMetrics(**data['metrics']) if data.get('metrics') else None,
                    mentioned_users=data.get('mentioned_users', []),
                    raw_text=data.get('raw_text', '')
                )

                if notification.notification_id not in self.seen_ids:
                    self.seen_ids.add(notification.notification_id)
                    self.notifications.append(notification)
                    self.stats['total'] += 1
                    self.stats[notification.type] = self.stats.get(notification.type, 0) + 1

                    # Print notification info
                    actor_name = notification.actor.handle if notification.actor else 'unknown'
                    console.print(
                        f"[green]📬[/green] {notification.type.upper()}: "
                        f"@{actor_name}"
                    )

        except Exception as e:
            # Silently ignore parsing errors
            pass

    def _save_json(self, filepath: Path):
        """Save notifications to JSON file"""
        output = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "total_notifications": len(self.notifications),
                "stats": self.stats,
                "account": "4botbsc@gmail.com"
            },
            "notifications": []
        }

        # Add all notifications with full detail
        for notif in self.notifications:
            notif_dict = asdict(notif)
            output["notifications"].append(notif_dict)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

    def _save_human_readable(self, filepath: Path):
        """Save human-readable text summary"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("X/TWITTER NOTIFICATION REPORT\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Total Notifications: {len(self.notifications)}\n\n")

            # Type breakdown
            f.write("NOTIFICATION TYPES:\n")
            f.write("-" * 30 + "\n")
            for notif_type, count in self.stats.items():
                if count > 0 and notif_type != 'total':
                    f.write(f"  {notif_type.capitalize()}: {count}\n")
            f.write("\n")

            # Detailed notifications
            f.write("DETAILED NOTIFICATIONS:\n")
            f.write("=" * 70 + "\n\n")

            for i, notif in enumerate(self.notifications, 1):
                f.write(f"#{i} [{notif.type.upper()}]\n")
                if notif.actor:
                    f.write(f"  From: @{notif.actor.handle}")
                    if notif.actor.display_name:
                        f.write(f" ({notif.actor.display_name})")
                    if notif.actor.verified:
                        f.write(" ✓")
                    f.write("\n")

                if notif.new_content and notif.new_content.text:
                    f.write(f"  Content: {notif.new_content.text[:200]}\n")
                    if notif.new_content.has_media:
                        f.write(f"  Media: {notif.new_content.media_count} item(s)\n")
                    if notif.new_content.hashtags:
                        f.write(f"  Hashtags: {', '.join(notif.new_content.hashtags)}\n")

                if notif.metrics:
                    f.write(f"  Metrics: ")
                    metrics_parts = []
                    if notif.metrics.likes > 0:
                        metrics_parts.append(f"{notif.metrics.likes} likes")
                    if notif.metrics.retweets > 0:
                        metrics_parts.append(f"{notif.metrics.retweets} retweets")
                    if notif.metrics.replies > 0:
                        metrics_parts.append(f"{notif.metrics.replies} replies")
                    f.write(", ".join(metrics_parts) + "\n")

                if notif.mentioned_users:
                    f.write(f"  Mentions: {', '.join(notif.mentioned_users)}\n")

                f.write(f"  Time: {notif.timestamp_captured}\n")
                f.write("-" * 50 + "\n\n")

    def _display_summary(self):
        """Display summary table"""
        table = Table(title="Notification Summary", border_style="cyan")
        table.add_column("Type", style="cyan", justify="left")
        table.add_column("Count", style="green", justify="center")
        table.add_column("Percentage", style="yellow", justify="right")

        total = self.stats['total']
        if total > 0:
            for notif_type in ['like', 'retweet', 'reply', 'mention', 'follow', 'quote', 'unknown']:
                count = self.stats.get(notif_type, 0)
                if count > 0:
                    percentage = (count / total) * 100
                    table.add_row(
                        notif_type.capitalize(),
                        str(count),
                        f"{percentage:.1f}%"
                    )

            table.add_row("", "", "", style="dim")
            table.add_row("TOTAL", str(total), "100%", style="bold")

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