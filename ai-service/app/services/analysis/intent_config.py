"""
Domain-Aware Intent Configuration System
Supports ANY app type with dynamic categorization
"""
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
import re

# Import from base enums
from app.services.analysis.base_enums import AppDomain


class IntentCategory(str, Enum):
    """High-level intent categories"""
    CREATE_NEW = "create_new"
    MODIFY_EXISTING = "modify_existing"
    EXTEND_FEATURES = "extend_features"
    CLARIFY_REQUEST = "clarify_request"
    TECHNICAL_HELP = "technical_help"
    UNSUPPORTED = "unsupported"


class ClassificationTier(str, Enum):
    """Classification tiers"""
    LLAMA3 = "llama3"
    CLAUDE = "claude"
    GROQ = "groq"
    HEURISTIC = "heuristic"
    FAILED = "failed"


# Hardware/Device Control Patterns
HARDWARE_PATTERNS = {
    "drone": {
        "keywords": ["drone", "quadcopter", "uav", "flight", "fly", "controller", "fpv"],
        "required_features": ["real_time_control", "video_stream", "telemetry", "gps"],
        "special_components": ["joystick_control", "map_view", "battery_indicator", "status_panel"],
        "apis_needed": ["bluetooth", "websockets", "gps_api"],
        "permissions": ["bluetooth", "location", "camera"]
    },
    "3d_printer": {
        "keywords": ["3d printer", "print", "filament", "gcode", "slicer", "extruder"],
        "required_features": ["file_upload", "print_control", "temperature_monitoring", "progress_tracking"],
        "special_components": ["model_preview", "temperature_chart", "control_panel", "file_manager"],
        "apis_needed": ["serial_api", "websockets", "file_system"],
        "permissions": ["usb", "storage"]
    },
    "iot_device": {
        "keywords": ["smart home", "iot", "sensor", "device", "automation", "control"],
        "required_features": ["device_pairing", "real_time_updates", "automation_rules", "notifications"],
        "special_components": ["device_list", "control_card", "automation_editor", "dashboard"],
        "apis_needed": ["mqtt", "websockets", "bluetooth"],
        "permissions": ["bluetooth", "wifi", "location"]
    }
}


# AI/ML Patterns
AI_PATTERNS = {
    "image_to_3d": {
        "keywords": ["image to 3d", "photo to 3d", "picture to model", "scan to 3d"],
        "required_features": ["image_upload", "processing", "3d_preview", "export"],
        "special_components": ["image_uploader", "3d_viewer", "parameter_controls", "progress_indicator"],
        "apis_needed": ["tensorflow.js", "webgl", "file_system"],
        "permissions": ["camera", "storage"]
    },
    "ai_model_trainer": {
        "keywords": ["train model", "machine learning", "neural network", "ai training"],
        "required_features": ["data_upload", "model_training", "prediction", "results_visualization"],
        "special_components": ["data_uploader", "training_progress", "results_chart", "model_selector"],
        "apis_needed": ["tensorflow.js", "webworkers", "file_system"],
        "permissions": ["storage"]
    },
    "image_processing": {
        "keywords": ["image processing", "filter", "edit photo", "detect objects"],
        "required_features": ["image_upload", "processing", "preview", "export"],
        "special_components": ["image_viewer", "filter_controls", "processing_options"],
        "apis_needed": ["canvas_api", "webworkers"],
        "permissions": ["camera", "storage"]
    }
}


# Technical Requirements by Complexity
TECHNICAL_REQUIREMENTS = {
    "hardware": {
        "apis_needed": ["bluetooth", "websockets", "serial_api", "usb"],
        "permissions": ["bluetooth", "location", "camera", "usb"],
        "platform_considerations": ["low_latency", "real_time", "background_operations"],
        "risk_level": "high"
    },
    "ai_ml": {
        "apis_needed": ["tensorflow.js", "webgl", "webworkers", "file_system"],
        "permissions": ["camera", "storage"],
        "platform_considerations": ["performance", "memory", "processing_power"],
        "risk_level": "medium"
    },
    "enterprise": {
        "apis_needed": ["rest_apis", "websockets", "database", "authentication"],
        "permissions": ["internet", "storage", "camera"],
        "platform_considerations": ["security", "scalability", "offline_support"],
        "risk_level": "medium"
    },
    "integrated": {
        "apis_needed": ["rest_apis", "local_storage", "camera", "location"],
        "permissions": ["internet", "storage"],
        "platform_considerations": ["network_status", "caching", "error_handling"],
        "risk_level": "low"
    }
}


