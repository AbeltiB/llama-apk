"""
Fixed Context Builder - Production Ready
Works with unified schemas and proper error handling
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.services.analysis.intent_schemas import IntentAnalysisResult
from app.models.schemas.component_catalog import get_template_components


class ContextRelevanceScore:
    """Calculate confidence that a project is relevant to current request"""
    
    @staticmethod
    def calculate(
        project: Dict[str, Any],
        user_id: str,
        session_id: str,
        intent_result: IntentAnalysisResult
    ) -> float:
        """
        Calculate relevance score (0.0 to 1.0)
        
        Args:
            project: Project data dict
            user_id: Current user ID
            session_id: Current session ID
            intent_result: Intent analysis result
            
        Returns:
            float: Relevance score
        """
        score = 0.0
        
        # CRITICAL: Ownership verification
        if project.get('user_id') != user_id:
            return 0.0  # Wrong user - NEVER return
        
        # Session match (highest weight)
        project_metadata = project.get('metadata', {})
        if project_metadata.get('session_id') == session_id:
            score += 0.6  # Same session = very relevant
        
        # Recency (within last hour)
        updated_at = project.get('updated_at')
        if updated_at:
            if isinstance(updated_at, str):
                updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            
            age_hours = (datetime.now(timezone.utc) - updated_at).total_seconds() / 3600
            if age_hours < 1:
                score += 0.3
            elif age_hours < 24:
                score += 0.1
        
        # Intent match - check if project domain matches intent domain
        if intent_result.domain:
            project_domain = project.get('domain') or project.get('metadata', {}).get('domain')
            if project_domain == intent_result.domain.value:
                score += 0.1
        
        return min(score, 1.0)


class EnrichedContext:
    """Container for enriched context data"""
    
    def __init__(
        self,
        original_request: Dict[str, Any],
        intent_analysis: IntentAnalysisResult,
        conversation_history: List[Dict[str, Any]] = None,
        existing_project: Optional[Dict[str, Any]] = None,
        project_confidence: float = 0.0,
        user_preferences: Dict[str, Any] = None,
        user_expertise: str = "beginner",
        timestamp: datetime = None
    ):
        self.original_request = original_request
        self.intent_analysis = intent_analysis
        self.conversation_history = conversation_history or []
        self.existing_project = existing_project
        self.project_confidence = project_confidence
        self.user_preferences = user_preferences or {}
        self.user_expertise = user_expertise
        self.timestamp = timestamp or datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "original_request": self.original_request,
            "intent_analysis": self.intent_analysis.to_dict(),
            "conversation_history": self.conversation_history,
            "existing_project": self.existing_project,
            "project_confidence": self.project_confidence,
            "user_preferences": self.user_preferences,
            "user_expertise": self.user_expertise,
            "timestamp": self.timestamp.isoformat()
        }


class ProductionContextBuilder:
    """
    Production-ready context builder
    
    Features:
    - Robust error handling
    - Proper schema validation
    - Works with any database manager
    - Graceful degradation
    - Intent-context integration
    - Project relevance scoring
    """
    
    # Minimum confidence threshold
    MIN_CONFIDENCE_THRESHOLD = 0.5
    
    def __init__(self, db_manager=None):
        """
        Initialize context builder
        
        Args:
            db_manager: Database manager instance (optional)
        """
        self.db_manager = db_manager
        self.stats = {
            'total_builds': 0,
            'with_project': 0,
            'with_history': 0,
            'errors': []
        }
        
        print("✅ Production context builder initialized")
    
    async def build_context(
        self,
        user_id: str,
        session_id: str,
        prompt: str,
        intent_result: IntentAnalysisResult,
        original_request: Dict[str, Any],
        project_id: Optional[str] = None
    ) -> EnrichedContext:
        """
        Build comprehensive enriched context
        
        Args:
            user_id: User identifier
            session_id: Session identifier
            prompt: User's prompt
            intent_result: Intent analysis result
            original_request: Original request data
            project_id: Optional explicit project ID
            
        Returns:
            EnrichedContext - GUARANTEED to return
        """
        self.stats['total_builds'] += 1
        
        print(f"🔨 Building context for user {user_id[:8]}...")
        
        try:
            # Create base context
            context = EnrichedContext(
                original_request=original_request,
                intent_analysis=intent_result,
                conversation_history=[],
                existing_project=None,
                project_confidence=0.0,
                user_preferences={},
                user_expertise="beginner",
                timestamp=datetime.now(timezone.utc)
            )
            
            # Load conversation history (if db available)
            if self.db_manager:
                try:
                    context.conversation_history = await self._load_conversation_history(
                        user_id=user_id,
                        session_id=session_id,
                        limit=10
                    )
                    if context.conversation_history:
                        self.stats['with_history'] += 1
                        print(f"   ✓ Loaded {len(context.conversation_history)} history items")
                        
                        # Determine user expertise from history
                        context.user_expertise = self._determine_expertise_from_history(
                            context.conversation_history
                        )
                except Exception as e:
                    print(f"   ⚠️  Failed to load history: {e}")
                    context.conversation_history = []
            
            # Load existing project (if needed)
            if intent_result.requires_context or project_id or intent_result.intent_type in [
                IntentType.MODIFY_APP, IntentType.EXTEND_APP
            ]:
                if self.db_manager:
                    try:
                        project_data = await self._load_existing_project_safe(
                            user_id=user_id,
                            session_id=session_id,
                            intent_result=intent_result,
                            explicit_project_id=project_id
                        )
                        
                        if project_data:
                            context.existing_project = project_data['project']
                            context.project_confidence = project_data['confidence']
                            self.stats['with_project'] += 1
                            print(f"   ✓ Loaded project: {context.existing_project.get('project_name', 'Unnamed')} (confidence: {context.project_confidence:.2f})")
                        elif intent_result.requires_context:
                            print(f"   ⚠️  Context required but no project found")
                    except Exception as e:
                        print(f"   ⚠️  Failed to load project: {e}")
                        self.stats['errors'].append(str(e))
                        context.existing_project = None
                        context.project_confidence = 0.0
            
            # Load user preferences (if db available)
            if self.db_manager:
                try:
                    context.user_preferences = await self._load_user_preferences(user_id)
                    if context.user_preferences:
                        print(f"   ✓ Loaded user preferences")
                except Exception as e:
                    print(f"   ⚠️  Failed to load preferences: {e}")
                    context.user_preferences = self._get_default_preferences()
            else:
                context.user_preferences = self._get_default_preferences()
            
            print(f"✅ Context built successfully")
            return context
            
        except Exception as e:
            print(f"❌ Critical error building context: {e}")
            self.stats['errors'].append(str(e))
            
            # Return minimal safe context
            return EnrichedContext(
                original_request=original_request,
                intent_analysis=intent_result,
                conversation_history=[],
                existing_project=None,
                project_confidence=0.0,
                user_preferences=self._get_default_preferences(),
                user_expertise="beginner",
                timestamp=datetime.now(timezone.utc)
            )
    
    def _determine_expertise_from_history(self, history: List[Dict[str, Any]]) -> str:
        """Determine user expertise level from conversation history"""
        if not history:
            return "beginner"
        
        # Look for technical terms in user messages
        technical_terms = [
            "api", "database", "backend", "frontend", "state", "redux",
            "component", "prop", "hook", "effect", "async", "promise",
            "bluetooth", "websocket", "hardware", "sensor", "drone"
        ]
        
        user_messages = [msg for msg in history if msg.get('role') == 'user']
        if not user_messages:
            return "beginner"
        
        # Count technical terms across all user messages
        technical_count = 0
        for msg in user_messages:
            content = msg.get('content', '').lower()
            technical_count += sum(1 for term in technical_terms if term in content)
        
        # Determine expertise
        if technical_count >= 5:
            return "expert"
        elif technical_count >= 2:
            return "intermediate"
        else:
            return "beginner"
    
    async def _load_conversation_history(
        self,
        user_id: str,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Load recent conversation history"""
        
        if not self.db_manager:
            return []
        
        try:
            if hasattr(self.db_manager, 'get_conversation_history'):
                conversations = await self.db_manager.get_conversation_history(
                    user_id=user_id,
                    session_id=session_id,
                    limit=limit
                )
                return conversations if conversations else []
            else:
                print("   ⓘ Database manager doesn't support conversation history")
                return []
                
        except Exception as e:
            print(f"   ⚠️  Error loading conversation history: {e}")
            return []
    
    async def _load_existing_project_safe(
        self,
        user_id: str,
        session_id: str,
        intent_result: IntentAnalysisResult,
        explicit_project_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Load existing project with strict validation
        
        Args:
            user_id: User identifier
            session_id: Session identifier  
            intent_result: Intent analysis result
            explicit_project_id: Optional explicit project ID
            
        Returns:
            Dict with 'project' and 'confidence' or None
        """
        
        if not self.db_manager:
            return None
        
        try:
            # Case 1: Explicit project ID provided
            if explicit_project_id:
                if hasattr(self.db_manager, 'get_project'):
                    project = await self.db_manager.get_project(explicit_project_id)
                    
                    if not project:
                        print(f"   ⚠️  Project {explicit_project_id} not found")
                        return None
                    
                    # CRITICAL: Verify ownership
                    if project.get('user_id') != user_id:
                        print(f"   🔴 SECURITY: Project ownership violation!")
                        return None
                    
                    return {
                        'project': project,
                        'confidence': 1.0,
                        'match_reason': 'explicit_project_id'
                    }
            
            # Case 2: Match by session_id and intent
            if hasattr(self.db_manager, 'get_user_projects'):
                projects = await self.db_manager.get_user_projects(
                    user_id=user_id,
                    limit=5
                )
                
                if not projects:
                    return None
                
                # Find best match with confidence scoring
                scored_projects = []
                
                for project in projects:
                    confidence = ContextRelevanceScore.calculate(
                        project=project,
                        user_id=user_id,
                        session_id=session_id,
                        intent_result=intent_result
                    )
                    
                    if confidence >= self.MIN_CONFIDENCE_THRESHOLD:
                        scored_projects.append({
                            'project': project,
                            'confidence': confidence,
                            'match_reason': 'session_match'
                        })
                
                if not scored_projects:
                    print(f"   ⓘ No confident project match found")
                    return None
                
                # Return highest confidence match
                best_match = max(scored_projects, key=lambda p: p['confidence'])
                return best_match
            
            return None
            
        except Exception as e:
            print(f"   ⚠️  Error loading project: {e}")
            return None
    
    async def _load_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Load user preferences"""
        
        if not self.db_manager:
            return self._get_default_preferences()
        
        try:
            if hasattr(self.db_manager, 'get_user_preferences'):
                preferences = await self.db_manager.get_user_preferences(user_id)
                return preferences if preferences else self._get_default_preferences()
            else:
                return self._get_default_preferences()
                
        except Exception as e:
            print(f"   ⚠️  Error loading preferences: {e}")
            return self._get_default_preferences()
    
    def _get_default_preferences(self) -> Dict[str, Any]:
        """Get default user preferences"""
        return {
            "theme": "light",
            "component_style": "detailed",
            "preferred_colors": {
                "primary": "#007AFF",
                "secondary": "#5856D6",
                "background": "#FFFFFF",
                "text": "#000000"
            },
            "layout_style": "modern",
            "enable_animations": True
        }
    
    def format_context_for_prompt(self, context: EnrichedContext) -> str:
        """Format enriched context into string for LLM prompts"""
        
        parts = []
        
        # Intent information
        intent = context.intent_analysis
        parts.append(f"**Intent:** {intent.intent_type.value}")
        parts.append(f"**Complexity:** {intent.complexity.value}")
        parts.append(f"**Confidence:** {intent.confidence.overall:.2f}")
        
        # Domain
        if intent.domain:
            parts.append(f"**Domain:** {intent.domain.value}")
        
        # Extracted entities
        if intent.extracted_entities.components:
            parts.append(f"**Components:** {', '.join(intent.extracted_entities.components)}")
        if intent.extracted_entities.features:
            parts.append(f"**Features:** {', '.join(intent.extracted_entities.features)}")
        
        # Technical requirements
        if intent.technical_requirements:
            reqs = []
            if intent.technical_requirements.needs_hardware:
                reqs.append("Hardware control")
            if intent.technical_requirements.needs_ai_ml:
                reqs.append("AI/ML processing")
            if intent.technical_requirements.needs_real_time:
                reqs.append("Real-time updates")
            if reqs:
                parts.append(f"**Technical Needs:** {', '.join(reqs)}")
        
        # Conversation history
        if context.conversation_history:
            recent = context.conversation_history[-3:]
            history_str = "\n".join([
                f"  - {msg.get('role', 'unknown')}: {msg.get('content', '')[:100]}"
                for msg in recent
            ])
            parts.append(f"**Recent Conversation:**\n{history_str}")
        
        # Existing project
        if context.existing_project and context.project_confidence >= self.MIN_CONFIDENCE_THRESHOLD:
            proj = context.existing_project
            
            parts.append(f"**Existing Project:** {proj.get('project_name', 'Unnamed')}")
            parts.append(f"  - Match confidence: {context.project_confidence:.2f}")
            
            if proj.get('architecture'):
                arch = proj['architecture']
                parts.append(f"  - Type: {arch.get('app_type', 'unknown')}")
                parts.append(f"  - Screens: {len(arch.get('screens', []))}")
        
        # User expertise
        parts.append(f"**User Expertise:** {context.user_expertise}")
        
        # User preferences
        if context.user_preferences:
            prefs = context.user_preferences
            parts.append(f"**User Preferences:**")
            if 'theme' in prefs:
                parts.append(f"  - Theme: {prefs['theme']}")
            if 'component_style' in prefs:
                parts.append(f"  - Style: {prefs['component_style']}")
        
        return "\n".join(parts)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics"""
        total = self.stats['total_builds']
        if total == 0:
            return self.stats
        
        return {
            **self.stats,
            'project_load_rate': (self.stats['with_project'] / total) * 100,
            'history_load_rate': (self.stats['with_history'] / total) * 100,
        }


# Global instance (optional)
context_builder = ProductionContextBuilder()


# Factory function
def create_context_builder(db_manager=None) -> ProductionContextBuilder:
    """
    Create context builder instance
    
    Args:
        db_manager: Optional database manager
        
    Returns:
        ProductionContextBuilder instance
    """
    return ProductionContextBuilder(db_manager)