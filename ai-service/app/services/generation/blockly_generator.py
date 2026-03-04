"""
Enhanced Blockly Generator with full event support and real-world logic.
Generates complete visual programming blocks for app functionality.
"""
import json
import asyncio
import uuid
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import re

from app.config import settings
from app.models.schemas.architecture import ArchitectureDesign, ScreenDefinition
from app.models.schemas.layout import EnhancedLayoutDefinition
from app.models.schemas.blockly import (
    EnhancedBlocklyDefinition, BlockDefinition, BlocklyWorkspace,
    BlocklyVariable, CustomBlockDefinition, BlockTypes
)
from app.models.schemas.component_catalog import (
    get_component_event, is_input_component, has_component_event,
    get_component_states
)
from app.models.prompts import prompts
from app.services.generation.blockly_validator import blockly_validator
from app.llm.orchestrator import LLMOrchestrator
from app.llm.base import LLMMessage
from app.utils.logging import get_logger

logger = get_logger(__name__)


class BlocklyGenerationError(Exception):
    """Base exception for Blockly generation errors"""
    pass


class BlocklyGenerator:
    """
    Enhanced Blockly generator that creates complete app logic with:
    
    - Event handlers for all interactive components
    - State management (get/set variables)
    - Navigation between screens
    - Form validation and submission
    - Data fetching and processing
    - Hardware control (joystick, sensors)
    - Notifications and alerts
    - File operations
    - Maps and location
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
        
        # Retry configuration
        self.max_retries = 3
        self.retry_delay = 2
        
        # Statistics
        self.stats = {
            'total_requests': 0,
            'successful': 0,
            'failed': 0,
            'heuristic_fallbacks': 0,
            'llama3_successes': 0
        }
        
        logger.info(
            "🧩 Blockly generator initialized",
            extra={
                "llm_provider": "llama3",
                "heuristic_fallback_enabled": True
            }
        )
    
    async def generate(
        self,
        architecture: ArchitectureDesign,
        layouts: Dict[str, EnhancedLayoutDefinition]
    ) -> EnhancedBlocklyDefinition:
        """
        Generate complete Blockly logic for the app.
        
        Args:
            architecture: Complete architecture design
            layouts: Map of screen_id -> layout
            
        Returns:
            EnhancedBlocklyDefinition with full app logic
        """
        self.stats['total_requests'] += 1
        
        logger.info(
            "🧩 Blockly generation started",
            extra={
                "screens": len(architecture.screens) if architecture and hasattr(architecture, 'screens') else 0,
                "layouts": len(layouts) if layouts else 0
            }
        )
        
        # Validate inputs
        if not architecture:
            logger.error("Architecture missing")
            return self._create_minimal_blockly(architecture, layouts, "No architecture provided")
        
        try:
            # Try LLM generation first
            blockly = await self._generate_with_llm(architecture, layouts)
            
            if blockly and blockly.blocks.blocks:
                self.stats['llama3_successes'] += 1
                logger.info(
                    "✅ LLM Blockly generation successful",
                    extra={
                        "blocks": len(blockly.blocks.blocks),
                        "variables": len(blockly.variables)
                    }
                )
            else:
                raise BlocklyGenerationError("LLM generated empty blocks")
            
        except Exception as e:
            logger.warning(f"LLM Blockly generation failed: {e}, using heuristic")
            self.stats['heuristic_fallbacks'] += 1
            
            # Fallback to heuristic generation
            blockly = await self._generate_heuristic_blockly(architecture, layouts)
        
        # Validate
        is_valid, issues = await blockly_validator.validate(blockly.model_dump())
        
        if not is_valid:
            logger.warning(
                "Blockly validation found issues",
                extra={"issue_count": len(issues)}
            )
            blockly.metadata['validation_issues'] = [i.to_dict() for i in issues[:5]]
        else:
            logger.info("✅ Blockly validation passed")
        
        # Add metadata
        blockly.metadata.update({
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'blocks_count': len(blockly.blocks.blocks),
            'variables_count': len(blockly.variables),
            'validation_passed': is_valid
        })
        
        self.stats['successful'] += 1
        
        return blockly
    
    async def _generate_with_llm(
        self,
        architecture: ArchitectureDesign,
        layouts: Dict[str, EnhancedLayoutDefinition]
    ) -> EnhancedBlocklyDefinition:
        """Generate Blockly using LLM"""
        
        # Extract component events
        component_events = self._extract_component_events(layouts)
        
        # Extract screens
        screens = [
            {
                'id': screen.id,
                'name': screen.name,
                'components': [
                    {
                        'id': comp.id if hasattr(comp, 'id') else f"comp_{idx}",
                        'type': comp.component_type if hasattr(comp, 'component_type') else 'unknown'
                    }
                    for idx, comp in enumerate(getattr(screen, 'components', []))
                ]
            }
            for screen in architecture.screens
        ]
        
        # Extract state variables
        state_vars = []
        if hasattr(architecture, 'state_management') and architecture.state_management:
            for state in architecture.state_management:
                state_vars.append({
                    'name': state.name,
                    'type': getattr(state, 'type', 'local-state'),
                    'initial': getattr(state, 'initial_value', None)
                })
        
        # Build prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            architecture, screens, component_events, state_vars
        )
        
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt)
        ]
        
        # Call LLM
        response = await self.orchestrator.generate(
            messages=messages,
            temperature=0.7,
            max_tokens=8192  # More tokens for complex logic
        )
        
        # Parse response
        blockly_data = await self._parse_blockly_response(response.content)
        
        # Convert to EnhancedBlocklyDefinition
        blockly = self._create_blockly_from_data(blockly_data, architecture, layouts)
        
        return blockly
    
    def _build_system_prompt(self) -> str:
        """Build comprehensive system prompt for Blockly generation"""
        return """You are an expert visual programming architect creating Blockly logic for mobile apps.

