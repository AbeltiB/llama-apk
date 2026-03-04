"""
Enhanced Layout Validator with modern design validation
"""
from typing import List, Tuple, Dict, Any, Optional
import math

from app.config import settings
from app.models.schemas.layout import (
    EnhancedLayoutDefinition, ScreenSection, EnhancedComponentPlacement,
    DesignSystem, LayoutPattern
)
from app.models.schemas.components import EnhancedComponentDefinition
from app.models.schemas.core import PropertyValue
from app.models.schemas.component_catalog import (
    get_interactive_components, is_input_component,
    get_component_default_dimensions
)
from app.utils.logging import get_logger

logger = get_logger(__name__)


class LayoutValidationIssue:
    """Rich validation issue with severity and suggestions"""
    
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


class LayoutValidator:
    """
    Comprehensive layout validation with modern design principles
    
    Validates:
    - Technical constraints (bounds, collisions)
    - Design system compliance (spacing, typography)
    - UX best practices (touch targets, form layout)
    - Accessibility (contrast, labels)
    - Platform conventions (safe areas)
    """
    
    def __init__(self):
        self.canvas_width = settings.canvas_width
        self.canvas_height = settings.canvas_height
        self.min_touch_size = settings.min_touch_target_size
        
        # Design system defaults
        self.base_spacing = 8
        self.ideal_form_spacing = 24
        self.ideal_section_spacing = 32
        
        # Statistics
        self.stats = {
            'total_validations': 0,
            'passed': 0,
            'failed': 0,
            'warnings': 0,
            'suggestions': 0
        }
        
        logger.info(
            "🔍 Layout validator initialized",
            extra={
                "canvas": f"{self.canvas_width}x{self.canvas_height}",
                "min_touch_size": self.min_touch_size
            }
        )
    
    async def validate(
        self,
        layout: EnhancedLayoutDefinition
    ) -> Tuple[bool, List[LayoutValidationIssue]]:
        """
        Comprehensive validation of layout
        
        Args:
            layout: Layout to validate
            
        Returns:
            Tuple of (is_valid, issues_list)
        """
        self.stats['total_validations'] += 1
        issues: List[LayoutValidationIssue] = []
        
        logger.info(
            "🔍 Layout validation started",
            extra={
                "screen_id": layout.screen_id,
                "screen_name": layout.screen_name,
                "sections": len(layout.sections) if hasattr(layout, 'sections') else 0,
                "components": len(layout.components)
            }
        )
        
        # Technical validation
        self._validate_canvas(layout, issues)
        self._validate_component_bounds(layout, issues)
        self._validate_collisions(layout, issues)
        self._validate_unique_ids(layout, issues)
        
        # Design system validation
        self._validate_design_system(layout, issues)
        self._validate_spacing(layout, issues)
        self._validate_typography(layout, issues)
        self._validate_color_contrast(layout, issues)
        
        # UX validation
        self._validate_touch_targets(layout, issues)
        self._validate_form_layout(layout, issues)
        self._validate_component_grouping(layout, issues)
        self._validate_navigation_elements(layout, issues)
        
        # Platform validation
        self._validate_safe_areas(layout, issues)
        
        # Determine if layout is valid
        critical_issues = [i for i in issues if i.level == "critical"]
        error_issues = [i for i in issues if i.level == "error"]
        is_valid = len(critical_issues) == 0 and len(error_issues) == 0
        
        # Update stats
        if is_valid:
            self.stats['passed'] += 1
        else:
            self.stats['failed'] += 1
        
        self.stats['warnings'] += len([i for i in issues if i.level == "warning"])
        self.stats['suggestions'] += len([i for i in issues if i.level in ["info", "suggestion"]])
        
        # Log results
        self._log_results(issues, is_valid)
        
        return is_valid, issues
    
    def _validate_canvas(self, layout: EnhancedLayoutDefinition, issues: List):
        """Validate canvas configuration"""
        canvas = layout.canvas
        
        # Check canvas dimensions
        if canvas['width'] != self.canvas_width:
            issues.append(LayoutValidationIssue(
                level="warning",
                component="canvas",
                message=f"Canvas width {canvas['width']} != standard {self.canvas_width}",
                suggestion=f"Use standard width of {self.canvas_width}px for consistency"
            ))
        
        if canvas['height'] != self.canvas_height:
            issues.append(LayoutValidationIssue(
                level="info",
                component="canvas",
                message=f"Canvas height {canvas['height']} != standard {self.canvas_height}",
                suggestion="Different height may cause scrolling issues"
            ))
        
        # Check background color
        if canvas.get('background_color', '#FFFFFF') not in ['#FFFFFF', '#F9F9FB']:
            issues.append(LayoutValidationIssue(
                level="info",
                component="canvas",
                message="Non-standard background color",
                suggestion="Consider using white or light gray for better contrast"
            ))
    
    def _validate_component_bounds(self, layout: EnhancedLayoutDefinition, issues: List):
        """Validate components are within canvas bounds"""
        safe_frame = layout.get_safe_area_frame()
        
        for component in layout.components:
            bounds = self._get_component_bounds(component)
            if not bounds:
                issues.append(LayoutValidationIssue(
                    level="error",
                    component=component.component_id,
                    message="Missing style property",
                    suggestion="Add style with position and dimensions"
                ))
                continue
            
            left, top, right, bottom = bounds
            
            # Check bounds
            if left < 0:
                issues.append(LayoutValidationIssue(
                    level="error",
                    component=component.component_id,
                    message=f"Component extends beyond left edge (x={left})",
                    suggestion=f"Move right by {abs(left)}px"
                ))
            
            if top < safe_frame['y']:
                issues.append(LayoutValidationIssue(
                    level="warning",
                    component=component.component_id,
                    message=f"Component in status bar area (y={top})",
                    suggestion=f"Move down to y ≥ {safe_frame['y']}"
                ))
            
            if right > self.canvas_width:
                issues.append(LayoutValidationIssue(
                    level="error",
                    component=component.component_id,
                    message=f"Component exceeds canvas width ({right} > {self.canvas_width})",
                    suggestion=f"Reduce width by {right - self.canvas_width}px"
                ))
            
            if bottom > self.canvas_height:
                issues.append(LayoutValidationIssue(
                    level="warning",
                    component=component.component_id,
                    message=f"Component exceeds canvas height",
                    suggestion="Ensure screen is scrollable"
                ))
    
    def _validate_collisions(self, layout: EnhancedLayoutDefinition, issues: List):
        """Detect component collisions"""
        components = layout.components
        
        for i, comp1 in enumerate(components):
            bounds1 = self._get_component_bounds(comp1)
            if not bounds1:
                continue
            
            for comp2 in components[i+1:]:
                bounds2 = self._get_component_bounds(comp2)
                if not bounds2:
                    continue
                
                if self._rectangles_overlap(bounds1, bounds2):
                    issues.append(LayoutValidationIssue(
                        level="error",
                        component=f"{comp1.component_id} & {comp2.component_id}",
                        message="Components overlap",
                        suggestion="Reposition or adjust sizes"
                    ))
    
    def _validate_unique_ids(self, layout: EnhancedLayoutDefinition, issues: List):
        """Ensure all component IDs are unique"""
        ids = [comp.component_id for comp in layout.components]
        duplicates = [id for id in ids if ids.count(id) > 1]
        
        if duplicates:
            issues.append(LayoutValidationIssue(
                level="error",
                component="ids",
                message=f"Duplicate component IDs: {set(duplicates)}",
                suggestion="Use unique IDs for all components"
            ))
    
    def _validate_design_system(self, layout: EnhancedLayoutDefinition, issues: List):
        """Validate design system consistency"""
        ds = layout.design_system
        
        # Check spacing multiples
        for section in getattr(layout, 'sections', []):
            if section.spacing % ds.spacing.unit != 0:
                issues.append(LayoutValidationIssue(
                    level="info",
                    component=f"section:{section.id}",
                    message=f"Spacing {section.spacing} not a multiple of base unit {ds.spacing.unit}",
                    suggestion=f"Use spacing in multiples of {ds.spacing.unit}px"
                ))
    
    def _validate_spacing(self, layout: EnhancedLayoutDefinition, issues: List):
        """Validate spacing between components"""
        ds = layout.design_system
        components_by_y = sorted(
            [(c, self._get_component_bounds(c)) for c in layout.components],
            key=lambda x: x[1][1] if x[1] else 0
        )
        
        for i, (comp1, bounds1) in enumerate(components_by_y[:-1]):
            comp2, bounds2 = components_by_y[i + 1]
            if not bounds1 or not bounds2:
                continue
            
            # Vertical spacing
            spacing = bounds2[1] - bounds1[3]
            
            if 0 < spacing < ds.spacing.sm:
                issues.append(LayoutValidationIssue(
                    level="info",
                    component=f"{comp1.component_id} & {comp2.component_id}",
                    message=f"Tight vertical spacing: {spacing}px",
                    suggestion=f"Increase to at least {ds.spacing.sm}px"
                ))
            elif spacing > ds.spacing.xxl:
                issues.append(LayoutValidationIssue(
                    level="info",
                    component=f"{comp1.component_id} & {comp2.component_id}",
                    message=f"Large vertical gap: {spacing}px",
                    suggestion="Consider if this spacing is intentional"
                ))
    
    def _validate_typography(self, layout: EnhancedLayoutDefinition, issues: List):
        """Validate typography usage"""
        ds = layout.design_system
        
        for component in layout.components:
            if component.component_type == 'Text_Content':
                # Check font size
                font_prop = component.properties.get('fontSize')
                if font_prop and font_prop.type == "literal":
                    size = font_prop.value
                    if size not in [ds.typography.h1, ds.typography.h2, ds.typography.h3,
                                   ds.typography.h4, ds.typography.body, ds.typography.body_small,
                                   ds.typography.caption, ds.typography.button]:
                        issues.append(LayoutValidationIssue(
                            level="info",
                            component=component.component_id,
                            message=f"Non-standard font size: {size}",
                            suggestion="Use design system typography scale"
                        ))
    
    def _validate_color_contrast(self, layout: EnhancedLayoutDefinition, issues: List):
        """Basic color contrast validation"""
        ds = layout.design_system
        
        for component in layout.components:
            if component.component_type in ['Text_Content', 'Button']:
                color_prop = component.properties.get('color')
                bg_prop = component.properties.get('backgroundColor')
                
                if color_prop and color_prop.type == "literal":
                    color = color_prop.value
                    if color == ds.colors.background:
                        issues.append(LayoutValidationIssue(
                            level="warning",
                            component=component.component_id,
                            message="Text color same as background",
                            suggestion="Ensure sufficient contrast"
                        ))
    
    def _validate_touch_targets(self, layout: EnhancedLayoutDefinition, issues: List):
        """Validate touch targets meet minimum size"""
        interactive_types = set(get_interactive_components())
        
        for component in layout.components:
            if component.component_type not in interactive_types:
                continue
            
            bounds = self._get_component_bounds(component)
            if not bounds:
                continue
            
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]
            
            if height < self.min_touch_size:
                issues.append(LayoutValidationIssue(
                    level="error",
                    component=component.component_id,
                    message=f"Touch target too short: {height}px < {self.min_touch_size}px",
                    suggestion=f"Increase height to at least {self.min_touch_size}px"
                ))
            
            if component.component_type == 'Button' and width < self.min_touch_size:
                issues.append(LayoutValidationIssue(
                    level="warning",
                    component=component.component_id,
                    message=f"Button too narrow: {width}px",
                    suggestion=f"Increase width to at least {self.min_touch_size}px"
                ))
    
    def _validate_form_layout(self, layout: EnhancedLayoutDefinition, issues: List):
        """Validate form layouts for good UX"""
        inputs = [c for c in layout.components if is_input_component(c.component_type)]
        
        if len(inputs) > 1:
            # Check spacing between inputs
            for i, input1 in enumerate(inputs[:-1]):
                input2 = inputs[i + 1]
                bounds1 = self._get_component_bounds(input1)
                bounds2 = self._get_component_bounds(input2)
                
                if not bounds1 or not bounds2:
                    continue
                
                spacing = bounds2[1] - bounds1[3]
                
                if spacing != self.ideal_form_spacing:
                    issues.append(LayoutValidationIssue(
                        level="info",
                        component="form",
                        message=f"Form field spacing {spacing}px",
                        suggestion=f"Use consistent {self.ideal_form_spacing}px spacing between form fields"
                    ))
        
        # Check if inputs have labels
        text_components = [c for c in layout.components if c.component_type == 'Text_Content']
        
        for input_comp in inputs:
            has_label = False
            input_bounds = self._get_component_bounds(input_comp)
            
            if not input_bounds:
                continue
            
            for text_comp in text_components:
                text_bounds = self._get_component_bounds(text_comp)
                if not text_bounds:
                    continue
                
                # Check if text is above and aligned with input
                if (text_bounds[3] <= input_bounds[1] and
                    abs(text_bounds[0] - input_bounds[0]) < 50):
                    has_label = True
                    break
            
            if not has_label:
                issues.append(LayoutValidationIssue(
                    level="info",
                    component=input_comp.component_id,
                    message="Input may be missing label",
                    suggestion="Add a Text component above as label"
                ))
    
    def _validate_component_grouping(self, layout: EnhancedLayoutDefinition, issues: List):
        """Validate logical grouping of components"""
        # Check if related components are grouped
        if hasattr(layout, 'sections') and layout.sections:
            return  # Already grouped by sections
        
        # Heuristic: buttons should be near inputs they control
        buttons = [c for c in layout.components if c.component_type == 'Button']
        inputs = [c for c in layout.components if is_input_component(c.component_type)]
        
        for button in buttons:
            button_bounds = self._get_component_bounds(button)
            if not button_bounds:
                continue
            
            # Find closest input
            min_distance = float('inf')
            for input_comp in inputs:
                input_bounds = self._get_component_bounds(input_comp)
                if not input_bounds:
                    continue
                
                distance = self._get_component_distance(button_bounds, input_bounds)
                min_distance = min(min_distance, distance)
            
            if min_distance > 200 and inputs:
                issues.append(LayoutValidationIssue(
                    level="info",
                    component=button.component_id,
                    message="Button far from related inputs",
                    suggestion="Group buttons near the inputs they control"
                ))
    
    def _validate_navigation_elements(self, layout: EnhancedLayoutDefinition, issues: List):
        """Validate navigation elements placement"""
        # Check if back button exists and is in top-left
        back_buttons = [c for c in layout.components 
                       if c.component_type == 'Button' and 
                       'back' in c.component_id.lower()]
        
        for btn in back_buttons:
            bounds = self._get_component_bounds(btn)
            if bounds and bounds[0] > 50:  # Not at left edge
                issues.append(LayoutValidationIssue(
                    level="info",
                    component=btn.component_id,
                    message="Back button not at left edge",
                    suggestion="Place back buttons in top-left corner (x ≈ 16)"
                ))
    
    def _validate_safe_areas(self, layout: EnhancedLayoutDefinition, issues: List):
        """Validate safe area compliance"""
        safe_frame = layout.get_safe_area_frame()
        
        for component in layout.components:
            bounds = self._get_component_bounds(component)
            if not bounds:
                continue
            
            # Check if component is within safe area
            if bounds[1] < safe_frame['y']:
                issues.append(LayoutValidationIssue(
                    level="info",
                    component=component.component_id,
                    message="Component in unsafe area (status bar region)",
                    suggestion="Respect safe area insets"
                ))
            
            if bounds[3] > safe_frame['y'] + safe_frame['height']:
                issues.append(LayoutValidationIssue(
                    level="info",
                    component=component.component_id,
                    message="Component in unsafe area (home indicator region)",
                    suggestion="Ensure scrollable content or respect safe area"
                ))
    
    def _get_component_bounds(self, component: EnhancedComponentDefinition) -> Optional[Tuple[int, int, int, int]]:
        """Get component bounding rectangle"""
        style_prop = component.properties.get('style')
        if not style_prop or style_prop.type != "literal":
            return None
        
        style = style_prop.value
        if not isinstance(style, dict):
            return None
        
        left = style.get('left', 0)
        top = style.get('top', 0)
        width = style.get('width', 0)
        height = style.get('height', 0)
        
        return (left, top, left + width, top + height)
    
    def _get_component_distance(
        self,
        bounds1: Tuple[int, int, int, int],
        bounds2: Tuple[int, int, int, int]
    ) -> float:
        """Calculate minimum distance between components"""
        l1_x, l1_y, r1_x, r1_y = bounds1
        l2_x, l2_y, r2_x, r2_y = bounds2
        
        # Calculate center points
        c1_x = (l1_x + r1_x) / 2
        c1_y = (l1_y + r1_y) / 2
        c2_x = (l2_x + r2_x) / 2
        c2_y = (l2_y + r2_y) / 2
        
        return math.sqrt((c2_x - c1_x)**2 + (c2_y - c1_y)**2)
    
    def _rectangles_overlap(
        self,
        rect1: Tuple[int, int, int, int],
        rect2: Tuple[int, int, int, int]
    ) -> bool:
        """Check if two rectangles overlap"""
        l1_x, l1_y, r1_x, r1_y = rect1
        l2_x, l2_y, r2_x, r2_y = rect2
        
        if r1_x <= l2_x or r2_x <= l1_x:
            return False
        if r1_y <= l2_y or r2_y <= l1_y:
            return False
        
        return True
    
    def _log_results(self, issues: List[LayoutValidationIssue], is_valid: bool):
        """Log validation results"""
        levels = {}
        for issue in issues:
            levels[issue.level] = levels.get(issue.level, 0) + 1
        
        if is_valid:
            logger.info(
                "✅ Layout validation passed",
                extra={
                    "issues": levels,
                    "total": len(issues)
                }
            )
        else:
            logger.warning(
                "⚠️ Layout validation failed",
                extra={
                    "issues": levels,
                    "total": len(issues)
                }
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get validation statistics"""
        total = self.stats['total_validations']
        return {
            **self.stats,
            'pass_rate': (self.stats['passed'] / total * 100) if total > 0 else 0,
            'avg_issues': (self.stats['warnings'] + self.stats['suggestions']) / total if total > 0 else 0
        }


# Global instance
layout_validator = LayoutValidator()