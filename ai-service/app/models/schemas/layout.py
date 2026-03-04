"""
Enhanced layout models with modern design patterns and validation.
"""
from __future__ import annotations

from enum import Enum
from typing import List, Dict, Any, Optional, Literal, Tuple
from pydantic import BaseModel, Field, model_validator, field_validator
import re

from .components import EnhancedComponentDefinition
from .component_catalog import get_component_default_dimensions


class Spacing(BaseModel):
    """Consistent spacing system"""
    unit: int = 8  # Base spacing unit
    xs: int = 4    # Extra small
    sm: int = 8    # Small
    md: int = 16   # Medium
    lg: int = 24   # Large
    xl: int = 32   # Extra large
    xxl: int = 48  # 2x Extra large


class Typography(BaseModel):
    """Typography scale"""
    h1: int = 32
    h2: int = 28
    h3: int = 24
    h4: int = 20
    body: int = 16
    body_small: int = 14
    caption: int = 12
    button: int = 16


class ColorPalette(BaseModel):
    """Modern color palette"""
    primary: str = "#007AFF"
    secondary: str = "#5856D6"
    success: str = "#34C759"
    danger: str = "#FF3B30"
    warning: str = "#FF9500"
    info: str = "#5856D6"
    light: str = "#F2F2F7"
    dark: str = "#1C1C1E"
    gray: str = "#8E8E93"
    background: str = "#FFFFFF"
    surface: str = "#F9F9FB"
    text_primary: str = "#000000"
    text_secondary: str = "#3C3C43"
    text_tertiary: str = "#8E8E93"


class DesignSystem(BaseModel):
    """Complete design system for consistent layouts"""
    spacing: Spacing = Field(default_factory=Spacing)
    typography: Typography = Field(default_factory=Typography)
    colors: ColorPalette = Field(default_factory=ColorPalette)
    borderRadius: Dict[str, int] = Field(default_factory=lambda: {
        "none": 0,
        "sm": 4,
        "md": 8,
        "lg": 12,
        "xl": 16,
        "full": 9999
    })
    shadows: Dict[str, Dict[str, Any]] = Field(default_factory=lambda: {
        "none": {},
        "sm": {
            "color": "#000",
            "opacity": 0.1,
            "radius": 4,
            "offset": {"width": 0, "height": 2}
        },
        "md": {
            "color": "#000",
            "opacity": 0.15,
            "radius": 8,
            "offset": {"width": 0, "height": 4}
        },
        "lg": {
            "color": "#000",
            "opacity": 0.2,
            "radius": 12,
            "offset": {"width": 0, "height": 6}
        }
    })


class LayoutPattern(str, Enum):
    """Modern layout patterns"""
    STACK_VERTICAL = "stack_vertical"
    STACK_HORIZONTAL = "stack_horizontal"
    GRID = "grid"
    CAROUSEL = "carousel"
    FORM = "form"
    MASTER_DETAIL = "master_detail"
    CARD = "card"
    LIST = "list"
    DASHBOARD = "dashboard"
    MODAL = "modal"
    TAB_BAR = "tab_bar"
    BOTTOM_SHEET = "bottom_sheet"
    DRAWER = "drawer"


class ComponentAlignment(BaseModel):
    """Alignment within layout"""
    horizontal: Literal["left", "center", "right", "stretch"] = "stretch"
    vertical: Literal["top", "center", "bottom", "stretch"] = "center"


class ComponentConstraints(BaseModel):
    """Layout constraints for responsive design"""
    min_width: Optional[int] = None
    max_width: Optional[int] = None
    min_height: Optional[int] = None
    max_height: Optional[int] = None
    aspect_ratio: Optional[float] = None
    flex: Optional[int] = None  # For flexbox layouts


class EnhancedComponentPlacement(BaseModel):
    """Enhanced component placement with design system integration"""
    component: EnhancedComponentDefinition
    alignment: ComponentAlignment = Field(default_factory=ComponentAlignment)
    constraints: ComponentConstraints = Field(default_factory=ComponentConstraints)
    margin: Dict[str, int] = Field(default_factory=lambda: {"top": 0, "bottom": 0, "left": 0, "right": 0})
    padding: Dict[str, int] = Field(default_factory=lambda: {"top": 0, "bottom": 0, "left": 0, "right": 0})


class ScreenSection(BaseModel):
    """A section of the screen with its own layout"""
    id: str
    type: Literal["header", "content", "footer", "sidebar", "modal"]
    components: List[EnhancedComponentPlacement]
    layout_pattern: LayoutPattern = LayoutPattern.STACK_VERTICAL
    background_color: Optional[str] = None
    spacing: int = 16  # Internal spacing between components


