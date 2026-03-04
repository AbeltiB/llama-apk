"""
Enhanced Blockly visual programming models with full event support.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET  
from xml.dom import minidom  

from typing import List, Dict, Any, Optional, Literal, Union
from pydantic import BaseModel, Field, field_validator, model_validator
import re


class BlockPosition(BaseModel):
    """Position of block in workspace"""
    x: int = 20
    y: int = 20


class BlockField(BaseModel):
    """Field in a block (user-editable)"""
    name: str
    value: Any


class BlockInput(BaseModel):
    """Input connection on a block"""
    name: str
    block: Optional['BlockDefinition'] = None
    shadow: Optional['BlockDefinition'] = None


class BlockDefinition(BaseModel):
    """Complete block definition with all connections"""
    type: str = Field(..., description="Block type identifier (e.g., 'component_event', 'state_set', 'navigate_to')")
    id: str = Field(..., description="Unique block ID")
    x: Optional[int] = 20
    y: Optional[int] = 20
    fields: Dict[str, Any] = Field(default_factory=dict)
    inputs: Dict[str, Union['BlockInput', Dict[str, Any]]] = Field(default_factory=dict)
    next: Optional[Union['BlockDefinition', Dict[str, Any]]] = None
    previous: Optional[bool] = None  # Whether block has a previous connection
    output: Optional[str] = None  # Output type if block returns a value
    
    @field_validator('id')
    @classmethod
    def validate_block_id(cls, v: str) -> str:
        """Ensure valid block ID"""
        if not v or len(v) == 0:
            raise ValueError("Block ID cannot be empty")
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', v):
            raise ValueError(f"Block ID '{v}' must start with letter and contain only letters, numbers, underscores")
        return v


# Need to update forward reference
BlockInput.model_rebuild()


class BlocklyWorkspace(BaseModel):
    """Complete Blockly workspace with all blocks"""
    languageVersion: int = 0
    blocks: List[BlockDefinition] = Field(default_factory=list)


class BlocklyVariable(BaseModel):
    """Variable declaration for Blockly"""
    name: str = Field(..., description="Variable name")
    id: str = Field(..., description="Unique variable ID")
    type: Literal["String", "Number", "Boolean", "Array", "Object"] = "String"
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate variable name"""
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', v):
            raise ValueError(f"Variable name '{v}' must start with letter and contain only letters, numbers, underscores")
        return v


class CustomBlockDefinition(BaseModel):
    """Definition for a custom block type"""
    type: str
    message0: str
    args0: List[Dict[str, Any]]
    output: Optional[str] = None
    colour: int = 230
    tooltip: str = ""
    helpUrl: str = ""


class EnhancedBlocklyDefinition(BaseModel):
    """
    Enhanced Blockly definition with full event support and validation
    """
    # Core workspace
    blocks: BlocklyWorkspace = Field(default_factory=BlocklyWorkspace)
    
    # Variables
    variables: List[BlocklyVariable] = Field(default_factory=list)
    
    # Custom block types
    custom_blocks: List[CustomBlockDefinition] = Field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @model_validator(mode='after')
    def validate_block_references(self) -> 'EnhancedBlocklyDefinition':
        """
        Validate all block references and connections
        """
        block_ids = {block.id for block in self.blocks.blocks}
        variable_names = {var.name for var in self.variables}
        
        def validate_block(block: BlockDefinition, path: List[str] = None):
            if path is None:
                path = []
            
            current_path = path + [block.id]
            
            # Check field references to variables
            for field_name, field_value in block.fields.items():
                if field_name in ['VAR', 'VARIABLE'] and isinstance(field_value, str):
                    if field_value not in variable_names and field_value not in ['count', 'value', 'text']:
                        # Common defaults, don't warn
                        pass
            
            # Validate inputs recursively
            for input_name, input_value in block.inputs.items():
                if isinstance(input_value, dict) and 'block' in input_value:
                    nested = input_value['block']
                    if isinstance(nested, dict):
                        # Convert dict to BlockDefinition for validation
                        try:
                            nested_block = BlockDefinition(**nested)
                            validate_block(nested_block, current_path)
                        except Exception:
                            # Invalid nested block structure
                            pass
                elif isinstance(input_value, BlockInput) and input_value.block:
                    validate_block(input_value.block, current_path)
            
            # Validate next block recursively
            if block.next:
                if isinstance(block.next, dict):
                    try:
                        next_block = BlockDefinition(**block.next)
                        validate_block(next_block, current_path)
                    except Exception:
                        pass
                elif isinstance(block.next, BlockDefinition):
                    validate_block(block.next, current_path)
        
        for block in self.blocks.blocks:
            try:
                validate_block(block)
            except Exception as e:
                # Add validation error to metadata but don't fail
                if 'validation_errors' not in self.metadata:
                    self.metadata['validation_errors'] = []
                self.metadata['validation_errors'].append(str(e))
        
        return self
    
    def to_blockly_xml(self) -> str:
        """Convert to Blockly XML format (for frontend)"""
        import xml.etree.ElementTree as ET
        from xml.dom import minidom
        
        xml = ET.Element('xml')
        
        # Add variables
        variables_xml = ET.SubElement(xml, 'variables')
        for var in self.variables:
            var_xml = ET.SubElement(variables_xml, 'variable')
            var_xml.set('id', var.id)
            var_xml.set('type', var.type)
            var_xml.text = var.name
        
        # Add blocks
        for block in self.blocks.blocks:
            block_xml = self._block_to_xml(block)
            xml.append(block_xml)
        
        # Pretty print
        rough_string = ET.tostring(xml, 'utf-8')
        reparsed = minidom.parseString(rough_string)
        return reparsed.toprettyxml(indent="  ")
    
    def _block_to_xml(self, block: BlockDefinition) -> ET.Element:
        """Convert a block to XML element"""
        block_xml = ET.Element('block')
        block_xml.set('type', block.type)
        block_xml.set('id', block.id)
        block_xml.set('x', str(block.x))
        block_xml.set('y', str(block.y))
        
        # Add fields
        for field_name, field_value in block.fields.items():
            field_xml = ET.SubElement(block_xml, 'field')
            field_xml.set('name', field_name)
            field_xml.text = str(field_value)
        
        # Add inputs
        for input_name, input_value in block.inputs.items():
            if isinstance(input_value, dict) and 'block' in input_value:
                value_xml = ET.SubElement(block_xml, 'value')
                value_xml.set('name', input_name)
                nested_block = self._block_to_xml(BlockDefinition(**input_value['block']))
                value_xml.append(nested_block)
            elif isinstance(input_value, BlockInput) and input_value.block:
                value_xml = ET.SubElement(block_xml, 'value')
                value_xml.set('name', input_name)
                nested_block = self._block_to_xml(input_value.block)
                value_xml.append(nested_block)
        
        # Add next block
        if block.next:
            if isinstance(block.next, dict):
                next_block = self._block_to_xml(BlockDefinition(**block.next))
                block_xml.append(next_block)
            elif isinstance(block.next, BlockDefinition):
                next_block = self._block_to_xml(block.next)
                block_xml.append(next_block)
        
        return block_xml


