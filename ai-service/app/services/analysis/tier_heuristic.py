"""
Enhanced heuristic tier with fuzzy matching.

Tier 3 - Fast, reliable fallback using pattern matching and NLP techniques.
"""
from typing import List, Optional, Tuple, Set
from rapidfuzz import fuzz, process
from loguru import logger

from app.services.analysis.intent_config import IntentConfig
from app.services.analysis.intent_schemas import (
    IntentAnalysisResult, IntentType, ComplexityLevel,
    ExtractedEntities, ConfidenceBreakdown, SafetyStatus,
    ActionRecommendation, AppDomain, ClassificationRequest
)
from app.services.analysis.tier_base import ClassificationTierBase
from app.services.analysis.entity_extractor import EntityExtractor
from app.services.analysis.safety_checker import SafetyChecker


class EnhancedHeuristicTier(ClassificationTierBase):
    """
    Enhanced heuristic classification with fuzzy matching.
    
    Features:
    - Fuzzy string matching for typos
    - Component aliases recognition
    - Pattern-based classification
    - Complexity scoring
    - Safety detection
    """
    
    def __init__(self):
        from app.services.analysis.intent_config import config, ClassificationTier
        super().__init__(
            tier=ClassificationTier.HEURISTIC,
            retry_config=config.TIERS["heuristic"].retry_config if hasattr(config, 'TIERS') else None
        )
        self.intent_config = IntentConfig()
        self.entity_extractor = EntityExtractor()
        self.safety_checker = SafetyChecker()
        self._prepare_patterns()
    
    def _prepare_patterns(self):
        """Prepare patterns for fast matching"""
        # Intent patterns
        self.intent_keywords = {
            IntentType.CREATE_APP: ["create", "build", "make", "generate", "new"],
            IntentType.MODIFY_APP: ["change", "modify", "update", "edit"],
            IntentType.EXTEND_APP: ["add", "include", "also", "plus", "extra"],
            IntentType.BUG_FIX: ["fix", "bug", "issue", "problem", "broken"],
            IntentType.OPTIMIZE_PERFORMANCE: ["optimize", "improve", "faster", "speed"],
            IntentType.HELP: ["help", "how", "what", "why", "explain"],
        }
        
        # Component aliases
        self.component_aliases_flat = []
        # This would ideally come from component_catalog, but we'll use a simplified version
        common_components = ["Button", "Text", "Input", "List", "Checkbox", "Switch", "Slider", "Image"]
        self.component_aliases_flat.extend(common_components)
    
    async def _classify_internal(
        self,
        request: ClassificationRequest
    ) -> IntentAnalysisResult:
        """Classify using enhanced heuristics"""
        
        prompt_lower = request.prompt.lower()
        words = prompt_lower.split()
        word_count = len(words)
        
        # Step 1: Detect domain
        domain, domain_conf = AppDomain.detect_from_text(prompt_lower)
        
        # Step 2: Classify intent
        intent_type, intent_confidence = self._classify_intent(prompt_lower, words)
        
        # Step 3: Extract entities
        entities = self.entity_extractor.extract_heuristic(prompt_lower)
        entity_conf = min(0.8, 0.3 + (len(entities.components) * 0.1))
        
        # Step 4: Determine complexity
        complexity = ComplexityLevel.from_text(
            prompt_lower,
            len(entities.components)
        )
        complexity_confidence = 0.6
        
        # Step 5: Check safety
        safety_status, safety_confidence = self.safety_checker.check_heuristic(prompt_lower)
        
        # Step 6: Calculate overall confidence
        overall_confidence = (
            intent_confidence * 0.25 +
            domain_conf * 0.20 +
            complexity_confidence * 0.15 +
            entity_conf * 0.20 +
            safety_confidence * 0.20
        )
        
        # Build confidence breakdown
        confidence = ConfidenceBreakdown(
            overall=overall_confidence,
            intent_confidence=intent_confidence,
            complexity_confidence=complexity_confidence,
            entity_confidence=entity_conf,
            safety_confidence=safety_confidence,
            context_confidence=0.5
        )
        
        # Determine action
        action = self._determine_action(intent_type, safety_status, confidence)
        
        # Check if context required
        requires_context = intent_type in [
            IntentType.MODIFY_APP, IntentType.EXTEND_APP
        ]
        
        # Generate message
        user_message = self._generate_user_message(
            action, intent_type, confidence
        )
        
        # Extract technical requirements
        specific_type = None
        if domain == AppDomain.IOT_HARDWARE:
            for device_type, patterns in HARDWARE_PATTERNS.items():
                if any(kw in prompt_lower for kw in patterns["keywords"]):
                    specific_type = device_type
                    break
        elif domain == AppDomain.CREATIVE_MEDIA:
            for ai_type, patterns in AI_PATTERNS.items():
                if any(kw in prompt_lower for kw in patterns["keywords"]):
                    specific_type = ai_type
                    break
        
        technical_requirements = self.intent_config.extract_special_requirements(
            prompt_lower, domain, specific_type or ""
        )
        
        return IntentAnalysisResult(
            intent_type=intent_type,
            complexity=complexity,
            confidence=confidence,
            extracted_entities=entities,
            technical_requirements=TechnicalRequirements(**technical_requirements),
            action_recommendation=action,
            safety_status=safety_status,
            requires_context=requires_context,
            multi_turn=False,
            user_message=user_message,
            reasoning="Classified using enhanced heuristic analysis",
            domain=domain,
            specific_type=specific_type,
            tier_used="heuristic",
            tier_attempts=[],
            total_latency_ms=0,
            total_cost_usd=0.0
        )
    
    def _classify_intent(
        self,
        prompt_lower: str,
        words: List[str]
    ) -> Tuple[IntentType, float]:
        """Classify intent with fuzzy matching"""
        
        scores = {}
        
        for intent_type, keywords in self.intent_keywords.items():
            score = 0.0
            matches = 0
            
            # Exact keyword matches
            for keyword in keywords:
                if keyword in prompt_lower:
                    score += 1.0
                    matches += 1
            
            # Fuzzy matches for individual words
            for word in words:
                if len(word) >= 4:  # Only fuzzy match longer words
                    best_match = process.extractOne(
                        word,
                        keywords,
                        scorer=fuzz.ratio,
                        score_cutoff=80
                    )
                    if best_match:
                        score += 0.5
                        matches += 1
            
            # Normalize by number of keywords
            if len(keywords) > 0:
                scores[intent_type] = (score / len(keywords), matches)
            else:
                scores[intent_type] = (0.0, 0)
        
        # Get best match
        if not scores:
            return IntentType.CLARIFICATION, 0.3
        
        best_intent = max(scores.items(), key=lambda x: (x[1][0], x[1][1]))
        intent_type = best_intent[0]
        normalized_score = best_intent[1][0]
        match_count = best_intent[1][1]
        
        # Calculate confidence
        confidence = min(0.85, normalized_score * 0.8 + (match_count * 0.05))
        
        # Lower confidence if score too low
        if normalized_score < 0.1:
            return IntentType.CLARIFICATION, 0.3
        
        return intent_type, confidence
    
    def _determine_action(
        self,
        intent_type: IntentType,
        safety: SafetyStatus,
        confidence: ConfidenceBreakdown
    ) -> ActionRecommendation:
        """Determine recommended action"""
        if safety == SafetyStatus.UNSAFE:
            return ActionRecommendation.REJECT
        
        if intent_type == IntentType.MODIFY_APP:
            if confidence.overall < 0.7:
                return ActionRecommendation.BLOCK_MODIFY
        
        if intent_type == IntentType.EXTEND_APP:
            if confidence.overall < 0.7:
                return ActionRecommendation.BLOCK_EXTEND
        
        # Heuristic is less confident, so more likely to ask for clarification
        if confidence.overall < 0.75:
            return ActionRecommendation.CLARIFY
        
        return ActionRecommendation.PROCEED
    
    def _generate_user_message(
        self,
        action: ActionRecommendation,
        intent_type: IntentType,
        confidence: ConfidenceBreakdown
    ) -> Optional[str]:
        """Generate user-facing message"""
        if action == ActionRecommendation.PROCEED:
            return None
        
        if action == ActionRecommendation.REJECT:
            return "I cannot help with this request as it appears to be unsafe."
        
        if action == ActionRecommendation.BLOCK_MODIFY:
            return "I need more clarity about what you want to modify before proceeding."
        
        if action == ActionRecommendation.BLOCK_EXTEND:
            return "I need more clarity about what features to add before proceeding."
        
        if action == ActionRecommendation.CLARIFY:
            intent_guess = intent_type.value.replace("_", " ")
            return f"I think you want to {intent_guess}, but I need more details. Could you elaborate?"
        
        return None
    
    def get_name(self) -> str:
        return "heuristic"