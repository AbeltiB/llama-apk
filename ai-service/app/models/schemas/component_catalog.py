"""Centralized UI component registry with all 22 components and their attributes.

This module is the single source of truth for component definitions used across
prompting, schema validation, and output formatting.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple, TypedDict


class ComponentImport(TypedDict):
    """Import definition required to render a component."""

    name: str
    source: str


class ComponentDefinition(TypedDict, total=False):
    """Full definition for a UI component."""

    id: str
    name: str
    displayName: str
    category: str
    output_type: str
    aliases: List[str]
    required_imports: List[ComponentImport]
    default_props: Dict[str, Any]
    resizable: bool
    states: List[str]  # State variables this component manages
    schema: Dict[str, Any]


# ============================================================================
# COMPONENT DEFINITIONS - All 22 components with their attributes
# ============================================================================

COMPONENT_DEFINITIONS: Dict[str, ComponentDefinition] = {
    # 1. Group
    "Group": {
        "id": "layout.group",
        "name": "Group",
        "displayName": "Group",
        "category": "layout",
        "output_type": "Group",
        "aliases": ["Container", "Box"],
        "required_imports": [{"name": "Stack", "source": "react-native"}],
        "resizable": False,
        "default_props": {
            "backgroundColor": "transparent",
            "borderColor": "#CCCCCC",
            "borderWidth": 0,
            "borderStyle": "solid",
            "borderRadius": 0,
            "padding": 0,
        },
        "schema": {
            "backgroundColor": {"type": "string", "required": False},
            "borderColor": {"type": "string", "required": False},
            "borderWidth": {"type": "number", "required": False},
            "borderStyle": {"type": "string", "enum": ["solid", "dashed", "dotted"], "required": False},
            "borderRadius": {"type": "number", "required": False},
            "padding": {"type": "number", "required": False},
            "style": {"type": "object", "required": False},
        },
    },
    
    # 2. Layout
    "Layout": {
        "id": "layout.container",
        "name": "Layout",
        "displayName": "Layout",
        "category": "layout",
        "output_type": "Layout",
        "aliases": ["VStack", "HStack", "YStack", "XStack"],
        "required_imports": [
            {"name": "YStack", "source": "tamagui"},
            {"name": "XStack", "source": "tamagui"},
        ],
        "resizable": True,
        "default_props": {
            "direction": "vertical",
            "spacing": 8,
        },
        "schema": {
            "direction": {"type": "string", "enum": ["vertical", "horizontal"], "required": False},
            "spacing": {"type": "number", "required": False},
            "style": {"type": "object", "required": False},
        },
    },
    
    # 3. Button
    "Button": {
        "id": "core.button",
        "name": "Button",
        "displayName": "Button",
        "category": "input",
        "output_type": "Button",
        "aliases": ["Btn", "Pressable"],
        "required_imports": [{"name": "Button", "source": "tamagui"}],
        "resizable": True,
        "states": ["text"],
        "default_props": {
            "text": "Button",
            "variant": "primary",
            "size": "medium",
            "color": "#FFFFFF",
            "backgroundColor": "#007AFF",
            "borderWidth": 0,
            "borderColor": "#007AFF",
            "borderRadius": 8,
        },
        "schema": {
            "text": {"type": "string", "required": True},
            "variant": {"type": "string", "enum": ["primary", "secondary", "outline", "ghost"], "required": False},
            "size": {"type": "string", "enum": ["small", "medium", "large"], "required": False},
            "color": {"type": "string", "required": False},
            "backgroundColor": {"type": "string", "required": False},
            "borderWidth": {"type": "number", "required": False},
            "borderColor": {"type": "string", "required": False},
            "borderRadius": {"type": "number", "required": False},
            "style": {"type": "object", "required": False},
        },
    },
    
    # 4. Text_Content
    "Text_Content": {
        "id": "core.text",
        "name": "Text_Content",
        "displayName": "Text",
        "category": "display",
        "output_type": "Text_Content",
        "aliases": ["Text", "Label"],
        "required_imports": [
            {"name": "Text", "source": "tamagui"},
            {"name": "XStack", "source": "tamagui"},
        ],
        "resizable": True,
        "states": ["text"],
        "default_props": {
            "text": "Text",
            "fontSize": 16,
            "color": "#000000",
            "backgroundColor": "transparent",
        },
        "schema": {
            "text": {"type": "string", "required": True},
            "fontSize": {"type": "number", "required": False},
            "color": {"type": "string", "required": False},
            "backgroundColor": {"type": "string", "required": False},
            "style": {"type": "object", "required": False},
        },
    },
    
    # 5. Input_Text
    "Input_Text": {
        "id": "core.input_text",
        "name": "Input_Text",
        "displayName": "Input Text",
        "category": "input",
        "output_type": "Input",
        "aliases": ["Input", "TextInput", "TextField"],
        "required_imports": [{"name": "Input", "source": "tamagui"}],
        "resizable": True,
        "states": ["value"],
        "default_props": {
            "placeholder": "Enter text...",
            "value": "",
            "secureTextEntry": False,
            "variant": "outline",
            "size": "medium",
            "color": "#000000",
            "backgroundColor": "#FFFFFF",
            "borderColor": "#CCCCCC",
            "borderWidth": 1,
            "borderRadius": 8,
            "placeholderColor": "#999999",
        },
        "schema": {
            "placeholder": {"type": "string", "required": False},
            "value": {"type": "string", "required": False},
            "secureTextEntry": {"type": "boolean", "required": False},
            "variant": {"type": "string", "enum": ["outline", "filled", "underlined"], "required": False},
            "size": {"type": "string", "enum": ["small", "medium", "large"], "required": False},
            "color": {"type": "string", "required": False},
            "backgroundColor": {"type": "string", "required": False},
            "borderColor": {"type": "string", "required": False},
            "borderWidth": {"type": "number", "required": False},
            "borderRadius": {"type": "number", "required": False},
            "placeholderColor": {"type": "string", "required": False},
            "focusStyle": {"type": "object", "required": False},
            "style": {"type": "object", "required": False},
        },
    },
    
    # 6. Switch
    "Switch": {
        "id": "core.switch",
        "name": "Switch",
        "displayName": "Switch",
        "category": "input",
        "output_type": "Switch",
        "aliases": ["Toggle"],
        "required_imports": [
            {"name": "Switch", "source": "tamagui"},
            {"name": "Label", "source": "tamagui"},
            {"name": "XStack", "source": "tamagui"},
        ],
        "resizable": True,
        "states": ["label"],
        "default_props": {
            "defaultChecked": False,
            "size": "medium",
            "label": "Toggle",
            "value": False,
            "backgroundColor": "#E0E0E0",
            "checkedColor": "#34C759",
            "thumbColor": "#FFFFFF",
        },
        "schema": {
            "defaultChecked": {"type": "boolean", "required": False},
            "size": {"type": "string", "enum": ["small", "medium", "large"], "required": False},
            "label": {"type": "string", "required": False},
            "value": {"type": "boolean", "required": False},
            "backgroundColor": {"type": "string", "required": False},
            "checkedColor": {"type": "string", "required": False},
            "thumbColor": {"type": "string", "required": False},
            "style": {"type": "object", "required": False},
        },
    },
    
    # 7. Checkbox
    "Checkbox": {
        "id": "core.checkbox",
        "name": "Checkbox",
        "displayName": "Checkbox",
        "category": "input",
        "output_type": "Checkbox",
        "aliases": ["Check", "Tick"],
        "required_imports": [
            {"name": "Checkbox", "source": "tamagui"},
            {"name": "Label", "source": "tamagui"},
            {"name": "XStack", "source": "tamagui"},
            {"name": "Check", "source": "@tamagui/lucide-icons"},
        ],
        "resizable": True,
        "states": ["label"],
        "default_props": {
            "checked": False,
            "size": 24,
            "color": "#007AFF",
            "borderColor": "#CCCCCC",
            "backgroundColor": "#FFFFFF",
            "label": "",
        },
        "schema": {
            "checked": {"type": "boolean", "required": False},
            "size": {"type": "number", "required": False},
            "color": {"type": "string", "required": False},
            "borderColor": {"type": "string", "required": False},
            "backgroundColor": {"type": "string", "required": False},
            "label": {"type": "string", "required": False},
            "style": {"type": "object", "required": False},
        },
    },
    
    # 8. Text_Area
    "Text_Area": {
        "id": "core.text_area",
        "name": "Text_Area",
        "displayName": "Text Area",
        "category": "input",
        "output_type": "TextArea",
        "aliases": ["TextArea", "MultilineInput"],
        "required_imports": [{"name": "TextArea", "source": "tamagui"}],
        "resizable": True,
        "states": ["value"],
        "default_props": {
            "placeholder": "Enter multi-line text...",
            "value": "",
            "multiline": True,
            "variant": "outline",
            "size": "medium",
            "color": "#000000",
            "backgroundColor": "#FFFFFF",
            "borderColor": "#CCCCCC",
            "borderWidth": 1,
            "borderRadius": 8,
            "placeholderColor": "#999999",
        },
        "schema": {
            "placeholder": {"type": "string", "required": False},
            "value": {"type": "string", "required": False},
            "multiline": {"type": "boolean", "required": False},
            "variant": {"type": "string", "enum": ["outline", "filled", "underlined"], "required": False},
            "size": {"type": "string", "enum": ["small", "medium", "large"], "required": False},
            "color": {"type": "string", "required": False},
            "backgroundColor": {"type": "string", "required": False},
            "borderColor": {"type": "string", "required": False},
            "borderWidth": {"type": "number", "required": False},
            "borderRadius": {"type": "number", "required": False},
            "placeholderColor": {"type": "string", "required": False},
            "focusStyle": {"type": "object", "required": False},
            "style": {"type": "object", "required": False},
        },
    },
    
    # 9. Spinner
    "Spinner": {
        "id": "feedback.spinner",
        "name": "Spinner",
        "displayName": "Spinner",
        "category": "feedback",
        "output_type": "Spinner",
        "aliases": ["Loader", "ActivityIndicator"],
        "required_imports": [{"name": "Spinner", "source": "tamagui"}],
        "resizable": False,
        "states": ["visible"],
        "default_props": {
            "size": "small",
            "visible": True,
            "color": "#007AFF",
        },
        "schema": {
            "size": {"type": "string", "enum": ["small", "large"], "required": False},
            "visible": {"type": "boolean", "required": False},
            "color": {"type": "string", "required": False},
            "style": {"type": "object", "required": False},
        },
    },
    
    # 10. Chart
    "Chart": {
        "id": "data.chart",
        "name": "Chart",
        "displayName": "Chart",
        "category": "data_viz",
        "output_type": "Chart",
        "aliases": ["Graph", "Plot"],
        "required_imports": [{"name": "ChartWidget", "source": "../utils/ChartWidget"}],
        "resizable": True,
        "default_props": {
            "type": "line",
            "values": [],
            "labels": [],
        },
        "schema": {
            "type": {"type": "string", "enum": ["line", "bar", "pie", "scatter"], "required": False},
            "values": {"type": "array", "required": False},
            "labels": {"type": "array", "required": False},
            "style": {"type": "object", "required": False},
        },
    },
    
    # 11. Image
    "Image": {
        "id": "media.image",
        "name": "Image",
        "displayName": "Image",
        "category": "media",
        "output_type": "Image",
        "aliases": ["Img", "Picture"],
        "required_imports": [{"name": "Image", "source": "react-native"}],
        "resizable": True,
        "default_props": {
            "source": "",
            "alt": "",
        },
        "schema": {
            "source": {"type": "string", "required": True},
            "alt": {"type": "string", "required": False},
            "style": {"type": "object", "required": False},
        },
    },
    
    # 12. Video
    "Video": {
        "id": "media.video",
        "name": "Video",
        "displayName": "Video",
        "category": "media",
        "output_type": "Video",
        "aliases": ["VideoPlayer"],
        "required_imports": [
            {"name": "VideoView", "source": "expo-video"},
            {"name": "useVideoPlayer", "source": "expo-video"},
        ],
        "resizable": True,
        "states": ["shouldPlay", "isLooping", "isMuted", "volume"],
        "default_props": {
            "source": "",
            "shouldPlay": False,
            "isLooping": False,
            "isMuted": False,
            "volume": 1.0,
            "resizeMode": "contain",
        },
        "schema": {
            "source": {"type": "string", "required": True},
            "shouldPlay": {"type": "boolean", "required": False},
            "isLooping": {"type": "boolean", "required": False},
            "isMuted": {"type": "boolean", "required": False},
            "volume": {"type": "number", "required": False},
            "resizeMode": {"type": "string", "enum": ["contain", "cover", "stretch"], "required": False},
            "style": {"type": "object", "required": False},
        },
    },
    
    # 13. Joystick
    "Joystick": {
        "id": "input.joystick",
        "name": "Joystick",
        "displayName": "Joystick",
        "category": "input",
        "output_type": "Joystick",
        "aliases": ["ControlStick"],
        "required_imports": [{"name": "Joystick", "source": "react-native-joystick-lite"}],
        "resizable": True,
        "states": ["x", "y", "distance", "angle", "isActive"],
        "default_props": {
            "size": 150,
            "color": "#007AFF",
            "haptics": True,
            "interval": 16,
        },
        "schema": {
            "size": {"type": "number", "required": False},
            "color": {"type": "string", "required": False},
            "haptics": {"type": "boolean", "required": False},
            "interval": {"type": "number", "required": False},
            "style": {"type": "object", "required": False},
        },
    },
    
    # 14. Slider
    "Slider": {
        "id": "input.slider",
        "name": "Slider",
        "displayName": "Slider",
        "category": "input",
        "output_type": "Slider",
        "aliases": ["Range"],
        "required_imports": [
            {"name": "Slider", "source": "tamagui"},
            {"name": "XStack", "source": "tamagui"},
        ],
        "resizable": False,
        "states": ["value"],
        "default_props": {
            "value": 50,
            "min": 0,
            "max": 100,
            "step": 1,
            "size": "medium",
            "trackColor": "#E0E0E0",
            "thumbColor": "#007AFF",
            "activeTrackColor": "#007AFF",
            "borderRadius": 8,
        },
        "schema": {
            "value": {"type": "number", "required": False},
            "min": {"type": "number", "required": True},
            "max": {"type": "number", "required": True},
            "step": {"type": "number", "required": False},
            "size": {"type": "string", "enum": ["small", "medium", "large"], "required": False},
            "trackColor": {"type": "string", "required": False},
            "thumbColor": {"type": "string", "required": False},
            "activeTrackColor": {"type": "string", "required": False},
            "borderRadius": {"type": "number", "required": False},
            "style": {"type": "object", "required": False},
        },
    },
    
    # 15. Progress_Bar
    "Progress_Bar": {
        "id": "feedback.progress",
        "name": "Progress_Bar",
        "displayName": "Progress Bar",
        "category": "feedback",
        "output_type": "Progress",
        "aliases": ["Progress"],
        "required_imports": [
            {"name": "Progress", "source": "tamagui"},
            {"name": "XStack", "source": "tamagui"},
            {"name": "Text", "source": "tamagui"},
        ],
        "resizable": False,
        "states": ["value"],
        "default_props": {
            "value": 0,
            "min": 0,
            "max": 100,
            "size": "medium",
            "backgroundColor": "#E0E0E0",
            "indicatorColor": "#007AFF",
            "borderRadius": 8,
        },
        "schema": {
            "value": {"type": "number", "required": False},
            "min": {"type": "number", "required": True},
            "max": {"type": "number", "required": True},
            "size": {"type": "string", "enum": ["small", "medium", "large"], "required": False},
            "backgroundColor": {"type": "string", "required": False},
            "indicatorColor": {"type": "string", "required": False},
            "borderRadius": {"type": "number", "required": False},
            "style": {"type": "object", "required": False},
        },
    },
    
    # 16. ToastAlert
    "ToastAlert": {
        "id": "feedback.toast",
        "name": "ToastAlert",
        "displayName": "Toast Alert",
        "category": "feedback",
        "output_type": "Toast",
        "aliases": ["Toast", "Snackbar"],
        "required_imports": [
            {"name": "Toast", "source": "@tamagui/toast"},
            {"name": "useToastState", "source": "@tamagui/toast"},
            {"name": "useToastController", "source": "@tamagui/toast"},
            {"name": "YStack", "source": "tamagui"},
        ],
        "resizable": True,
        "states": ["title", "description", "duration", "animation"],
        "default_props": {
            "title": "Notification",
            "description": "This is a toast message",
            "duration": 3000,
            "animation": "slide",
            "size": "medium",
            "opacity": 0.9,
            "scale": 1,
        },
        "schema": {
            "title": {"type": "string", "required": False},
            "description": {"type": "string", "required": False},
            "duration": {"type": "number", "required": False},
            "animation": {"type": "string", "enum": ["slide", "fade", "scale"], "required": False},
            "size": {"type": "string", "enum": ["small", "medium", "large"], "required": False},
            "opacity": {"type": "number", "required": False},
            "scale": {"type": "number", "required": False},
            "style": {"type": "object", "required": False},
        },
    },
    
    # 17. FilePickerInput
    "FilePickerInput": {
        "id": "input.file_picker",
        "name": "FilePickerInput",
        "displayName": "File Picker Input",
        "category": "input",
        "output_type": "FilePicker",
        "aliases": ["FileInput"],
        "required_imports": [
            {"name": "Image", "source": "react-native"},
            {"name": "TouchableOpacity", "source": "react-native"},
            {"name": "Linking", "source": "react-native"},
            {"name": "Modal", "source": "react-native"},
            {"name": "Text", "source": "tamagui"},
            {"name": "DocumentPicker", "source": "expo-document-picker"},
            {"name": "WebBrowser", "source": "expo-web-browser"},
        ],
        "resizable": False,
        "states": ["image", "file", "isPreviewing"],
        "default_props": {
            "placeholder": "Select a file...",
            "pickImageFile": True,
            "image": None,
            "file": None,
            "isPreviewing": False,
        },
        "schema": {
            "placeholder": {"type": "string", "required": False},
            "pickImageFile": {"type": "boolean", "required": False},
            "image": {"type": "any", "required": False},
            "file": {"type": "any", "required": False},
            "isPreviewing": {"type": "boolean", "required": False},
            "style": {"type": "object", "required": False},
        },
    },
    
    # 18. DatePicker
    "DatePicker": {
        "id": "form.date_picker",
        "name": "DatePicker",
        "displayName": "Date Picker",
        "category": "form",
        "output_type": "DatePicker",
        "aliases": ["DateInput"],
        "required_imports": [
            {"name": "Text", "source": "tamagui"},
            {"name": "Button", "source": "tamagui"},
        ],
        "resizable": True,
        "states": ["UTC_date", "SelectedDate"],
        "default_props": {
            "UTC_date": None,
            "SelectedDate": None,
            "size": "medium",
            "color": "#000000",
            "backgroundColor": "#FFFFFF",
            "borderColor": "#CCCCCC",
            "borderRadius": 8,
        },
        "schema": {
            "UTC_date": {"type": "any", "required": False},
            "SelectedDate": {"type": "any", "required": False},
            "size": {"type": "string", "enum": ["small", "medium", "large"], "required": False},
            "color": {"type": "string", "required": False},
            "backgroundColor": {"type": "string", "required": False},
            "borderColor": {"type": "string", "required": False},
            "borderRadius": {"type": "number", "required": False},
            "style": {"type": "object", "required": False},
        },
    },
    
    # 19. TimePicker
    "TimePicker": {
        "id": "form.time_picker",
        "name": "TimePicker",
        "displayName": "Time",
        "category": "form",
        "output_type": "TimePicker",
        "aliases": ["TimeInput"],
        "required_imports": [
            {"name": "Text", "source": "tamagui"},
            {"name": "Button", "source": "tamagui"},
        ],
        "resizable": True,
        "states": ["UTC_time", "SelectedTime"],
        "default_props": {
            "UTC_time": None,
            "SelectedTime": None,
            "size": "medium",
            "color": "#000000",
            "backgroundColor": "#FFFFFF",
            "borderColor": "#CCCCCC",
            "borderRadius": 8,
        },
        "schema": {
            "UTC_time": {"type": "any", "required": False},
            "SelectedTime": {"type": "any", "required": False},
            "size": {"type": "string", "enum": ["small", "medium", "large"], "required": False},
            "color": {"type": "string", "required": False},
            "backgroundColor": {"type": "string", "required": False},
            "borderColor": {"type": "string", "required": False},
            "borderRadius": {"type": "number", "required": False},
            "style": {"type": "object", "required": False},
        },
    },
    
    # 20. ColorPicker
    "ColorPicker": {
        "id": "form.color_picker",
        "name": "ColorPicker",
        "displayName": "Color",
        "category": "form",
        "output_type": "ColorPicker",
        "aliases": ["ColorInput"],
        "required_imports": [
            {"name": "Modal", "source": "react-native"},
            {"name": "TouchableWithoutFeedback", "source": "react-native"},
            {"name": "Pressable", "source": "react-native"},
            {"name": "Text", "source": "tamagui"},
        ],
        "resizable": True,
        "default_props": {},
        "schema": {
            "style": {"type": "object", "required": False},
        },
    },
    
    # 21. GoogleMap
    "GoogleMap": {
        "id": "location.map",
        "name": "GoogleMap",
        "displayName": "Map",
        "category": "location",
        "output_type": "Map",
        "aliases": ["Map"],
        "required_imports": [
            {"name": "View", "source": "react-native"},
            {"name": "TouchableOpacity", "source": "react-native"},
            {"name": "Text", "source": "react-native"},
            {"name": "SafeAreaView", "source": "react-native-safe-area-context"},
            {"name": "useMapController", "source": "../hooks/useMapController"},
            {"name": "MapUnit", "source": "../components/MapUnit"},
        ],
        "resizable": True,
        "default_props": {
            "latitude": 37.7749,
            "longitude": -122.4194,
            "wsUrl": "",
        },
        "schema": {
            "latitude": {"type": "number", "required": False},
            "longitude": {"type": "number", "required": False},
            "wsUrl": {"type": "string", "required": False},
            "style": {"type": "object", "required": False},
        },
    },
    
    # 22. LocalPushNotification
    "LocalPushNotification": {
        "id": "notifications.local",
        "name": "LocalPushNotification",
        "displayName": "Local Push Notification",
        "category": "notifications",
        "output_type": "Notification",
        "aliases": ["Notification"],
        "required_imports": [
            {"name": "setupAndroidChannel", "source": "../utils/LocalPushNotification"},
            {"name": "triggerNotification", "source": "../utils/LocalPushNotification"},
            {"name": "ensureNotificationPermission", "source": "../utils/LocalPushNotification"},
        ],
        "resizable": False,
        "default_props": {
            "title": "Notification",
            "body": "This is a notification",
            "subtitle": "",
            "sound": True,
            "badge": 1,
            "timeToLive": 86400,
            "priority": "high",
        },
        "schema": {
            "title": {"type": "string", "required": True},
            "body": {"type": "string", "required": True},
            "subtitle": {"type": "string", "required": False},
            "sound": {"type": "boolean", "required": False},
            "badge": {"type": "number", "required": False},
            "timeToLive": {"type": "number", "required": False},
            "priority": {"type": "string", "enum": ["high", "normal", "low"], "required": False},
            "style": {"type": "object", "required": False},
        },
    },
}


# ============================================================================
# COMPONENT CATEGORIES
# ============================================================================

COMPONENT_CATEGORIES: Dict[str, List[str]] = {
    "layout": ["Group", "Layout"],
    "input": ["Button", "Input_Text", "Switch", "Checkbox", "Text_Area", "Joystick", "Slider", "FilePickerInput"],
    "display": ["Text_Content", "Image", "Video"],
    "feedback": ["Spinner", "Progress_Bar", "ToastAlert"],
    "data_viz": ["Chart"],
    "media": ["Image", "Video"],
    "form": ["DatePicker", "TimePicker", "ColorPicker"],
    "location": ["GoogleMap"],
    "notifications": ["LocalPushNotification"],
}


# ============================================================================
# COMPONENT DEFAULT DIMENSIONS
# ============================================================================

COMPONENT_DEFAULT_DIMENSIONS: Dict[str, Tuple[int, int]] = {
    "Group": (375, 100),
    "Layout": (375, 100),
    "Button": (120, 44),
    "Text_Content": (200, 28),
    "Input_Text": (280, 44),
    "Switch": (72, 44),
    "Checkbox": (32, 32),
    "Text_Area": (280, 100),
    "Spinner": (32, 32),
    "Chart": (320, 220),
    "Image": (320, 240),
    "Video": (320, 240),
    "Joystick": (150, 150),
    "Slider": (280, 44),
    "Progress_Bar": (280, 12),
    "ToastAlert": (320, 80),
    "FilePickerInput": (280, 44),
    "DatePicker": (280, 44),
    "TimePicker": (280, 44),
    "ColorPicker": (280, 44),
    "GoogleMap": (375, 300),
    "LocalPushNotification": (0, 0),  # Not a visual component
}


# ============================================================================
# COMPONENT DEFAULT PROPERTIES (for quick access)
# ============================================================================

COMPONENT_DEFAULT_PROPERTIES: Dict[str, Dict[str, Any]] = {
    name: definition.get("default_props", {})
    for name, definition in COMPONENT_DEFINITIONS.items()
}


# ============================================================================
# COMPONENT EVENTS
# ============================================================================

COMPONENT_EVENT_BY_TYPE: Dict[str, str] = {
    "Button": "onPress",
    "Input_Text": "onChangeText",
    "Switch": "onValueChange",
    "Checkbox": "onCheckedChange",
    "Slider": "onValueChange",
    "Text_Area": "onChangeText",
    "Joystick": "onMove",
    "FilePickerInput": "onPickFile",
    "DatePicker": "onDateChange",
    "TimePicker": "onTimeChange",
    "ColorPicker": "onColorChange",
    "GoogleMap": "onMapPress",
}


# ============================================================================
# APP TEMPLATE COMPONENTS
# ============================================================================

APP_TEMPLATE_COMPONENTS: Dict[str, List[str]] = {
    "todo": ["Input_Text", "Button", "Checkbox", "Text_Content"],
    "counter": ["Text_Content", "Button", "Button"],
    "calculator": ["Text_Content", "Button", "Button", "Button", "Button"],
    "timer": ["Text_Content", "Button", "Button"],
    "notes": ["Input_Text", "Text_Area", "Button", "Text_Content"],
    "weather": ["Text_Content", "Image", "GoogleMap"],
    "drone": ["Joystick", "Video", "GoogleMap", "Text_Content"],
    "iot": ["Switch", "Slider", "Progress_Bar", "Text_Content"],
    "quiz": ["Text_Content", "Button", "Button", "Button", "Button"],
    "search": ["Input_Text", "Button", "Text_Content"],
    "form": ["Input_Text", "Input_Text", "Text_Area", "Button"],
    "media": ["Video", "Image", "Button"],
    "generic": ["Text_Content", "Button", "Input_Text"],
}


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _build_alias_index() -> Dict[str, str]:
    """Build index of all component aliases"""
    aliases: Dict[str, str] = {}
    for canonical, definition in COMPONENT_DEFINITIONS.items():
        aliases[canonical.lower()] = canonical
        for alias in definition.get("aliases", []):
            aliases[alias.lower()] = canonical
    return aliases


_COMPONENT_ALIAS_INDEX = _build_alias_index()


def get_component_definition(component_name: str) -> Optional[ComponentDefinition]:
    """Get full definition for a component"""
    canonical = normalize_component_type(component_name, fallback="")
    if not canonical:
        return None
    return deepcopy(COMPONENT_DEFINITIONS.get(canonical))


def get_available_components() -> List[str]:
    """Get list of all available component names"""
    return sorted(COMPONENT_DEFINITIONS.keys())


def get_components_by_category() -> Dict[str, List[str]]:
    """Get components grouped by category"""
    return deepcopy(COMPONENT_CATEGORIES)


def get_output_component_type(component_name: str) -> str:
    """Get the output type for a component"""
    definition = get_component_definition(component_name)
    if not definition:
        return component_name
    return definition.get("output_type", component_name)


def get_component_imports(component_name: str) -> List[ComponentImport]:
    """Get required imports for a component"""
    definition = get_component_definition(component_name)
    if not definition:
        return []
    return deepcopy(definition.get("required_imports", []))


def get_component_default_properties(component_name: str) -> Dict[str, Any]:
    """Get default properties for a component"""
    definition = get_component_definition(component_name)
    if not definition:
        return {}
    return deepcopy(definition.get("default_props", {}))


def get_component_states(component_name: str) -> List[str]:
    """Get state variables managed by this component"""
    definition = get_component_definition(component_name)
    if not definition:
        return []
    return deepcopy(definition.get("states", []))


def get_component_event(component_type: str) -> str:
    """Get the primary event for a component"""
    canonical = normalize_component_type(component_type, fallback="")
    return COMPONENT_EVENT_BY_TYPE.get(canonical, "")


def get_component_default_dimensions(component_type: str) -> Tuple[int, int]:
    """Get default dimensions for a component"""
    canonical = normalize_component_type(component_type)
    return COMPONENT_DEFAULT_DIMENSIONS.get(canonical, (280, 44))


def get_component_type_union_literal() -> str:
    """Get TypeScript union type string for all components"""
    members = " | ".join(f'"{name}"' for name in get_available_components())
    return members or '"Text_Content"'


def get_interactive_components() -> List[str]:
    """Get list of components that can handle user interaction"""
    interactive = []
    for comp in COMPONENT_EVENT_BY_TYPE.keys():
        if comp in COMPONENT_DEFINITIONS:
            interactive.append(comp)
    return sorted(interactive)


def get_template_components(template_name: str) -> List[str]:
    """Get component list for common app templates"""
    return deepcopy(APP_TEMPLATE_COMPONENTS.get(template_name.lower(), APP_TEMPLATE_COMPONENTS["generic"]))


def normalize_component_type(component_type: str, fallback: str = "Text_Content") -> str:
    """Normalize component name using alias index"""
    if not component_type:
        return fallback
    
    normalized = component_type.strip()
    if not normalized:
        return fallback
    
    # Try direct match in alias index
    canonical = _COMPONENT_ALIAS_INDEX.get(normalized.lower())
    if canonical:
        return canonical
    
    # Try fuzzy match if rapidfuzz is available
    try:
        from rapidfuzz import process
        available = list(COMPONENT_DEFINITIONS.keys())
        match = process.extractOne(normalized, available)
        if match and match[1] > 80:  # 80% similarity threshold
            return match[0]
    except ImportError:
        pass
    
    return fallback


def is_input_component(component_type: str) -> bool:
    """Check if component is an input type"""
    definition = get_component_definition(component_type)
    return bool(definition and definition.get("category") == "input")


def has_component_event(component_type: str, event_name: str) -> bool:
    """Check if component supports a specific event"""
    canonical = normalize_component_type(component_type, fallback="")
    if not canonical:
        return False
    
    # Check if component has this event in its schema
    definition = COMPONENT_DEFINITIONS.get(canonical, {})
    schema = definition.get("schema", {})
    
    # Check if event is in schema with type "event_handler"
    if event_name in schema:
        event_schema = schema[event_name]
        if isinstance(event_schema, dict) and event_schema.get("type") == "event_handler":
            return True
    
    # Check primary event map
    return COMPONENT_EVENT_BY_TYPE.get(canonical) == event_name


def export_component_catalog() -> Dict[str, Any]:
    """Export complete component catalog for debugging"""
    return {
        "components": deepcopy(COMPONENT_DEFINITIONS),
        "categories": deepcopy(COMPONENT_CATEGORIES),
        "aliases": deepcopy(_COMPONENT_ALIAS_INDEX),
        "interactive_components": get_interactive_components(),
        "template_components": deepcopy(APP_TEMPLATE_COMPONENTS),
        "default_dimensions": deepcopy(COMPONENT_DEFAULT_DIMENSIONS),
        "default_properties": deepcopy(COMPONENT_DEFAULT_PROPERTIES),
        "events": deepcopy(COMPONENT_EVENT_BY_TYPE),
    }
    
def get_component_by_category() -> Dict[str, List[str]]:
    """Get components grouped by category"""
    return deepcopy(COMPONENT_CATEGORIES)