# Block type constants for easier reference
class BlockTypes:
    """Common Blockly block types"""
    # Event blocks
    COMPONENT_EVENT = "component_event"
    SCREEN_LOAD = "screen_load"
    TIMER_EVENT = "timer_event"
    
    # State blocks
    STATE_GET = "state_get"
    STATE_SET = "state_set"
    STATE_TOGGLE = "state_toggle"
    
    # Navigation blocks
    NAVIGATE_TO = "navigate_to"
    NAVIGATE_BACK = "navigate_back"
    
    # Logic blocks
    CONTROLS_IF = "controls_if"
    LOGIC_COMPARE = "logic_compare"
    LOGIC_OPERATION = "logic_operation"
    LOGIC_NEGATE = "logic_negate"
    LOGIC_BOOLEAN = "logic_boolean"
    LOGIC_NULL = "logic_null"
    LOGIC_TERNARY = "logic_ternary"
    
    # Loop blocks
    LOOPS_REPEAT = "loops_repeat"
    LOOPS_WHILE = "loops_while"
    LOOPS_FOR = "loops_for"
    LOOPS_FOREACH = "loops_foreach"
    
    # Math blocks
    MATH_NUMBER = "math_number"
    MATH_ARITHMETIC = "math_arithmetic"
    MATH_SINGLE = "math_single"
    MATH_TRIG = "math_trig"
    MATH_CONSTANT = "math_constant"
    MATH_NUMBER_PROPERTY = "math_number_property"
    MATH_ROUND = "math_round"
    MATH_ON_LIST = "math_on_list"
    MATH_MODULO = "math_modulo"
    MATH_CONSTRAIN = "math_constrain"
    MATH_RANDOM_INT = "math_random_int"
    MATH_RANDOM_FLOAT = "math_random_float"
    MATH_ATAN2 = "math_atan2"
    
    # Text blocks
    TEXT = "text"
    TEXT_JOIN = "text_join"
    TEXT_APPEND = "text_append"
    TEXT_LENGTH = "text_length"
    TEXT_ISEMPTY = "text_isEmpty"
    TEXT_INDEXOF = "text_indexOf"
    TEXT_CHARAT = "text_charAt"
    TEXT_GET_SUBSTRING = "text_getSubstring"
    TEXT_CHANGE_CASE = "text_changeCase"
    TEXT_TRIM = "text_trim"
    TEXT_PRINT = "text_print"
    TEXT_PROMPT = "text_prompt"
    
    # List blocks
    LISTS_CREATE_EMPTY = "lists_create_empty"
    LISTS_CREATE_WITH = "lists_create_with"
    LISTS_REPEAT = "lists_repeat"
    LISTS_LENGTH = "lists_length"
    LISTS_ISEMPTY = "lists_isEmpty"
    LISTS_INDEXOF = "lists_indexOf"
    LISTS_GET_INDEX = "lists_getIndex"
    LISTS_SET_INDEX = "lists_setIndex"
    LISTS_GET_SUBLIST = "lists_getSublist"
    LISTS_SPLIT = "lists_split"
    LISTS_SORT = "lists_sort"
    
    # Hardware blocks
    JOYSTICK_READ = "joystick_read"
    SENSOR_READ = "sensor_read"
    DEVICE_CONNECT = "device_connect"
    DEVICE_DISCONNECT = "device_disconnect"
    SEND_COMMAND = "send_command"
    
    # Notification blocks
    SHOW_TOAST = "show_toast"
    SHOW_ALERT = "show_alert"
    SEND_NOTIFICATION = "send_notification"
    
    # File blocks
    PICK_FILE = "pick_file"
    READ_FILE = "read_file"
    SAVE_FILE = "save_file"
    
    # Map blocks
    MAP_CREATE = "map_create"
    MAP_ADD_MARKER = "map_add_marker"
    MAP_GET_LOCATION = "map_get_location"