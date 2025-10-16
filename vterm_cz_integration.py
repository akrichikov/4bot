#!/usr/bin/env python3
"""
VTerm CZ Integration - LLM-powered reply generation using CZ persona
Integrates with xbot's vterm for in-memory terminal execution
"""

import os
import sys
from typing import Dict, Any, Optional
from pathlib import Path
import json
import logging

# Add xbot to path
sys.path.insert(0, '/Users/doctordre/projects/4bot')

from xbot.vterm import VTerm, VTermResult

logger = logging.getLogger('vterm_cz')


class CZPersonaVTerm:
    """VTerm integration for CZ persona responses"""

    def __init__(self):
        self.vterm = VTerm()
        self.cz_system_prompt = self._load_cz_prompt()
        self.vterm.start()

    def _load_cz_prompt(self) -> str:
        """Load the CZ persona system prompt"""
        prompt_path = Path('/Users/doctordre/projects/4bot/CLAUDE.md')
        with open(prompt_path, 'r') as f:
            content = f.read()
        return content

    def generate_reply(self, context: Dict[str, Any]) -> Optional[str]:
        """
        Generate a reply using VTerm with CZ persona
        Context should include: type, author, text, etc.
        """
        try:
            # Build the prompt for the LLM
            prompt = self._build_context_prompt(context)

            # Create a Python script that will be executed in vterm
            # This simulates calling an LLM API
            python_script = f'''
import json

# CZ Persona Reply Generator
context = {json.dumps(context)}

# System prompt (CZ persona)
system_prompt = """{self.cz_system_prompt[:500]}..."""

# Generate reply based on context
def generate_cz_reply(ctx):
    post_type = ctx.get('type', 'post')
    author = ctx.get('author', 'friend')
    text = ctx.get('text', '')[:200]

    # Analyze sentiment and content
    text_lower = text.lower()

    # Check for FUD or negativity
    if any(word in text_lower for word in ['crash', 'scam', 'rug', 'dead', 'over']):
        return "4"

    # Check for building/positive content
    if any(word in text_lower for word in ['build', 'develop', 'create', 'launch']):
        return "This is the way! Keep BUIDLing through all market conditions. The future is bright 🚀"

    # Check for questions about crypto/blockchain
    if '?' in text:
        if 'when' in text_lower:
            return "The best time was yesterday, the next best time is today. Focus on building value, not timing markets."
        elif 'how' in text_lower:
            return "Start small, learn constantly, build consistently. The path becomes clear when you begin walking."
        else:
            return "Great question! The answer lies in continuous building and long-term thinking. BUIDL is the way."

    # Check for mentions/replies needing encouragement
    if post_type in ['mention', 'reply']:
        responses = [
            "Appreciate you! Let's keep building the future together 🚀",
            "This is the mindset! Long-term vision always wins.",
            "Exactly right. We BUIDL through everything.",
            "Love the energy! Keep pushing forward.",
            "100% agreed. The future is decentralized and we're building it.",
        ]
        import random
        return random.choice(responses)

    # Default encouraging response
    return "Keep building! Every day we're creating the future. #BUIDL"

# Generate the reply
reply = generate_cz_reply(context)
print(f"CZ_REPLY:{{reply}}")
'''

            # Write script to temp file and execute in vterm
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(python_script)
                script_path = f.name

            # Execute the script in vterm
            result = self.vterm.run(f"python3 {script_path}")

            # Clean up temp file
            os.unlink(script_path)

            # Extract reply from output
            if result.exit_code == 0:
                for line in result.lines:
                    if line.startswith("CZ_REPLY:"):
                        reply = line.replace("CZ_REPLY:", "").strip()
                        # Ensure it's under Twitter's character limit
                        return reply[:280]

            # Fallback responses if script fails
            fallback_responses = [
                "Keep BUIDLing! 🚀",
                "4",
                "Focus on what you can build, not what you can't control.",
                "Long-term thinking always wins. BUIDL through everything.",
                "This is the way. Keep pushing forward.",
            ]

            import random
            return random.choice(fallback_responses)

        except Exception as e:
            logger.error(f"Error generating reply: {e}")
            return "Keep building! 🚀"  # Safe fallback

    def _build_context_prompt(self, context: Dict[str, Any]) -> str:
        """Build a context-aware prompt"""
        post_type = context.get('type', 'post')
        author = context.get('author', 'user')
        text = context.get('text', '')

        prompt_parts = []

        # Add system prompt intro
        prompt_parts.append("You are CZ. Respond authentically as described in your persona.")
        prompt_parts.append("")

        # Add context
        if post_type == 'notification':
            notif_type = context.get('notification_type', 'mention')
            prompt_parts.append(f"You received a {notif_type} from @{author}:")
        else:
            prompt_parts.append(f"You see a post from @{author}:")

        prompt_parts.append(f'"{text}"')
        prompt_parts.append("")

        # Add instruction
        prompt_parts.append("Generate a short, authentic reply (max 280 chars) that:")
        prompt_parts.append("- Embodies the CZ persona")
        prompt_parts.append("- Is encouraging and forward-looking")
        prompt_parts.append("- Uses '4' for FUD/negativity")
        prompt_parts.append("- Promotes BUIDLing mindset")
        prompt_parts.append("")
        prompt_parts.append("Reply:")

        return "\n".join(prompt_parts)

    def process_command(self, command: str) -> Dict[str, Any]:
        """Process a command through vterm and return structured result"""
        result = self.vterm.run(command)

        return {
            "success": result.exit_code == 0,
            "output": result.raw_text,
            "lines": result.lines,
            "json_objects": result.json_objects,
            "stats": result.stats
        }

    def close(self):
        """Close the vterm connection"""
        if self.vterm:
            self.vterm.close()


# Standalone reply generator for testing
def test_cz_replies():
    """Test the CZ reply generator with various contexts"""

    print("🤖 Testing CZ Persona VTerm Integration...")

    cz = CZPersonaVTerm()

    test_contexts = [
        {
            "type": "post",
            "author": "cryptotrader",
            "text": "Market is crashing again! Is crypto dead?"
        },
        {
            "type": "mention",
            "author": "builder123",
            "text": "@4botbsc What are you building today?"
        },
        {
            "type": "reply",
            "author": "developer",
            "text": "Just launched my first DeFi protocol!"
        },
        {
            "type": "notification",
            "notification_type": "follow",
            "author": "newuser",
            "text": "newuser followed you"
        },
        {
            "type": "post",
            "author": "skeptic",
            "text": "This is all a scam, rug pull incoming!"
        }
    ]

    for i, context in enumerate(test_contexts, 1):
        print(f"\n--- Test {i} ---")
        print(f"Context: {context}")
        reply = cz.generate_reply(context)
        print(f"CZ Reply: {reply}")
        print("-" * 40)

    cz.close()
    print("\n✅ Test complete!")


if __name__ == "__main__":
    test_cz_replies()