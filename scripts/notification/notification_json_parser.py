#!/usr/bin/env python3
"""
Thin CLI wrapper delegating to canonical xbot.notification_json_parser.
"""

import asyncio
import argparse
from pathlib import Path
import sys

# Ensure package root is importable when executed directly
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from xbot.notification_json_parser import NotificationJSONParser  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="X/Twitter notification JSON parser")
    ap.add_argument("--duration", type=int, default=60, help="Monitoring duration in seconds")
    args = ap.parse_args()

    async def _run():
        parser = NotificationJSONParser()
        await parser.parse_notifications(duration=args.duration)

    asyncio.run(_run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
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
            extraction_script = (Path(__file__).resolve().parents[0] / 'enhanced_notification_extractor.js').read_text() if (Path(__file__).resolve().parents[0] / 'enhanced_notification_extractor.js').exists() else r"""
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
