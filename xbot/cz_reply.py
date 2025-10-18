from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import random


@dataclass
class CZPersona:
    system_prompt: str = ""


class CZReplyGenerator:
    """Deterministic template-based CZ reply generator.

    Centralizes heuristics used across proxy and batch scripts to keep logic DRY.
    """

    def __init__(self, persona_path: Path | None = None):
        self.persona = CZPersona(system_prompt=self._load_persona(persona_path))
        self.fud_words = {'scam', 'rug', 'ponzi', 'dead', 'crash', 'failing', 'exit', 'fraud', 'fake', 'dump', 'worthless'}
        self.build_words = {'build', 'buidl', 'develop', 'create', 'launch', 'ship', 'deploy', 'code'}
        self.market_words = {'price', 'chart', 'pump', 'dump', 'moon', 'bear', 'bull'}
        self.security_words = {'hack', 'security', 'safe', 'protect', 'vulnerability'}

        self.responses = {
            'fud': ["4", "4.", "4 🤷‍♂️"],
            'fud_extended': [
                "4. Back to building.",
                "4. Focus on building, not noise.",
                "4. We build through FUD.",
                "4. BUIDL > FUD",
            ],
            'building': [
                "This is the way! Keep BUIDLing 🚀",
                "Love to see builders building through everything.",
                "Exactly right. We build through all market conditions.",
                "Building is the answer. Always has been.",
                "Less noise, more signal. BUIDL.",
            ],
            'questions': {
                'when': "The best time was yesterday; next best is today. Keep building.",
                'how': "Start small, learn constantly, build consistently. The path reveals itself.",
                'why': "Because the future needs builders, not spectators.",
                'what': "Build value for users. Everything else follows.",
                'default': "Great question! The answer is always: keep building. BUIDL is the way.",
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
            ],
        }

    def _load_persona(self, persona_path: Path | None) -> str:
        try:
            p = persona_path or Path.cwd() / 'CLAUDE.md'
            if p.exists():
                return p.read_text(encoding='utf-8')[:2000]
        except Exception:
            pass
        return ""

    def generate(self, author: str, content: str, post_url: str) -> str:
        text = (content or "").lower()

        if any(w in text for w in self.fud_words):
            return random.choice(self.responses['fud_extended'] if random.random() > 0.7 else self.responses['fud'])

        if any(w in text for w in self.build_words):
            return random.choice(self.responses['building'])

        if '?' in (content or ''):
            for q, ans in self.responses['questions'].items():
                if q != 'default' and q in text:
                    return ans
            return self.responses['questions']['default']

        if any(w in text for w in self.market_words):
            return random.choice(self.responses['market'])

        if any(w in text for w in self.security_words):
            return random.choice(self.responses['security'])

        return random.choice(self.responses['encouragement'])

