"""
Production-grade Architecture Generator with:
- Dynamic component catalog integration
- Multi-stage generation
- Self-correction
- Domain awareness
- Performance optimization
"""
import json
import asyncio
import re
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime, timezone
import hashlib

from app.config import settings
from app.models.schemas.architecture import ArchitectureDesign, ScreenDefinition, ScreenComponent
from app.models.schemas.context import EnrichedContext
from app.models.schemas.component_catalog import (
    get_available_components,
    get_component_definition,
    get_template_components,
    get_component_default_dimensions,
    get_component_default_properties,
    normalize_component_type
)
from app.services.generation.architecture_validator import architecture_validator, ValidationIssue
from app.services.generation.heuristic_generator import heuristic_architecture_generator
from app.llm.orchestrator import LLMOrchestrator
from app.llm.base import LLMMessage
from app.llm.prompt_manager import PromptManager, PromptType, PromptVersion
from app.core.cache import cache_manager
from app.utils.logging import get_logger, trace_async

logger = get_logger(__name__)


class ArchitectureGenerationError(Exception):
    """Base exception for architecture generation"""
    pass


class RetryableError(ArchitectureGenerationError):
    """Error that can be retried"""
    pass


class NonRetryableError(ArchitectureGenerationError):
    """Error that cannot be retried"""
    pass


