"""
Keyboard Builder - builds keyboards from templates
"""

from typing import Any, Dict, List


class KeyboardBuilder:
    """Builds inline/reply keyboards from item arrays using templates"""
    
    def __init__(self, default_buttons_per_row: int, logger):
        self.default_buttons_per_row = default_buttons_per_row
        self.logger = logger
    
    def build(self, data: dict) -> Dict[str, Any]:
        """
        Build keyboard from items array
        
        Args:
            items: array of IDs
            keyboard_type: 'inline' or 'reply'
            text_template: template with $value$ placeholder
            callback_template: template for inline keyboards (required for inline)
            buttons_per_row: buttons per row (optional, default from settings)
        
        Returns:
            {result: "success", response_data: {keyboard, keyboard_type, rows_count, buttons_count}}
        """
        try:
            items = data.get('items')
            keyboard_type = data.get('keyboard_type')
            text_template = data.get('text_template')
            callback_template = data.get('callback_template')
            buttons_per_row = data.get('buttons_per_row', self.default_buttons_per_row)
            
            # Validation
            if not items:
                return self._error("VALIDATION_ERROR", "items is required")
            
            if not keyboard_type:
                return self._error("VALIDATION_ERROR", "keyboard_type is required")
            
            if not text_template:
                return self._error("VALIDATION_ERROR", "text_template is required")
            
            if keyboard_type == 'inline' and not callback_template:
                return self._error("VALIDATION_ERROR", "callback_template required for inline keyboard")
            
            # Build keyboard
            keyboard = []
            current_row = []
            
            for item_id in items:
                button = self._create_button(
                    item_id,
                    text_template,
                    callback_template,
                    keyboard_type
                )
                
                current_row.append(button)
                
                # Add row if full
                if len(current_row) >= buttons_per_row:
                    keyboard.append(current_row)
                    current_row = []
            
            # Add remaining buttons
            if current_row:
                keyboard.append(current_row)
            
            return {
                "result": "success",
                "response_data": {
                    "keyboard": keyboard,
                    "keyboard_type": keyboard_type,
                    "rows_count": len(keyboard),
                    "buttons_count": len(items)
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error building keyboard: {e}")
            return self._error("INTERNAL_ERROR", str(e))
    
    def _create_button(self, item_id, text_template, callback_template, keyboard_type):
        """Create single button"""
        text = str(text_template).replace('$value$', str(item_id))
        
        if keyboard_type == 'inline':
            callback = str(callback_template).replace('$value$', str(item_id))
            return {text: callback}
        else:  # reply
            return text
    
    def _error(self, code: str, message: str) -> Dict[str, Any]:
        """Helper to create error response"""
        return {
            "result": "error",
            "error": {"code": code, "message": message}
        }
