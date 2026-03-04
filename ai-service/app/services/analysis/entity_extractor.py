"""
Advanced entity extractor for rich component and relationship extraction
"""
import re
from typing import Dict, List, Any, Optional, Set, Tuple
from rapidfuzz import fuzz, process

from app.services.analysis.intent_schemas import ExtractedEntities
from app.models.schemas.component_catalog import (
    COMPONENT_DEFINITIONS
)


class EntityExtractor:
    """
    Advanced entity extraction with:
    - Component recognition with aliases
    - Relationship detection
    - Feature extraction
    - Screen detection
    - Integration detection
    """
    
    def __init__(self):
        # Build component index
        self.component_index = self._build_component_index()
        
        # Action keywords
        self.action_keywords = {
            "create": ["create", "add", "new", "make"],
            "read": ["view", "show", "display", "see"],
            "update": ["update", "edit", "change", "modify"],
            "delete": ["delete", "remove", "erase"],
            "complete": ["complete", "done", "finish", "mark"],
            "search": ["search", "find", "filter", "look"],
            "navigate": ["go", "navigate", "back", "next"],
            "share": ["share", "send", "export"],
            "save": ["save", "store", "keep"],
            "load": ["load", "fetch", "get", "retrieve"],
        }
        
        # Feature keywords
        self.feature_keywords = {
            "authentication": ["login", "signup", "auth", "authenticate"],
            "notifications": ["notification", "alert", "remind", "push"],
            "payments": ["pay", "payment", "checkout", "purchase"],
            "search": ["search", "find", "filter"],
            "sharing": ["share", "social", "post"],
            "offline": ["offline", "sync", "cache"],
            "export": ["export", "download", "save"],
            "import": ["import", "upload", "load"],
        }
        
        # Screen patterns
        self.screen_patterns = {
            "home": ["home", "main", "dashboard", "index"],
            "detail": ["detail", "details", "view", "info"],
            "create": ["create", "add", "new", "edit"],
            "settings": ["settings", "preferences", "config"],
            "profile": ["profile", "account", "user"],
            "search": ["search", "results"],
            "list": ["list", "catalog", "gallery"],
        }
    
    def _build_component_index(self) -> Dict[str, Any]:
        """Build searchable index of components"""
        index = {
            "by_name": {},
            "by_alias": {},
            "search_terms": [],
        }
        
        for comp_name, definition in COMPONENT_DEFINITIONS.items():
            canonical = comp_name
            index["by_name"][canonical.lower()] = canonical
            
            # Add aliases
            aliases = definition.get("aliases", [])
            for alias in aliases:
                index["by_alias"][alias.lower()] = canonical
            
            # Add all search terms
            index["search_terms"].append(canonical.lower())
            index["search_terms"].extend([a.lower() for a in aliases])
        
        return index
    
    def extract_heuristic(self, text: str) -> ExtractedEntities:
        """Extract entities using heuristic matching"""
        text_lower = text.lower()
        words = text_lower.split()
        
        components = self._extract_components_heuristic(text_lower, words)
        actions = self._extract_actions_heuristic(text_lower)
        features = self._extract_features_heuristic(text_lower)
        screens = self._extract_screens_heuristic(text_lower)
        
        return ExtractedEntities(
            components=components,
            actions=actions,
            features=features,
            screens=screens
        )
    
    def _extract_components_heuristic(
        self,
        text_lower: str,
        words: List[str]
    ) -> List[str]:
        """Extract components using heuristic matching"""
        components = set()
        
        # Exact matches
        for term in self.component_index["search_terms"]:
            if term in text_lower:
                # Find canonical name
                if term in self.component_index["by_name"]:
                    components.add(self.component_index["by_name"][term])
                elif term in self.component_index["by_alias"]:
                    components.add(self.component_index["by_alias"][term])
        
        # Fuzzy matches for typos
        for word in words:
            if len(word) >= 4:
                match = process.extractOne(
                    word,
                    self.component_index["search_terms"],
                    scorer=fuzz.ratio,
                    score_cutoff=85
                )
                if match:
                    matched_term = match[0]
                    if matched_term in self.component_index["by_name"]:
                        components.add(self.component_index["by_name"][matched_term])
                    elif matched_term in self.component_index["by_alias"]:
                        components.add(self.component_index["by_alias"][matched_term])
        
        return list(components)
    
    def _extract_actions_heuristic(self, text_lower: str) -> List[str]:
        """Extract actions using heuristic matching"""
        actions = set()
        
        for action, keywords in self.action_keywords.items():
            if any(kw in text_lower for kw in keywords):
                actions.add(action)
        
        return list(actions)
    
    def _extract_features_heuristic(self, text_lower: str) -> List[str]:
        """Extract features using heuristic matching"""
        features = set()
        
        for feature, keywords in self.feature_keywords.items():
            if any(kw in text_lower for kw in keywords):
                features.add(feature)
        
        return list(features)
    
    def _extract_screens_heuristic(self, text_lower: str) -> List[str]:
        """Extract screens using heuristic matching"""
        screens = set()
        
        for screen_type, patterns in self.screen_patterns.items():
            if any(pattern in text_lower for pattern in patterns):
                screens.add(f"{screen_type}_screen")
        
        return list(screens)