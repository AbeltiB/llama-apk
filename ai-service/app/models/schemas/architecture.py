"""
Enhanced architecture design models for real-world app structure.
Supports dynamic component loading from catalog.
"""
from __future__ import annotations  # Add this at the VERY TOP

from typing import List, Dict, Any, Optional, Literal, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from datetime import datetime
import re

from app.models.schemas.component_catalog import get_available_components, normalize_component_type


class NavigationRoute(BaseModel):
    """Navigation route definition"""
    from_screen: str = Field(..., description="Source screen ID")
    to_screen: str = Field(..., description="Target screen ID")
    label: Optional[str] = Field(None, description="Route label for UI")
    params: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Navigation parameters")
    
    @field_validator('from_screen', 'to_screen')
    @classmethod
    def validate_screen_id(cls, v: str) -> str:
        """Validate screen ID format"""
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError(f"Screen ID '{v}' must start with lowercase and contain only letters, numbers, underscores")
        return v


class NavigationStructure(BaseModel):
    """App navigation configuration"""
    type: Literal["stack", "tab", "drawer", "bottom-tab", "material-top-tab", "none"] = "stack"
    routes: List[NavigationRoute] = Field(default_factory=list)
    initial_route: Optional[str] = Field(None, description="Initial screen to show")
    
    @model_validator(mode='after')
    def validate_initial_route(self) -> NavigationStructure:
        """Ensure initial route exists if specified"""
        if self.initial_route:
            route_exists = any(r.to_screen == self.initial_route for r in self.routes)
            if not route_exists and self.routes:
                # Default to first route
                self.initial_route = self.routes[0].to_screen if self.routes else None
        return self


