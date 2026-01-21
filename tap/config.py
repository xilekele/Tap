"""配置管理模块"""

import os
import json
from pathlib import Path
from typing import Optional

DEFAULT_CONFIG_FILE = Path.home() / ".tap" / "config.json"

class Config:
    """配置管理类"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or DEFAULT_CONFIG_FILE
        self._config = {}
        self._load()
    
    def _load(self) -> None:
        """加载配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except Exception:
                self._config = {}
    
    def save(self) -> None:
        """保存配置"""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, ensure_ascii=False, indent=2)
    
    @property
    def app_id(self) -> Optional[str]:
        return self._config.get("APP_ID")
    
    @app_id.setter
    def app_id(self, value: str):
        self._config["APP_ID"] = value
    
    @property
    def app_secret(self) -> Optional[str]:
        return self._config.get("APP_SECRET")
    
    @app_secret.setter
    def app_secret(self, value: str):
        self._config["APP_SECRET"] = value
    
    @property
    def app_token(self) -> Optional[str]:
        return self._config.get("app_token")
    
    @app_token.setter
    def app_token(self, value: str):
        self._config["app_token"] = value
    
    @property
    def tenant_access_token(self) -> Optional[str]:
        return self._config.get("tenant_access_token")
    
    @tenant_access_token.setter
    def tenant_access_token(self, value: str):
        self._config["tenant_access_token"] = value
    
    @property
    def tenant_access_token_expires_at(self) -> Optional[int]:
        return self._config.get("tenant_access_token_expires_at")
    
    @tenant_access_token_expires_at.setter
    def tenant_access_token_expires_at(self, value: int):
        self._config["tenant_access_token_expires_at"] = value
    
    def get(self, key: str, default=None):
        """获取配置项"""
        return self._config.get(key, default)
    
    def set(self, key: str, value):
        """设置配置项"""
        self._config[key] = value
    
    def is_configured(self) -> bool:
        """检查是否已配置"""
        return bool(self.app_id and self.app_secret)

# 全局配置实例
_default_config: Optional[Config] = None

def get_config(config_path: Optional[Path] = None) -> Config:
    """获取全局配置实例"""
    global _default_config
    if _default_config is None:
        _default_config = Config(config_path)
    return _default_config

def reset_config():
    """重置配置"""
    global _default_config
    _default_config = None