BLOCK TYPES REFERENCE:

EVENT BLOCKS:
- component_event: Triggers when user interacts with component
  Fields: COMPONENT (component_id), EVENT (onPress, onChange, etc.)
- screen_load: Triggers when screen loads
  Fields: SCREEN (screen_id)

STATE BLOCKS:
- state_get: Gets current value of a variable
  Fields: VAR (variable name)
- state_set: Sets variable to new value
  Fields: VAR (variable name)
  Inputs: VALUE (block that provides the value)
- state_toggle: Toggles boolean variable
  Fields: VAR (variable name)

NAVIGATION BLOCKS:
- navigate_to: Navigate to another screen
  Fields: SCREEN (target screen_id)
- navigate_back: Go back to previous screen

LOGIC BLOCKS:
- controls_if: If-then-else conditional
  Inputs: IF0 (condition), DO0 (then block), ELSE (else block)
- logic_compare: Compare two values
  Fields: OP (EQ, NEQ, LT, LTE, GT, GTE)
  Inputs: A, B
- logic_operation: AND/OR operations
  Fields: OP (AND, OR)
  Inputs: A, B
- logic_boolean: True/False value
  Fields: BOOL (TRUE, FALSE)

MATH BLOCKS:
- math_number: Number value
  Fields: NUM (number)
- math_arithmetic: Basic arithmetic
  Fields: OP (ADD, MINUS, MULTIPLY, DIVIDE, POWER)
  Inputs: A, B

TEXT BLOCKS:
- text: String literal
  Fields: TEXT (string)
- text_join: Join strings together
  Inputs: elements (multiple text inputs)

HARDWARE BLOCKS:
- joystick_read: Read joystick position
  Outputs: x, y, angle, distance
- send_command: Send command to hardware
  Fields: DEVICE, COMMAND, VALUE

NOTIFICATION BLOCKS:
- show_toast: Show temporary message
  Fields: TITLE, DESCRIPTION, DURATION
- send_notification: Send push notification
  Fields: TITLE, BODY

FILE BLOCKS:
- pick_file: Open file picker
  Fields: TYPE (image, document, any)
- read_file: Read file contents
  Fields: FILE (file reference)

MAP BLOCKS:
- map_add_marker: Add marker to map
  Fields: LATITUDE, LONGITUDE, TITLE
- map_get_location: Get current location
  Outputs: latitude, longitude

