
import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

SETTINGS_FILE = "settings.json"

class SettingsManager:
    def __init__(self):
        self._settings: Dict[str, Any] = {}
        self._load_settings()

    def _load_settings(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    self._settings = json.load(f)
                logger.info(f"Loaded settings from {SETTINGS_FILE}")
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
        
        # Apply to environment variables immediately upon load
        if "zhipu_api_key" in self._settings:
            os.environ["ZHIPU_API_KEY"] = self._settings["zhipu_api_key"]
            logger.info("Updated ZHIPU_API_KEY from settings")
            
        if "zhipu_model" in self._settings:
            os.environ["ZHIPU_MODEL"] = self._settings["zhipu_model"]
            logger.info(f"Updated ZHIPU_MODEL from settings: {self._settings['zhipu_model']}")

    def _save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved settings to {SETTINGS_FILE}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def get_setting(self, key: str, default=None):
        return self._settings.get(key, default)

    def set_setting(self, key: str, value: Any):
        self._settings[key] = value
        self._save_settings()
        
        # Specific handling for known keys
        if key == "zhipu_api_key":
            os.environ["ZHIPU_API_KEY"] = str(value)
            logger.info("Updated ZHIPU_API_KEY in environment")
        elif key == "zhipu_model":
            os.environ["ZHIPU_MODEL"] = str(value)
            logger.info(f"Updated ZHIPU_MODEL to {value} in environment")

settings_manager = SettingsManager()
