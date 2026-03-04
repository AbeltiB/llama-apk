"""
Base enums used across intent analysis modules
"""
from __future__ import annotations

from enum import Enum
from typing import Tuple


class AppDomain(str, Enum):
    """Application domains - Single source of truth"""
    PRODUCTIVITY = "productivity"
    ENTERTAINMENT = "entertainment"
    UTILITY = "utility"
    BUSINESS = "business"
    EDUCATION = "education"
    HEALTH_FITNESS = "health_fitness"
    FINANCE = "finance"
    DEVELOPMENT = "development"
    IOT_HARDWARE = "iot_hardware"
    CREATIVE_MEDIA = "creative_media"
    DATA_SCIENCE = "data_science"
    CUSTOM = "custom"
    
    @classmethod
    def detect_from_text(cls, text: str) -> Tuple[AppDomain, float]:
        """Detect domain from text with confidence"""
        text_lower = text.lower()
        
        # Domain signatures with weighted keywords
        signatures = {
            cls.PRODUCTIVITY: {
                "keywords": ["todo", "task", "note", "calendar", "reminder", "schedule"],
                "weight": 0.3
            },
            cls.UTILITY: {
                "keywords": ["calculator", "converter", "scanner", "qr", "barcode", "timer"],
                "weight": 0.3
            },
            cls.BUSINESS: {
                "keywords": ["inventory", "pos", "crm", "invoice", "payment", "ecommerce"],
                "weight": 0.3
            },
            cls.EDUCATION: {
                "keywords": ["learn", "course", "quiz", "flashcard", "tutorial", "language"],
                "weight": 0.3
            },
            cls.HEALTH_FITNESS: {
                "keywords": ["fitness", "workout", "health", "tracker", "diet", "nutrition"],
                "weight": 0.3
            },
            cls.FINANCE: {
                "keywords": ["bank", "budget", "expense", "investment", "stock", "crypto"],
                "weight": 0.3
            },
            cls.DEVELOPMENT: {
                "keywords": ["code", "editor", "git", "terminal", "api", "debug"],
                "weight": 0.3
            },
            cls.IOT_HARDWARE: {
                "keywords": ["drone", "printer", "sensor", "bluetooth", "arduino", "raspberry", "robot"],
                "weight": 0.4
            },
            cls.CREATIVE_MEDIA: {
                "keywords": ["photo", "video", "edit", "design", "3d", "draw", "art"],
                "weight": 0.3
            },
            cls.DATA_SCIENCE: {
                "keywords": ["data", "analyze", "visualize", "chart", "graph", "dataset"],
                "weight": 0.3
            },
        }
        
        scores = {}
        for domain, config in signatures.items():
            matches = sum(1 for kw in config["keywords"] if kw in text_lower)
            if matches:
                score = (matches / len(config["keywords"])) * config["weight"]
                scores[domain] = min(score, 0.95)
        
        if not scores:
            return cls.CUSTOM, 0.3
        
        best_domain = max(scores, key=scores.get)
        return best_domain, scores[best_domain]


__all__ = ["AppDomain"]