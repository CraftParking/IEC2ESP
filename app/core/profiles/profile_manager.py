import json
import os
from typing import Dict, List, Optional, Tuple


class ProfileValidationError(Exception):
    """Raised when a profile fails validation."""
    pass


class ProfileManager:
    """Manages controller profiles with validation and safe loading."""
    
    def __init__(self, profiles_dir: str):
        self.profiles_dir = profiles_dir
        self.loaded_profiles: Dict[str, dict] = {}
        self._load_builtin_profiles()
    
    def _load_builtin_profiles(self) -> None:
        """Load built-in profiles that are always available."""
        builtin_files = [
            "esp32.json",
            "xiao-esp32s3.json",
            "xiao-esp32c6.json",
            "xiao-esp32c5.json",
            "cyd.json",
            "custom.json",
        ]
        
        for filename in builtin_files:
            filepath = os.path.join(self.profiles_dir, filename)
            if os.path.exists(filepath):
                try:
                    profile = self.load_profile(filepath)
                    if profile:
                        profile_name = profile.get("name", filename.replace(".json", ""))
                        self.loaded_profiles[profile_name] = profile
                except ProfileValidationError:
                    continue
    
    def validate_profile(self, profile: dict) -> Tuple[bool, Optional[str]]:
        """
        Validate a profile structure.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required top-level fields
        if "name" not in profile:
            return False, "Profile missing 'name' field"
        
        if not isinstance(profile["name"], str) or not profile["name"].strip():
            return False, "Profile 'name' must be a non-empty string"
        
        # Check if it's a pin-based profile (like ESP32) or simple profile (like Custom)
        if "pins" in profile:
            # Pin-based profile validation
            if "pin_count" not in profile:
                return False, "Pin-based profile missing 'pin_count' field"
            
            if not isinstance(profile["pin_count"], int) or profile["pin_count"] <= 0:
                return False, "Profile 'pin_count' must be a positive integer"
            
            if not isinstance(profile["pins"], list):
                return False, "Profile 'pins' must be an array"
            
            # Validate each pin
            for pin in profile["pins"]:
                if "pin" not in pin:
                    return False, "Pin entry missing 'pin' field"
                
                if not isinstance(pin["pin"], int) or pin["pin"] < 0:
                    return False, f"Pin 'pin' must be a non-negative integer (got {pin.get('pin')})"
                
                # Must have either 'allowed_types', 'type', or 'capabilities'
                if "allowed_types" not in pin and "type" not in pin and "capabilities" not in pin:
                    return False, f"Pin {pin['pin']} must have 'allowed_types', 'type', or 'capabilities' field"
                
                # If allowed_types exists, validate it
                if "allowed_types" in pin:
                    if not isinstance(pin["allowed_types"], list):
                        return False, f"Pin {pin['pin']} 'allowed_types' must be an array"
                    
                    if not pin["allowed_types"]:
                        return False, f"Pin {pin['pin']} 'allowed_types' cannot be empty"
                
                # If capabilities exists, validate it (new capability-based format)
                if "capabilities" in pin:
                    if not isinstance(pin["capabilities"], list):
                        return False, f"Pin {pin['pin']} 'capabilities' must be an array"
                
                # Validate flags if present
                if "flags" in pin:
                    if not isinstance(pin["flags"], list):
                        return False, f"Pin {pin['pin']} 'flags' must be an array"
                
                # Validate pull_support if present (legacy format)
                if "pull_support" in pin:
                    if not isinstance(pin["pull_support"], bool):
                        return False, f"Pin {pin['pin']} 'pull_support' must be a boolean"
        
        elif "allowed_types" in profile:
            # Simple profile validation (like Custom)
            if not isinstance(profile["allowed_types"], list):
                return False, "Profile 'allowed_types' must be an array"
            
            if not profile["allowed_types"]:
                return False, "Profile 'allowed_types' cannot be empty"
            
            # Validate pull_support if present
            if "pull_support" in profile:
                if not isinstance(profile["pull_support"], bool):
                    return False, "Profile 'pull_support' must be a boolean"
        else:
            return False, "Profile must have either 'pins' or 'allowed_types' field"
        
        return True, None
    
    def load_profile(self, filepath: str) -> Optional[dict]:
        """
        Load and validate a profile from a JSON file.
        
        Args:
            filepath: Path to the JSON profile file
            
        Returns:
            Profile dictionary if valid, None otherwise
            
        Raises:
            ProfileValidationError: If profile fails validation
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                profile = json.load(f)
        except json.JSONDecodeError as e:
            raise ProfileValidationError(f"Invalid JSON: {e}")
        except IOError as e:
            raise ProfileValidationError(f"Cannot read file: {e}")
        
        is_valid, error_msg = self.validate_profile(profile)
        if not is_valid:
            raise ProfileValidationError(f"Validation failed: {error_msg}")
        
        return profile
    
    def import_profile(self, filepath: str) -> Tuple[bool, Optional[str], Optional[dict]]:
        """
        Import a profile from a file and add to loaded profiles.
        
        Args:
            filepath: Path to the JSON profile file
            
        Returns:
            Tuple of (success, error_message, profile)
        """
        try:
            profile = self.load_profile(filepath)
            profile_name = profile.get("name", os.path.basename(filepath).replace(".json", ""))
            
            # Check if profile with same name already exists
            if profile_name in self.loaded_profiles:
                return False, f"Profile '{profile_name}' already exists", None
            
            self.loaded_profiles[profile_name] = profile
            return True, None, profile
        except ProfileValidationError as e:
            return False, str(e), None
    
    def get_profile(self, name: str) -> Optional[dict]:
        """Get a loaded profile by name."""
        return self.loaded_profiles.get(name)
    
    def get_all_profiles(self) -> Dict[str, dict]:
        """Get all loaded profiles."""
        return self.loaded_profiles.copy()
    
    def get_profile_names(self) -> List[str]:
        """Get list of all loaded profile names."""
        return list(self.loaded_profiles.keys())