class EnhancedLayoutDefinition(BaseModel):
    """
    Enhanced layout with modern design patterns and responsive behavior
    """
    # Core
    screen_id: str
    screen_name: str
    
    # Design system
    design_system: DesignSystem = Field(default_factory=DesignSystem)
    
    # Canvas
    canvas: Dict[str, Any] = Field(
        default_factory=lambda: {
            "width": 375,
            "height": 667,
            "background_color": "#FFFFFF",
            "safe_area_insets": {
                "top": 47,   # Status bar + notch
                "bottom": 34, # Home indicator
                "left": 0,
                "right": 0
            }
        }
    )
    
    # Layout structure
    sections: List[ScreenSection] = Field(default_factory=list)
    
    # Legacy support (for backward compatibility)
    components: List[EnhancedComponentDefinition] = Field(default_factory=list)
    
    # Layout pattern for the entire screen
    primary_pattern: LayoutPattern = LayoutPattern.STACK_VERTICAL
    
    # Metadata
    layout_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @field_validator('screen_id')
    @classmethod
    def validate_screen_id(cls, v: str) -> str:
        """Validate screen ID format"""
        if not re.match(r'^[a-z][a-z0-9_]*$', v):
            raise ValueError(f"Screen ID '{v}' must be snake_case starting with lowercase")
        return v
    
    @model_validator(mode='after')
    def build_components_from_sections(self) -> EnhancedLayoutDefinition:
        """Build flat components list from sections for backward compatibility"""
        flat_components = []
        for section in self.sections:
            for placement in section.components:
                flat_components.append(placement.component)
        self.components = flat_components
        return self
    
    def get_safe_area_frame(self) -> Dict[str, int]:
        """Get the safe area frame accounting for insets"""
        insets = self.canvas.get("safe_area_insets", {})
        return {
            "x": 0,
            "y": insets.get("top", 0),
            "width": self.canvas["width"],
            "height": self.canvas["height"] - insets.get("top", 0) - insets.get("bottom", 0)
        }


class LayoutTemplate(BaseModel):
    """Predefined layout templates for common patterns"""
    name: str
    pattern: LayoutPattern
    sections: List[Dict[str, Any]]
    description: str


# Common layout templates
LAYOUT_TEMPLATES = {
    "form": LayoutTemplate(
        name="form",
        pattern=LayoutPattern.FORM,
        sections=[
            {
                "type": "header",
                "components": ["Text_Content"],
                "spacing": 16
            },
            {
                "type": "content",
                "components": ["Input_Text", "Input_Text", "Text_Area", "Button"],
                "spacing": 24
            }
        ],
        description="Standard form layout with header and input fields"
    ),
    "list_detail": LayoutTemplate(
        name="list_detail",
        pattern=LayoutPattern.MASTER_DETAIL,
        sections=[
            {
                "type": "header",
                "components": ["Text_Content", "Button"],
                "spacing": 16
            },
            {
                "type": "content",
                "components": ["List", "SearchBar"],
                "spacing": 16
            }
        ],
        description="List with search and detail navigation"
    ),
    "dashboard": LayoutTemplate(
        name="dashboard",
        pattern=LayoutPattern.DASHBOARD,
        sections=[
            {
                "type": "header",
                "components": ["Text_Content", "Button"],
                "spacing": 16
            },
            {
                "type": "content",
                "components": ["Chart", "Progress_Bar", "List"],
                "spacing": 24
            }
        ],
        description="Dashboard with charts and metrics"
    ),
    "media_player": LayoutTemplate(
        name="media_player",
        pattern=LayoutPattern.STACK_VERTICAL,
        sections=[
            {
                "type": "content",
                "components": ["Video", "Image"],
                "spacing": 16
            },
            {
                "type": "footer",
                "components": ["Slider", "Button", "Button"],
                "spacing": 16
            }
        ],
        description="Media player with controls"
    ),
    "drone_control": LayoutTemplate(
        name="drone_control",
        pattern=LayoutPattern.DASHBOARD,
        sections=[
            {
                "type": "header",
                "components": ["Text_Content", "Text_Content"],
                "spacing": 16
            },
            {
                "type": "content",
                "components": ["Video", "GoogleMap"],
                "spacing": 16
            },
            {
                "type": "footer",
                "components": ["Joystick", "Slider", "Button"],
                "spacing": 24
            }
        ],
        description="Drone control interface with video feed and controls"
    )
}