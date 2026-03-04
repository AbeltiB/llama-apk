"""
Production-Ready Intent Analyzer - Backward Compatible
Exports global 'intent_analyzer' instance for existing code
"""
import json
import re
import time
import hashlib
import asyncio
import os
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
import httpx

from app.services.analysis.intent_schemas import (
    IntentAnalysisResult,
    IntentType,
    ComplexityLevel,
    SafetyStatus,
    ActionRecommendation,
    AppDomain,
    ExtractedEntities,
    ConfidenceBreakdown,
    TechnicalRequirements,
    ClassificationRequest,
)
from app.services.analysis.intent_config import IntentConfig, HARDWARE_PATTERNS, AI_PATTERNS
from app.services.analysis.safety_checker import SafetyChecker
from app.services.analysis.entity_extractor import EntityExtractor
from app.utils.logging import get_logger
from app.models.schemas.component_catalog import get_template_components
from app.core.cache import cache_manager

logger = get_logger(__name__)


class TierResult:
    """Result from a single classification tier"""
    def __init__(
        self,
        success: bool,
        result: Optional[IntentAnalysisResult] = None,
        error: Optional[str] = None,
        latency_ms: int = 0,
        tier_name: str = "unknown"
    ):
        self.success = success
        self.result = result
        self.error = error
        self.latency_ms = latency_ms
        self.tier_name = tier_name
    
    def __bool__(self):
        return self.success


