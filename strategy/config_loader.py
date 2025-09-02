import tomllib
import importlib
from typing import Tuple, Type

class StrategyConfig:
    def __init__(self):
        with open("config/strategy_config.toml", 'rb') as f:
            self.config = tomllib.load(f)
        
    def get_strategy(self, name: str | None = None) -> Tuple[Type, dict]:
        if name is None:
            # 默认取第一个策略
            name = "MACD"
        
        strategy_info = self.config.get(name)
        if not strategy_info:
            raise ValueError(f"没有策略 '{name}' ")
        
        module_name = strategy_info.get('module')
        class_name = strategy_info.get('class')
        params = strategy_info.get('params', {})
        
        if not module_name or not class_name:
            raise ValueError(f"策略 '{name}' 缺少模块或类名信息")
        
        module = importlib.import_module(module_name)
        strategy_class = getattr(module, class_name)
        
        return strategy_class, params