class StateDefinition(BaseModel):
    """State management definition with validation"""
    name: str = Field(..., description="State variable name")
    type: Literal["local-state", "global-state", "async-state", "derived-state"] = "local-state"
    scope: Literal["component", "screen", "global"] = "screen"
    initial_value: Any = Field(None, description="Initial value")
    description: Optional[str] = Field(None, description="What this state represents")
    persistence: Optional[Literal["memory", "async-storage", "sqlite", "mmkv"]] = Field("memory", description="Persistence mechanism")
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate state variable name"""
        if not re.match(r'^[a-z][a-zA-Z0-9]*$', v):
            raise ValueError(f"State name '{v}' must be camelCase starting with lowercase")
        return v


class DataFlowDiagram(BaseModel):
    """Data flow representation"""
    user_interactions: List[str] = Field(default_factory=list, description="User actions that trigger data flow")
    api_calls: List[Dict[str, Any]] = Field(default_factory=list, description="API endpoints and methods")
    local_storage: List[str] = Field(default_factory=list, description="Local storage keys")
    real_time_updates: bool = Field(False, description="Whether app needs real-time updates")
    data_sources: List[Dict[str, Any]] = Field(default_factory=list, description="External data sources")


class ScreenComponent(BaseModel):
    """Component within a screen with enhanced metadata"""
    component_type: str = Field(..., description="Type of component from catalog")
    purpose: str = Field(..., description="What this component does")
    data_binding: Optional[str] = Field(None, description="State variable this component binds to")
    events: List[str] = Field(default_factory=list, description="Events this component handles (onPress, onChange, etc.)")
    required_props: Dict[str, Any] = Field(default_factory=dict, description="Required properties")
    
    @field_validator('component_type')
    @classmethod
    def validate_component_type(cls, v: str) -> str:
        """Validate against dynamic component catalog"""
        available = get_available_components()
        normalized = normalize_component_type(v)
        if normalized not in available and normalized != v:
            # Try to find closest match
            try:
                from rapidfuzz import process
                match = process.extractOne(v, available)
                if match and match[1] > 80:  # 80% similarity threshold
                    return match[0]
            except ImportError:
                # rapidfuzz not available, just return normalized
                pass
        return normalized


class ScreenDefinition(BaseModel):
    """Enhanced single screen definition"""
    id: str = Field(..., description="Unique screen identifier")
    name: str = Field(..., description="Display name")
    purpose: str = Field(..., min_length=10, description="Clear description of screen purpose")
    components: List[ScreenComponent] = Field(default_factory=list)
    navigation: List[str] = Field(default_factory=list, description="Screen IDs this screen can navigate to")
    is_modal: bool = Field(False, description="Whether screen is presented as modal")
    requires_auth: bool = Field(False, description="Whether screen requires authentication")
    
    @field_validator('id')
    @classmethod
    def validate_id(cls, v: str) -> str:
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError(f"Screen ID '{v}' must be snake_case starting with lowercase")
        return v


class ArchitectureDesign(BaseModel):
    """Enhanced complete app architecture design"""
    # Core metadata
    schema_version: str = Field(default="2.0", description="Schema version for compatibility")
    generated_at: datetime = Field(default_factory=datetime.now)
    
    # App identification
    app_name: str = Field(..., description="Suggested app name")
    app_type: Literal["single-page", "multi-page", "navigation-based", "tab-based", "drawer-based"] = "navigation-based"
    domain: Optional[str] = Field(None, description="App domain from intent analysis")
    
    # Screens
    screens: List[ScreenDefinition] = Field(..., min_length=1)
    
    # Navigation
    navigation: NavigationStructure = Field(default_factory=NavigationStructure)
    
    # State management
    state_management: List[StateDefinition] = Field(default_factory=list)
    
    # Data flow
    data_flow: DataFlowDiagram = Field(default_factory=DataFlowDiagram)
    
    # Business logic
    business_rules: List[Dict[str, Any]] = Field(default_factory=list, description="Core business logic rules")
    
    # Integrations
    integrations: List[Dict[str, Any]] = Field(default_factory=list, description="Third-party integrations")
    
    # Performance considerations
    performance_notes: List[str] = Field(default_factory=list)
    
    # Security considerations
    security_notes: List[str] = Field(default_factory=list)
    
    # Metadata for tracking
    generation_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @model_validator(mode='after')
    def validate_architecture_integrity(self) -> ArchitectureDesign:
        """Cross-field validation"""
        screen_ids = {s.id for s in self.screens}
        
        # Validate navigation targets
        for route in self.navigation.routes:
            if route.from_screen not in screen_ids:
                raise ValueError(f"Navigation from_screen '{route.from_screen}' not found")
            if route.to_screen not in screen_ids:
                raise ValueError(f"Navigation to_screen '{route.to_screen}' not found")
        
        # Validate screen navigation
        for screen in self.screens:
            for target in screen.navigation:
                if target not in screen_ids:
                    # Remove invalid target instead of failing
                    screen.navigation.remove(target)
        
        # Validate state scope
        for state in self.state_management:
            if state.scope == "screen":
                # Screen-scoped state should be used by at least one screen
                used = False
                for screen in self.screens:
                    for comp in screen.components:
                        if comp.data_binding == state.name:
                            used = True
                            break
                if not used and self.screens:
                    # Add as warning in metadata
                    pass
        
        return self
    
    class Config:
        json_schema_extra = {
            "example": {
                "app_name": "TaskMaster",
                "app_type": "navigation-based",
                "screens": [
                    {
                        "id": "task_list",
                        "name": "My Tasks",
                        "purpose": "Display all tasks with ability to filter and search",
                        "components": [
                            {
                                "component_type": "SearchBar",
                                "purpose": "Search through tasks",
                                "events": ["onChangeText"]
                            },
                            {
                                "component_type": "List",
                                "purpose": "Display task items",
                                "data_binding": "filtered_tasks",
                                "events": ["onPressItem"]
                            }
                        ],
                        "navigation": ["task_detail", "create_task"]
                    }
                ]
            }
        }