class ProductionIntentAnalyzer:
    """
    Production-ready intent analyzer with:
    - Llama3 primary classification
    - Multi-tier fallback
    - Robust heuristic fallback
    - Comprehensive error handling
    - Request caching
    - Performance monitoring
    - Circuit breakers
    - Entity extraction
    - Safety checking
    """
    
    def __init__(self, config: Dict[str, Any]):
        """Initialize analyzer"""
        # Llama3 configuration
        self.api_url = config.get('llama3_api_url', 'https://fastchat.ideeza.com/v1/chat/completions')
        self.api_key = config.get('llama3_api_key', '')
        self.model = config.get('llama3_model', 'llama-3-70b-instruct')
        self.timeout = config.get('timeout', 60.0)
        self.max_retries = config.get('max_retries', 3)
        
        # Caching configuration
        self.cache_enabled = config.get('enable_caching', True)
        self.cache_ttl = config.get('cache_ttl', 3600)  # 1 hour
        
        # Llama3 availability
        self.llama3_available = bool(self.api_url)
        if not self.llama3_available:
            logger.warning("Llama3 API URL not configured - using heuristic fallback only")
        elif not self.api_key:
            logger.warning("Llama3 API key not configured - API calls may fail")
        
        # Circuit breaker for Llama3
        self.llama3_failure_count = 0
        self.llama3_max_failures = 3
        self.llama3_circuit_open = False
        
        # Component extractors
        self.entity_extractor = EntityExtractor()
        self.safety_checker = SafetyChecker()
        self.intent_config = IntentConfig()
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'llama3_success': 0,
            'llama3_failures': 0,
            'heuristic_fallback': 0,
            'total_latency_ms': 0,
        }
        
        logger.info(
            "intent_analyzer.initialized",
            extra={
                "llama3_available": self.llama3_available,
                "api_url": self.api_url[:50] if self.api_url else "Not configured",
                "cache_enabled": self.cache_enabled
            }
        )
    
    async def analyze(
        self,
        prompt: str,
        user_id: str = "unknown",
        session_id: str = "unknown",
        context: Optional[Dict[str, Any]] = None
    ) -> IntentAnalysisResult:
        """
        Main analysis method - GUARANTEED to return result
        
        Args:
            prompt: User's natural language request
            user_id: User identifier
            session_id: Session identifier
            context: Optional context information
            
        Returns:
            IntentAnalysisResult - always returns, never raises
        """
        start_time = time.time()
        self.stats['total_requests'] += 1
        
        try:
            # Create request object
            request = ClassificationRequest(
                prompt=prompt,
                user_id=user_id,
                session_id=session_id,
                context=context
            )
            
            # Check cache
            if self.cache_enabled:
                cached = await self._check_cache(request)
                if cached:
                    self.stats['cache_hits'] += 1
                    logger.debug("intent_analyzer.cache_hit")
                    return cached
            
            # Quick safety check
            quick_safety = self.safety_checker.quick_check(prompt)
            if quick_safety == "unsafe":
                logger.warning("Quick safety check flagged unsafe")
                return self._create_safe_result(
                    intent_type=IntentType.OTHER,
                    safety_status=SafetyStatus.UNSAFE,
                    safety_reasoning="Request flagged by safety checker"
                )
            
            # Try Llama3 first (if available and circuit not open)
            if self.llama3_available and not self.llama3_circuit_open:
                try:
                    result = await self._analyze_with_llama3(request)
                    
                    # Success - reset failure count
                    self.llama3_failure_count = 0
                    self.stats['llama3_success'] += 1
                    
                    # Cache result
                    if self.cache_enabled:
                        await self._cache_result(request, result)
                    
                    # Update latency
                    latency_ms = int((time.time() - start_time) * 1000)
                    result.total_latency_ms = latency_ms
                    self.stats['total_latency_ms'] += latency_ms
                    
                    logger.info(
                        "intent_analyzer.llama3_success",
                        extra={
                            "intent": result.intent_type.value,
                            "domain": result.domain.value if result.domain else "unknown",
                            "latency_ms": latency_ms
                        }
                    )
                    return result
                    
                except Exception as e:
                    # Llama3 failed - log and continue to fallback
                    self._handle_llama3_failure(e)
            
            # Fallback to heuristic
            result = await self._analyze_with_heuristic(request)
            self.stats['heuristic_fallback'] += 1
            result.source = "heuristic"
            
            # Cache result
            if self.cache_enabled:
                await self._cache_result(request, result)
            
            # Update latency
            latency_ms = int((time.time() - start_time) * 1000)
            result.total_latency_ms = latency_ms
            self.stats['total_latency_ms'] += latency_ms
            
            logger.info(
                "intent_analyzer.heuristic_success",
                extra={
                    "intent": result.intent_type.value,
                    "domain": result.domain.value if result.domain else "unknown"
                }
            )
            return result
            
        except Exception as e:
            # Critical error - return safe fallback
            logger.error(
                "intent_analyzer.critical_error",
                extra={"error": str(e)},
                exc_info=True
            )
            return self._create_safe_fallback(prompt)
    
    # ================== LLAMA3 INTEGRATION ==================
    
    async def _analyze_with_llama3(
        self,
        request: ClassificationRequest
    ) -> IntentAnalysisResult:
        """Analyze using Llama3 API with robust error handling"""
        
        # Build prompts
        system_prompt = self._build_llama3_system_prompt()
        user_prompt = self._build_llama3_user_prompt(request)
        
        # Call API with retries
        for attempt in range(1, self.max_retries + 1):
            try:
                response_data = await self._call_llama3_api(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    attempt=attempt
                )
                
                # Parse response
                result = self._parse_llama3_response(response_data, request)
                
                # Enhance with deep entity extraction
                result = await self._enhance_with_entities(result, request.prompt)
                
                # Final safety check
                result = await self._final_safety_check(result)
                
                return result
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise Exception("Llama3 API authentication failed - check API key")
                elif e.response.status_code == 429:
                    if attempt < self.max_retries:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    raise
                else:
                    raise
            
            except Exception as e:
                if attempt < self.max_retries:
                    await asyncio.sleep(1 * attempt)
                    continue
                raise
        
        raise Exception(f"Llama3 API failed after {self.max_retries} attempts")
    
    async def _call_llama3_api(
        self,
        system_prompt: str,
        user_prompt: str,
        attempt: int = 1
    ) -> Dict[str, Any]:
        """Make API call to Llama3"""
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 2000,
            "top_p": 0.9,
        }
        
        headers = {
            "Content-Type": "application/json",
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                self.api_url,
                json=payload,
                headers=headers
            )
            
            response.raise_for_status()
            return response.json()
    
    def _build_llama3_system_prompt(self) -> str:
        """Build system prompt for Llama3"""
        return """You are an expert intent classifier for a mobile app generation system.

Analyze the user's request and provide a complete intent classification.

### INTENT TYPES (choose ONE):
- create_app: User wants to create a new app from scratch
- modify_app: User wants to modify an existing app
- extend_app: User wants to add features to an existing app
- bug_fix: User reports a bug or issue
- optimize_performance: User wants performance improvements
- clarification: User needs more information
- help: General question about app building
- other: Doesn't fit above categories

### DOMAINS (choose ONE if identifiable):
- productivity: Todo, notes, calendar, tasks
- utility: Calculator, converter, scanner, tools
- business: POS, inventory, CRM, e-commerce
- education: Learning apps, quizzes, courses
- health_fitness: Workout tracking, health monitoring
- finance: Banking, budgeting, crypto, investments
- social: Messaging, sharing, feeds
- entertainment: Media players, games, streaming
- iot_hardware: Drone control, 3D printer, sensors
- creative_media: Photo/video editors, 3D apps
- data_science: Data visualization, analytics
- development: Code editors, debugging tools
- custom: Not fitting above categories

### COMPLEXITY (choose ONE):
- simple: Basic UI, 1-3 components, single screen
- medium: 4-8 components, 2-3 screens, simple logic
- complex: 9+ components, multiple screens, APIs, state management

### TECHNICAL REQUIREMENTS (detect if applicable):
- needs_hardware: true/false (Bluetooth, USB, serial control)
- needs_ai_ml: true/false (image processing, ML models)
- needs_real_time: true/false (live updates, streaming)
- needs_3d: true/false (3D viewer, WebGL)
- special_apis: List of APIs (e.g., ["weather_api", "payment_gateway"])
- permissions_required: List of permissions (e.g., ["camera", "location"])

### EXTRACTED ENTITIES (be thorough):
- components: UI components mentioned (Button, Text, Input, List, etc.)
- actions: User interactions mentioned (click, swipe, type, etc.)
- data_types: Data entities mentioned (todo, user, product, etc.)
- features: App capabilities mentioned (login, search, payment, etc.)
- screens: Screen names mentioned (home, settings, profile, etc.)

### SAFETY CLASSIFICATION:
- safe: Normal, constructive request
- suspicious: Potentially problematic but unclear
- unsafe: Malicious, harmful, or policy-violating

### RESPONSE FORMAT - STRICT JSON:
{
  "intent_type": "create_app",
  "domain": "productivity",
  "complexity": "medium",
  "confidence": {
    "overall": 0.85,
    "intent_confidence": 0.9,
    "domain_confidence": 0.8,
    "complexity_confidence": 0.85,
    "entity_confidence": 0.8,
    "safety_confidence": 1.0
  },
  "extracted_entities": {
    "components": ["List", "Checkbox", "InputText"],
    "actions": ["add", "complete", "delete"],
    "data_types": ["todo", "task"],
    "features": ["create_task", "complete_task", "delete_task"],
    "screens": ["home_screen", "detail_screen"]
  },
  "technical_requirements": {
    "needs_hardware": false,
    "needs_ai_ml": false,
    "needs_real_time": false,
    "needs_3d": false,
    "special_apis": [],
    "permissions_required": []
  },
  "safety_status": "safe",
  "requires_context": false,
  "reasoning": "User wants a todo app with create, complete, and delete functionality"
}

CRITICAL: Return ONLY valid JSON, no markdown, no explanations.
"""
    
    def _build_llama3_user_prompt(
        self,
        request: ClassificationRequest
    ) -> str:
        """Build user prompt with context"""
        parts = [f"User request: \"{request.prompt}\""]
        
        # Add context if available
        if request.context:
            if request.context.get('has_existing_project'):
                parts.append("\nUser has an existing project in this session.")
            
            if request.context.get('conversation_history'):
                history = request.context.get('conversation_history', [])
                if history:
                    parts.append("\nRecent conversation:")
                    for msg in history[-2:]:
                        parts.append(f"- {msg.get('role', 'user')}: {msg.get('content', '')[:100]}")
        
        return "\n".join(parts)
    
    def _parse_llama3_response(
        self,
        response_data: Dict[str, Any],
        request: ClassificationRequest
    ) -> IntentAnalysisResult:
        """Parse Llama3 response to IntentAnalysisResult"""
        
        # Extract content
        if 'choices' not in response_data or len(response_data['choices']) == 0:
            raise ValueError("Invalid Llama3 response: no choices")
        
        content = response_data['choices'][0]['message']['content']
        
        # Clean markdown
        content = content.strip()
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()
        
        # Extract JSON if embedded
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group()
        
        # Parse JSON
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Llama3 response: {e}")
            raise ValueError("Could not parse Llama3 response as JSON")
        
        # Map to enums
        intent_type = IntentType.from_string(data.get('intent_type', 'other'))
        
        # Parse domain
        domain_str = data.get('domain', 'custom')
        try:
            domain = AppDomain(domain_str)
        except ValueError:
            domain = AppDomain.CUSTOM
        
        # Parse complexity
        complexity_str = data.get('complexity', 'medium')
        complexity = ComplexityLevel.normalize(complexity_str)
        
        # Safety
        safety_map = {
            "safe": SafetyStatus.SAFE,
            "suspicious": SafetyStatus.SUSPICIOUS,
            "unsafe": SafetyStatus.UNSAFE,
        }
        safety = safety_map.get(
            data.get('safety_status', 'safe'),
            SafetyStatus.SAFE
        )
        
        # Confidence
        conf_data = data.get('confidence', {})
        confidence = ConfidenceBreakdown(
            overall=conf_data.get('overall', 0.75),
            intent_confidence=conf_data.get('intent_confidence', 0.75),
            complexity_confidence=conf_data.get('complexity_confidence', 0.75),
            entity_confidence=conf_data.get('entity_confidence', 0.75),
            safety_confidence=conf_data.get('safety_confidence', 1.0),
        )
        
        # Entities
        entities_data = data.get('extracted_entities', {})
        entities = ExtractedEntities(
            components=entities_data.get('components', []),
            actions=entities_data.get('actions', []),
            data_types=entities_data.get('data_types', []),
            features=entities_data.get('features', []),
            screens=entities_data.get('screens', []),
            integrations=entities_data.get('integrations', [])
        )
        
        # Technical requirements
        tech_data = data.get('technical_requirements', {})
        technical_requirements = TechnicalRequirements(
            needs_hardware=tech_data.get('needs_hardware', False),
            needs_ai_ml=tech_data.get('needs_ai_ml', False),
            needs_real_time=tech_data.get('needs_real_time', False),
            needs_3d=tech_data.get('needs_3d', False),
            special_apis=tech_data.get('special_apis', []),
            permissions_required=tech_data.get('permissions_required', [])
        )
        
        # Determine action
        action = self._determine_action(intent_type, safety, confidence)
        
        # Estimate cost
        tokens = response_data.get('usage', {}).get('total_tokens', 0)
        cost_usd = (tokens / 1000) * 0.001
        
        return IntentAnalysisResult(
            intent_type=intent_type,
            complexity=complexity,
            confidence=confidence,
            extracted_entities=entities,
            technical_requirements=technical_requirements,
            action_recommendation=action,
            safety_status=safety,
            requires_context=data.get('requires_context', False),
            reasoning=data.get('reasoning', ''),
            domain=domain,
            specific_type=data.get('specific_type'),
            source="llama3",
            total_cost_usd=cost_usd,
            tokens_used=tokens
        )
    
    def _handle_llama3_failure(self, error: Exception):
        """Handle Llama3 failure with circuit breaker"""
        self.llama3_failure_count += 1
        self.stats['llama3_failures'] += 1
        
        logger.warning(
            "intent_analyzer.llama3_failed",
            extra={"error": str(error), "failures": self.llama3_failure_count}
        )
        
        if self.llama3_failure_count >= self.llama3_max_failures:
            self.llama3_circuit_open = True
            logger.error("intent_analyzer.circuit_breaker_open")
    
    # ================== HEURISTIC FALLBACK ==================
    
    async def _analyze_with_heuristic(
        self,
        request: ClassificationRequest
    ) -> IntentAnalysisResult:
        """Heuristic analysis using pattern matching"""
        
        prompt_lower = request.prompt.lower()
        
        # Detect intent
        intent_type = self._heuristic_detect_intent(prompt_lower)
        
        # Detect domain
        domain, domain_conf = AppDomain.detect_from_text(prompt_lower)
        
        # Extract entities
        entities, entity_conf = self._heuristic_extract_entities(prompt_lower)
        
        # Determine complexity
        complexity = ComplexityLevel.from_text(
            prompt_lower,
            len(entities.components)
        )
        
        # Check safety
        safety, safety_conf = self._heuristic_check_safety(prompt_lower)
        
        # Calculate overall confidence
        overall = (
            0.6 * 0.25 +  # intent confidence (fixed at 0.6 for heuristic)
            domain_conf * 0.20 +
            0.6 * 0.20 +  # complexity confidence
            entity_conf * 0.20 +
            safety_conf * 0.15
        )
        
        confidence = ConfidenceBreakdown(
            overall=overall,
            intent_confidence=0.6,
            complexity_confidence=0.6,
            entity_confidence=entity_conf,
            safety_confidence=safety_conf,
            context_confidence=0.5
        )
        
        action = self._determine_action(intent_type, safety, confidence)
        
        return IntentAnalysisResult(
            intent_type=intent_type,
            complexity=complexity,
            confidence=confidence,
            extracted_entities=entities,
            action_recommendation=action,
            safety_status=safety,
            requires_context=intent_type in [IntentType.MODIFY_APP, IntentType.EXTEND_APP],
            domain=domain,
            source="heuristic",
        )
    
    def _heuristic_detect_intent(self, prompt_lower: str) -> IntentType:
        """Classify intent using keywords"""
            
        patterns = {
            IntentType.CREATE_APP: ["create", "build", "make", "generate", "new"],
            IntentType.MODIFY_APP: ["change", "modify", "update", "edit", "fix"],
            IntentType.EXTEND_APP: ["add", "also", "include", "plus", "extend"],
            IntentType.HELP: ["help", "how", "what", "why", "explain"],
            IntentType.CLARIFICATION: ["?", "unclear", "not sure"],
        }
        
        scores = {intent: 0 for intent in patterns}
        
        for intent, keywords in patterns.items():
            for keyword in keywords:
                if keyword in prompt_lower:
                    scores[intent] += 1
        
        if sum(scores.values()) == 0:
            return IntentType.CLARIFICATION
        
        return max(scores, key=scores.get)
    
    def _heuristic_extract_entities(self, prompt_lower: str) -> tuple:
        """Extract entities using heuristic matching"""
        
        components = []
        actions = []
        features = []
        
        comp_map = {
            "button": ["button", "btn"],
            "text": ["text", "label"],
            "input": ["input", "textbox", "field"],
            "list": ["list", "items"],
            "checkbox": ["checkbox", "check"],
            "switch": ["switch", "toggle"],
        }
        
        for comp, aliases in comp_map.items():
            if any(a in prompt_lower for a in aliases):
                components.append(comp.capitalize())
        
        action_words = ["click", "tap", "press", "type", "input", "swipe", "scroll"]
        actions = [a for a in action_words if a in prompt_lower]
        
        feature_words = ["login", "search", "filter", "notification", "share", "export"]
        features = [f for f in feature_words if f in prompt_lower]
        
        entities = ExtractedEntities(
            components=components,
            actions=actions,
            features=features,
        )
        
        total = len(components) + len(actions) + len(features)
        conf = min(0.8, 0.4 + (total * 0.1))
        
        return entities, conf
    
    def _heuristic_check_safety(self, prompt_lower: str) -> tuple:
        """Check for unsafe content"""
        
        unsafe_keywords = [
            "hack", "malware", "virus", "exploit", "crack",
            "steal", "password", "credit card", "unauthorized"
        ]
        
        for keyword in unsafe_keywords:
            if keyword in prompt_lower:
                return SafetyStatus.UNSAFE, 0.95
        
        return SafetyStatus.SAFE, 0.9
    
    # ================== ENHANCEMENT METHODS ==================
    
    async def _enhance_with_entities(
        self,
        result: IntentAnalysisResult,
        prompt: str
    ) -> IntentAnalysisResult:
        """Enhance result with additional entity extraction"""
        
        # Use entity extractor for deep extraction
        deep_entities = self.entity_extractor.extract_heuristic(prompt)
        
        # Merge entities
        result.extracted_entities.components.extend(
            [c for c in deep_entities.components if c not in result.extracted_entities.components]
        )
        result.extracted_entities.actions.extend(
            [a for a in deep_entities.actions if a not in result.extracted_entities.actions]
        )
        result.extracted_entities.features.extend(
            [f for f in deep_entities.features if f not in result.extracted_entities.features]
        )
        
        return result
    
    async def _final_safety_check(
        self,
        result: IntentAnalysisResult
    ) -> IntentAnalysisResult:
        """Final safety check before returning"""
        
        # Use safety checker for deep check
        safety_result = self.safety_checker.deep_check(result)
        
        if safety_result['status'] != result.safety_status.value:
            logger.warning(
                "Safety status changed after deep check",
                extra={
                    "before": result.safety_status.value,
                    "after": safety_result['status']
                }
            )
            result.safety_status = SafetyStatus(safety_result['status'])
            result.safety_reasoning = safety_result.get('reasoning')
            
            # Update action if unsafe
            if result.safety_status == SafetyStatus.UNSAFE:
                result.action_recommendation = ActionRecommendation.REJECT
        
        return result
    
    # ================== COMMON UTILITIES ==================
    
    def _determine_action(
        self,
        intent: IntentType,
        safety: SafetyStatus,
        confidence: ConfidenceBreakdown
    ) -> ActionRecommendation:
        """Determine recommended action"""
        
        if safety == SafetyStatus.UNSAFE:
            return ActionRecommendation.REJECT
        
        if intent == IntentType.MODIFY_APP and confidence.overall < 0.7:
            return ActionRecommendation.BLOCK_MODIFY
        
        if intent == IntentType.EXTEND_APP and confidence.overall < 0.7:
            return ActionRecommendation.BLOCK_EXTEND
        
        if confidence.overall < 0.6:
            return ActionRecommendation.CLARIFY
        
        return ActionRecommendation.PROCEED
    
    def _create_safe_fallback(self, prompt: str) -> IntentAnalysisResult:
        """Create safe fallback result"""
        return IntentAnalysisResult(
            intent_type=IntentType.CLARIFICATION,
            complexity=ComplexityLevel.MEDIUM,
            confidence=ConfidenceBreakdown(
                overall=0.3,
                intent_confidence=0.3,
                complexity_confidence=0.4,
                entity_confidence=0.2,
                safety_confidence=0.8,
            ),
            extracted_entities=ExtractedEntities(),
            action_recommendation=ActionRecommendation.CLARIFY,
            safety_status=SafetyStatus.SAFE,
            user_message="I need more information to understand your request.",
            source="fallback",
        )
    
    def _create_safe_result(
        self,
        intent_type: IntentType = IntentType.CLARIFICATION,
        safety_status: SafetyStatus = SafetyStatus.SAFE,
        safety_reasoning: Optional[str] = None
    ) -> IntentAnalysisResult:
        """Create safe result for edge cases"""
        return IntentAnalysisResult(
            intent_type=intent_type,
            complexity=ComplexityLevel.MEDIUM,
            confidence=ConfidenceBreakdown(overall=0.3),
            extracted_entities=ExtractedEntities(),
            action_recommendation=ActionRecommendation.CLARIFY,
            safety_status=safety_status,
            safety_reasoning=safety_reasoning,
            user_message="I need more information to understand your request.",
            source="safe_fallback"
        )
    
    # ================== CACHING ==================
    
    async def _check_cache(self, request: ClassificationRequest) -> Optional[IntentAnalysisResult]:
        """Check cache for result"""
        cache_key = self._cache_key(request)
        
        cached = await cache_manager.get(cache_key)
        if cached:
            try:
                # Convert dict to IntentAnalysisResult
                if isinstance(cached, dict):
                    # Reconstruct entities
                    entities_data = cached.get('extracted_entities', {})
                    entities = ExtractedEntities(**entities_data)
                    
                    # Reconstruct confidence
                    conf_data = cached.get('confidence', {})
                    confidence = ConfidenceBreakdown(**conf_data)
                    
                    # Reconstruct technical requirements if present
                    tech_data = cached.get('technical_requirements')
                    tech_reqs = TechnicalRequirements(**tech_data) if tech_data else None
                    
                    # Create result
                    result = IntentAnalysisResult(
                        intent_type=IntentType(cached.get('intent_type', 'clarification')),
                        complexity=ComplexityLevel.normalize(cached.get('complexity', 'medium')),
                        confidence=confidence,
                        extracted_entities=entities,
                        technical_requirements=tech_reqs,
                        action_recommendation=ActionRecommendation(cached.get('action_recommendation', 'clarify')),
                        safety_status=SafetyStatus(cached.get('safety_status', 'safe')),
                        requires_context=cached.get('requires_context', False),
                        user_message=cached.get('user_message'),
                        domain=AppDomain(cached.get('domain', 'custom')) if cached.get('domain') else None,
                        specific_type=cached.get('specific_type'),
                        source=cached.get('source', 'cache'),
                        total_latency_ms=cached.get('total_latency_ms', 0),
                        total_cost_usd=cached.get('total_cost_usd', 0),
                        tokens_used=cached.get('tokens_used', 0)
                    )
                    return result
            except Exception as e:
                logger.warning(f"Failed to deserialize cache: {e}")
        
        return None
    
    async def _cache_result(self, request: ClassificationRequest, result: IntentAnalysisResult):
        """Cache result"""
        cache_key = self._cache_key(request)
        await cache_manager.set(cache_key, result.to_dict(), ttl=self.cache_ttl)
    
    def _cache_key(self, request: ClassificationRequest) -> str:
        """Generate cache key"""
        data = f"{request.prompt.lower().strip()}|{request.user_id}"
        return f"intent:{hashlib.md5(data.encode()).hexdigest()[:32]}"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        total = self.stats['total_requests']
        if total == 0:
            return self.stats
        
        return {
            **self.stats,
            'cache_hit_rate': (self.stats['cache_hits'] / total) * 100,
            'llama3_success_rate': (self.stats['llama3_success'] / total) * 100,
            'heuristic_rate': (self.stats['heuristic_fallback'] / total) * 100,
            'avg_latency_ms': self.stats['total_latency_ms'] / total if total > 0 else 0,
        }
    
    def reset_stats(self):
        """Reset statistics"""
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'llama3_success': 0,
            'llama3_failures': 0,
            'heuristic_fallback': 0,
            'total_latency_ms': 0,
        }


