"""
Production safety checker for intent analysis
"""
import re
from typing import Dict, Any, Tuple, List, Optional
from rapidfuzz import fuzz

from app.services.analysis.intent_schemas import IntentAnalysisResult, SafetyStatus


class SafetyChecker:
    """
    Multi-level safety checking:
    - Quick check (fast keyword matching)
    - Deep check (contextual analysis)
    - Pattern matching for known threats
    """
    
    def __init__(self):
        # Unsafe patterns (exact matches)
        self.unsafe_patterns = {
            # Malicious intent
            "hack": ["hack", "crack", "exploit", "breach"],
            "malware": ["malware", "virus", "trojan", "ransomware"],
            "steal": ["steal", "theft", "stolen", "unauthorized"],
            "phishing": ["phish", "phishing", "credential"],
            
            # Harmful content
            "violence": ["violence", "violent", "attack", "harm"],
            "hate": ["hate", "discriminate", "racist"],
            "explicit": ["explicit", "adult", "porn", "nsfw"],
            
            # Privacy violations
            "tracking": ["track", "spy", "monitor", "surveillance"],
            "data_theft": ["collect data", "extract", "scrape"],
            
            # Dangerous operations
            "destroy": ["destroy", "delete", "erase", "wipe"],
            "bypass": ["bypass", "circumvent", "avoid"],
        }
        
        # Suspicious patterns (require confirmation)
        self.suspicious_patterns = {
            "admin": ["admin", "root", "sudo", "privilege"],
            "bypass": ["bypass", "skip", "override"],
            "hidden": ["hidden", "secret", "stealth"],
            "fake": ["fake", "spoof", "impersonate"],
            "unlimited": ["unlimited", "infinite", "unrestricted"],
        }
        
        # Contextual safety rules
        self.contextual_rules = [
            {
                "pattern": r"bypass.*(?:login|auth|security)",
                "reason": "Attempting to bypass authentication",
                "severity": "unsafe"
            },
            {
                "pattern": r"access.*(?:other|someone|another).*data",
                "reason": "Request to access other users' data",
                "severity": "unsafe"
            },
            {
                "pattern": r"remove.*(?:limit|restriction|constraint)",
                "reason": "Attempting to remove application limits",
                "severity": "suspicious"
            },
            {
                "pattern": r"hide.*(?:from|admin|moderator)",
                "reason": "Attempting to hide content from moderation",
                "severity": "suspicious"
            },
            {
                "pattern": r"fake.*(?:identity|profile|account)",
                "reason": "Attempting to create fake identity",
                "severity": "unsafe"
            },
        ]
    
    def quick_check(self, text: str) -> str:
        """
        Quick safety check - returns 'safe', 'suspicious', or 'unsafe'
        Fast enough for pre-filtering
        """
        text_lower = text.lower()
        
        # Check unsafe patterns
        for category, patterns in self.unsafe_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                return "unsafe"
        
        # Check suspicious patterns
        for category, patterns in self.suspicious_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                return "suspicious"
        
        # Check contextual patterns
        for rule in self.contextual_rules:
            if re.search(rule["pattern"], text_lower):
                return rule["severity"]
        
        return "safe"
    
    def check_heuristic(self, text: str) -> Tuple[str, float]:
        """
        Heuristic safety check with confidence
        """
        text_lower = text.lower()
        words = text_lower.split()
        
        # Score unsafe patterns
        unsafe_score = 0
        for category, patterns in self.unsafe_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    unsafe_score += 0.3
                # Fuzzy match for variations
                for word in words:
                    if len(word) >= 5:
                        ratio = fuzz.ratio(word, pattern)
                        if ratio > 85:
                            unsafe_score += 0.2
        
        if unsafe_score >= 0.5:
            return "unsafe", min(unsafe_score, 0.95)
        
        # Score suspicious patterns
        suspicious_score = 0
        for category, patterns in self.suspicious_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    suspicious_score += 0.2
        
        if suspicious_score >= 0.3:
            return "suspicious", min(suspicious_score, 0.8)
        
        return "safe", 0.9
    
    def deep_check(
        self,
        result: IntentAnalysisResult
    ) -> Dict[str, Any]:
        """
        Deep contextual safety check
        Analyzes intent, entities, and context together
        """
        safety_result = {
            "status": result.safety_status.value,
            "reasoning": result.safety_reasoning,
            "flags": []
        }
        
        # Check if intent doesn't match domain
        if result.intent_type in [IntentType.CREATE_APP, IntentType.EXTEND_APP]:
            if result.domain in [AppDomain.SOCIAL, AppDomain.ENTERTAINMENT]:
                # These domains are usually safe
                pass
            elif result.domain in [AppDomain.FINANCE, AppDomain.BUSINESS]:
                # These domains need extra caution
                if result.technical_requirements and result.technical_requirements.special_apis:
                    # Check if APIs are payment-related
                    payment_apis = ["payment", "stripe", "paypal", "bank"]
                    if any(api in str(result.technical_requirements.special_apis).lower() 
                           for api in payment_apis):
                        safety_result["flags"].append({
                            "type": "warning",
                            "message": "Payment handling requires secure implementation"
                        })
        
        # Check for sensitive data types
        sensitive_data = ["password", "credit card", "ssn", "bank", "private"]
        if any(data in str(result.extracted_entities.data_types).lower() 
               for data in sensitive_data):
            safety_result["flags"].append({
                "type": "warning",
                "message": "App will handle sensitive data - ensure proper security"
            })
        
        # Check for excessive permissions
        if result.technical_requirements:
            permissions = result.technical_requirements.permissions_required
            dangerous_perms = ["camera", "microphone", "location", "contacts", "photos"]
            if any(perm in dangerous_perms for perm in permissions):
                if len(permissions) > 2:
                    safety_result["flags"].append({
                        "type": "caution",
                        "message": f"App requests multiple sensitive permissions: {permissions}"
                    })
        
        # Update status based on flags
        if safety_result["flags"]:
            if any(f["type"] == "warning" for f in safety_result["flags"]):
                if safety_result["status"] == "safe":
                    safety_result["status"] = "suspicious"
                    safety_result["reasoning"] = "Additional security considerations needed"
        
        return safety_result