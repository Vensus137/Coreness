"""
Access Validator - module for validating access to actions
"""

from typing import Any, Dict, List


class AccessValidator:
    """
    Access validator for actions
    """
    
    def __init__(self, **kwargs):
        self.logger = kwargs['logger']
        self.settings_manager = kwargs['settings_manager']
        
        self.groups = {}
        self.access_rules = {}
        
        # Load access configuration
        self._load_access_config()
    
    def _load_access_config(self):
        """Load groups and access rules from ActionHub settings"""
        try:
            # Get ActionHub plugin settings through settings_manager
            plugin_settings = self.settings_manager.get_plugin_settings('action_hub')
            
            # Load groups
            self.groups = plugin_settings.get('groups', {})
            
            # Load access rules
            self.access_rules = plugin_settings.get('access_rules', {})
            
            self.logger.info(f"AccessValidator: loaded groups: {list(self.groups.keys())}")
            self.logger.info(f"AccessValidator: loaded access rules: {list(self.access_rules.keys())}")
            
        except Exception as e:
            self.logger.error(f"AccessValidator: error loading access configuration: {e}")
            self.groups = {}
            self.access_rules = {}
    
    def validate_action_access(self, action_name: str, action_config: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate access to action based on its configuration"""
        try:
            access_rules = action_config.get('access_rules', [])
            
            # If no access rules - skip check
            if not access_rules:
                return {"result": "success"}
            
            # Execute all action rules
            for rule_name in access_rules:
                rule_result = self._execute_access_rule(rule_name, data)
                if rule_result.get("result") != "success":
                    return rule_result
            
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"Error validating access for action '{action_name}': {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Access validation error: {str(e)}"
                }
            }
    
    def _execute_access_rule(self, rule_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute specific access rule by name"""
        try:
            rule_config = self.access_rules.get(rule_name)
            if not rule_config:
                self.logger.warning(f"Rule {rule_name} not found in configuration")
                return {"result": "success"}
            
            # Unified structure: allowed_groups + check_fields
            allowed_groups = rule_config.get('allowed_groups', [])
            check_fields = rule_config.get('check_fields', [])
            
            # Universal access rule for all rules
            return self._check_universal_access(allowed_groups, check_fields, data)
                
        except Exception as e:
            self.logger.error(f"Error executing rule {rule_name}: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    def _check_universal_access(self, allowed_groups: List[str], check_fields: List[str], data: Dict[str, Any]) -> Dict[str, Any]:
        """Universal access check"""
        try:
            # If check_fields exist - check for data tampering
            if check_fields:
                return self._check_data_integrity(allowed_groups, check_fields, data)
            
            # If no check_fields - check only access groups
            system_data = data.get('system', {})
            return self._check_group_access(allowed_groups, system_data)
            
        except Exception as e:
            self.logger.error(f"Error in universal access check: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    def _check_group_access(self, allowed_groups: List[str], system_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check access by groups - check if system attributes match group requirements"""
        try:
            if not allowed_groups:
                return {"result": "success"}
            
            # Check each allowed group
            for group_name in allowed_groups:
                if group_name not in self.groups:
                    continue
                
                group_requirements = self.groups[group_name]
                group_matches = True
                
                # Check all group requirements
                for field_name, allowed_values in group_requirements.items():
                    field_value = system_data.get(field_name)
                    if field_value not in allowed_values:
                        group_matches = False
                        break
                
                # If group matches - access granted
                if group_matches:
                    return {"result": "success"}
            
            # No group matched
            return {
                "result": "error",
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": f"System data does not match requirements of any group: {allowed_groups}"
                }
            }
            
        except Exception as e:
            self.logger.error(f"Error checking group access: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }
    
    def _check_data_integrity(self, allowed_groups: List[str], check_fields: List[str], data: Dict[str, Any]) -> Dict[str, Any]:
        """Check data integrity (protection against tampering)"""
        try:
            if not check_fields:
                return {"result": "success"}
            
            # Check each field for tampering
            for field in check_fields:
                system_value = data.get('system', {}).get(field)
                public_value = data.get(field)
                
                if system_value is None:
                    continue  # Skip if system value is missing
                
                # If values don't match - check tampering rights through group_access
                if public_value != system_value:
                    # Use existing group check logic
                    access_result = self._check_group_access(allowed_groups, data.get('system', {}))
                    if access_result.get("result") != "success":
                        error_msg = access_result.get('error', {})
                        if isinstance(error_msg, dict):
                            error_msg = error_msg.get('message', '')
                        else:
                            error_msg = str(error_msg)
                        return {
                            "result": "error",
                            "error": {
                                "code": "PERMISSION_DENIED",
                                "message": f"Detected attempt to tamper with field {field} for {field}={system_value}. {error_msg}"
                            }
                        }
            
            return {"result": "success"}
            
        except Exception as e:
            self.logger.error(f"Error checking data integrity: {e}")
            return {
                "result": "error",
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": str(e)
                }
            }