# ================== FACTORY FUNCTION ==================

def create_intent_analyzer(config: Dict[str, Any]) -> ProductionIntentAnalyzer:
    """Factory function to create analyzer instance"""
    return ProductionIntentAnalyzer(config)


# ================== GLOBAL INSTANCE (for backward compatibility) ==================

def _create_global_instance():
    """Create global instance from environment/settings"""
    try:
        from app.config import settings
        
        config = {
            'llama3_api_url': getattr(settings, 'LLAMA3_API_URL', os.getenv('LLAMA3_API_URL', '')),
            'llama3_api_key': getattr(settings, 'LLAMA3_API_KEY', os.getenv('LLAMA3_API_KEY', '')),
            'llama3_model': getattr(settings, 'LLAMA3_MODEL', os.getenv('LLAMA3_MODEL', 'llama-3-70b-instruct')),
            'timeout': float(getattr(settings, 'LLAMA3_TIMEOUT', os.getenv('LLAMA3_TIMEOUT', '60.0'))),
            'max_retries': int(getattr(settings, 'LLAMA3_MAX_RETRIES', os.getenv('LLAMA3_MAX_RETRIES', '3'))),
            'enable_caching': True,
            'cache_ttl': 3600,
        }
        
        return ProductionIntentAnalyzer(config)
        
    except Exception as e:
        logger.warning(
            "Failed to create global intent analyzer from settings, using fallback config",
            extra={"error": str(e)}
        )
        
        # Fallback config - will use heuristic only
        fallback_config = {
            'llama3_api_url': os.getenv('LLAMA3_API_URL', ''),
            'llama3_api_key': os.getenv('LLAMA3_API_KEY', ''),
            'llama3_model': 'llama-3-70b-instruct',
            'timeout': 60.0,
            'max_retries': 3,
            'enable_caching': True,
            'cache_ttl': 3600,
        }
        
        return ProductionIntentAnalyzer(fallback_config)


# Create global instance
intent_analyzer = _create_global_instance()


# ================== EXPORTS ==================

__all__ = [
    "ProductionIntentAnalyzer",
    "create_intent_analyzer",
    "intent_analyzer",  # Global instance for backward compatibility
]