OUTPUT FORMAT - STRICT JSON:
{
  "blocks": [
    {
      "id": "event_1",
      "type": "component_event",
      "x": 20,
      "y": 20,
      "fields": {
        "COMPONENT": "btn_submit",
        "EVENT": "onPress"
      },
      "next": {
        "id": "state_set_1",
        "type": "state_set",
        "fields": {"VAR": "isLoading"},
        "inputs": {
          "VALUE": {
            "block": {
              "type": "logic_boolean",
              "fields": {"BOOL": "TRUE"}
            }
          }
        },
        "next": {
          "id": "navigate_1",
          "type": "navigate_to",
          "fields": {"SCREEN": "home_screen"}
        }
      }
    }
  ],
  "variables": [
    {"name": "count", "type": "Number", "id": "var_1"},
    {"name": "isLoading", "type": "Boolean", "id": "var_2"}
  ]
}

RULES:
1. Every interactive component should have an event handler
2. Form submissions should include validation and state updates
3. Navigation should be included where appropriate
4. Variables must be declared in variables list
5. Use proper block connections via "next" field
6. Return ONLY valid JSON, no explanations
"""
    
    def _build_user_prompt(
        self,
        architecture: ArchitectureDesign,
        screens: List[Dict],
        component_events: List[Dict],
        state_vars: List[Dict]
    ) -> str:
        """Build user prompt with app context"""
        
        return f"""
APP ARCHITECTURE:
App Name: {architecture.app_name}
App Type: {architecture.app_type}
Domain: {getattr(architecture, 'domain', 'unknown')}

SCREENS:
{json.dumps(screens, indent=2)}

INTERACTIVE COMPONENTS (need event handlers):
{json.dumps(component_events, indent=2)}

STATE VARIABLES (available for use):
{json.dumps(state_vars, indent=2)}

TASK:
Generate complete Blockly logic for this app including:
1. Event handlers for all interactive components
2. State updates when values change
3. Navigation between screens
4. Form validation and submission logic
5. Any hardware control logic needed
6. Notifications for important actions

