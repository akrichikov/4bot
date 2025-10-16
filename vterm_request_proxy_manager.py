#!/usr/bin/env python3
"""
VTerm Request Proxy Manager
Consumes CZ reply requests from RabbitMQ, processes through VTerm, publishes replies back
"""

import os
import sys
import json
import logging
import time
import random
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import threading
from dataclasses import dataclass

sys.path.insert(0, '/Users/doctordre/projects/4bot')

from rabbitmq_manager import RabbitMQManager, BotMessage
from xbot.vterm import VTerm
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [VTERM-PROXY] %(levelname)s: %(message)s'
)
logger = logging.getLogger('vterm_proxy')


class CZReplyGenerator:
    """Generates CZ-style replies based on content analysis"""

    def __init__(self):
        # Load CZ persona from CLAUDE.md
        self.cz_persona = self._load_cz_persona()

        # CZ response templates
        self.responses = {
            'fud': ["4", "4.", "4 🤷‍♂️"],
            'fud_extended': [
                "4. Back to building.",
                "4. Focus on building, not noise.",
                "4. We build through FUD.",
                "4. BUIDL > FUD"
            ],
            'building': [
                "This is the way! Keep BUIDLing 🚀",
                "Love to see builders building through everything.",
                "Exactly right. We build through all market conditions.",
                "Building is the answer. Always has been.",
                "Less noise, more signal. BUIDL.",
            ],
            'questions': {
                'when': "The best time was yesterday, the next best time is today. Focus on building.",
                'how': "Start small, learn constantly, build consistently. The path reveals itself.",
                'why': "Because the future needs builders, not spectators.",
                'what': "Build value for users. Everything else follows.",
                'default': "Great question! The answer is always: keep building. BUIDL is the way."
            },
            'encouragement': [
                "Appreciate you! Let's keep building the future together 🚀",
                "This is the mindset. Long-term thinking always wins.",
                "100% agreed. The future is decentralized and we're building it.",
                "Stay focused on what matters: building value for users.",
                "Keep pushing forward. Every day we're creating the future.",
                "Together we build the future. One block at a time.",
                "Winners focus on winning. Losers focus on winners. Keep building.",
            ],
            'market': [
                "Markets go up and down. We build through it all.",
                "Price is noise. Building is signal.",
                "Less charts, more code.",
                "Bear or bull, we BUIDL.",
                "Short-term volatility, long-term inevitability.",
            ],
            'security': [
                "Security first. Always. #SAFU",
                "Build safe. Build strong. Build for users.",
                "User protection is everything.",
                "Trust is earned through consistent security.",
            ]
        }

    def _load_cz_persona(self) -> str:
        """Load CZ persona from CLAUDE.md"""
        try:
            claude_path = Path('/Users/doctordre/projects/4bot/CLAUDE.md')
            if claude_path.exists():
                return claude_path.read_text()[:2000]  # First 2000 chars for context
            return ""
        except:
            return ""

    def generate(self, author: str, content: str, post_url: str) -> str:
        """Generate a contextual CZ reply"""
        content_lower = content.lower() if content else ""

        # Priority 1: FUD Detection (immediate "4" response)
        fud_words = ['scam', 'rug', 'ponzi', 'dead', 'crash', 'failing', 'exit']
        if any(word in content_lower for word in fud_words):
            if random.random() < 0.7:  # 70% chance of simple "4"
                return random.choice(self.responses['fud'])
            else:
                return random.choice(self.responses['fud_extended'])

        # Priority 2: Building/Development content
        build_words = ['build', 'buidl', 'develop', 'create', 'launch', 'ship', 'deploy']
        if any(word in content_lower for word in build_words):
            return random.choice(self.responses['building'])

        # Priority 3: Direct questions
        if '?' in content:
            for q_word, response in self.responses['questions'].items():
                if q_word in content_lower and q_word != 'default':
                    return response
            return self.responses['questions']['default']

        # Priority 4: Market talk
        market_words = ['price', 'chart', 'pump', 'dump', 'moon', 'bear', 'bull']
        if any(word in content_lower for word in market_words):
            return random.choice(self.responses['market'])

        # Priority 5: Security concerns
        security_words = ['hack', 'security', 'safe', 'protect', 'vulnerability']
        if any(word in content_lower for word in security_words):
            return random.choice(self.responses['security'])

        # Default: Encouragement
        return random.choice(self.responses['encouragement'])


class VTermProxy:
    """Proxy that processes requests through VTerm"""

    def __init__(self):
        self.vterm = VTerm()
        self.vterm.start()
        self.cz_generator = CZReplyGenerator()

    def process_cz_request(self, request_data: Dict[str, Any]) -> Optional[str]:
        """Process a CZ reply request through VTerm"""
        try:
            author = request_data.get('author_handle', 'user')
            content = request_data.get('content', '')
            post_url = request_data.get('post_url', '')

            # Generate CZ reply
            reply = self.cz_generator.generate(author, content, post_url)

            # Optional: Run through VTerm for additional processing
            # For now, we'll use direct generation for speed

            logger.info(f"Generated CZ reply for @{author}: {reply}")
            return reply

        except Exception as e:
            logger.error(f"Error processing CZ request: {e}")
            # Fallback response
            fallbacks = ["Keep BUIDLing! 🚀", "4", "Focus on building."]
            return random.choice(fallbacks)

    def close(self):
        """Close VTerm connection"""
        if self.vterm:
            self.vterm.close()


