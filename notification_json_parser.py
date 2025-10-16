#!/usr/bin/env python3
"""
Comprehensive X/Twitter Notification JSON Parser
Extracts all possible details from notifications and outputs structured JSON
"""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from enum import Enum
import re


# Setup structured logging
log_dir = Path("notification_json_logs")
log_dir.mkdir(exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

# JSON file for structured notifications
json_log_file = log_dir / f'notifications_{timestamp}.json'
text_log_file = log_dir / f'notifications_{timestamp}.log'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.FileHandler(text_log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


@dataclass
class NotificationUser:
    """User information in notification"""
    handle: str
    display_name: Optional[str] = None
    profile_image_url: Optional[str] = None
    is_verified: bool = False
    is_blue_verified: bool = False


@dataclass
class PostContent:
    """Content of a post in notification"""
    text: Optional[str] = None
    post_id: Optional[str] = None
    url: Optional[str] = None
    has_media: bool = False
    media_count: int = 0
    media_urls: List[str] = None
    quoted_post_id: Optional[str] = None


@dataclass
class NotificationMetrics:
    """Engagement metrics"""
    likes: Optional[int] = None
    retweets: Optional[int] = None
    replies: Optional[int] = None
    views: Optional[int] = None


@dataclass
class ParsedNotification:
    """Complete parsed notification"""
    notification_id: str
    type: str  # like, retweet, reply, mention, follow, quote
    timestamp_captured: str
    timestamp_relative: Optional[str] = None  # "2m ago", "1h ago"

    # Actor (who performed the action)
    actor: NotificationUser = None
    additional_actors: List[NotificationUser] = None  # For "X and Y liked"
    actor_count: int = 1  # Total number of actors

    # Action details
    action_text: Optional[str] = None  # "liked your post", "replied to you"

    # Target content (your post being interacted with)
    target_post: Optional[PostContent] = None

    # New content (for replies/quotes)
    new_content: Optional[PostContent] = None

    # Metrics
    metrics: Optional[NotificationMetrics] = None

    # Thread context
    is_thread: bool = False
    thread_participants: List[str] = None

    # Raw data
    raw_text: Optional[str] = None
    raw_html_snippet: Optional[str] = None


class NotificationJSONParser:
    """Comprehensive notification parser with JSON output"""

    def __init__(self):
        self.notifications: List[ParsedNotification] = []
        self.notification_count = 0
        self.json_buffer = []

    def parse_metrics_text(self, text: str) -> Optional[int]:
        """Parse metric text like '1.2K' to integer"""
        if not text:
            return None

        text = text.strip().replace(',', '')

        try:
            if 'K' in text:
                return int(float(text.replace('K', '')) * 1000)
            elif 'M' in text:
                return int(float(text.replace('M', '')) * 1000000)
            else:
                return int(text) if text.isdigit() else None
        except:
            return None

    def extract_notification_type(self, text: str) -> str:
        """Determine notification type from text patterns"""
        text_lower = text.lower()

        if 'liked your' in text_lower or 'liked a post' in text_lower:
            return 'like'
        elif 'reposted your' in text_lower or 'retweeted' in text_lower:
            return 'retweet'
        elif 'replied to' in text_lower or 'replying to' in text_lower:
            return 'reply'
        elif 'mentioned you' in text_lower:
            return 'mention'
        elif 'followed you' in text_lower:
            return 'follow'
        elif 'quoted your' in text_lower:
            return 'quote'
        elif 'sent you a message' in text_lower:
            return 'message'
        else:
            return 'unknown'

    async def process_notification_data(self, data: Dict[str, Any]):
        """Process raw notification data into structured format"""
        try:
            # Generate unique ID
            notif_id = f"{data.get('type', 'unknown')}_{datetime.now().timestamp()}"

            # Create parsed notification
            notification = ParsedNotification(
                notification_id=notif_id,
                type=data.get('type', 'unknown'),
                timestamp_captured=datetime.now().isoformat(),
                timestamp_relative=data.get('time_ago'),
                raw_text=data.get('raw_text'),
                raw_html_snippet=data.get('html_snippet', '')[:500]  # Limit HTML size
            )

            # Parse actor information
            if data.get('actor_handle'):
                notification.actor = NotificationUser(
                    handle=data['actor_handle'],
                    display_name=data.get('actor_name'),
                    profile_image_url=data.get('actor_avatar'),
                    is_verified=data.get('actor_verified', False),
                    is_blue_verified=data.get('actor_blue', False)
                )

            # Parse additional actors (for grouped notifications)
            if data.get('additional_actors'):
                notification.additional_actors = []
                for actor in data['additional_actors']:
                    notification.additional_actors.append(NotificationUser(
                        handle=actor.get('handle', 'unknown'),
                        display_name=actor.get('name')
                    ))
                notification.actor_count = len(notification.additional_actors) + 1

            # Parse action text
            notification.action_text = data.get('action_text')

            # Parse target post (your post being interacted with)
            if data.get('target_post_text') or data.get('target_post_id'):
                notification.target_post = PostContent(
                    text=data.get('target_post_text'),
                    post_id=data.get('target_post_id'),
                    url=f"https://x.com/i/status/{data.get('target_post_id')}" if data.get('target_post_id') else None,
                    has_media=data.get('target_has_media', False),
                    media_count=data.get('target_media_count', 0)
                )

            # Parse new content (for replies/quotes)
            if data.get('reply_text') or data.get('quote_text'):
                notification.new_content = PostContent(
                    text=data.get('reply_text') or data.get('quote_text'),
                    post_id=data.get('reply_post_id') or data.get('quote_post_id'),
                    has_media=data.get('reply_has_media', False)
                )

            # Parse metrics
            if any(data.get(k) for k in ['likes', 'retweets', 'replies', 'views']):
                notification.metrics = NotificationMetrics(
                    likes=self.parse_metrics_text(str(data.get('likes', 0))),
                    retweets=self.parse_metrics_text(str(data.get('retweets', 0))),
                    replies=self.parse_metrics_text(str(data.get('replies', 0))),
                    views=self.parse_metrics_text(str(data.get('views', 0)))
                )

            # Parse thread information
            if data.get('thread_participants'):
                notification.is_thread = True
                notification.thread_participants = data['thread_participants']

            # Add to notifications list
            self.notifications.append(notification)
            self.notification_count += 1

            # Convert to dict for JSON
            notif_dict = self._notification_to_dict(notification)
            self.json_buffer.append(notif_dict)

            # Log the notification
            self._log_notification(notification, notif_dict)

            # Save to JSON file immediately
            self._save_json()

        except Exception as e:
            logger.error(f"Error processing notification: {e}")

    def _notification_to_dict(self, notification: ParsedNotification) -> Dict:
        """Convert notification to dictionary for JSON serialization"""
        def convert(obj):
            if hasattr(obj, '__dict__'):
                return {k: v for k, v in obj.__dict__.items() if v is not None}
            return obj

        # Manual conversion for better control
        result = {
            'notification_id': notification.notification_id,
            'type': notification.type,
            'timestamp_captured': notification.timestamp_captured,
            'timestamp_relative': notification.timestamp_relative
        }

        # Add actor info
        if notification.actor:
            result['actor'] = {
                'handle': notification.actor.handle,
                'display_name': notification.actor.display_name,
                'is_verified': notification.actor.is_verified,
                'is_blue_verified': notification.actor.is_blue_verified
            }
            if notification.actor.profile_image_url:
                result['actor']['profile_image_url'] = notification.actor.profile_image_url

        # Add additional actors
        if notification.additional_actors:
            result['additional_actors'] = [
                {'handle': a.handle, 'display_name': a.display_name}
                for a in notification.additional_actors
            ]
            result['actor_count'] = notification.actor_count

        # Add action text
        if notification.action_text:
            result['action_text'] = notification.action_text

        # Add target post
        if notification.target_post:
            result['target_post'] = {
                'text': notification.target_post.text,
                'post_id': notification.target_post.post_id,
                'url': notification.target_post.url,
                'has_media': notification.target_post.has_media,
                'media_count': notification.target_post.media_count
            }

        # Add new content
        if notification.new_content:
            result['new_content'] = {
                'text': notification.new_content.text,
                'post_id': notification.new_content.post_id,
                'has_media': notification.new_content.has_media
            }

        # Add metrics
        if notification.metrics:
            result['metrics'] = {
                'likes': notification.metrics.likes,
                'retweets': notification.metrics.retweets,
                'replies': notification.metrics.replies,
                'views': notification.metrics.views
            }

        # Add thread info
        if notification.is_thread:
            result['is_thread'] = True
            result['thread_participants'] = notification.thread_participants

        # Add raw text for debugging
        if notification.raw_text:
            result['raw_text'] = notification.raw_text[:500]  # Limit size

        return result

    def _log_notification(self, notification: ParsedNotification, notif_dict: Dict):
        """Log notification in human-readable format"""
        emoji_map = {
            'like': '❤️',
            'retweet': '🔄',
            'reply': '💬',
            'mention': '🔔',
            'follow': '➕',
            'quote': '💭',
            'message': '✉️',
            'unknown': '📌'
        }

        emoji = emoji_map.get(notification.type, '📌')

        logger.info("=" * 70)
        logger.info(f"{emoji} NOTIFICATION #{self.notification_count}")
        logger.info(f"Type: {notification.type.upper()}")

        if notification.actor:
            logger.info(f"From: @{notification.actor.handle} ({notification.actor.display_name or 'N/A'})")
            if notification.actor.is_blue_verified:
                logger.info("  ✓ Blue verified")

        if notification.action_text:
            logger.info(f"Action: {notification.action_text}")

        if notification.target_post and notification.target_post.text:
            logger.info(f"Your post: {notification.target_post.text[:100]}...")

        if notification.new_content and notification.new_content.text:
            logger.info(f"Their content: {notification.new_content.text[:100]}...")

        if notification.metrics:
            metrics_str = []
            if notification.metrics.likes:
                metrics_str.append(f"❤️ {notification.metrics.likes}")
            if notification.metrics.retweets:
                metrics_str.append(f"🔄 {notification.metrics.retweets}")
            if notification.metrics.replies:
                metrics_str.append(f"💬 {notification.metrics.replies}")
            if metrics_str:
                logger.info(f"Metrics: {' | '.join(metrics_str)}")

        logger.info(f"JSON saved: {json_log_file}")
        logger.info("=" * 70)

    def _save_json(self):
        """Save notifications to JSON file"""
        try:
            output = {
                'metadata': {
                    'timestamp': datetime.now().isoformat(),
                    'total_notifications': self.notification_count,
                    'types': {}
                },
                'notifications': self.json_buffer
            }

            # Count notification types
            for notif in self.json_buffer:
                notif_type = notif.get('type', 'unknown')
                output['metadata']['types'][notif_type] = output['metadata']['types'].get(notif_type, 0) + 1

            # Save with pretty formatting
            with open(json_log_file, 'w') as f:
                json.dump(output, f, indent=2, ensure_ascii=False)

        except Exception as e:
            logger.error(f"Error saving JSON: {e}")

    async def monitor_notifications(self, duration_seconds=120):
        """Monitor notifications and parse to JSON"""

        logger.info("=" * 70)
        logger.info("NOTIFICATION JSON PARSER STARTED")
        logger.info(f"Duration: {duration_seconds} seconds")
        logger.info(f"JSON output: {json_log_file}")
        logger.info(f"Text log: {text_log_file}")
        logger.info("=" * 70)

        # Load cookies
        cookie_file = Path("chrome_profiles/cookies/default_cookies.json")
        with open(cookie_file, 'r') as f:
            cookies = json.load(f)

        playwright = await async_playwright().start()

        try:
            # Launch browser
            browser = await playwright.chromium.launch(
                headless=True,  # Set to False to see browser
                args=['--disable-blink-features=AutomationControlled']
            )

            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )

            await context.add_cookies(cookies)
            page = await context.new_page()

            # Enhanced extraction script with full detail capture
            extraction_script = Path('enhanced_notification_extractor.js').read_text() if Path('enhanced_notification_extractor.js').exists() else """
            (() => {
                const seenNotifications = new Set();

                function extractFullNotification(element) {
                    try {
                        // Generate unique ID
                        const elementText = element.textContent || '';
                        const notifId = btoa(elementText.substring(0, 200));

                        if (seenNotifications.has(notifId)) return;
                        seenNotifications.add(notifId);

                        // Extract everything possible
                        const data = {
                            raw_text: elementText.substring(0, 1000),
                            html_snippet: element.innerHTML.substring(0, 500),
                            timestamp: new Date().toISOString()
                        };

                        // Get actor information
                        const userLinks = element.querySelectorAll('a[href^="/"][role="link"]');
                        if (userLinks.length > 0) {
                            const firstUser = userLinks[0];
                            data.actor_handle = firstUser.href.split('/').pop();

                            // Get display name
                            const nameSpan = firstUser.querySelector('span');
                            if (nameSpan) data.actor_name = nameSpan.textContent;

                            // Check for verification badges
                            const verifiedBadge = firstUser.querySelector('[aria-label*="Verified"]');
                            if (verifiedBadge) {
                                data.actor_verified = true;
                                if (verifiedBadge.getAttribute('aria-label').includes('verified')) {
                                    data.actor_blue = true;
                                }
                            }

                            // Get avatar URL
                            const avatar = element.querySelector('img[src*="pbs.twimg.com/profile_images"]');
                            if (avatar) data.actor_avatar = avatar.src;
                        }

                        // Extract notification type and action text
                        const spans = element.querySelectorAll('span');
                        spans.forEach(span => {
                            const text = span.textContent || '';
                            if (text.includes('liked') || text.includes('reposted') ||
                                text.includes('replied') || text.includes('followed') ||
                                text.includes('mentioned') || text.includes('quoted')) {
                                data.action_text = text;

                                // Determine type
                                if (text.includes('liked')) data.type = 'like';
                                else if (text.includes('reposted')) data.type = 'retweet';
                                else if (text.includes('replied')) data.type = 'reply';
                                else if (text.includes('followed')) data.type = 'follow';
                                else if (text.includes('mentioned')) data.type = 'mention';
                                else if (text.includes('quoted')) data.type = 'quote';
                            }
                        });

                        // Get relative time
                        const timeElement = element.querySelector('time');
                        if (timeElement) {
                            data.time_ago = timeElement.textContent;
                            data.exact_time = timeElement.getAttribute('datetime');
                        }

                        // Extract post content
                        const tweetText = element.querySelector('[data-testid="tweetText"]');
                        if (tweetText) {
                            if (data.type === 'reply' || data.type === 'quote') {
                                data.reply_text = tweetText.textContent;
                            } else {
                                data.target_post_text = tweetText.textContent;
                            }
                        }

                        // Get all tweet texts if multiple (for threads)
                        const allTweets = element.querySelectorAll('[data-testid="tweetText"]');
                        if (allTweets.length > 1) {
                            data.is_thread = true;
                            data.thread_texts = Array.from(allTweets).map(t => t.textContent);
                        }

                        // Extract post ID from status link
                        const statusLink = element.querySelector('a[href*="/status/"]');
                        if (statusLink) {
                            const match = statusLink.href.match(/status\\/(\\d+)/);
                            if (match) {
                                if (data.type === 'reply' || data.type === 'quote') {
                                    data.reply_post_id = match[1];
                                } else {
                                    data.target_post_id = match[1];
                                }
                            }
                        }

                        // Extract metrics
                        const likeButton = element.querySelector('[data-testid="like"], [data-testid="unlike"]');
                        const retweetButton = element.querySelector('[data-testid="retweet"]');
                        const replyButton = element.querySelector('[data-testid="reply"]');

                        if (likeButton) {
                            const likesText = likeButton.querySelector('span')?.textContent;
                            if (likesText) data.likes = likesText;
                        }

                        if (retweetButton) {
                            const retweetsText = retweetButton.querySelector('span')?.textContent;
                            if (retweetsText) data.retweets = retweetsText;
                        }

                        if (replyButton) {
                            const repliesText = replyButton.querySelector('span')?.textContent;
                            if (repliesText) data.replies = repliesText;
                        }

                        // Check for media
                        const hasPhoto = !!element.querySelector('[data-testid="tweetPhoto"]');
                        const hasVideo = !!element.querySelector('[data-testid="videoPlayer"]');
                        const hasCard = !!element.querySelector('[data-testid="card.wrapper"]');

                        if (hasPhoto || hasVideo || hasCard) {
                            data.target_has_media = true;
                            data.target_media_count = element.querySelectorAll('img[src*="media"], video').length;
                        }

                        // Get all mentioned users
                        const mentions = [];
                        element.querySelectorAll('a[href^="/"]').forEach(link => {
                            const href = link.href;
                            if (href && !href.includes('/status/')) {
                                const handle = href.split('/').pop();
                                if (handle && !mentions.includes(handle)) {
                                    mentions.push(handle);
                                }
                            }
                        });
                        if (mentions.length > 0) data.mentioned_users = mentions;

                        // For grouped notifications (e.g., "X and 2 others liked")
                        const groupedText = elementText.match(/(\\d+) others?/);
                        if (groupedText) {
                            data.is_grouped = true;
                            data.group_count = parseInt(groupedText[1]) + 1;
                        }

                        // Set default type if not detected
                        if (!data.type) data.type = 'unknown';

                        console.log('__FULL_NOTIFICATION__:' + JSON.stringify(data));
                        return data;

                    } catch (error) {
                        console.error('Extraction error:', error);
                        return null;
                    }
                }

                // Process existing notifications
                document.querySelectorAll('article, [data-testid="cellInnerDiv"]').forEach(extractFullNotification);

                // Monitor for new
                const observer = new MutationObserver(mutations => {
                    mutations.forEach(mutation => {
                        mutation.addedNodes.forEach(node => {
                            if (node.nodeType === Node.ELEMENT_NODE && node.querySelectorAll) {
                                node.querySelectorAll('article, [data-testid="cellInnerDiv"]').forEach(extractFullNotification);
                            }
                        });
                    });
                });

                observer.observe(document.body, { childList: true, subtree: true });
                console.log('Full notification extractor active');
            })();
            """

            # Console handler
            async def handle_console(msg):
                text = msg.text
                if '__FULL_NOTIFICATION__' in text or '__ENHANCED_NOTIFICATION__' in text:
                    try:
                        json_str = text.split(':')[1] if ':' in text else text
                        data = json.loads(json_str)
                        await self.process_notification_data(data)
                    except Exception as e:
                        logger.debug(f"Console parse error: {e}")

            page.on("console", lambda msg: asyncio.create_task(handle_console(msg)))

            # Navigate to notifications
            logger.info("Navigating to notifications page...")
            await page.goto('https://x.com/notifications', wait_until='domcontentloaded')
            await asyncio.sleep(3)

            # Inject extraction script
            await page.evaluate(extraction_script)
            logger.info("Extraction script injected")
            logger.info("Monitoring notifications...")

            # Monitor for specified duration
            start_time = asyncio.get_event_loop().time()
            last_refresh = 0

            while asyncio.get_event_loop().time() - start_time < duration_seconds:
                await asyncio.sleep(1)

                # Refresh periodically to get new notifications
                if asyncio.get_event_loop().time() - last_refresh > 30:
                    logger.info(f"Refreshing... ({self.notification_count} notifications captured so far)")
                    await page.reload()
                    await asyncio.sleep(3)
                    await page.evaluate(extraction_script)
                    last_refresh = asyncio.get_event_loop().time()

            # Final save
            self._save_json()

            # Summary
            logger.info("=" * 70)
            logger.info("MONITORING COMPLETE")
            logger.info(f"Total notifications parsed: {self.notification_count}")
            logger.info(f"JSON file: {json_log_file}")

            # Type breakdown
            type_counts = {}
            for notif in self.json_buffer:
                t = notif.get('type', 'unknown')
                type_counts[t] = type_counts.get(t, 0) + 1

            logger.info("Notification types:")
            for notif_type, count in type_counts.items():
                logger.info(f"  {notif_type}: {count}")

            logger.info("=" * 70)

            await browser.close()

        except Exception as e:
            logger.error(f"Monitor error: {e}")
            import traceback
            traceback.print_exc()

        finally:
            await playwright.stop()


async def main():
    """Main entry point"""
    import sys
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 60

    print("""
    ╔══════════════════════════════════════════════════════════════════╗
    ║         X/TWITTER NOTIFICATION JSON PARSER                       ║
    ║                                                                  ║
    ║  Extracts all notification details into structured JSON          ║
    ║  Outputs: notification_json_logs/notifications_*.json           ║
    ╚══════════════════════════════════════════════════════════════════╝
    """)

    parser = NotificationJSONParser()
    await parser.monitor_notifications(duration_seconds=duration)

    print(f"\n✅ Complete! Check {json_log_file} for structured notifications")


if __name__ == "__main__":
    asyncio.run(main())