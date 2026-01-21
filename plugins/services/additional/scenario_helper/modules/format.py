"""
Format Module - formatting structured data to text format
"""

import re
from typing import Any, Dict, List, Optional


class DataFormatter:
    """
    Class for formatting structured data to text format
    """
    
    def __init__(self, logger):
        self.logger = logger
    
    async def format_data_to_text(self, data: dict) -> Dict[str, Any]:
        """
        Format structured data to text format
        """
        try:
            format_type = data.get('format_type')
            input_data = data.get('input_data')
            title = data.get('title')
            item_template = data.get('item_template')
            
            if not format_type:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Format type (format_type) not specified. Available: list, structured"
                    }
                }
            
            if input_data is None:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "Array of elements for formatting (input_data) not specified"
                    }
                }
            
            # Check that input_data is an array
            if not isinstance(input_data, list):
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": "input_data must be an array"
                    }
                }
            
            # Choose formatter
            if format_type == "list":
                if not item_template:
                    return {
                        "result": "error",
                        "error": {
                            "code": "VALIDATION_ERROR",
                            "message": "For 'list' format item template (item_template) is required"
                        }
                    }
                formatted_text = self._format_list(input_data, title, item_template)
            elif format_type == "structured":
                formatted_text = self._format_structured(input_data, title)
            else:
                return {
                    "result": "error",
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": f"Unknown format type: {format_type}. Available: list, structured"
                    }
                }
            
            # Form response_data
            response_data = {
                "formatted_text": formatted_text
            }
            
            return {
                "result": "success",
                "response_data": response_data
            }
            
        except Exception as e:
            self.logger.error(f"Error formatting data: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    def _format_list(self, items: List[Dict[str, Any]], title: Optional[str], item_template: str) -> str:
        """
        Format simple list of elements
        """
        lines = []
        
        # Add title if specified
        if title:
            lines.append(title)
        
        # Format each element
        for item in items:
            if not isinstance(item, dict):
                self.logger.warning(f"Skipped element that is not an object: {item}")
                continue
            
            # Replace placeholders via $ with values from item
            formatted_item = self._apply_template(item_template, item)
            lines.append(formatted_item)
        
        return "\n".join(lines)
    
    def _format_structured(self, items: List[Dict[str, Any]], title: Optional[str]) -> str:
        """
        Format structured list with headers, subheaders and nested blocks
        """
        lines = []
        
        # Add general title if specified
        if title:
            lines.append(title)
        
        # Format each element
        for item in items:
            if not isinstance(item, dict):
                self.logger.warning(f"Skipped element that is not an object: {item}")
                continue
            
            # Element header: name - description (on one line)
            item_name = item.get('name') or item.get('id')
            description = item.get('description')
            
            if item_name and description:
                lines.append(f"{item_name} — {description}")
            elif item_name:
                lines.append(item_name)
            elif description:
                lines.append(description)
            
            # Parameters block (if exists)
            parameters = item.get('parameters')
            if parameters and isinstance(parameters, dict):
                lines.append("  Parameters:")
                
                for param_name, param_info in parameters.items():
                    if isinstance(param_info, dict):
                        param_type = param_info.get('type', 'unknown')
                        param_desc = param_info.get('description', '')
                        param_default = param_info.get('default')
                        param_optional = param_info.get('optional', False)
                        
                        # Format parameter: - param_name (type) (optional) - description. Default: default
                        param_line = f"  - {param_name} ({param_type})"
                        if param_optional:
                            param_line += " (optional)"
                        if param_desc:
                            param_line += f" — {param_desc}"
                        if param_default is not None:
                            param_line += f". Default: {param_default}"
                        lines.append(param_line)
                    else:
                        # Simple parameter without details
                        lines.append(f"  - {param_name}")
            
            # Empty line between elements
            lines.append("")
        
        # Remove last empty line
        if lines and lines[-1] == "":
            lines.pop()
        
        return "\n".join(lines)
    
    def _apply_template(self, template: str, data: Dict[str, Any]) -> str:
        """
        Apply template with placeholders via $ to data
        """
        result = template
        
        # Find all placeholders via $ (e.g., $id, $description)
        # Support simple keys: $key
        pattern = r'\$(\w+)'
        
        def replace_placeholder(match):
            key = match.group(1)
            value = data.get(key, '')
            # If value is string, return as is, otherwise convert to string
            return str(value) if value is not None else ''
        
        result = re.sub(pattern, replace_placeholder, result)
        
        return result