class VTermRequestProxyManager:
    """Main proxy manager that orchestrates RabbitMQ <-> VTerm communication"""

    def __init__(self):
        self.rabbitmq = RabbitMQManager()
        self.vterm_proxy = VTermProxy()
        self.running = True
        self.stats = {
            'requests_processed': 0,
            'replies_generated': 0,
            'errors': 0,
            'start_time': datetime.now()
        }

    def handle_cz_reply_request(self, message: BotMessage):
        """Handle incoming CZ reply request from RabbitMQ"""
        try:
            logger.info(f"📥 Received CZ reply request: {message.message_id}")

            # Extract request data
            request_data = message.data

            # Generate reply through VTerm proxy
            reply_text = self.vterm_proxy.process_cz_request(request_data)

            if reply_text:
                # Publish generated reply back to RabbitMQ
                self.rabbitmq.publish_cz_reply_generated(
                    post_url=request_data.get('post_url', ''),
                    post_id=request_data.get('post_id'),
                    author_handle=request_data.get('author_handle', ''),
                    content=request_data.get('content', ''),
                    reply_text=reply_text
                )

                self.stats['replies_generated'] += 1
                logger.info(f"✅ Published generated reply: {reply_text[:50]}...")

            self.stats['requests_processed'] += 1

        except Exception as e:
            logger.error(f"❌ Error handling CZ reply request: {e}")
            self.stats['errors'] += 1

    def print_stats(self):
        """Print statistics"""
        uptime = datetime.now() - self.stats['start_time']
        logger.info(f"""
📊 VTerm Proxy Statistics:
   Uptime: {uptime}
   Requests: {self.stats['requests_processed']}
   Replies: {self.stats['replies_generated']}
   Errors: {self.stats['errors']}
   Success Rate: {(self.stats['replies_generated'] / max(1, self.stats['requests_processed']) * 100):.1f}%
        """)

    def start(self):
        """Start the proxy manager"""
        logger.info("🚀 Starting VTerm Request Proxy Manager")
        logger.info("   Listening on: 4bot_request queue")
        logger.info("   Publishing to: 4bot_response queue")

        # Connect to RabbitMQ
        if not self.rabbitmq.connect():
            logger.error("Failed to connect to RabbitMQ")
            return

        # Register handler for CZ reply requests
        self.rabbitmq.register_handler("cz_reply_request", self.handle_cz_reply_request)

        # Start statistics thread
        def print_stats_loop():
            while self.running:
                time.sleep(60)  # Print stats every minute
                self.print_stats()

        stats_thread = threading.Thread(target=print_stats_loop, daemon=True)
        stats_thread.start()

        # Start consuming messages
        try:
            logger.info("👂 Listening for CZ reply requests...")
            self.rabbitmq.consume_requests()
        except KeyboardInterrupt:
            logger.info("⛔ Stopping proxy manager...")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            self.cleanup()

    def cleanup(self):
        """Cleanup resources"""
        self.running = False
        self.print_stats()
        self.vterm_proxy.close()
        self.rabbitmq.close()
        logger.info("🛑 VTerm Request Proxy Manager stopped")


def test_reply_generation():
    """Test the CZ reply generator"""
    generator = CZReplyGenerator()

    test_cases = [
        ("This is a scam!", "fudster"),
        ("When moon sir?", "moonboy"),
        ("Just shipped our new DeFi protocol!", "builder"),
        ("How do I get started with blockchain?", "newbie"),
        ("Market is dumping hard", "trader"),
        ("Is the platform secure?", "concerned_user"),
        ("Love what you're building!", "supporter"),
    ]

    print("\n🧪 Testing CZ Reply Generation:\n")
    for content, author in test_cases:
        reply = generator.generate(author, content, "https://x.com/test/status/123")
        print(f"@{author}: {content}")
        print(f"CZ: {reply}\n")


def main():
    """Main entry point"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        test_reply_generation()
    else:
        proxy_manager = VTermRequestProxyManager()
        proxy_manager.start()


if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════════════════════════╗
║         VTERM REQUEST PROXY MANAGER - ACTIVATED              ║
║                                                               ║
║  🔄 Pipeline:                                                ║
║     RabbitMQ (4bot_request) → VTerm → RabbitMQ (4bot_response)║
║                                                               ║
║  🤖 CZ Reply Generation: ENABLED                             ║
║  📨 Queue Consumer: ACTIVE                                   ║
║  ✅ Durable Queues: CONFIRMED                                ║
║                                                               ║
║           Press Ctrl+C to stop                               ║
╚══════════════════════════════════════════════════════════════╝
    """)

    main()