class IntentConfig:
    """Dynamic intent configuration that adapts to ANY app type"""
    
    @staticmethod
    def detect_domain(prompt_lower: str) -> Tuple[AppDomain, str, float]:
        """
        Detect application domain and specific type with confidence
        
        Returns: (domain, specific_type, confidence)
        """
        # Check hardware/device patterns first
        for device_type, patterns in HARDWARE_PATTERNS.items():
            if any(keyword in prompt_lower for keyword in patterns["keywords"]):
                return (AppDomain.IOT_HARDWARE, device_type, 0.9)
        
        # Check AI/ML patterns
        for ai_type, patterns in AI_PATTERNS.items():
            if any(keyword in prompt_lower for keyword in patterns["keywords"]):
                return (AppDomain.CREATIVE_MEDIA, ai_type, 0.85)
        
        # Use AppDomain's built-in detection
        domain, confidence = AppDomain.detect_from_text(prompt_lower)
        return (domain, domain.value, confidence)
    
    @staticmethod
    def extract_special_requirements(
        prompt: str, 
        domain: AppDomain, 
        specific_type: str
    ) -> Dict[str, Any]:
        """Extract special requirements for complex app types"""
        requirements = {
            "needs_hardware": False,
            "needs_ai_ml": False,
            "needs_real_time": False,
            "needs_3d": False,
            "special_apis": [],
            "complex_components": [],
            "permissions_required": []
        }
        
        prompt_lower = prompt.lower()
        
        # Hardware/device requirements
        if domain == AppDomain.IOT_HARDWARE:
            requirements["needs_hardware"] = True
            requirements["needs_real_time"] = True
            
            if specific_type in HARDWARE_PATTERNS:
                reqs = HARDWARE_PATTERNS[specific_type]
                requirements["special_apis"] = reqs.get("apis_needed", [])
                requirements["complex_components"] = reqs.get("special_components", [])
                requirements["permissions_required"] = reqs.get("permissions", [])
        
        # AI/ML requirements
        if domain == AppDomain.CREATIVE_MEDIA and specific_type in AI_PATTERNS:
            requirements["needs_ai_ml"] = True
            reqs = AI_PATTERNS[specific_type]
            requirements["special_apis"] = reqs.get("apis_needed", [])
            requirements["complex_components"] = reqs.get("special_components", [])
            requirements["permissions_required"] = reqs.get("permissions", [])
        
        # 3D requirements
        if any(word in prompt_lower for word in ["3d", "three.js", "webgl", "model", "mesh"]):
            requirements["needs_3d"] = True
            if "webgl" not in requirements["special_apis"]:
                requirements["special_apis"].append("webgl")
            if "three.js" not in requirements["special_apis"]:
                requirements["special_apis"].append("three.js")
        
        # Real-time requirements
        if any(word in prompt_lower for word in ["real-time", "live", "stream", "control", "telemetry"]):
            requirements["needs_real_time"] = True
            if "websockets" not in requirements["special_apis"]:
                requirements["special_apis"].append("websockets")
        
        return requirements
    
    @staticmethod
    def get_complexity_level(
        prompt: str, 
        domain: AppDomain, 
        app_type: str
    ) -> str:
        """Determine complexity level based on domain and requirements"""
        from app.services.analysis.intent_schemas import ComplexityLevel
        
        prompt_lower = prompt.lower()
        
        # Check for known complex types
        if domain == AppDomain.IOT_HARDWARE:
            return "hardware"
        
        if domain == AppDomain.CREATIVE_MEDIA and app_type in AI_PATTERNS:
            return "ai_ml"
        
        # Check for enterprise features
        enterprise_keywords = ["payment", "bank", "invoice", "crm", "erp", "multi-tenant"]
        if any(word in prompt_lower for word in enterprise_keywords):
            return "enterprise"
        
        # Check for integrations
        integration_keywords = ["api", "database", "backend", "sync", "cloud"]
        if sum(1 for word in integration_keywords if word in prompt_lower) >= 2:
            return "integrated"
        
        # Check for data features
        data_keywords = ["chart", "graph", "data", "analyze", "report"]
        if any(word in prompt_lower for word in data_keywords):
            return "data_driven"
        
        # Default to simple UI
        return "simple_ui"
    
    @staticmethod
    def get_template_for_domain(domain: AppDomain, app_type: str) -> Dict[str, str]:
        """Get appropriate templates for the domain"""
        templates = {
            AppDomain.IOT_HARDWARE: {
                "architecture_template": "hardware_control",
                "layout_template": "device_dashboard",
                "blockly_template": "hardware_events"
            },
            AppDomain.CREATIVE_MEDIA: {
                "architecture_template": "creative_tool",
                "layout_template": "editor_workspace",
                "blockly_template": "media_processing"
            },
            AppDomain.DATA_SCIENCE: {
                "architecture_template": "data_analysis",
                "layout_template": "data_dashboard",
                "blockly_template": "data_pipeline"
            },
            AppDomain.PRODUCTIVITY: {
                "architecture_template": "productivity_app",
                "layout_template": "list_detail",
                "blockly_template": "crud_operations"
            },
            AppDomain.UTILITY: {
                "architecture_template": "utility_app",
                "layout_template": "simple_interface",
                "blockly_template": "basic_logic"
            }
        }
        
        # Check if it's a hardware type
        if app_type in HARDWARE_PATTERNS:
            return templates.get(AppDomain.IOT_HARDWARE, {
                "architecture_template": "custom_app",
                "layout_template": "custom_layout",
                "blockly_template": "custom_logic"
            })
        
        # Check if it's an AI type
        if app_type in AI_PATTERNS:
            return templates.get(AppDomain.CREATIVE_MEDIA, {
                "architecture_template": "custom_app",
                "layout_template": "custom_layout",
                "blockly_template": "custom_logic"
            })
        
        # Return domain-specific or custom
        return templates.get(domain, {
            "architecture_template": "custom_app",
            "layout_template": "custom_layout",
            "blockly_template": "custom_logic"
        })