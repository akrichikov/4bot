"""
Event-based interceptor for X/Twitter posts using Playwright.
Monitors DOM changes and intercepts new posts in real-time.
"""

from __future__ import annotations
import asyncio
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Pattern, Set
from playwright.async_api import Page, ConsoleMessage
import logging

logger = logging.getLogger(__name__)


@dataclass
class PostEvent:
    """Represents an intercepted X/Twitter post."""
    id: str
    author: str
    author_handle: str
    content: str
    timestamp: datetime
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    has_media: bool = False
    media_urls: List[str] = field(default_factory=list)
    is_retweet: bool = False
    is_reply: bool = False
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PatternSubscription:
    """Pattern-based subscription for filtering posts."""
    id: str
    name: str
    patterns: List[Pattern] = field(default_factory=list)
    keywords: Set[str] = field(default_factory=set)
    authors: Set[str] = field(default_factory=set)
    exclude_patterns: List[Pattern] = field(default_factory=list)
    exclude_keywords: Set[str] = field(default_factory=set)
    callback: Optional[Callable[[PostEvent], None]] = None
    active: bool = True

    def matches(self, post: PostEvent) -> bool:
        """Check if post matches subscription criteria."""
        if not self.active:
            return False

        # Check exclusions first
        content_lower = post.content.lower()
        if self.exclude_keywords and any(kw.lower() in content_lower for kw in self.exclude_keywords):
            return False
        if self.exclude_patterns and any(p.search(post.content) for p in self.exclude_patterns):
            return False

        # Check inclusions (if any specified)
        matches = True
        if self.patterns:
            matches = matches and any(p.search(post.content) for p in self.patterns)
        if self.keywords:
            matches = matches and any(kw.lower() in content_lower for kw in self.keywords)
        if self.authors:
            matches = matches and (post.author_handle.lower() in {a.lower() for a in self.authors})

        return matches


