"""
Prompt templates for Llama-based APIs.

ALL prompts in this file enforce STRICT VALID JSON OUTPUT.
NO markdown. NO explanations. NO code blocks.
"""

from typing import Any, Tuple
from dataclasses import dataclass
from enum import Enum

from app.models.schemas.component_catalog import get_available_components


@dataclass
class PromptTemplate:
    """
    Reusable prompt template with system and user components.
    """
    system: str
    user_template: str

    def format(self, **kwargs: Any) -> Tuple[str, str]:
        return self.system, self.user_template.format(**kwargs)


class PromptVersion(str, Enum):
    V1 = "v1"
    V2 = "v2"


class PromptType(str, Enum):
    APP_GENERATION = "app_generation"
    ARCHITECTURE_EXTEND = "architecture_extend"
    LAYOUT_GENERATION = "layout_generation"
    BLOCKLY_GENERATION = "blockly_generation"
    CODE_GENERATION = "code_generation"
    INTENT_ANALYSIS = "intent_analysis"
    OPTIMIZATION = "optimization"


# ======================================================================
# SHARED STRICT JSON RULES - MOVED OUTSIDE CLASS TO MODULE LEVEL
# ======================================================================

STRICT_JSON_RULES = """
CRITICAL OUTPUT RULES (MANDATORY):
1. Output MUST be a SINGLE valid JSON value
2. NO markdown, NO comments, NO explanations
3. NO text before or after JSON
4. Use DOUBLE QUOTES for all strings
5. Output MUST parse using json.loads() in Python
6. If unsure, still return valid JSON
"""


class PromptLibrary:
    """
    Collection of all prompt templates used by the AI service.
    ALL outputs MUST be strict JSON.
    """
    
    AVAILABLE_COMPONENTS = get_available_components()

    # ======================================================================
    # ARCHITECTURE DESIGN
    # ======================================================================

    ARCHITECTURE_DESIGN = PromptTemplate(
        system=f"""
You are an expert mobile app architect.

Your task is to generate a COMPLETE mobile app architecture.

{STRICT_JSON_RULES}

Allowed UI components:
{{components}}

Output schema (MUST MATCH EXACTLY):

{{
  "app_type": "single-page" | "multi-page" | "navigation-based",
  "screens": [
    {{
      "id": "string",
      "name": "string",
      "purpose": "string",
      "components": ["ComponentName"],
      "navigation": ["screen_id"]
    }}
  ],
  "navigation": {{
    "type": "stack" | "tab" | "drawer" | "none",
    "routes": [
      {{ "from": "screen_id", "to": "screen_id", "label": "string" }}
    ]
  }},
  "state_management": [
    {{
      "name": "string",
      "type": "local-state" | "global-state" | "async-state",
      "scope": "component" | "screen" | "global",
      "initial_value": {{}}
    }}
  ],
  "data_flow": {{
    "user_interactions": ["string"],
    "api_calls": ["string"],
    "local_storage": ["string"]
  }}
}}

Rules:
- ONLY use allowed components
- Screens must be minimal and focused
- Screen IDs must use only letters, numbers, and underscores
- Example screen IDs: home_screen, create_note_screen
""",
        user_template="""
User request:
"{prompt}"

Context:
{context_section}
"""
    )

    # ======================================================================
    # LAYOUT GENERATION
    # ======================================================================

    LAYOUT_GENERATE = PromptTemplate(
        system=f"""
You are an expert mobile UI/UX designer creating beautiful, modern app layouts.

{STRICT_JSON_RULES}

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
          "text": "Screen Title",
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
          "label": "Email"
        }},
        {{
          "component_type": "Input_Text",
          "purpose": "Password input",
          "placeholder": "Enter your password",
          "label": "Password",
          "secureTextEntry": true
        }},
        {{
          "component_type": "Button",
          "purpose": "Submit form",
          "text": "Sign In",
          "variant": "primary"
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
""",
        user_template="""
SCREEN TO DESIGN:
ID: {{screen_id}}
Name: {{screen_name}}
Purpose: {{screen_purpose}}

REQUIRED COMPONENTS:
{{required_components}}

APP CONTEXT:
App Name: {{app_name}}
App Type: {{app_type}}
Domain: {{domain}}

SUGGESTED LAYOUT PATTERN: {{suggested_pattern}}

Design a beautiful, modern layout for this screen that:
1. Follows the design system guidelines
2. Uses appropriate spacing (8px grid)
3. Groups related components logically
4. Creates clear visual hierarchy
5. Ensures good touch targets (min 44px)
6. Follows platform conventions

Return ONLY the JSON layout specification.
"""
    )

    # ======================================================================
    # BLOCKLY GENERATION (STRICT JSON AST)
    # ======================================================================

    BLOCKLY_GENERATE = PromptTemplate(
        system=f"""
You are an expert visual programming architect creating Blockly logic for mobile apps.

{STRICT_JSON_RULES}

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
{{
  "blocks": [
    {{
      "id": "event_1",
      "type": "component_event",
      "x": 20,
      "y": 20,
      "fields": {{
        "COMPONENT": "btn_submit",
        "EVENT": "onPress"
      }},
      "next": {{
        "id": "state_set_1",
        "type": "state_set",
        "fields": {{"VAR": "isLoading"}},
        "inputs": {{
          "VALUE": {{
            "block": {{
              "type": "logic_boolean",
              "fields": {{"BOOL": "TRUE"}}
            }}
          }}
        }},
        "next": {{
          "id": "navigate_1",
          "type": "navigate_to",
          "fields": {{"SCREEN": "home_screen"}}
        }}
      }}
    }}
  ],
  "variables": [
    {{"name": "count", "type": "Number", "id": "var_1"}},
    {{"name": "isLoading", "type": "Boolean", "id": "var_2"}}
  ]
}}

RULES:
1. Every interactive component should have an event handler
2. Form submissions should include validation and state updates
3. Navigation should be included where appropriate
4. Variables must be declared in variables list
5. Use proper block connections via "next" field
6. Return ONLY valid JSON, no explanations
""",
        user_template="""
APP ARCHITECTURE:
App Name: {{app_name}}
App Type: {{app_type}}
Domain: {{domain}}

SCREENS:
{{screens}}

INTERACTIVE COMPONENTS (need event handlers):
{{component_events}}

STATE VARIABLES (available for use):
{{state_vars}}

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
    )

    # ======================================================================
    # CODE GENERATION (JSON CODE MODEL, NOT SOURCE CODE)
    # ======================================================================

    CODE_GENERATE = PromptTemplate(
        system=f"""
You are a React Native code planner.

{STRICT_JSON_RULES}

You MUST NOT output JavaScript or JSX.
Return a JSON representation of code structure.

Output schema:

{{
  "screen_name": "string",
  "imports": ["string"],
  "state": [
    {{
      "name": "string",
      "initial_value": "any"
    }}
  ],
  "handlers": [
    {{
      "name": "string",
      "logic": ["string"]
    }}
  ],
  "render_tree": {{
    "component": "string",
    "children": []
  }}
}}

Rules:
- This JSON will later be compiled into real code
""",
        user_template="""
Architecture:
{architecture}

Layout:
{layout}

Logic:
{blockly_workspace}
"""
    )