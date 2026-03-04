"""
Enhanced heuristic architecture generator with template system
"""
from typing import Dict, Any, Optional, List
import re

from app.models.schemas.architecture import (
    ArchitectureDesign, ScreenDefinition, ScreenComponent,
    NavigationStructure, NavigationRoute, StateDefinition,
    DataFlowDiagram
)
from app.models.schemas.component_catalog import get_template_components
from app.utils.logging import get_logger

logger = get_logger(__name__)


class HeuristicArchitectureGenerator:
    """
    Template-based architecture generator for fallback scenarios
    """
    
    def __init__(self):
        self.templates = self._init_templates()
        logger.info("🛡️ Heuristic generator initialized", extra={"templates": len(self.templates)})
    
    def _init_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize architecture templates"""
        return {
            "todo": {
                "app_name": "TodoApp",
                "app_type": "navigation-based",
                "screens": [
                    {
                        "id": "task_list",
                        "name": "My Tasks",
                        "purpose": "View and manage all tasks",
                        "components": ["SearchBar", "List", "FloatingButton"],
                        "navigation": ["task_detail", "create_task"]
                    },
                    {
                        "id": "create_task",
                        "name": "New Task",
                        "purpose": "Create or edit a task",
                        "components": ["InputText", "TextArea", "DatePicker", "Button"],
                        "navigation": ["task_list"]
                    }
                ],
                "state": [
                    {"name": "tasks", "type": "global-state", "initial": []},
                    {"name": "filter", "type": "local-state", "initial": "all"}
                ]
            },
            "counter": {
                "app_name": "CounterApp",
                "app_type": "single-page",
                "screens": [
                    {
                        "id": "main",
                        "name": "Counter",
                        "purpose": "Display and modify counter",
                        "components": ["Text", "Button", "Button"],
                        "navigation": []
                    }
                ],
                "state": [
                    {"name": "count", "type": "local-state", "initial": 0}
                ]
            },
            "calculator": {
                "app_name": "Calculator",
                "app_type": "single-page",
                "screens": [
                    {
                        "id": "main",
                        "name": "Calculator",
                        "purpose": "Perform calculations",
                        "components": ["Text", "Button", "Button", "Button", "Button"],
                        "navigation": []
                    }
                ],
                "state": [
                    {"name": "display", "type": "local-state", "initial": "0"},
                    {"name": "operation", "type": "local-state", "initial": None}
                ]
            },
            "generic": {
                "app_name": "MyApp",
                "app_type": "navigation-based",
                "screens": [
                    {
                        "id": "home",
                        "name": "Home",
                        "purpose": "Main screen",
                        "components": ["Text", "Button"],
                        "navigation": ["details"]
                    },
                    {
                        "id": "details",
                        "name": "Details",
                        "purpose": "Detail view",
                        "components": ["Text", "Button"],
                        "navigation": ["home"]
                    }
                ],
                "state": []
            }
        }
    
    async def generate(
        self,
        prompt: str,
        template_type: str = "generic"
    ) -> ArchitectureDesign:
        """Generate architecture from template"""
        
        # Find best matching template
        template = self._find_template(prompt, template_type)
        
        # Convert to ArchitectureDesign
        screens = []
        for screen_data in template.get('screens', []):
            components = []
            for comp_name in screen_data.get('components', []):
                components.append(ScreenComponent(
                    component_type=comp_name,
                    purpose=f"Display {comp_name}",
                    events=[]
                ))
            
            screens.append(ScreenDefinition(
                id=screen_data['id'],
                name=screen_data['name'],
                purpose=screen_data['purpose'],
                components=components,
                navigation=screen_data.get('navigation', [])
            ))
        
        # Build navigation
        routes = []
        for screen in screens:
            for target in screen.navigation:
                routes.append(NavigationRoute(
                    from_screen=screen.id,
                    to_screen=target
                ))
        
        navigation = NavigationStructure(
            type="stack" if len(screens) > 1 else "none",
            routes=routes,
            initial_route=screens[0].id if screens else None
        )
        
        # Build state
        state = []
        for state_data in template.get('state', []):
            state.append(StateDefinition(
                name=state_data['name'],
                type=state_data.get('type', 'local-state'),
                scope=state_data.get('scope', 'screen'),
                initial_value=state_data.get('initial'),
                persistence="memory"
            ))
        
        return ArchitectureDesign(
            app_name=template.get('app_name', 'MyApp'),
            app_type=template.get('app_type', 'navigation-based'),
            screens=screens,
            navigation=navigation,
            state_management=state,
            data_flow=DataFlowDiagram()
        )
    
    def _find_template(self, prompt: str, template_type: str) -> Dict[str, Any]:
        """Find best matching template"""
        prompt_lower = prompt.lower()
        
        # Try exact match first
        if template_type in self.templates:
            return self.templates[template_type]
        
        # Try keyword matching
        for key, template in self.templates.items():
            if key in prompt_lower:
                return template
        
        # Return generic
        return self.templates['generic']


# Global instance
heuristic_architecture_generator = HeuristicArchitectureGenerator()