Create a cohesive program that makes the app functional and intuitive.
"""
    
    async def _parse_blockly_response(self, content: str) -> Dict[str, Any]:
        """Parse and clean Blockly JSON response"""
        
        # Clean response
        content = content.strip()
        
        # Remove markdown code blocks
        if '```json' in content:
            content = content.split('```json')[1].split('```')[0].strip()
        elif '```' in content:
            content = content.split('```')[1].split('```')[0].strip()
        
        # Extract JSON object
        json_match = re.search(r'\{.*\}', content, re.DOTALL)
        if json_match:
            content = json_match.group()
        
        # Fix common JSON issues
        content = re.sub(r',\s*}', '}', content)  # Remove trailing commas
        content = re.sub(r',\s*]', ']', content)
        content = re.sub(r'(\w+):', r'"\1":', content)  # Quote keys
        
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Blockly JSON: {e}")
            # Return minimal structure
            data = {"blocks": [], "variables": []}
        
        # Ensure required fields
        if 'blocks' not in data:
            data['blocks'] = []
        if 'variables' not in data:
            data['variables'] = []
        
        return data
    
    def _create_blockly_from_data(
        self,
        data: Dict[str, Any],
        architecture: ArchitectureDesign,
        layouts: Dict[str, EnhancedLayoutDefinition]
    ) -> EnhancedBlocklyDefinition:
        """Create EnhancedBlocklyDefinition from parsed data"""
        
        blocks = []
        variables = []
        
        # Create blocks
        for block_data in data.get('blocks', []):
            try:
                # Ensure block has required fields
                if 'id' not in block_data:
                    block_data['id'] = f"block_{len(blocks)}"
                if 'type' not in block_data:
                    block_data['type'] = 'unknown'
                if 'x' not in block_data:
                    block_data['x'] = 20 + (len(blocks) * 10)
                if 'y' not in block_data:
                    block_data['y'] = 20 + (len(blocks) * 50)
                
                block = BlockDefinition(**block_data)
                blocks.append(block)
            except Exception as e:
                logger.warning(f"Failed to create block: {e}")
        
        # Create variables
        for var_data in data.get('variables', []):
            try:
                if 'id' not in var_data:
                    var_data['id'] = f"var_{len(variables)}"
                if 'type' not in var_data:
                    var_data['type'] = 'String'
                
                var = BlocklyVariable(**var_data)
                variables.append(var)
            except Exception as e:
                logger.warning(f"Failed to create variable: {e}")
        
        # If no blocks were created, use heuristic
        if not blocks:
            logger.warning("No blocks from LLM, using heuristic")
            return self._generate_heuristic_blockly(architecture, layouts)
        
        return EnhancedBlocklyDefinition(
            blocks=BlocklyWorkspace(blocks=blocks),
            variables=variables,
            custom_blocks=[],
            metadata={'generation_method': 'llm'}
        )
    
    async def _generate_heuristic_blockly(
        self,
        architecture: ArchitectureDesign,
        layouts: Dict[str, EnhancedLayoutDefinition]
    ) -> EnhancedBlocklyDefinition:
        """Generate Blockly using heuristic templates"""
        
        logger.info("🛡️ Using heuristic Blockly generation")
        
        blocks = []
        variables = []
        var_counter = 1
        
        # Extract component events
        component_events = self._extract_component_events(layouts)
        
        # Create state variables from architecture
        if hasattr(architecture, 'state_management') and architecture.state_management:
            for idx, state in enumerate(architecture.state_management):
                var_type = 'String'
                if 'count' in state.name.lower() or 'number' in state.name.lower():
                    var_type = 'Number'
                elif 'bool' in state.name.lower() or 'loading' in state.name.lower() or 'visible' in state.name.lower():
                    var_type = 'Boolean'
                elif 'list' in state.name.lower() or 'array' in state.name.lower():
                    var_type = 'Array'
                
                variables.append(BlocklyVariable(
                    name=state.name,
                    id=f"var_{var_counter}",
                    type=var_type
                ))
                var_counter += 1
        
        # Add default variables if none
        if not variables:
            variables = [
                BlocklyVariable(name='count', id='var_1', type='Number'),
                BlocklyVariable(name='isLoading', id='var_2', type='Boolean'),
                BlocklyVariable(name='userInput', id='var_3', type='String')
            ]
            var_counter = 4
        
        # Create event handlers for each interactive component
        y_position = 20
        for idx, event_info in enumerate(component_events):
            component_id = event_info['component_id']
            event_name = event_info['event']
            screen_id = event_info['screen_id']
            component_type = event_info.get('component_type', 'unknown')
            
            # Create event block
            event_id = f"event_{idx + 1}"
            event_block = BlockDefinition(
                id=event_id,
                type='component_event',
                x=20,
                y=y_position,
                fields={
                    'COMPONENT': component_id,
                    'EVENT': event_name,
                    'SCREEN': screen_id
                }
            )
            
            current_block = event_block
            y_position += 100
            
            # Add logic based on component type
            if component_type == 'Button':
                # Buttons usually perform actions
                if 'submit' in component_id.lower() or 'save' in component_id.lower():
                    # Submit button - set loading state
                    loading_block = self._create_state_set_block(
                        var_name='isLoading',
                        value_block={
                            'type': 'logic_boolean',
                            'fields': {'BOOL': 'TRUE'}
                        },
                        block_id=f"set_loading_{idx + 1}"
                    )
                    current_block.next = loading_block.model_dump()
                    current_block = loading_block
                    
                    # Then navigate or show toast
                    if len(architecture.screens) > 1:
                        # Navigate to first screen
                        nav_block = self._create_navigation_block(
                            screen_id=architecture.screens[0].id,
                            block_id=f"nav_{idx + 1}"
                        )
                        current_block.next = nav_block.model_dump()
                        current_block = nav_block
                    else:
                        # Show success toast
                        toast_block = self._create_toast_block(
                            title="Success",
                            description="Action completed",
                            block_id=f"toast_{idx + 1}"
                        )
                        current_block.next = toast_block.model_dump()
                        current_block = toast_block
                
                elif 'increment' in component_id.lower():
                    # Increment button
                    # Get current count
                    get_block = self._create_state_get_block(
                        var_name='count',
                        block_id=f"get_{idx + 1}"
                    )
                    
                    # Add 1
                    add_block = self._create_math_block(
                        operation='ADD',
                        a_block=get_block.model_dump(),
                        b_value=1,
                        block_id=f"math_{idx + 1}"
                    )
                    
                    # Set new count
                    set_block = self._create_state_set_block(
                        var_name='count',
                        value_block=add_block.model_dump(),
                        block_id=f"set_{idx + 1}"
                    )
                    
                    current_block.next = set_block.model_dump()
                    current_block = set_block
                
                elif 'decrement' in component_id.lower():
                    # Decrement button
                    get_block = self._create_state_get_block(
                        var_name='count',
                        block_id=f"get_{idx + 1}"
                    )
                    
                    subtract_block = self._create_math_block(
                        operation='MINUS',
                        a_block=get_block.model_dump(),
                        b_value=1,
                        block_id=f"math_{idx + 1}"
                    )
                    
                    set_block = self._create_state_set_block(
                        var_name='count',
                        value_block=subtract_block.model_dump(),
                        block_id=f"set_{idx + 1}"
                    )
                    
                    current_block.next = set_block.model_dump()
                    current_block = set_block
                
                elif 'delete' in component_id.lower():
                    # Delete button - show confirmation
                    confirm_block = self._create_if_block(
                        condition_block={
                            'type': 'logic_boolean',
                            'fields': {'BOOL': 'TRUE'}  # Would need actual confirmation dialog
                        },
                        then_block=self._create_toast_block(
                            title="Deleted",
                            description="Item removed",
                            block_id=f"toast_{idx + 1}"
                        ).model_dump(),
                        block_id=f"if_{idx + 1}"
                    )
                    current_block.next = confirm_block.model_dump()
                    current_block = confirm_block
            
            elif component_type == 'Input_Text' and event_name == 'onChangeText':
                # Text input - update state
                set_block = self._create_state_set_block(
                    var_name=component_id.replace('input_', '') + 'Value',
                    value_block={
                        'type': 'text',
                        'fields': {'TEXT': ''}  # Will be replaced with input value
                    },
                    block_id=f"set_{idx + 1}"
                )
                current_block.next = set_block.model_dump()
                current_block = set_block
            
            elif component_type == 'Checkbox' and event_name == 'onCheckedChange':
                # Checkbox - toggle state
                var_name = component_id.replace('chk_', '') + 'Checked'
                set_block = self._create_state_set_block(
                    var_name=var_name,
                    value_block={
                        'type': 'logic_boolean',
                        'fields': {'BOOL': 'FALSE'}  # Will be replaced with checkbox value
                    },
                    block_id=f"set_{idx + 1}"
                )
                current_block.next = set_block.model_dump()
                current_block = set_block
            
            elif component_type == 'Switch' and event_name == 'onValueChange':
                # Switch - toggle state
                var_name = component_id.replace('switch_', '') + 'Enabled'
                set_block = self._create_state_set_block(
                    var_name=var_name,
                    value_block={
                        'type': 'logic_boolean',
                        'fields': {'BOOL': 'FALSE'}  # Will be replaced with switch value
                    },
                    block_id=f"set_{idx + 1}"
                )
                current_block.next = set_block.model_dump()
                current_block = set_block
            
            elif component_type == 'Slider' and event_name == 'onValueChange':
                # Slider - update state
                var_name = component_id.replace('slider_', '') + 'Value'
                set_block = self._create_state_set_block(
                    var_name=var_name,
                    value_block={
                        'type': 'math_number',
                        'fields': {'NUM': 0}  # Will be replaced with slider value
                    },
                    block_id=f"set_{idx + 1}"
                )
                current_block.next = set_block.model_dump()
                current_block = set_block
            
            elif component_type == 'Joystick' and event_name == 'onMove':
                # Joystick - update position state
                set_x = self._create_state_set_block(
                    var_name=f"{component_id}_x",
                    value_block={
                        'type': 'math_number',
                        'fields': {'NUM': 0}  # Will be replaced
                    },
                    block_id=f"set_x_{idx + 1}"
                )
                current_block.next = set_x.model_dump()
                current_block = set_x
                
                set_y = self._create_state_set_block(
                    var_name=f"{component_id}_y",
                    value_block={
                        'type': 'math_number',
                        'fields': {'NUM': 0}
                    },
                    block_id=f"set_y_{idx + 1}"
                )
                current_block.next = set_y.model_dump()
                current_block = set_y
                
                set_angle = self._create_state_set_block(
                    var_name=f"{component_id}_angle",
                    value_block={
                        'type': 'math_number',
                        'fields': {'NUM': 0}
                    },
                    block_id=f"set_angle_{idx + 1}"
                )
                current_block.next = set_angle.model_dump()
                current_block = set_angle
            
            elif component_type == 'FilePickerInput' and event_name == 'onPickFile':
                # File picker - update file state
                set_file = self._create_state_set_block(
                    var_name=f"{component_id}_file",
                    value_block={
                        'type': 'text',
                        'fields': {'TEXT': ''}  # Will be replaced with file path
                    },
                    block_id=f"set_file_{idx + 1}"
                )
                current_block.next = set_file.model_dump()
                current_block = set_file
            
            elif component_type == 'DatePicker' and event_name == 'onDateChange':
                # Date picker - update date state
                set_date = self._create_state_set_block(
                    var_name=f"{component_id}_date",
                    value_block={
                        'type': 'text',
                        'fields': {'TEXT': ''}  # Will be replaced with date string
                    },
                    block_id=f"set_date_{idx + 1}"
                )
                current_block.next = set_date.model_dump()
                current_block = set_date
            
            elif component_type == 'TimePicker' and event_name == 'onTimeChange':
                # Time picker - update time state
                set_time = self._create_state_set_block(
                    var_name=f"{component_id}_time",
                    value_block={
                        'type': 'text',
                        'fields': {'TEXT': ''}  # Will be replaced with time string
                    },
                    block_id=f"set_time_{idx + 1}"
                )
                current_block.next = set_time.model_dump()
                current_block = set_time
            
            elif component_type == 'ColorPicker' and event_name == 'onColorChange':
                # Color picker - update color state
                set_color = self._create_state_set_block(
                    var_name=f"{component_id}_color",
                    value_block={
                        'type': 'text',
                        'fields': {'TEXT': '#000000'}  # Default black
                    },
                    block_id=f"set_color_{idx + 1}"
                )
                current_block.next = set_color.model_dump()
                current_block = set_color
            
            elif component_type == 'GoogleMap' and event_name == 'onMapPress':
                # Map press - add marker or update location
                set_lat = self._create_state_set_block(
                    var_name='selected_latitude',
                    value_block={
                        'type': 'math_number',
                        'fields': {'NUM': 0}  # Will be replaced
                    },
                    block_id=f"set_lat_{idx + 1}"
                )
                current_block.next = set_lat.model_dump()
                current_block = set_lat
                
                set_lng = self._create_state_set_block(
                    var_name='selected_longitude',
                    value_block={
                        'type': 'math_number',
                        'fields': {'NUM': 0}
                    },
                    block_id=f"set_lng_{idx + 1}"
                )
                current_block.next = set_lng.model_dump()
                current_block = set_lng
            
            elif component_type == 'GoogleMap' and event_name == 'onMarkerPress':
                # Marker press - show details
                toast_block = self._create_toast_block(
                    title="Location",
                    description="Marker selected",
                    block_id=f"toast_{idx + 1}"
                )
                current_block.next = toast_block.model_dump()
                current_block = toast_block
            
            blocks.append(event_block)
        
        # Add screen load events for each screen
        if hasattr(architecture, 'screens') and architecture.screens:
            for idx, screen in enumerate(architecture.screens):
                load_id = f"load_{idx + 1}"
                load_block = BlockDefinition(
                    id=load_id,
                    type='screen_load',
                    x=20,
                    y=y_position + (idx * 100),
                    fields={'SCREEN': screen.id}
                )
                
                # Initialize screen-specific state
                current_block = load_block
                
                # Find components on this screen
                screen_components = []
                for screen_id, layout in layouts.items():
                    if screen_id == screen.id and hasattr(layout, 'components'):
                        for comp in layout.components:
                            if hasattr(comp, 'component_id'):
                                screen_components.append(comp)
                
                # Set initial states for inputs
                for comp in screen_components:
                    if hasattr(comp, 'component_type') and is_input_component(comp.component_type):
                        var_name = comp.component_id.replace('input_', '') + 'Value'
                        set_block = self._create_state_set_block(
                            var_name=var_name,
                            value_block={
                                'type': 'text',
                                'fields': {'TEXT': ''}
                            },
                            block_id=f"init_{screen.id}_{comp.component_id}"
                        )
                        current_block.next = set_block.model_dump()
                        current_block = set_block
                
                blocks.append(load_block)
        
        return EnhancedBlocklyDefinition(
            blocks=BlocklyWorkspace(blocks=blocks),
            variables=variables,
            custom_blocks=[],
            metadata={'generation_method': 'heuristic'}
        )
    
    def _create_state_get_block(self, var_name: str, block_id: str) -> BlockDefinition:
        """Create a state getter block"""
        return BlockDefinition(
            id=block_id,
            type='state_get',
            x=0, y=0,  # Position will be set by parent
            fields={'VAR': var_name}
        )
    
    def _create_state_set_block(
        self,
        var_name: str,
        value_block: Dict[str, Any],
        block_id: str
    ) -> BlockDefinition:
        """Create a state setter block"""
        return BlockDefinition(
            id=block_id,
            type='state_set',
            x=0, y=0,
            fields={'VAR': var_name},
            inputs={
                'VALUE': {
                    'block': value_block
                }
            }
        )
    
    def _create_math_block(
        self,
        operation: str,
        a_block: Dict[str, Any],
        b_value: Any,
        block_id: str
    ) -> BlockDefinition:
        """Create a math arithmetic block"""
        b_block = {
            'type': 'math_number',
            'fields': {'NUM': b_value}
        }
        
        return BlockDefinition(
            id=block_id,
            type='math_arithmetic',
            x=0, y=0,
            fields={'OP': operation},
            inputs={
                'A': {'block': a_block},
                'B': {'block': b_block}
            }
        )
    
    def _create_if_block(
        self,
        condition_block: Dict[str, Any],
        then_block: Dict[str, Any],
        block_id: str
    ) -> BlockDefinition:
        """Create an if-then block"""
        return BlockDefinition(
            id=block_id,
            type='controls_if',
            x=0, y=0,
            inputs={
                'IF0': {'block': condition_block},
                'DO0': {'block': then_block}
            }
        )
    
    def _create_toast_block(
        self,
        title: str,
        description: str,
        block_id: str
    ) -> BlockDefinition:
        """Create a toast notification block"""
        return BlockDefinition(
            id=block_id,
            type='show_toast',
            x=0, y=0,
            fields={
                'TITLE': title,
                'DESCRIPTION': description,
                'DURATION': 3000
            }
        )
    
    def _create_navigation_block(self, screen_id: str, block_id: str) -> BlockDefinition:
        """Create a navigation block"""
        return BlockDefinition(
            id=block_id,
            type='navigate_to',
            x=0, y=0,
            fields={'SCREEN': screen_id}
        )
    
    def _extract_component_events(
        self,
        layouts: Dict[str, EnhancedLayoutDefinition]
    ) -> List[Dict[str, str]]:
        """Extract all interactive components and their events"""
        events = []
        
        if not layouts:
            return events
        
        for screen_id, layout in layouts.items():
            if not hasattr(layout, 'components'):
                continue
            
            for component in layout.components:
                if not hasattr(component, 'component_type'):
                    continue
                
                # Get component type
                comp_type = component.component_type
                
                # Get event for this component type
                event_name = get_component_event(comp_type)
                
                # Skip if no event
                if not event_name:
                    continue
                
                # Get component ID
                comp_id = getattr(component, 'component_id', f"comp_{len(events)}")
                
                events.append({
                    'screen_id': screen_id,
                    'component_id': comp_id,
                    'component_type': comp_type,
                    'event': event_name
                })
        
        return events
    
    def _create_minimal_blockly(
        self,
        architecture: ArchitectureDesign,
        layouts: Dict[str, EnhancedLayoutDefinition],
        reason: str = ""
    ) -> EnhancedBlocklyDefinition:
        """Create minimal Blockly structure when all else fails"""
        
        blocks = []
        
        # Add a simple start block
        blocks.append(BlockDefinition(
            id='start_1',
            type='app_start',
            x=20,
            y=20,
            fields={'APP_NAME': getattr(architecture, 'app_name', 'App')}
        ))
        
        # Add navigation if multiple screens
        if hasattr(architecture, 'screens') and len(architecture.screens) > 1:
            blocks.append(BlockDefinition(
                id='nav_1',
                type='navigate_to',
                x=20,
                y=120,
                fields={'SCREEN': architecture.screens[0].id}
            ))
        
        return EnhancedBlocklyDefinition(
            blocks=BlocklyWorkspace(blocks=blocks),
            variables=[
                BlocklyVariable(name='app_state', id='var_1', type='String')
            ],
            custom_blocks=[],
            metadata={
                'generation_method': 'minimal_fallback',
                'fallback_reason': reason
            }
        )
    
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
blockly_generator = BlocklyGenerator()