"""
Enhanced Layout Generator with modern design patterns
"""
import json
import asyncio
import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
from enum import Enum

from app.config import settings
from app.models.schemas.architecture import ArchitectureDesign, ScreenDefinition
from app.models.schemas.components import EnhancedComponentDefinition
from app.models.schemas.layout import (
    EnhancedLayoutDefinition, DesignSystem, Spacing, Typography, ColorPalette,
    ScreenSection, EnhancedComponentPlacement, ComponentAlignment,
    ComponentConstraints, LayoutPattern, LAYOUT_TEMPLATES
)
from app.models.schemas.core import PropertyValue
from app.models.schemas.component_catalog import (
    normalize_component_type,
    get_component_default_dimensions,
    get_component_default_properties,
    get_component_states,
    is_input_component,
    has_component_event,
    get_available_components,
    get_components_by_category
)
from app.llm.orchestrator import LLMOrchestrator
from app.llm.base import LLMMessage
from app.services.generation.layout_validator import layout_validator
from app.utils.logging import get_logger

logger = get_logger(__name__)


class LayoutDesignError(Exception):
    """Base exception for layout design errors"""
    pass


class LayoutGenerator:
    """
    Enhanced layout generator with modern design patterns
    
    Features:
    - Design system integration
    - Multiple layout patterns (form, list, dashboard, etc.)
    - Responsive layouts
    - Component grouping
    - Smart spacing
    - Platform conventions
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
        
        # Canvas constraints
        self.canvas_width = settings.canvas_width
        self.canvas_height = settings.canvas_height
        self.safe_area_top = settings.canvas_safe_area_top
        self.safe_area_bottom = settings.canvas_safe_area_bottom
        
        # Design system
        self.design_system = self._create_design_system()
        
        # Available components
        self.available_components = get_available_components()
        self.components_by_category = get_components_by_category()
        
        # Layout templates
        self.templates = LAYOUT_TEMPLATES
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 2
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'heuristic_fallbacks': 0,
            'llama3_successes': 0,
            'components_normalized': 0,
            'templates_used': {}
        }
        
        logger.info(
            "🎨 Layout generator initialized",
            extra={
                "canvas": f"{self.canvas_width}x{self.canvas_height}",
                "components": len(self.available_components),
                "templates": list(self.templates.keys())
            }
        )
    
    def _create_design_system(self) -> DesignSystem:
        """Create consistent design system"""
        return DesignSystem(
            spacing=Spacing(unit=8, xs=4, sm=8, md=16, lg=24, xl=32, xxl=48),
            typography=Typography(
                h1=32, h2=28, h3=24, h4=20,
                body=16, body_small=14, caption=12, button=16
            ),
            colors=ColorPalette(
                primary="#007AFF",
                secondary="#5856D6",
                success="#34C759",
                danger="#FF3B30",
                warning="#FF9500",
                info="#5856D6",
                light="#F2F2F7",
                dark="#1C1C1E",
                gray="#8E8E93",
                background="#FFFFFF",
                surface="#F9F9FB",
                text_primary="#000000",
                text_secondary="#3C3C43",
                text_tertiary="#8E8E93"
            )
        )
    
    @staticmethod
    def sanitize_id(id_str: str) -> str:
        """Convert any ID to safe format"""
        if not id_str:
            return "unnamed"
        sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', str(id_str))
        sanitized = re.sub(r'_+', '_', sanitized).strip('_')
        return sanitized or "unnamed"
    
    def _normalize_component_type(self, component_type: str) -> str:
        """Normalize component type using central catalog"""
        if not component_type:
            return "Text_Content"
        
        normalized = normalize_component_type(component_type, fallback="Text_Content")
        
        if normalized != component_type:
            self.stats['components_normalized'] += 1
            logger.debug(
                "layout.component.normalized",
                extra={"original": component_type, "normalized": normalized}
            )
        
        return normalized
    
    async def generate(
        self,
        architecture: ArchitectureDesign,
        screen_id: str
    ) -> Tuple[EnhancedLayoutDefinition, Dict[str, Any]]:
        """
        Generate modern layout for a specific screen
        
        Args:
            architecture: Complete architecture design
            screen_id: Screen to generate layout for
            
        Returns:
            Tuple of (EnhancedLayoutDefinition, metadata)
        """
        self.stats['total_requests'] += 1
        
        # Find the screen
        screen = None
        for s in architecture.screens:
            if s.id == screen_id:
                screen = s
                break
        
        if not screen:
            raise LayoutDesignError(f"Screen '{screen_id}' not found in architecture")
        
        safe_screen_id = self.sanitize_id(screen_id)
        
        logger.info(
            "🎨 Layout generation started",
            extra={
                "screen_name": screen.name,
                "screen_id": safe_screen_id,
                "required_components": len(screen.components)
            }
        )
        
        try:
            # Try LLM generation first
            layout, metadata = await self._generate_with_llm(screen, architecture)
            
            self.stats['llama3_successes'] += 1
            logger.info(
                "✅ LLM layout generation successful",
                extra={
                    "sections": len(layout.sections),
                    "components": len(layout.components)
                }
            )
            
        except Exception as e:
            logger.warning(f"LLM layout generation failed: {e}, using templates")
            self.stats['heuristic_fallbacks'] += 1
            
            # Fallback to template-based generation
            layout, metadata = await self._generate_with_template(screen, architecture)
            metadata['generation_method'] = 'template'
        
        # Validate layout
        is_valid, issues = await layout_validator.validate(layout)
        
        if not is_valid:
            logger.warning(
                "Layout validation found issues",
                extra={"issue_count": len(issues)}
            )
            metadata['validation_issues'] = [i.to_dict() for i in issues[:5]]
        
        # Add metadata
        metadata.update({
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'screen_name': screen.name,
            'validation_passed': is_valid,
            'validation_issues': len(issues)
        })
        
        self.stats['successful'] += 1
        
        return layout, metadata
    
    async def _generate_with_llm(
        self,
        screen: ScreenDefinition,
        architecture: ArchitectureDesign
    ) -> Tuple[EnhancedLayoutDefinition, Dict[str, Any]]:
        """Generate layout using LLM with modern design patterns"""
        
        # Determine layout pattern based on screen purpose
        layout_pattern = self._determine_layout_pattern(screen)
        
        # Build prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(screen, architecture, layout_pattern)
        
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt)
        ]
        
        # Call LLM
        response = await self.orchestrator.generate(
            messages=messages,
            temperature=0.7,
            max_tokens=4096
        )
        
        # Parse response
        layout_data = await self._parse_layout_response(response.content, screen)
        
        # Convert to EnhancedLayoutDefinition
        layout = await self._create_layout_from_data(
            layout_data, screen, architecture
        )
        
        metadata = {
            'generation_method': 'llm',
            'provider': getattr(response, 'provider', 'llama3'),
            'tokens_used': getattr(response, 'tokens_used', 0),
            'layout_pattern': layout_pattern
        }
        
        return layout, metadata
    
    def _build_system_prompt(self) -> str:
        """Build comprehensive system prompt with design principles"""
        
        components_by_cat = self.components_by_category
        
        return f"""You are an expert mobile UI/UX designer creating beautiful, modern app layouts.

