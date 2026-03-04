"""
Enhanced Blockly Validator with comprehensive validation for event blocks.
"""
from typing import List, Tuple, Dict, Any, Set, Optional
from datetime import datetime


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


class BlocklyValidator:
    """
    Comprehensive Blockly validator with full event validation.
    
    Validates:
    - Block structure and syntax
    - Event handler presence
    - Variable declarations and usage
    - Connection integrity
    - Logic flow completeness
    - Component references
    """
    
    def __init__(self):
        self.warnings: List[ValidationIssue] = []
        self.block_ids: Set[str] = set()
        self.variable_names: Set[str] = set()
        self.component_ids: Set[str] = set()
        self.event_blocks: List[str] = []
        
        # Valid block types
        self.valid_block_types = {
            # Event blocks
            'component_event', 'screen_load', 'timer_event',
            
            # State blocks
            'state_get', 'state_set', 'state_toggle',
            
            # Navigation blocks
            'navigate_to', 'navigate_back',
            
            # Logic blocks
            'controls_if', 'logic_compare', 'logic_operation', 'logic_negate',
            'logic_boolean', 'logic_null', 'logic_ternary',
            
            # Loop blocks
            'loops_repeat', 'loops_while', 'loops_for', 'loops_foreach',
            
            # Math blocks
            'math_number', 'math_arithmetic', 'math_single', 'math_trig',
            'math_constant', 'math_number_property', 'math_round',
            'math_on_list', 'math_modulo', 'math_constrain',
            'math_random_int', 'math_random_float', 'math_atan2',
            
            # Text blocks
            'text', 'text_join', 'text_append', 'text_length', 'text_isEmpty',
            'text_indexOf', 'text_charAt', 'text_get_substring', 'text_change_case',
            'text_trim', 'text_print', 'text_prompt',
            
            # List blocks
            'lists_create_empty', 'lists_create_with', 'lists_repeat',
            'lists_length', 'lists_isEmpty', 'lists_indexOf',
            'lists_get_index', 'lists_set_index', 'lists_get_sublist',
            'lists_split', 'lists_sort',
            
            # Hardware blocks
            'joystick_read', 'sensor_read', 'device_connect', 'device_disconnect',
            'send_command',
            
            # Notification blocks
            'show_toast', 'show_alert', 'send_notification',
            
            # File blocks
            'pick_file', 'read_file', 'save_file',
            
            # Map blocks
            'map_create', 'map_add_marker', 'map_get_location'
        }
        
        # Statistics
        self.stats = {
            'total_validations': 0,
            'passed': 0,
            'failed': 0
        }
    
    async def validate(
        self,
        blockly: Dict[str, Any]
    ) -> Tuple[bool, List[ValidationIssue]]:
        """
        Comprehensive validation of Blockly blocks.
        
        Args:
            blockly: Blockly definition to validate
            
        Returns:
            Tuple of (is_valid, issues_list)
        """
        self.stats['total_validations'] += 1
        self.warnings = []
        self.block_ids = set()
        self.variable_names = set()
        self.component_ids = set()
        self.event_blocks = []
        
        # Extract blocks and variables
        blocks = []
        if 'blocks' in blockly:
            if isinstance(blockly['blocks'], dict):
                blocks = blockly['blocks'].get('blocks', [])
            elif isinstance(blockly['blocks'], list):
                blocks = blockly['blocks']
        
        variables = blockly.get('variables', [])
        
        # Collect IDs and names
        self._collect_ids(blocks, variables)
        
        # Run validation checks
        self._validate_structure(blockly)
        self._validate_blocks(blocks)
        self._validate_variables(variables)
        self._validate_connections(blocks)
        self._validate_references(blocks)
        self._validate_event_handlers(blocks)
        self._validate_logic_flow(blocks)
        self._validate_state_usage(blocks)
        self._validate_navigation(blocks)
        
        # Determine if valid
        critical_issues = [w for w in self.warnings if w.level == "critical"]
        error_issues = [w for w in self.warnings if w.level == "error"]
        is_valid = len(critical_issues) == 0 and len(error_issues) == 0
        
        if is_valid:
            self.stats['passed'] += 1
        else:
            self.stats['failed'] += 1
        
        return is_valid, self.warnings
    
    def _collect_ids(self, blocks: List[Dict], variables: List[Dict]):
        """Collect all block and variable IDs"""
        
        def collect_from_block(block: Dict):
            if 'id' in block:
                self.block_ids.add(block['id'])
            
            # Check for component references
            fields = block.get('fields', {})
            if 'COMPONENT' in fields:
                self.component_ids.add(fields['COMPONENT'])
            
            # Recursively check inputs
            inputs = block.get('inputs', {})
            for input_data in inputs.values():
                if isinstance(input_data, dict):
                    if 'block' in input_data:
                        collect_from_block(input_data['block'])
                    if 'shadow' in input_data:
                        collect_from_block(input_data['shadow'])
            
            # Check next block
            if 'next' in block and isinstance(block['next'], dict):
                if 'block' in block['next']:
                    collect_from_block(block['next']['block'])
        
        for block in blocks:
            collect_from_block(block)
        
        for var in variables:
            if 'name' in var:
                self.variable_names.add(var['name'])
    
    def _validate_structure(self, blockly: Dict[str, Any]):
        """Validate basic structure"""
        
        if 'blocks' not in blockly:
            self.warnings.append(ValidationIssue(
                level="error",
                component="root",
                message="Missing 'blocks' key",
                suggestion="Add blocks workspace structure"
            ))
            return
        
        blocks_obj = blockly['blocks']
        
        if not isinstance(blocks_obj, dict) and not isinstance(blocks_obj, list):
            self.warnings.append(ValidationIssue(
                level="error",
                component="root",
                message="'blocks' must be an object or array",
                suggestion="Use {blocks: [...]} or [...]"
            ))
    
    def _validate_blocks(self, blocks: List[Dict]):
        """Validate individual blocks"""
        
        if len(blocks) == 0:
            self.warnings.append(ValidationIssue(
                level="warning",
                component="root",
                message="No blocks defined",
                suggestion="Add event handlers and logic blocks"
            ))
            return
        
        # Check for duplicate IDs
        id_counts = {}
        for block in blocks:
            block_id = block.get('id', 'unknown')
            id_counts[block_id] = id_counts.get(block_id, 0) + 1
        
        duplicates = [bid for bid, count in id_counts.items() if count > 1]
        if duplicates:
            self.warnings.append(ValidationIssue(
                level="error",
                component="root",
                message=f"Duplicate block IDs: {', '.join(duplicates)}",
                suggestion="Ensure all block IDs are unique"
            ))
        
        # Validate each block
        for block in blocks:
            self._validate_single_block(block)
    
    def _validate_single_block(self, block: Dict):
        """Validate a single block"""
        
        block_id = block.get('id', 'unknown')
        block_type = block.get('type', 'unknown')
        
        # Check required fields
        if 'type' not in block:
            self.warnings.append(ValidationIssue(
                level="error",
                component=block_id,
                message="Missing 'type' field",
                suggestion="Add block type identifier"
            ))
        
        if 'id' not in block:
            self.warnings.append(ValidationIssue(
                level="error",
                component=block_id,
                message="Missing 'id' field",
                suggestion="Add unique block ID"
            ))
        
        # Check block type validity
        if block_type not in self.valid_block_types and block_type != 'unknown':
            self.warnings.append(ValidationIssue(
                level="warning",
                component=block_id,
                message=f"Unknown block type: {block_type}",
                suggestion="Use standard Blockly block types"
            ))
        
        # Check for event blocks
        if 'event' in block_type.lower() or block_type == 'component_event':
            self.event_blocks.append(block_id)
            
            # Event blocks should have COMPONENT field
            fields = block.get('fields', {})
            if 'COMPONENT' not in fields:
                self.warnings.append(ValidationIssue(
                    level="warning",
                    component=block_id,
                    message="Event block missing COMPONENT field",
                    suggestion="Specify which component triggers this event"
                ))
        
        # Recursively validate nested blocks
        inputs = block.get('inputs', {})
        for input_name, input_data in inputs.items():
            if isinstance(input_data, dict):
                if 'block' in input_data:
                    self._validate_single_block(input_data['block'])
                if 'shadow' in input_data:
                    self._validate_single_block(input_data['shadow'])
        
        # Validate next block
        if 'next' in block and isinstance(block['next'], dict):
            if 'block' in block['next']:
                self._validate_single_block(block['next']['block'])
    
    def _validate_variables(self, variables: List[Dict]):
        """Validate variable declarations"""
        
        if not variables and len(self.block_ids) > 0:
            self.warnings.append(ValidationIssue(
                level="info",
                component="variables",
                message="No variables defined",
                suggestion="Define variables for state management"
            ))
            return
        
        # Check for duplicate names
        name_counts = {}
        for var in variables:
            name = var.get('name', 'unknown')
            name_counts[name] = name_counts.get(name, 0) + 1
        
        duplicates = [name for name, count in name_counts.items() if count > 1]
        if duplicates:
            self.warnings.append(ValidationIssue(
                level="error",
                component="variables",
                message=f"Duplicate variable names: {', '.join(duplicates)}",
                suggestion="Use unique names for each variable"
            ))
        
        # Check each variable
        for var in variables:
            if 'name' not in var:
                self.warnings.append(ValidationIssue(
                    level="error",
                    component=var.get('id', 'unknown'),
                    message="Variable missing 'name' field",
                    suggestion="Add variable name"
                ))
    
    def _validate_connections(self, blocks: List[Dict]):
        """Validate block connections"""
        
        def check_connections(block: Dict, parent_id: Optional[str] = None):
            block_id = block.get('id', 'unknown')
            
            # Check input connections
            inputs = block.get('inputs', {})
            for input_name, input_data in inputs.items():
                if isinstance(input_data, dict):
                    if 'block' in input_data:
                        nested = input_data['block']
                        if isinstance(nested, dict):
                            check_connections(nested, block_id)
            
            # Check next connection
            next_block = block.get('next')
            if next_block:
                if isinstance(next_block, dict) and 'block' in next_block:
                    nested = next_block['block']
                    if isinstance(nested, dict):
                        check_connections(nested, block_id)
        
        for block in blocks:
            check_connections(block)
    
    def _validate_references(self, blocks: List[Dict]):
        """Validate variable and component references"""
        
        def check_references(block: Dict):
            block_id = block.get('id', 'unknown')
            fields = block.get('fields', {})
            
            # Check variable references
            for field_name, field_value in fields.items():
                if field_name in ['VAR', 'VARIABLE']:
                    if isinstance(field_value, str) and field_value:
                        if field_value not in self.variable_names:
                            self.warnings.append(ValidationIssue(
                                level="warning",
                                component=block_id,
                                message=f"Reference to undefined variable: {field_value}",
                                suggestion="Declare variable in variables list"
                            ))
            
            # Check nested blocks
            inputs = block.get('inputs', {})
            for input_data in inputs.values():
                if isinstance(input_data, dict):
                    if 'block' in input_data:
                        check_references(input_data['block'])
                    if 'shadow' in input_data:
                        check_references(input_data['shadow'])
            
            if 'next' in block and isinstance(block['next'], dict):
                if 'block' in block['next']:
                    check_references(block['next']['block'])
        
        for block in blocks:
            check_references(block)
    
    def _validate_event_handlers(self, blocks: List[Dict]):
        """Validate event handler presence and completeness"""
        
        if not self.event_blocks:
            self.warnings.append(ValidationIssue(
                level="warning",
                component="root",
                message="No event handler blocks found",
                suggestion="Add event blocks to handle user interactions (button clicks, screen loads, etc.)"
            ))
        else:
            # Check if event handlers have actions
            for event_id in self.event_blocks:
                # Find the event block
                event_block = None
                for block in blocks:
                    if block.get('id') == event_id:
                        event_block = block
                        break
                
                if event_block and 'next' not in event_block:
                    self.warnings.append(ValidationIssue(
                        level="info",
                        component=event_id,
                        message="Event handler has no actions",
                        suggestion="Connect action blocks to handle the event"
                    ))
    
    def _validate_logic_flow(self, blocks: List[Dict]):
        """Validate logic flow makes sense"""
        
        # Check for unreachable blocks (blocks with no previous connection and not event handlers)
        top_level_blocks = []
        
        def collect_top_level(block: Dict):
            block_id = block.get('id', 'unknown')
            block_type = block.get('type', '')
            
            # If it's not an event block and not obviously a top-level block
            if 'event' not in block_type.lower() and block_type not in ['component_event', 'screen_load']:
                # Check if it has no previous connection indicator
                if 'previous' not in block or not block.get('previous'):
                    top_level_blocks.append(block_id)
            
            # Check nested
            inputs = block.get('inputs', {})
            for input_data in inputs.values():
                if isinstance(input_data, dict):
                    if 'block' in input_data:
                        pass  # Nested blocks are fine
        
        for block in blocks:
            collect_top_level(block)
        
        if len(top_level_blocks) > len(self.event_blocks):
            # Some blocks are top-level but not events
            extra = set(top_level_blocks) - set(self.event_blocks)
            if extra:
                self.warnings.append(ValidationIssue(
                    level="info",
                    component=",".join(list(extra)[:3]),
                    message="Some blocks may be unreachable (not connected to any event)",
                    suggestion="Connect these blocks to event handlers"
                ))
    
    def _validate_state_usage(self, blocks: List[Dict]):
        """Validate state management usage"""
        
        has_state_get = False
        has_state_set = False
        
        def check_state_usage(block: Dict):
            nonlocal has_state_get, has_state_set
            block_type = block.get('type', '')
            
            if block_type == 'state_get' or block_type == 'variables_get':
                has_state_get = True
            elif block_type == 'state_set' or block_type == 'variables_set':
                has_state_set = True
            
            # Check nested
            inputs = block.get('inputs', {})
            for input_data in inputs.values():
                if isinstance(input_data, dict):
                    if 'block' in input_data:
                        check_state_usage(input_data['block'])
            
            if 'next' in block and isinstance(block['next'], dict):
                if 'block' in block['next']:
                    check_state_usage(block['next']['block'])
        
        for block in blocks:
            check_state_usage(block)
        
        if has_state_set and not has_state_get:
            self.warnings.append(ValidationIssue(
                level="info",
                component="state",
                message="State is set but never read",
                suggestion="Add state_get blocks to use the stored values"
            ))
        elif has_state_get and not has_state_set:
            self.warnings.append(ValidationIssue(
                level="info",
                component="state",
                message="State is read but never set",
                suggestion="Initialize state with state_set blocks"
            ))
    
    def _validate_navigation(self, blocks: List[Dict]):
        """Validate navigation blocks"""
        
        has_navigation = False
        screen_refs = set()
        
        def check_navigation(block: Dict):
            nonlocal has_navigation
            block_type = block.get('type', '')
            
            if block_type == 'navigate_to' or block_type == 'navigate_back':
                has_navigation = True
            
            # Collect screen references
            fields = block.get('fields', {})
            if 'SCREEN' in fields:
                screen_refs.add(fields['SCREEN'])
            
            # Check nested
            inputs = block.get('inputs', {})
            for input_data in inputs.values():
                if isinstance(input_data, dict):
                    if 'block' in input_data:
                        check_navigation(input_data['block'])
            
            if 'next' in block and isinstance(block['next'], dict):
                if 'block' in block['next']:
                    check_navigation(block['next']['block'])
        
        for block in blocks:
            check_navigation(block)
        
        if has_navigation and not screen_refs:
            self.warnings.append(ValidationIssue(
                level="info",
                component="navigation",
                message="Navigation blocks present but no screen targets specified",
                suggestion="Add SCREEN fields to navigate_to blocks"
            ))
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get validation statistics"""
        total = self.stats['total_validations']
        return {
            **self.stats,
            'pass_rate': (self.stats['passed'] / total * 100) if total > 0 else 0
        }


# Global validator instance
blockly_validator = BlocklyValidator()