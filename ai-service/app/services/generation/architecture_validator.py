"""
Production-grade Architecture Validator with comprehensive checks
Validates against dynamic component catalog and real-world requirements
"""
from typing import Dict, Any, List, Tuple, Optional, Set
from datetime import datetime
import re

from app.config import settings
from app.models.schemas.architecture import ArchitectureDesign, ScreenDefinition, ScreenComponent
from app.models.schemas.component_catalog import (
    get_available_components, 
    get_component_definition,
    get_component_by_category,
    is_input_component,
    has_component_event,
)
from app.services.analysis.intent_schemas import IntentAnalysisResult, AppDomain
from app.utils.logging import get_logger

logger = get_logger(__name__)


class ValidationIssue:
    """Rich validation issue with severity and fix suggestions"""
    
    def __init__(
        self,
        level: str,  # "critical", "error", "warning", "info", "suggestion"
        component: str,
        message: str,
        suggestion: str = "",
        auto_fix: Optional[callable] = None
    ):
        self.level = level
        self.component = component
        self.message = message
        self.suggestion = suggestion
        self.auto_fix = auto_fix
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, str]:
        return {
            'level': self.level,
            'component': self.component,
            'message': self.message,
            'suggestion': self.suggestion
        }
    
    def __str__(self) -> str:
        emoji = {
            "critical": "🔥",
            "error": "❌", 
            "warning": "⚠️",
            "info": "ℹ️",
            "suggestion": "💡"
        }
        return f"{emoji.get(self.level, '•')} [{self.level.upper()}] {self.component}: {self.message}"