DESIGN PHILOSOPHY:
- Clean, minimal, and purposeful
- Consistent spacing and alignment
- Visual hierarchy guides the eye
- Touch-friendly (minimum 44px targets)
- Platform conventions (iOS/Android)
- Accessibility first

DESIGN SYSTEM:
Spacing (multiples of 8px):
- xs: 4px (minimal separation)
- sm: 8px (related elements)
- md: 16px (grouped elements)
- lg: 24px (section separation)
- xl: 32px (major sections)
- xxl: 48px (screen sections)

Typography:
- h1: 32px (screen titles)
- h2: 28px (section headers)
- h3: 24px (card titles)
- h4: 20px (subheaders)
- body: 16px (regular text)
- body_small: 14px (secondary text)
- caption: 12px (labels)
- button: 16px (button text)

Colors:
- Primary: #007AFF (actions, key elements)
- Secondary: #5856D6 (secondary actions)
- Success: #34C759 (positive actions)
- Danger: #FF3B30 (destructive actions)
- Background: #FFFFFF (main background)
- Surface: #F9F9FB (cards, sheets)
- Text Primary: #000000 (primary text)
- Text Secondary: #3C3C43 (secondary text)

LAYOUT PATTERNS:
1. STACK_VERTICAL: Components stacked vertically (default)
2. STACK_HORIZONTAL: Components side by side (toolbars)
3. FORM: Label above input, consistent spacing (24px between fields)
4. LIST: Vertical list of similar items
5. CARD: Elevated containers with content
6. GRID: Equal-width columns (2-3 columns)
7. MASTER_DETAIL: List on left, detail on right
8. DASHBOARD: Cards with metrics and charts
9. MODAL: Centered content with overlay
10. BOTTOM_SHEET: Content sliding from bottom

