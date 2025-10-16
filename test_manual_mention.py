#!/usr/bin/env python3
"""Send a test mention to RabbitMQ to test the complete pipeline"""

from rabbitmq_manager import RabbitMQManager
import time

# The mention you tagged
mention_url = "https://x.com/krichikov10228/status/1978870565835542864"
mention_id = "1978870565835542864"
author = "krichikov10228"
content = "Test mention to @4botbsc - This should trigger an auto-reply!"

print("🧪 Sending test mention to RabbitMQ pipeline...")
print(f"   Author: @{author}")
print(f"   Tweet: {mention_url}")
print()

rabbitmq = RabbitMQManager()
rabbitmq.connect()

success = rabbitmq.publish_cz_reply_request(
    post_url=mention_url,
    post_id=mention_id,
    author_handle=author,
    content=content
)

if success:
    print("✅ Test mention published to RabbitMQ!")
    print()
    print("📋 Pipeline flow:")
    print("   1. ✅ Message in 4bot_request queue")
    print("   2. ⏳ VTerm Proxy will generate CZ reply...")
    print("   3. ⏳ Reply will be published to 4bot_response queue...")
    print("   4. ⏳ Reply Poster will post it to Twitter/X...")
    print()
    print("Check logs/vterm_proxy.log and logs/cz_reply_poster.log for progress!")
else:
    print("❌ Failed to publish test mention")

rabbitmq.close()