class EventInterceptor:
    """Main event interceptor for X/Twitter posts."""

    def __init__(self):
        self.subscriptions: Dict[str, PatternSubscription] = {}
        self.seen_posts: Set[str] = set()
        self.callbacks: List[Callable[[PostEvent], None]] = []
        self._monitoring = False

    def add_subscription(self, subscription: PatternSubscription) -> None:
        """Add a pattern subscription."""
        self.subscriptions[subscription.id] = subscription
        logger.info(f"Added subscription: {subscription.name}")

    def remove_subscription(self, subscription_id: str) -> None:
        """Remove a pattern subscription."""
        if subscription_id in self.subscriptions:
            del self.subscriptions[subscription_id]
            logger.info(f"Removed subscription: {subscription_id}")

    def add_callback(self, callback: Callable[[PostEvent], None]) -> None:
        """Add a global callback for all posts."""
        self.callbacks.append(callback)

    async def inject_observer(self, page: Page) -> None:
        """Inject DOM observer script into the page."""
        observer_script = """
        (() => {
            // Check if observer already injected
            if (window.__xEventObserver) {
                console.log('[EventInterceptor] Observer already active');
                return;
            }

            console.log('[EventInterceptor] Injecting DOM observer...');

            // Configuration
            const config = {
                childList: true,
                subtree: true,
                attributes: true,
                attributeFilter: ['data-testid']
            };

            // Track seen posts
            const seenPosts = new Set();

            // Extract post data from article element
            function extractPostData(article) {
                try {
                    // Get unique identifier
                    const link = article.querySelector('a[href*="/status/"]');
                    if (!link) return null;

                    const postId = link.href.split('/status/')[1]?.split('?')[0];
                    if (!postId || seenPosts.has(postId)) return null;

                    seenPosts.add(postId);

                    // Extract author info
                    const authorElement = article.querySelector('[data-testid="User-Name"]');
                    const authorName = authorElement?.querySelector('span')?.textContent || '';
                    const authorHandle = authorElement?.querySelector('a[href^="/"]')?.href.split('/').pop() || '';

                    // Extract content
                    const contentElement = article.querySelector('[data-testid="tweetText"]');
                    const content = contentElement?.textContent || '';

                    // Extract metrics
                    const replyButton = article.querySelector('[data-testid="reply"]');
                    const retweetButton = article.querySelector('[data-testid="retweet"]');
                    const likeButton = article.querySelector('[data-testid="like"], [data-testid="unlike"]');

                    const replies = parseInt(replyButton?.querySelector('span')?.textContent || '0');
                    const retweets = parseInt(retweetButton?.querySelector('span')?.textContent || '0');
                    const likes = parseInt(likeButton?.querySelector('span')?.textContent || '0');

                    // Check for media
                    const hasMedia = !!article.querySelector('[data-testid="tweetPhoto"], [data-testid="videoPlayer"], [data-testid="card.wrapper"]');
                    const mediaElements = article.querySelectorAll('img[src*="media"], video source');
                    const mediaUrls = Array.from(mediaElements).map(el => el.src || el.currentSrc).filter(Boolean);

                    // Check if retweet or reply
                    const isRetweet = !!article.querySelector('[data-testid="socialContext"]');
                    const isReply = !!article.querySelector('[data-testid="caret"]')?.closest('div')?.textContent?.includes('Replying to');

                    return {
                        id: postId,
                        author: authorName,
                        authorHandle: authorHandle,
                        content: content,
                        timestamp: new Date().toISOString(),
                        replies: replies,
                        retweets: retweets,
                        likes: likes,
                        hasMedia: hasMedia,
                        mediaUrls: mediaUrls,
                        isRetweet: isRetweet,
                        isReply: isReply
                    };
                } catch (error) {
                    console.error('[EventInterceptor] Error extracting post data:', error);
                    return null;
                }
            }

            // Mutation observer callback
            function observerCallback(mutations) {
                for (const mutation of mutations) {
                    for (const node of mutation.addedNodes) {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            // Check for article elements (tweets)
                            const articles = node.tagName === 'ARTICLE' ? [node] : node.querySelectorAll?.('article');

                            if (articles?.length) {
                                for (const article of articles) {
                                    const postData = extractPostData(article);
                                    if (postData) {
                                        // Send to Python via console
                                        console.log('__POST_EVENT__:' + JSON.stringify(postData));
                                    }
                                }
                            }
                        }
                    }
                }
            }

            // Create observer
            const observer = new MutationObserver(observerCallback);

            // Start observing
            observer.observe(document.body, config);

            // Store reference
            window.__xEventObserver = observer;

            // Initial scan for existing posts
            const existingArticles = document.querySelectorAll('article');
            existingArticles.forEach(article => {
                const postData = extractPostData(article);
                if (postData) {
                    console.log('__POST_EVENT__:' + JSON.stringify(postData));
                }
            });

            console.log('[EventInterceptor] Observer active, monitoring for posts...');

            // Return cleanup function
            return () => {
                observer.disconnect();
                window.__xEventObserver = null;
                console.log('[EventInterceptor] Observer disconnected');
            };
        })();
        """

        await page.evaluate(observer_script)
        logger.info("DOM observer injected successfully")

    async def start_monitoring(self, page: Page) -> None:
        """Start monitoring for posts on the page."""
        if self._monitoring:
            logger.warning("Already monitoring")
            return

        self._monitoring = True

        # Set up console message handler
        async def handle_console(msg: ConsoleMessage):
            text = msg.text
            if text.startswith('__POST_EVENT__:'):
                try:
                    post_data = json.loads(text.replace('__POST_EVENT__:', ''))
                    await self._handle_post_event(post_data)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse post event: {e}")

        page.on("console", handle_console)

        # Inject observer
        await self.inject_observer(page)
        logger.info("Started monitoring for posts")

    async def stop_monitoring(self, page: Page) -> None:
        """Stop monitoring for posts."""
        if not self._monitoring:
            return

        self._monitoring = False

        # Remove observer from page
        await page.evaluate("if (window.__xEventObserver) window.__xEventObserver.disconnect();")
        logger.info("Stopped monitoring for posts")

    async def _handle_post_event(self, post_data: Dict[str, Any]) -> None:
        """Handle an intercepted post event."""
        # Check if we've seen this post
        post_id = post_data.get('id')
        if not post_id or post_id in self.seen_posts:
            return

        self.seen_posts.add(post_id)

        # Create PostEvent
        post = PostEvent(
            id=post_id,
            author=post_data.get('author', ''),
            author_handle=post_data.get('authorHandle', ''),
            content=post_data.get('content', ''),
            timestamp=datetime.fromisoformat(post_data.get('timestamp', datetime.now().isoformat())),
            likes=post_data.get('likes', 0),
            retweets=post_data.get('retweets', 0),
            replies=post_data.get('replies', 0),
            has_media=post_data.get('hasMedia', False),
            media_urls=post_data.get('mediaUrls', []),
            is_retweet=post_data.get('isRetweet', False),
            is_reply=post_data.get('isReply', False),
            raw_data=post_data
        )

        # Check subscriptions
        for subscription in self.subscriptions.values():
            if subscription.matches(post):
                logger.info(f"Post {post.id} matches subscription: {subscription.name}")
                if subscription.callback:
                    await asyncio.create_task(self._safe_callback(subscription.callback, post))

        # Call global callbacks
        for callback in self.callbacks:
            await asyncio.create_task(self._safe_callback(callback, post))

    async def _safe_callback(self, callback: Callable, post: PostEvent) -> None:
        """Safely execute a callback."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(post)
            else:
                callback(post)
        except Exception as e:
            logger.error(f"Callback error: {e}")


# Example usage functions
def create_keyword_subscription(
    name: str,
    keywords: List[str],
    callback: Optional[Callable] = None
) -> PatternSubscription:
    """Create a simple keyword-based subscription."""
    return PatternSubscription(
        id=f"keyword_{name}_{datetime.now().timestamp()}",
        name=name,
        keywords=set(keywords),
        callback=callback
    )


def create_author_subscription(
    name: str,
    authors: List[str],
    callback: Optional[Callable] = None
) -> PatternSubscription:
    """Create an author-based subscription."""
    return PatternSubscription(
        id=f"author_{name}_{datetime.now().timestamp()}",
        name=name,
        authors=set(authors),
        callback=callback
    )


def create_regex_subscription(
    name: str,
    patterns: List[str],
    callback: Optional[Callable] = None
) -> PatternSubscription:
    """Create a regex pattern-based subscription."""
    compiled_patterns = [re.compile(p, re.IGNORECASE) for p in patterns]
    return PatternSubscription(
        id=f"regex_{name}_{datetime.now().timestamp()}",
        name=name,
        patterns=compiled_patterns,
        callback=callback
    )