AVAILABLE COMPONENTS by category:
{json.dumps(components_by_cat, indent=2)}

OUTPUT FORMAT - STRICT JSON:
{{
  "sections": [
    {{
      "id": "section_header",
      "type": "header",
      "layout_pattern": "stack_vertical",
      "spacing": 16,
      "components": [
        {{
          "component_type": "Text_Content",
          "purpose": "Screen title",
          "style": "h1",
          "alignment": {{"horizontal": "left", "vertical": "center"}}
        }}
      ]
    }},
    {{
      "id": "section_content",
      "type": "content",
      "layout_pattern": "form",
      "spacing": 24,
      "components": [
        {{
          "component_type": "Input_Text",
          "purpose": "Email input",
          "placeholder": "Enter your email",
          "margin": {{"top": 0, "bottom": 0}}
        }}
      ]
    }}
  ],
  "primary_pattern": "stack_vertical"
}}

RULES:
1. Use 8px grid system for all spacing
2. Minimum touch target: 44x44px
3. Group related components in sections
4. Labels above inputs, not beside
5. Buttons at bottom of forms
6. Back button top-left for detail screens
7. Use cards for grouped information
8. Maintain visual hierarchy
9. Consider both iOS and Android conventions
10. Return ONLY valid JSON
"""
    
    def _build_user_prompt(
        self,
        screen: ScreenDefinition,
        architecture: ArchitectureDesign,
        suggested_pattern: str
    ) -> str:
        """Build user prompt with screen details"""
        
        # Format required components
        components_list = []
        for comp in screen.components:
            if isinstance(comp, dict):
                comp_type = comp.get('component_type', 'Text_Content')
                comp_purpose = comp.get('purpose', '')
            else:
                comp_type = comp
                comp_purpose = ''
            
            components_list.append(f"- {comp_type}: {comp_purpose}")
        
        components_str = "\n".join(components_list) if components_list else "No specific components required"
        
        return f"""
SCREEN TO DESIGN:
ID: {screen.id}
Name: {screen.name}
Purpose: {screen.purpose}

REQUIRED COMPONENTS:
{components_str}

APP CONTEXT:
App Name: {architecture.app_name}
App Type: {architecture.app_type}
Domain: {getattr(architecture, 'domain', 'unknown')}

SUGGESTED LAYOUT PATTERN: {suggested_pattern}

Design a beautiful, modern layout for this screen that:
1. Follows the design system guidelines
2. Uses appropriate spacing (8px grid)
3. Groups related components logically
4. Creates clear visual hierarchy
5. Ensures good touch targets (min 44px)
6. Follows platform conventions