class ArchitectureValidator:
    """
    Comprehensive architecture validator with:
    - Schema validation
    - Business logic validation  
    - Domain-specific validation
    - Performance validation
    - Security validation
    - Accessibility validation
    - Component catalog integration
    """
    
    def __init__(self):
        self.available_components = set(get_available_components())
        self.component_defs = {c: get_component_definition(c) for c in self.available_components}
        
        # Validation rules by domain
        self.domain_rules = self._init_domain_rules()
        
        # Statistics
        self.stats = {
            'total_validations': 0,
            'passed': 0,
            'failed': 0,
            'critical_issues': 0,
            'warnings': 0
        }
        
        logger.info(
            "🔍 Architecture validator initialized",
            extra={
                "available_components": len(self.available_components),
                "domains_supported": len(self.domain_rules)
            }
        )
    
    def _init_domain_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize domain-specific validation rules"""
        return {
            "productivity": {
                "required_patterns": ["list_screen", "detail_screen", "create_screen"],
                "common_features": ["search", "filter", "sort"],
                "performance_tips": ["virtualized_lists", "debounced_search"]
            },
            "iot_hardware": {
                "required_patterns": ["connection_screen", "control_screen", "monitoring_screen"],
                "common_features": ["bluetooth", "real_time", "telemetry"],
                "performance_tips": ["background_tasks", "low_latency", "reconnection_logic"],
                "security_tips": ["secure_pairing", "encrypted_communication"]
            },
            "ecommerce": {
                "required_patterns": ["product_list", "product_detail", "cart", "checkout"],
                "common_features": ["payment", "user_auth", "order_tracking"],
                "performance_tips": ["image_optimization", "lazy_loading"],
                "security_tips": ["payment_data_encryption", "secure_storage"]
            },
            "social": {
                "required_patterns": ["feed", "profile", "notifications"],
                "common_features": ["sharing", "likes", "comments"],
                "performance_tips": ["infinite_scroll", "image_caching"],
                "security_tips": ["content_moderation", "privacy_controls"]
            }
        }
    
    async def validate(
        self,
        architecture: ArchitectureDesign,
        intent: Optional[IntentAnalysisResult] = None,
        source: str = "llama3"
    ) -> Tuple[bool, List[ValidationIssue]]:
        """
        Validate architecture comprehensively
        
        Args:
            architecture: Architecture to validate
            intent: Optional intent result for domain-specific validation
            source: Source of architecture
            
        Returns:
            Tuple of (is_valid, issues_list)
        """
        self.stats['total_validations'] += 1
        issues: List[ValidationIssue] = []
        
        logger.info(
            "🔍 Architecture validation started",
            extra={
                "app_name": architecture.app_name,
                "screens": len(architecture.screens),
                "source": source,
                "domain": architecture.domain
            }
        )
        
        # Run all validation checks
        self._validate_schema_integrity(architecture, issues)
        self._validate_screens(architecture, issues)
        self._validate_components(architecture, issues)
        self._validate_navigation(architecture, issues)
        self._validate_state_management(architecture, issues)
        self._validate_data_flow(architecture, issues)
        self._validate_performance(architecture, issues)
        self._validate_security(architecture, issues)
        self._validate_accessibility(architecture, issues)
        self._validate_naming_conventions(architecture, issues)
        
        # Domain-specific validation if intent provided
        if intent and intent.domain:
            self._validate_domain_requirements(architecture, intent, issues)
        
        # Determine if architecture is valid
        critical_issues = [i for i in issues if i.level == "critical"]
        error_issues = [i for i in issues if i.level == "error"]
        is_valid = len(critical_issues) == 0 and len(error_issues) == 0
        
        # Update stats
        if is_valid:
            self.stats['passed'] += 1
        else:
            self.stats['failed'] += 1
        self.stats['critical_issues'] += len(critical_issues)
        self.stats['warnings'] += len([i for i in issues if i.level == "warning"])
        
        # Log results
        self._log_validation_results(issues, is_valid, source)
        
        return is_valid, issues
    
    def _validate_schema_integrity(self, arch: ArchitectureDesign, issues: List[ValidationIssue]):
        """Basic schema validation"""
        if not arch.screens:
            issues.append(ValidationIssue(
                level="critical",
                component="architecture",
                message="No screens defined",
                suggestion="Add at least one screen to the architecture"
            ))
        
        if len(arch.screens) > 20:
            issues.append(ValidationIssue(
                level="warning",
                component="architecture",
                message=f"Very high screen count ({len(arch.screens)})",
                suggestion="Consider consolidating screens or using dynamic content"
            ))
    
    def _validate_screens(self, arch: ArchitectureDesign, issues: List[ValidationIssue]):
        """Validate screen definitions"""
        screen_ids = set()
        
        for idx, screen in enumerate(arch.screens):
            # Check for duplicate IDs
            if screen.id in screen_ids:
                issues.append(ValidationIssue(
                    level="critical",
                    component=f"screen:{screen.id}",
                    message=f"Duplicate screen ID: {screen.id}",
                    suggestion="Use unique screen IDs"
                ))
            screen_ids.add(screen.id)
            
            # Validate screen purpose
            if len(screen.purpose) < 10:
                issues.append(ValidationIssue(
                    level="warning",
                    component=f"screen:{screen.id}",
                    message=f"Screen '{screen.name}' has unclear purpose",
                    suggestion="Add a clear description (minimum 10 characters)"
                ))
            
            # Check for empty screens
            if not screen.components:
                issues.append(ValidationIssue(
                    level="warning",
                    component=f"screen:{screen.id}",
                    message=f"Screen '{screen.name}' has no components",
                    suggestion="Add UI components to make the screen functional"
                ))
            
            # Validate component count per screen
            if len(screen.components) > 15:
                issues.append(ValidationIssue(
                    level="warning",
                    component=f"screen:{screen.id}",
                    message=f"Screen '{screen.name}' has many components ({len(screen.components)})",
                    suggestion="Consider breaking into multiple screens or using components wisely"
                ))
    
    def _validate_components(self, arch: ArchitectureDesign, issues: List[ValidationIssue]):
        """Validate component usage against catalog"""
        all_components = []
        component_by_screen = {}
        
        for screen in arch.screens:
            for comp in screen.components:
                all_components.append(comp.component_type)
                if screen.id not in component_by_screen:
                    component_by_screen[screen.id] = []
                component_by_screen[screen.id].append(comp.component_type)
                
                # Validate component exists in catalog
                if comp.component_type not in self.available_components:
                    # Try to find closest match
                    from rapidfuzz import process
                    match = process.extractOne(comp.component_type, list(self.available_components))
                    if match and match[1] > 70:
                        issues.append(ValidationIssue(
                            level="info",
                            component=f"component:{comp.component_type}",
                            message=f"Component '{comp.component_type}' mapped to '{match[0]}'",
                            suggestion=f"Consider using '{match[0]}' instead"
                        ))
                    else:
                        issues.append(ValidationIssue(
                            level="warning",
                            component=f"component:{comp.component_type}",
                            message=f"Unknown component type: {comp.component_type}",
                            suggestion=f"Available components: {sorted(self.available_components)[:10]}..."
                        ))
                
                # Validate component has required props
                comp_def = self.component_defs.get(comp.component_type)
                if comp_def and comp_def.get('schema'):
                    required_props = [
                        k for k, v in comp_def['schema'].items() 
                        if isinstance(v, dict) and v.get('required', False)
                    ]
                    for req_prop in required_props:
                        if req_prop not in comp.required_props and req_prop not in ['style']:
                            issues.append(ValidationIssue(
                                level="info",
                                component=f"component:{comp.component_type}",
                                message=f"Component may need '{req_prop}' property",
                                suggestion=f"Consider adding '{req_prop}' to required_props"
                            ))
        
        # Check component diversity
        unique_components = set(all_components)
        if len(unique_components) == 1 and len(all_components) > 3:
            comp = next(iter(unique_components))
            issues.append(ValidationIssue(
                level="warning",
                component="components",
                message=f"App uses only '{comp}' component type",
                suggestion="Add more component types for richer UI (Button, Input, Text, etc.)"
            ))
        
        # Check for interactive components on all screens
        for screen_id, comps in component_by_screen.items():
            has_interactive = any(
                has_component_event(c, 'onPress') or is_input_component(c)
                for c in comps
            )
            if not has_interactive and comps:
                issues.append(ValidationIssue(
                    level="info",
                    component=f"screen:{screen_id}",
                    message="Screen has no interactive components",
                    suggestion="Add buttons, inputs, or other interactive elements"
                ))
    
    def _validate_navigation(self, arch: ArchitectureDesign, issues: List[ValidationIssue]):
        """Validate navigation structure"""
        screen_ids = {s.id for s in arch.screens}
        
        if len(arch.screens) > 1 and not arch.navigation.routes:
            issues.append(ValidationIssue(
                level="error",
                component="navigation",
                message="Multi-screen app has no navigation routes defined",
                suggestion="Define navigation between screens"
            ))
        
        # Track reachable screens
        reachable = set()
        if arch.navigation.routes:
            # Start from first screen or initial route
            start = arch.navigation.initial_route or (arch.screens[0].id if arch.screens else None)
            if start:
                reachable.add(start)
                
                # BFS to find all reachable screens
                queue = [start]
                while queue:
                    current = queue.pop(0)
                    for route in arch.navigation.routes:
                        if route.from_screen == current and route.to_screen not in reachable:
                            reachable.add(route.to_screen)
                            queue.append(route.to_screen)
        
        # Check for orphaned screens
        orphaned = screen_ids - reachable
        if orphaned and len(arch.screens) > 1:
            issues.append(ValidationIssue(
                level="warning",
                component="navigation",
                message=f"Unreachable screens: {', '.join(sorted(orphaned))}",
                suggestion="Add navigation routes to make these screens accessible"
            ))
        
        # Check for dead ends (screens with no outgoing navigation)
        if len(arch.screens) > 1:
            for screen in arch.screens:
                has_outgoing = any(r.from_screen == screen.id for r in arch.navigation.routes)
                if not has_outgoing and screen.id != arch.screens[-1].id:
                    issues.append(ValidationIssue(
                        level="info",
                        component=f"screen:{screen.id}",
                        message=f"Screen '{screen.name}' has no outgoing navigation",
                        suggestion="Consider adding navigation to other screens"
                    ))
    
    def _validate_state_management(self, arch: ArchitectureDesign, issues: List[ValidationIssue]):
        """Validate state management"""
        if not arch.state_management and len(arch.screens) > 1:
            issues.append(ValidationIssue(
                level="info",
                component="state",
                message="No state management defined for multi-screen app",
                suggestion="Consider adding state for data sharing between screens"
            ))
        
        # Check for duplicate state names
        state_names = [s.name for s in arch.state_management]
        duplicates = [name for name in state_names if state_names.count(name) > 1]
        if duplicates:
            issues.append(ValidationIssue(
                level="error",
                component="state",
                message=f"Duplicate state variable names: {set(duplicates)}",
                suggestion="Use unique names for each state variable"
            ))
        
        # Check for unused state
        used_states = set()
        for screen in arch.screens:
            for comp in screen.components:
                if comp.data_binding:
                    used_states.add(comp.data_binding)
        
        for state in arch.state_management:
            if state.name not in used_states and state.scope != "global":
                issues.append(ValidationIssue(
                    level="info",
                    component=f"state:{state.name}",
                    message=f"State '{state.name}' defined but not used",
                    suggestion="Either use this state or remove it"
                ))
    
    def _validate_data_flow(self, arch: ArchitectureDesign, issues: List[ValidationIssue]):
        """Validate data flow"""
        if arch.data_flow.api_calls and not arch.state_management:
            issues.append(ValidationIssue(
                level="warning",
                component="data_flow",
                message="API calls defined but no state management for responses",
                suggestion="Add state variables to store API response data"
            ))
        
        # Check for RESTful API naming
        for api in arch.data_flow.api_calls:
            if isinstance(api, dict) and 'method' in api and 'path' in api:
                method = api['method'].upper()
                if method not in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                    issues.append(ValidationIssue(
                        level="info",
                        component="api",
                        message=f"Unusual HTTP method: {method}",
                        suggestion="Use standard REST methods (GET, POST, PUT, DELETE, PATCH)"
                    ))
    
    def _validate_performance(self, arch: ArchitectureDesign, issues: List[ValidationIssue]):
        """Validate performance considerations"""
        total_components = sum(len(s.components) for s in arch.screens)
        
        if total_components > 50:
            issues.append(ValidationIssue(
                level="warning",
                component="performance",
                message=f"High total component count ({total_components})",
                suggestion="Consider virtualization for lists, lazy loading for images"
            ))
        
        # Check for large lists
        for screen in arch.screens:
            for comp in screen.components:
                if comp.component_type in ['List', 'FlatList', 'SectionList']:
                    issues.append(ValidationIssue(
                        level="info",
                        component=f"screen:{screen.id}",
                        message="List component detected",
                        suggestion="Ensure lists use virtualization and have proper key extraction"
                    ))
    
    def _validate_security(self, arch: ArchitectureDesign, issues: List[ValidationIssue]):
        """Validate security considerations"""
        # Check for sensitive data in state
        sensitive_keywords = ['password', 'token', 'secret', 'key', 'credit', 'ssn']
        for state in arch.state_management:
            if any(kw in state.name.lower() for kw in sensitive_keywords):
                issues.append(ValidationIssue(
                    level="warning",
                    component=f"state:{state.name}",
                    message=f"State '{state.name}' may contain sensitive data",
                    suggestion="Ensure sensitive data is encrypted and not persisted insecurely"
                ))
        
        # Check for authentication
        has_auth = any(
            'auth' in s.name.lower() or 'login' in s.name.lower() or 'signup' in s.name.lower()
            for s in arch.screens
        )
        
        if has_auth and not any(s.requires_auth for s in arch.screens):
            issues.append(ValidationIssue(
                level="info",
                component="security",
                message="Authentication screens present but no screens marked as requiring auth",
                suggestion="Mark protected screens with requires_auth=True"
            ))
    
    def _validate_accessibility(self, arch: ArchitectureDesign, issues: List[ValidationIssue]):
        """Validate accessibility considerations"""
        for screen in arch.screens:
            for comp in screen.components:
                # Check for interactive components without event handlers
                if is_input_component(comp.component_type) and not comp.events:
                    issues.append(ValidationIssue(
                        level="info",
                        component=f"screen:{screen.id}.{comp.component_type}",
                        message=f"Input component '{comp.component_type}' has no events",
                        suggestion="Add event handlers like onChange, onPress"
                    ))
    
    def _validate_naming_conventions(self, arch: ArchitectureDesign, issues: List[ValidationIssue]):
        """Validate naming conventions"""
        # Screen names should be descriptive
        for screen in arch.screens:
            if len(screen.name) < 3:
                issues.append(ValidationIssue(
                    level="info",
                    component=f"screen:{screen.id}",
                    message=f"Screen name '{screen.name}' is too short",
                    suggestion="Use descriptive names like 'HomeScreen', 'ProfileScreen'"
                ))
        
        # App name should be proper
        if len(arch.app_name) < 3:
            issues.append(ValidationIssue(
                level="info",
                component="app_name",
                message=f"App name '{arch.app_name}' is too short",
                suggestion="Choose a more descriptive app name"
            ))
    
    def _validate_domain_requirements(
        self,
        arch: ArchitectureDesign,
        intent: IntentAnalysisResult,
        issues: List[ValidationIssue]
    ):
        """Validate domain-specific requirements"""
        if not intent.domain:
            return
        
        domain = intent.domain.value
        rules = self.domain_rules.get(domain, {})
        
        # Check required patterns
        required_patterns = rules.get('required_patterns', [])
        screen_names = [s.name.lower() for s in arch.screens]
        
        for pattern in required_patterns:
            found = any(pattern.replace('_', ' ') in name for name in screen_names)
            if not found:
                issues.append(ValidationIssue(
                    level="warning" if domain in ['iot_hardware', 'ecommerce'] else "info",
                    component="domain",
                    message=f"Domain '{domain}' typically needs a {pattern}",
                    suggestion=f"Consider adding a {pattern.replace('_', ' ')} screen"
                ))
        
        # Add domain-specific tips
        if domain == "iot_hardware":
            self._validate_hardware_requirements(arch, issues)
        elif domain == "ecommerce":
            self._validate_ecommerce_requirements(arch, issues)
    
    def _validate_hardware_requirements(self, arch: ArchitectureDesign, issues: List[ValidationIssue]):
        """Hardware-specific validation"""
        has_realtime = arch.data_flow.real_time_updates
        if not has_realtime:
            issues.append(ValidationIssue(
                level="warning",
                component="hardware",
                message="Hardware app may need real-time updates",
                suggestion="Enable real_time_updates for live device communication"
            ))
    
    def _validate_ecommerce_requirements(self, arch: ArchitectureDesign, issues: List[ValidationIssue]):
        """E-commerce specific validation"""
        has_checkout = any('checkout' in s.name.lower() for s in arch.screens)
        has_cart = any('cart' in s.name.lower() for s in arch.screens)
        
        if has_cart and not has_checkout:
            issues.append(ValidationIssue(
                level="warning",
                component="ecommerce",
                message="Cart screen present but no checkout screen",
                suggestion="Add a checkout screen for payment processing"
            ))
    
    def _log_validation_results(self, issues: List[ValidationIssue], is_valid: bool, source: str):
        """Log validation results"""
        levels = {}
        for issue in issues:
            levels[issue.level] = levels.get(issue.level, 0) + 1
        
        if is_valid:
            logger.info(
                "✅ Architecture validation passed",
                extra={
                    "issues": levels,
                    "source": source
                }
            )
        else:
            logger.warning(
                "⚠️ Architecture validation failed",
                extra={
                    "issues": levels,
                    "source": source
                }
            )
        
        # Log detailed issues
        if issues:
            logger.debug(
                "Validation details",
                extra={
                    "issues": [i.to_dict() for i in issues[:10]]  # First 10
                }
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get validation statistics"""
        total = self.stats['total_validations']
        return {
            **self.stats,
            'pass_rate': (self.stats['passed'] / total * 100) if total > 0 else 0,
            'avg_issues_per_validation': (
                (self.stats['critical_issues'] + self.stats['warnings']) / total
                if total > 0 else 0
            )
        }


# Global instance
architecture_validator = ArchitectureValidator()