class ArchitectureGenerator:
    """
    Production-grade architecture generator with:
    
    Generation Flow:
    1. Context enrichment from intent analysis
    2. Dynamic component catalog integration
    3. Multi-stage LLM generation with retries
    4. Self-correction based on validation
    5. Heuristic fallback
    6. Comprehensive validation
    
    Features:
    - Domain-aware generation
    - Component catalog integration
    - Automatic validation and correction
    - Caching for performance
    - Circuit breaker pattern
    - Detailed metrics
    """
    
    def __init__(self, orchestrator: Optional[LLMOrchestrator] = None):
        # Initialize LLM orchestrator
        if orchestrator:
            self.orchestrator = orchestrator
        else:
            config = {
                "failure_threshold": 3,
                "failure_window_minutes": 5,
                "llama3_api_url": settings.llama3_api_url,
                "llama3_api_key": settings.llama3_api_key
            }
            self.orchestrator = LLMOrchestrator(config)
        
        self.prompt_manager = PromptManager(default_version=PromptVersion.V3)
        self.validator = architecture_validator
        
        # Component catalog cache
        self.components_cache = {
            'all': get_available_components(),
            'by_category': self._categorize_components()
        }
        
        # Generation configuration
        self.max_retries = 3
        self.retry_delay = 2
        self.timeout_seconds = 30
        self.enable_caching = True
        self.cache_ttl = 3600  # 1 hour
        
        # Circuit breaker
        self.failure_count = 0
        self.failure_threshold = 5
        self.circuit_open = False
        self.circuit_reset_time = None
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'cached': 0,
            'retries': 0,
            'corrections': 0,
            'heuristic_fallbacks': 0,
            'avg_latency_ms': 0,
            'total_tokens': 0
        }
        
        logger.info(
            "🏗️ Architecture generator initialized",
            extra={
                "components_available": len(self.components_cache['all']),
                "max_retries": self.max_retries,
                "caching_enabled": self.enable_caching
            }
        )
    
    def _categorize_components(self) -> Dict[str, List[str]]:
        """Categorize components for better prompting"""
        categories = {}
        for comp in get_available_components():
            defn = get_component_definition(comp)
            if defn:
                cat = defn.get('category', 'other')
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(comp)
        return categories
    
    @trace_async("architecture.generation")
    async def generate(
        self,
        prompt: str,
        context: Optional[EnrichedContext] = None
    ) -> Tuple[ArchitectureDesign, Dict[str, Any]]:
        """
        Generate architecture with comprehensive context
        
        Flow:
        1. Check cache
        2. Check circuit breaker
        3. Extract generation parameters from context
        4. Try LLM generation with retries
        5. Validate and correct
        6. Fallback to heuristic if needed
        7. Cache result
        
        Args:
            prompt: User's request
            context: Enriched context from previous stages
            
        Returns:
            Tuple of (ArchitectureDesign, metadata)
            
        Raises:
            ArchitectureGenerationError: Only if all generation methods fail
        """
        start_time = datetime.now()
        self.stats['total_requests'] += 1
        
        # Check circuit breaker
        if self._is_circuit_open():
            logger.warning("⚠️ Circuit breaker open, using heuristic fallback")
            return await self._generate_with_heuristic(prompt, context)
        
        # Generate cache key
        cache_key = self._generate_cache_key(prompt, context)
        
        # Check cache
        if self.enable_caching:
            cached = await self._check_cache(cache_key)
            if cached:
                self.stats['cached'] += 1
                logger.info("✅ Cache hit", extra={"key": cache_key[:8]})
                return cached
        
        try:
            # Extract generation parameters from context
            params = self._extract_generation_params(prompt, context)
            
            # Try LLM generation with retries
            architecture, metadata = await self._generate_with_retry(params)
            
            # Post-generation enhancement
            architecture = await self._enhance_architecture(architecture, context)
            
            # Validate and auto-correct
            architecture, corrections = await self._validate_and_correct(architecture, context)
            if corrections:
                self.stats['corrections'] += len(corrections)
                metadata['corrections'] = corrections
            
            # Add metadata
            metadata.update({
                'generated_at': datetime.now(timezone.utc).isoformat(),
                'latency_ms': (datetime.now() - start_time).total_seconds() * 1000,
                'components_used': self._count_components(architecture),
                'cache_key': cache_key[:8]
            })
            
            # Update statistics
            self._update_stats(architecture, metadata)
            
            # Cache result
            if self.enable_caching:
                await self._cache_result(cache_key, architecture, metadata)
            
            # Reset failure count on success
            self.failure_count = 0
            
            logger.info(
                "✅ Architecture generation successful",
                extra={
                    "app_name": architecture.app_name,
                    "screens": len(architecture.screens),
                    "latency_ms": metadata['latency_ms']
                }
            )
            
            return architecture, metadata
            
        except Exception as e:
            self.failure_count += 1
            self.stats['failed'] += 1
            
            logger.error(
                "❌ Architecture generation failed",
                extra={"error": str(e), "failures": self.failure_count},
                exc_info=e
            )
            
            # Fallback to heuristic
            logger.info("🔄 Falling back to heuristic generator")
            self.stats['heuristic_fallbacks'] += 1
            return await self._generate_with_heuristic(prompt, context)
    
    def _extract_generation_params(
        self,
        prompt: str,
        context: Optional[EnrichedContext]
    ) -> Dict[str, Any]:
        """Extract generation parameters from context"""
        params = {
            'prompt': prompt,
            'components': self.components_cache['all'],
            'components_by_category': self.components_cache['by_category'],
            'domain': None,
            'intent_type': None,
            'complexity': None,
            'features': [],
            'existing_architecture': None
        }
        
        if context:
            # Extract from intent analysis
            intent = context.intent_analysis
            if intent:
                params['domain'] = intent.domain.value if intent.domain else None
                params['intent_type'] = intent.intent_type.value
                params['complexity'] = intent.complexity.value
                params['features'] = intent.extracted_entities.features
                
                # Add extracted components as hints
                if intent.extracted_entities.components:
                    params['hint_components'] = intent.extracted_entities.components
            
            # Extract from existing project
            if context.existing_project and context.existing_project.get('architecture'):
                params['existing_architecture'] = context.existing_project['architecture']
            
            # Add user preferences
            if context.user_preferences:
                params['preferences'] = context.user_preferences
        
        return params
    
    async def _generate_with_retry(
        self,
        params: Dict[str, Any]
    ) -> Tuple[ArchitectureDesign, Dict[str, Any]]:
        """Generate with exponential backoff retry"""
        last_error = None
        
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug(f"Generation attempt {attempt}/{self.max_retries}")
                
                # Different strategies per attempt
                if attempt == 1:
                    # First attempt: Standard generation
                    result = await self._generate_standard(params)
                elif attempt == 2:
                    # Second attempt: More explicit instructions
                    result = await self._generate_with_examples(params)
                else:
                    # Third attempt: Simplified generation
                    result = await self._generate_simplified(params)
                
                return result
                
            except RetryableError as e:
                last_error = e
                self.stats['retries'] += 1
                
                delay = self.retry_delay * (2 ** (attempt - 1))  # Exponential backoff
                logger.warning(
                    f"Attempt {attempt} failed, retrying in {delay}s",
                    extra={"error": str(e)}
                )
                await asyncio.sleep(delay)
                
            except Exception as e:
                # Non-retryable error
                raise NonRetryableError(f"Non-retryable error: {e}")
        
        raise ArchitectureGenerationError(f"All retries failed: {last_error}")
    
    async def _generate_standard(
        self,
        params: Dict[str, Any]
    ) -> Tuple[ArchitectureDesign, Dict[str, Any]]:
        """Standard generation with full context"""
        
        # Build component list for prompt
        components_str = self._format_components_for_prompt(params['components_by_category'])
        
        # Build context section
        context_str = self._build_context_section(params)
        
        # Get prompt from manager
        system_prompt = self._build_system_prompt(components_str)
        user_prompt = self._build_user_prompt(params['prompt'], context_str)
        
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt)
        ]
        
        # Generate with timeout
        try:
            response = await asyncio.wait_for(
                self.orchestrator.generate(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=4096,
                    validate_json=True
                ),
                timeout=self.timeout_seconds
            )
        except asyncio.TimeoutError:
            raise RetryableError(f"Generation timeout after {self.timeout_seconds}s")
        
        # Parse response
        architecture = await self._parse_architecture_response(response.content)
        
        # Build metadata
        metadata = {
            'generation_method': 'llm_standard',
            'provider': response.provider.value if hasattr(response, 'provider') else 'llama3',
            'tokens_used': response.tokens_used if hasattr(response, 'tokens_used') else 0,
            'api_duration_ms': response.duration_ms if hasattr(response, 'duration_ms') else 0,
            'attempt': 1
        }
        
        self.stats['total_tokens'] += metadata['tokens_used']
        
        return architecture, metadata
    
    async def _generate_with_examples(
        self,
        params: Dict[str, Any]
    ) -> Tuple[ArchitectureDesign, Dict[str, Any]]:
        """Generation with examples for better quality"""
        
        components_str = self._format_components_for_prompt(params['components_by_category'])
        examples = self._get_domain_examples(params.get('domain'))
        
        system_prompt = f"""You are an expert mobile app architect.

Available components by category:
{components_str}

Here are examples of good architectures for reference:
{examples}

Follow these guidelines:
1. Create meaningful screen names (e.g., "task_list", "create_task")
2. Each screen must have a clear purpose
3. Use components appropriately from the catalog
4. Define state for data that changes
5. Design intuitive navigation

Return ONLY valid JSON following the schema."""
        
        user_prompt = self._build_user_prompt(params['prompt'], self._build_context_section(params))
        
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt)
        ]
        
        response = await self.orchestrator.generate(
            messages=messages,
            temperature=0.5,  # Lower temperature for more consistent output
            max_tokens=4096,
            validate_json=True
        )
        
        architecture = await self._parse_architecture_response(response.content)
        
        metadata = {
            'generation_method': 'llm_with_examples',
            'provider': response.provider.value if hasattr(response, 'provider') else 'llama3',
            'tokens_used': response.tokens_used if hasattr(response, 'tokens_used') else 0,
            'api_duration_ms': response.duration_ms if hasattr(response, 'duration_ms') else 0,
            'attempt': 2
        }
        
        return architecture, metadata
    
    async def _generate_simplified(
        self,
        params: Dict[str, Any]
    ) -> Tuple[ArchitectureDesign, Dict[str, Any]]:
        """Simplified generation for final attempt"""
        
        system_prompt = """You are a mobile app architect. Create a simple but complete architecture.

Focus on:
- Essential screens only (2-3 max)
- Basic components from catalog
- Simple navigation
- Core state only

Return valid JSON."""
        
        user_prompt = f"""
User request: {params['prompt']}

Create a minimal but functional architecture for this app.
Use only necessary screens and components.
"""
        
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt)
        ]
        
        response = await self.orchestrator.generate(
            messages=messages,
            temperature=0.3,
            max_tokens=2048,
            validate_json=True
        )
        
        architecture = await self._parse_architecture_response(response.content)
        
        metadata = {
            'generation_method': 'llm_simplified',
            'provider': response.provider.value if hasattr(response, 'provider') else 'llama3',
            'tokens_used': response.tokens_used if hasattr(response, 'tokens_used') else 0,
            'api_duration_ms': response.duration_ms if hasattr(response, 'duration_ms') else 0,
            'attempt': 3
        }
        
        return architecture, metadata
    
    def _build_system_prompt(self, components_str: str) -> str:
        """Build comprehensive system prompt"""
        return f"""You are an expert mobile app architect designing production-ready applications.

AVAILABLE COMPONENTS (use ONLY these):
{components_str}

ARCHITECTURE REQUIREMENTS:
1. Create meaningful, descriptive screen IDs (snake_case)
2. Each screen must have a clear purpose statement
3. Use components appropriately from the available list
4. Define state for all data that changes
5. Design intuitive navigation between screens
6. Consider performance and user experience

OUTPUT SCHEMA (STRICT JSON):
{{
  "app_name": "string (descriptive name)",
  "app_type": "single-page | multi-page | navigation-based | tab-based",
  "screens": [
    {{
      "id": "string (snake_case)",
      "name": "string (display name)",
      "purpose": "string (clear description)",
      "components": [
        {{
          "component_type": "string (from available list)",
          "purpose": "string (what this component does)",
          "data_binding": "string (optional state variable)",
          "events": ["onPress", "onChange", etc.],
          "required_props": {{}}
        }}
      ],
      "navigation": ["screen_id1", "screen_id2"],
      "is_modal": false,
      "requires_auth": false
    }}
  ],
  "navigation": {{
    "type": "stack | tab | drawer",
    "routes": [
      {{"from_screen": "screen_id", "to_screen": "screen_id", "label": "optional"}}
    ],
    "initial_route": "screen_id"
  }},
  "state_management": [
    {{
      "name": "stateVarName",
      "type": "local-state | global-state",
      "scope": "component | screen | global",
      "initial_value": null,
      "description": "what this state represents",
      "persistence": "memory | async-storage"
    }}
  ],
  "data_flow": {{
    "user_interactions": ["action1", "action2"],
    "api_calls": [],
    "real_time_updates": false
  }}
}}

CRITICAL RULES:
- Return ONLY valid JSON, no explanations
- Use EXACT component names from available list
- Ensure all screen IDs are referenced correctly in navigation
- State variables must be camelCase
- Screen IDs must be snake_case

QUALITY GUIDELINES:
- Apps should have 2-5 screens typically
- Each screen should have 2-8 components
- Use appropriate component types for the job
- Consider edge cases in state management
- Design for real-world usage scenarios
"""
    
    def _build_user_prompt(self, prompt: str, context_str: str) -> str:
        """Build user prompt with context"""
        return f"""
USER REQUEST:
"{prompt}"

CONTEXT:
{context_str}

Design a complete, production-ready architecture for this app.
"""
    
    def _build_context_section(self, params: Dict[str, Any]) -> str:
        """Build context section from parameters"""
        parts = []
        
        if params.get('domain'):
            parts.append(f"Domain: {params['domain']}")
        
        if params.get('intent_type'):
            parts.append(f"Intent: {params['intent_type']}")
        
        if params.get('complexity'):
            parts.append(f"Complexity: {params['complexity']}")
        
        if params.get('features'):
            parts.append(f"Requested features: {', '.join(params['features'])}")
        
        if params.get('hint_components'):
            parts.append(f"Suggested components: {', '.join(params['hint_components'])}")
        
        if params.get('existing_architecture'):
            parts.append("Existing project context available")
        
        return "\n".join(parts) if parts else "No additional context"
    
    def _format_components_for_prompt(self, components_by_category: Dict[str, List[str]]) -> str:
        """Format components by category for prompt"""
        parts = []
        for category, comps in components_by_category.items():
            if comps:
                parts.append(f"  {category.upper()}: {', '.join(sorted(comps))}")
        return "\n".join(parts)
    
    def _get_domain_examples(self, domain: Optional[str]) -> str:
        """Get example architectures for domain"""
        examples = {
            "productivity": """
Example Todo App:
{
  "app_name": "TaskMaster",
  "screens": [
    {
      "id": "task_list",
      "name": "My Tasks",
      "components": [
        {"component_type": "SearchBar", "purpose": "Search tasks"},
        {"component_type": "List", "purpose": "Display tasks", "data_binding": "filtered_tasks"}
      ]
    }
  ]
}""",
            "iot_hardware": """
Example Drone Controller:
{
  "app_name": "Drone Pilot",
  "screens": [
    {
      "id": "control_panel",
      "name": "Control",
      "components": [
        {"component_type": "Joystick", "purpose": "Flight control"},
        {"component_type": "VideoView", "purpose": "FPV feed"}
      ]
    }
  ]
}"""
        }
        return examples.get(domain, "Standard app with list and detail screens")
    
    async def _parse_architecture_response(self, content: str) -> ArchitectureDesign:
        """Parse and validate LLM response"""
        
        # Clean response
        content = self._clean_llm_response(content)
        
        # Parse JSON
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            # Try to repair
            data = await self._repair_json(content)
            if not data:
                raise RetryableError(f"Could not parse JSON: {e}")
        
        # Validate required fields
        required = ['app_name', 'screens']
        missing = [f for f in required if f not in data]
        if missing:
            # Fill missing with defaults
            if 'app_name' not in data:
                data['app_name'] = "MyApp"
            if 'screens' not in data:
                data['screens'] = []
        
        # Ensure screens have required fields
        for screen in data.get('screens', []):
            if 'id' not in screen:
                screen['id'] = f"screen_{len(data['screens'])}"
            if 'name' not in screen:
                screen['name'] = screen['id'].replace('_', ' ').title()
            if 'purpose' not in screen:
                screen['purpose'] = f"Main screen for {screen['name']}"
            if 'components' not in screen:
                screen['components'] = []
        
        # Create ArchitectureDesign object
        try:
            architecture = ArchitectureDesign(**data)
            return architecture
        except Exception as e:
            logger.error(f"Pydantic validation error: {e}")
            raise RetryableError(f"Invalid architecture structure: {e}")
    
    def _clean_llm_response(self, content: str) -> str:
        """Clean LLM response of markdown and extra text"""
        # Remove markdown code blocks
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()
        
        # Extract JSON if embedded
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group()
        
        return content.strip()
    
    async def _repair_json(self, content: str) -> Optional[Dict[str, Any]]:
        """Attempt to repair malformed JSON"""
        try:
            # Remove trailing commas
            import re
            content = re.sub(r',(\s*[}\]])', r'\1', content)
            
            # Fix unquoted keys
            content = re.sub(r'(\s*)(\w+)(\s*):', r'\1"\2"\3:', content)
            
            # Try parsing again
            return json.loads(content)
        except:
            return None
    
    async def _validate_and_correct(
        self,
        architecture: ArchitectureDesign,
        context: Optional[EnrichedContext]
    ) -> Tuple[ArchitectureDesign, List[Dict[str, Any]]]:
        """Validate and auto-correct issues"""
        intent = context.intent_analysis if context else None
        is_valid, issues = await self.validator.validate(architecture, intent)
        
        corrections = []
        
        # Auto-correct fixable issues
        for issue in issues:
            if issue.level in ['warning', 'info'] and issue.auto_fix:
                try:
                    architecture = await issue.auto_fix(architecture)
                    corrections.append({
                        'issue': issue.message,
                        'fix': issue.suggestion
                    })
                except Exception as e:
                    logger.warning(f"Auto-fix failed: {e}")
        
        return architecture, corrections
    
    async def _enhance_architecture(
        self,
        architecture: ArchitectureDesign,
        context: Optional[EnrichedContext]
    ) -> ArchitectureDesign:
        """Post-generation enhancements"""
        
        # Add domain from context if missing
        if context and context.intent_analysis and context.intent_analysis.domain:
            if not architecture.domain:
                architecture.domain = context.intent_analysis.domain.value
        
        # Ensure each screen has at least one component
        for screen in architecture.screens:
            if not screen.components:
                # Add a default Text component
                screen.components.append(ScreenComponent(
                    component_type="Text",
                    purpose="Placeholder content",
                    events=[]
                ))
        
        return architecture
    
    async def _generate_with_heuristic(
        self,
        prompt: str,
        context: Optional[EnrichedContext]
    ) -> Tuple[ArchitectureDesign, Dict[str, Any]]:
        """Generate using heuristic fallback"""
        
        logger.info("🛡️ Using heuristic architecture generator")
        
        # Get template based on intent
        template_type = "generic"
        if context and context.intent_analysis:
            intent = context.intent_analysis
            if intent.domain:
                template_type = intent.domain.value
            elif intent.extracted_entities.features:
                # Use first feature as template hint
                template_type = intent.extracted_entities.features[0]
        
        architecture = await heuristic_architecture_generator.generate(
            prompt=prompt,
            template_type=template_type
        )
        
        metadata = {
            'generation_method': 'heuristic',
            'template_type': template_type,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        
        return architecture, metadata
    
    def _count_components(self, architecture: ArchitectureDesign) -> Dict[str, int]:
        """Count components by type"""
        counts = {}
        for screen in architecture.screens:
            for comp in screen.components:
                counts[comp.component_type] = counts.get(comp.component_type, 0) + 1
        return counts
    
    def _generate_cache_key(self, prompt: str, context: Optional[EnrichedContext]) -> str:
        """Generate cache key from prompt and context"""
        # Include intent info in cache key if available
        context_str = ""
        if context and context.intent_analysis:
            intent = context.intent_analysis
            context_str = f"|{intent.domain}|{intent.complexity}"
        
        data = f"{prompt.lower().strip()}{context_str}"
        return f"arch:{hashlib.sha256(data.encode()).hexdigest()[:32]}"
    
    async def _check_cache(
        self,
        cache_key: str
    ) -> Optional[Tuple[ArchitectureDesign, Dict[str, Any]]]:
        """Check cache for existing result"""
        cached = await cache_manager.get(cache_key)
        if cached:
            try:
                # Reconstruct architecture from cached dict
                if isinstance(cached, dict) and 'architecture' in cached:
                    arch_data = cached['architecture']
                    metadata = cached.get('metadata', {})
                    
                    # Handle different storage formats
                    if isinstance(arch_data, dict):
                        architecture = ArchitectureDesign(**arch_data)
                    else:
                        architecture = arch_data
                    
                    return architecture, metadata
            except Exception as e:
                logger.warning(f"Cache deserialization failed: {e}")
        
        return None
    
    async def _cache_result(
        self,
        cache_key: str,
        architecture: ArchitectureDesign,
        metadata: Dict[str, Any]
    ):
        """Cache generation result"""
        try:
            cache_data = {
                'architecture': architecture.model_dump(),
                'metadata': metadata,
                'cached_at': datetime.now(timezone.utc).isoformat()
            }
            await cache_manager.set(cache_key, cache_data, ttl=self.cache_ttl)
        except Exception as e:
            logger.warning(f"Cache write failed: {e}")
    
    def _is_circuit_open(self) -> bool:
        """Check if circuit breaker is open"""
        if not self.circuit_open:
            return False
        
        # Check if enough time has passed to reset
        if self.circuit_reset_time and datetime.now() > self.circuit_reset_time:
            self.circuit_open = False
            self.failure_count = 0
            self.circuit_reset_time = None
            logger.info("🔌 Circuit breaker reset")
            return False
        
        return True
    
    def _update_stats(self, architecture: ArchitectureDesign, metadata: Dict[str, Any]):
        """Update statistics"""
        self.stats['successful'] += 1
        
        # Update average latency
        total = self.stats['successful']
        current_avg = self.stats['avg_latency_ms']
        new_latency = metadata.get('latency_ms', 0)
        self.stats['avg_latency_ms'] = (current_avg * (total - 1) + new_latency) / total
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get generator statistics"""
        total_attempts = self.stats['successful'] + self.stats['failed']
        
        return {
            **self.stats,
            'success_rate': (self.stats['successful'] / total_attempts * 100) if total_attempts > 0 else 0,
            'cache_hit_rate': (self.stats['cached'] / self.stats['total_requests'] * 100) if self.stats['total_requests'] > 0 else 0,
            'circuit_breaker_open': self.circuit_open
        }


# Global instance
architecture_generator = ArchitectureGenerator()


__all__ = [
    'ArchitectureGenerator',
    'ArchitectureGenerationError',
    'architecture_generator'
]