Return ONLY the JSON layout specification.
"""
    
    def _determine_layout_pattern(self, screen: ScreenDefinition) -> str:
        """Determine appropriate layout pattern based on screen purpose"""
        purpose_lower = screen.purpose.lower()
        components = [c.get('component_type', '') if isinstance(c, dict) else c 
                     for c in screen.components]
        
        # Pattern detection logic
        if any('form' in purpose_lower or 'create' in purpose_lower or 'edit' in purpose_lower):
            return "form"
        
        if any('list' in purpose_lower or 'browse' in purpose_lower or 'catalog' in purpose_lower):
            if 'SearchBar' in components:
                return "master_detail"
            return "list"
        
        if any('dashboard' in purpose_lower or 'overview' in purpose_lower or 'home' in purpose_lower):
            return "dashboard"
        
        if any('detail' in purpose_lower or 'view' in purpose_lower):
            if 'Image' in components or 'Video' in components:
                return "card"
            return "stack_vertical"
        
        if 'Chart' in components or 'Progress_Bar' in components:
            return "dashboard"
        
        if 'Joystick' in components or 'GoogleMap' in components:
            return "dashboard"
        
        if 'Input_Text' in components and len(components) > 2:
            return "form"
        
        return "stack_vertical"
    
    async def _parse_layout_response(
        self,
        content: str,
        screen: ScreenDefinition
    ) -> Dict[str, Any]:
        """Parse and validate LLM response"""
        
        # Clean response
        content = self._clean_json_response(content)
        
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            # Create default layout
            data = self._create_default_layout_data(screen)
        
        # Ensure required fields
        if 'sections' not in data:
            data['sections'] = []
        
        if 'primary_pattern' not in data:
            data['primary_pattern'] = 'stack_vertical'
        
        return data
    
    def _clean_json_response(self, text: str) -> str:
        """Clean JSON response from markdown and common issues"""
        text = text.strip()
        
        # Remove markdown code blocks
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0].strip()
        elif '```' in text:
            text = text.split('```')[1].split('```')[0].strip()
        
        # Extract JSON object
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            text = json_match.group()
        
        # Fix common issues
        text = re.sub(r',\s*}', '}', text)  # Remove trailing commas
        text = re.sub(r',\s*]', ']', text)
        text = re.sub(r'(\w+):', r'"\1":', text)  # Quote keys
        
        return text.strip()
    
    def _create_default_layout_data(self, screen: ScreenDefinition) -> Dict[str, Any]:
        """Create default layout data when parsing fails"""
        return {
            "sections": [
                {
                    "id": "header",
                    "type": "header",
                    "layout_pattern": "stack_vertical",
                    "spacing": 16,
                    "components": [
                        {
                            "component_type": "Text_Content",
                            "purpose": f"Screen title",
                            "style": "h1",
                            "text": screen.name
                        }
                    ]
                },
                {
                    "id": "content",
                    "type": "content",
                    "layout_pattern": "stack_vertical",
                    "spacing": 24,
                    "components": [
                        {
                            "component_type": comp if isinstance(comp, str) else comp.get('component_type', 'Text_Content'),
                            "purpose": f"Content component"
                        }
                        for comp in screen.components[:3]  # First 3 components
                    ]
                }
            ],
            "primary_pattern": "stack_vertical"
        }
    
    async def _create_layout_from_data(
        self,
        data: Dict[str, Any],
        screen: ScreenDefinition,
        architecture: ArchitectureDesign
    ) -> EnhancedLayoutDefinition:
        """Create EnhancedLayoutDefinition from parsed data"""
        
        sections = []
        all_components = []
        
        # Starting Y position (after safe area)
        current_y = self.safe_area_top + self.design_system.spacing.md
        
        for section_idx, section_data in enumerate(data.get('sections', [])):
            section_id = section_data.get('id', f"section_{section_idx}")
            section_type = section_data.get('type', 'content')
            section_pattern = section_data.get('layout_pattern', 'stack_vertical')
            section_spacing = section_data.get('spacing', self.design_system.spacing.md)
            
            section_components = []
            
            for comp_idx, comp_data in enumerate(section_data.get('components', [])):
                # Get component type
                raw_type = comp_data.get('component_type', 'Text_Content')
                comp_type = self._normalize_component_type(raw_type)
                
                # Get default dimensions
                width, height = get_component_default_dimensions(comp_type)
                
                # Calculate position (centered horizontally)
                x = (self.canvas_width - width) // 2
                
                # Adjust for section pattern
                if section_pattern == 'form':
                    x = self.design_system.spacing.lg  # Left-aligned for forms
                elif section_pattern == 'dashboard':
                    if comp_idx % 2 == 0:  # Two-column grid
                        x = self.design_system.spacing.md
                    else:
                        x = self.canvas_width - width - self.design_system.spacing.md
                
                # Create style
                style = {
                    'left': x,
                    'top': current_y,
                    'width': width,
                    'height': height
                }
                
                # Create component properties
                properties = {
                    'style': PropertyValue(type="literal", value=style)
                }
                
                # Add component-specific properties
                if comp_type == 'Text_Content':
                    text = comp_data.get('text', screen.name if comp_idx == 0 else 'Content')
                    properties['text'] = PropertyValue(type="literal", value=text)
                    
                    # Apply typography
                    style_hint = comp_data.get('style', 'body')
                    if style_hint == 'h1':
                        properties['fontSize'] = PropertyValue(type="literal", value=self.design_system.typography.h1)
                    elif style_hint == 'h2':
                        properties['fontSize'] = PropertyValue(type="literal", value=self.design_system.typography.h2)
                    elif style_hint == 'h3':
                        properties['fontSize'] = PropertyValue(type="literal", value=self.design_system.typography.h3)
                    elif style_hint == 'body':
                        properties['fontSize'] = PropertyValue(type="literal", value=self.design_system.typography.body)
                    
                    properties['color'] = PropertyValue(type="literal", value=self.design_system.colors.text_primary)
                
                elif comp_type == 'Button':
                    text = comp_data.get('text', 'Button')
                    properties['text'] = PropertyValue(type="literal", value=text)
                    
                    # Primary vs secondary
                    if comp_idx == len(section_data.get('components', [])) - 1:  # Last button is primary
                        properties['variant'] = PropertyValue(type="literal", value="primary")
                        properties['backgroundColor'] = PropertyValue(type="literal", value=self.design_system.colors.primary)
                    else:
                        properties['variant'] = PropertyValue(type="literal", value="outline")
                        properties['backgroundColor'] = PropertyValue(type="literal", value="transparent")
                
                elif comp_type == 'Input_Text':
                    placeholder = comp_data.get('placeholder', 'Enter text...')
                    properties['placeholder'] = PropertyValue(type="literal", value=placeholder)
                    properties['backgroundColor'] = PropertyValue(type="literal", value=self.design_system.colors.surface)
                
                elif comp_type == 'SearchBar':
                    properties['placeholder'] = PropertyValue(type="literal", value="Search...")
                    properties['backgroundColor'] = PropertyValue(type="literal", value=self.design_system.colors.surface)
                
                elif comp_type == 'List':
                    properties['backgroundColor'] = PropertyValue(type="literal", value="transparent")
                
                elif comp_type == 'Checkbox':
                    properties['label'] = PropertyValue(type="literal", value=comp_data.get('label', 'Option'))
                    properties['color'] = PropertyValue(type="literal", value=self.design_system.colors.primary)
                
                elif comp_type == 'Slider':
                    properties['min'] = PropertyValue(type="literal", value=0)
                    properties['max'] = PropertyValue(type="literal", value=100)
                    properties['value'] = PropertyValue(type="literal", value=50)
                    properties['thumbColor'] = PropertyValue(type="literal", value=self.design_system.colors.primary)
                
                elif comp_type == 'Progress_Bar':
                    properties['value'] = PropertyValue(type="literal", value=50)
                    properties['indicatorColor'] = PropertyValue(type="literal", value=self.design_system.colors.primary)
                
                elif comp_type == 'Joystick':
                    properties['size'] = PropertyValue(type="literal", value=150)
                    properties['color'] = PropertyValue(type="literal", value=self.design_system.colors.primary)
                
                elif comp_type == 'GoogleMap':
                    properties['latitude'] = PropertyValue(type="literal", value=37.7749)
                    properties['longitude'] = PropertyValue(type="literal", value=-122.4194)
                
                # Create component
                component_id = f"{self.sanitize_id(screen.id)}_{comp_type.lower()}_{comp_idx}"
                
                component = EnhancedComponentDefinition(
                    component_id=component_id,
                    component_type=comp_type,
                    properties=properties,
                    z_index=comp_idx
                )
                
                # Create placement
                placement = EnhancedComponentPlacement(
                    component=component,
                    alignment=ComponentAlignment(
                        horizontal="center",
                        vertical="center"
                    ),
                    margin={"top": 0, "bottom": 0, "left": 0, "right": 0}
                )
                
                section_components.append(placement)
                all_components.append(component)
                
                # Update Y position for next component
                current_y += height + section_spacing
            
            # Create section
            section = ScreenSection(
                id=section_id,
                type=section_type,
                components=section_components,
                layout_pattern=LayoutPattern(section_pattern),
                spacing=section_spacing
            )
            
            sections.append(section)
            
            # Add extra spacing between sections
            current_y += self.design_system.spacing.xl
        
        # Create layout
        layout = EnhancedLayoutDefinition(
            screen_id=self.sanitize_id(screen.id),
            screen_name=screen.name,
            design_system=self.design_system,
            sections=sections,
            primary_pattern=LayoutPattern(data.get('primary_pattern', 'stack_vertical')),
            canvas={
                "width": self.canvas_width,
                "height": self.canvas_height,
                "background_color": "#FFFFFF",
                "safe_area_insets": {
                    "top": self.safe_area_top,
                    "bottom": self.safe_area_bottom,
                    "left": 0,
                    "right": 0
                }
            }
        )
        
        return layout
    
    async def _generate_with_template(
        self,
        screen: ScreenDefinition,
        architecture: ArchitectureDesign
    ) -> Tuple[EnhancedLayoutDefinition, Dict[str, Any]]:
        """Generate layout using templates"""
        
        # Determine template type
        template_type = self._determine_template_type(screen, architecture)
        
        # Get template
        template = self.templates.get(template_type, self.templates['form'])
        
        # Build sections from template
        sections = []
        all_components = []
        current_y = self.safe_area_top + self.design_system.spacing.md
        
        for section_idx, section_template in enumerate(template.sections):
            section_id = f"section_{section_idx}"
            section_type = section_template['type']
            section_spacing = section_template.get('spacing', 16)
            
            section_components = []
            
            for comp_idx, comp_type in enumerate(section_template['components']):
                # Get component type
                normalized_type = self._normalize_component_type(comp_type)
                
                # Get dimensions
                width, height = get_component_default_dimensions(normalized_type)
                
                # Calculate position (centered)
                x = (self.canvas_width - width) // 2
                
                # Create style
                style = {
                    'left': x,
                    'top': current_y,
                    'width': width,
                    'height': height
                }
                
                # Create properties
                properties = {
                    'style': PropertyValue(type="literal", value=style)
                }
                
                # Add default properties
                defaults = get_component_default_properties(normalized_type)
                for key, value in defaults.items():
                    properties[key] = PropertyValue(type="literal", value=value)
                
                # Apply design system
                if normalized_type == 'Text_Content':
                    if comp_idx == 0 and section_type == 'header':
                        properties['fontSize'] = PropertyValue(type="literal", value=self.design_system.typography.h2)
                        properties['text'] = PropertyValue(type="literal", value=screen.name)
                    else:
                        properties['fontSize'] = PropertyValue(type="literal", value=self.design_system.typography.body)
                        properties['text'] = PropertyValue(type="literal", value="Content")
                    
                    properties['color'] = PropertyValue(type="literal", value=self.design_system.colors.text_primary)
                
                elif normalized_type == 'Button':
                    if 'primary' in comp_type.lower() or comp_idx == len(section_template['components']) - 1:
                        properties['variant'] = PropertyValue(type="literal", value="primary")
                        properties['backgroundColor'] = PropertyValue(type="literal", value=self.design_system.colors.primary)
                    else:
                        properties['variant'] = PropertyValue(type="literal", value="outline")
                        properties['backgroundColor'] = PropertyValue(type="literal", value="transparent")
                    
                    properties['text'] = PropertyValue(type="literal", value="Button")
                
                elif normalized_type == 'Input_Text':
                    properties['placeholder'] = PropertyValue(type="literal", value="Enter text...")
                    properties['backgroundColor'] = PropertyValue(type="literal", value=self.design_system.colors.surface)
                
                # Create component
                component_id = f"{self.sanitize_id(screen.id)}_{normalized_type.lower()}_{section_idx}_{comp_idx}"
                
                component = EnhancedComponentDefinition(
                    component_id=component_id,
                    component_type=normalized_type,
                    properties=properties,
                    z_index=comp_idx
                )
                
                # Create placement
                placement = EnhancedComponentPlacement(
                    component=component,
                    alignment=ComponentAlignment(horizontal="center", vertical="center")
                )
                
                section_components.append(placement)
                all_components.append(component)
                
                # Update Y position
                current_y += height + section_spacing
            
            # Create section
            section = ScreenSection(
                id=section_id,
                type=section_type,
                components=section_components,
                layout_pattern=LayoutPattern(template.pattern),
                spacing=section_spacing
            )
            
            sections.append(section)
            current_y += self.design_system.spacing.xl
        
        # Create layout
        layout = EnhancedLayoutDefinition(
            screen_id=self.sanitize_id(screen.id),
            screen_name=screen.name,
            design_system=self.design_system,
            sections=sections,
            primary_pattern=template.pattern,
            canvas={
                "width": self.canvas_width,
                "height": self.canvas_height,
                "background_color": "#FFFFFF",
                "safe_area_insets": {
                    "top": self.safe_area_top,
                    "bottom": self.safe_area_bottom,
                    "left": 0,
                    "right": 0
                }
            }
        )
        
        metadata = {
            'generation_method': 'template',
            'template_used': template_type,
            'sections': len(sections),
            'components': len(all_components)
        }
        
        self.stats['templates_used'][template_type] = self.stats['templates_used'].get(template_type, 0) + 1
        
        return layout, metadata
    
    def _determine_template_type(
        self,
        screen: ScreenDefinition,
        architecture: ArchitectureDesign
    ) -> str:
        """Determine appropriate template type"""
        purpose_lower = screen.purpose.lower()
        
        # Check domain from architecture
        domain = getattr(architecture, 'domain', '')
        
        if domain == 'iot_hardware' or 'drone' in purpose_lower:
            return 'drone_control'
        
        if 'media' in purpose_lower or 'video' in purpose_lower or 'player' in purpose_lower:
            return 'media_player'
        
        if 'dashboard' in purpose_lower or 'overview' in purpose_lower:
            return 'dashboard'
        
        if 'form' in purpose_lower or 'create' in purpose_lower or 'edit' in purpose_lower:
            return 'form'
        
        if 'list' in purpose_lower or 'browse' in purpose_lower:
            return 'list_detail'
        
        return 'form'  # Default
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get generator statistics"""
        total = self.stats['total_requests']
        return {
            **self.stats,
            'success_rate': (self.stats['successful'] / total * 100) if total > 0 else 0,
            'llama3_rate': (self.stats['llama3_successes'] / total * 100) if total > 0 else 0,
            'heuristic_rate': (self.stats['heuristic_fallbacks'] / total * 100) if total > 0 else 0
        }


# Global instance
layout_generator = LayoutGenerator()