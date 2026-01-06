"""策略配置加载器模块。

该模块负责从配置文件加载策略配置，并根据配置动态导入策略类。
"""

import importlib
import tomllib


class StrategyConfig:
    """策略配置类，用于加载和管理交易策略配置。

    该类从TOML配置文件中读取策略配置信息，并提供动态加载策略类的功能。

    Attributes:
        config: 从配置文件中加载的策略配置字典
    """

    def __init__(self) -> None:
        """初始化策略配置加载器。

        Raises:
            FileNotFoundError: 当配置文件不存在时抛出
            tomllib.TOMLDecodeError: 当配置文件格式错误时抛出
        """
        with open("config/strategy_config.toml", "rb") as f:
            self.config = tomllib.load(f)

    def get_strategy(self, name: str | None = None) -> tuple[type, dict]:
        """获取指定名称的策略类和参数。

        Args:
            name: 策略名称，如果为None则使用默认策略"MACD"

        Returns:
            包含策略类和参数字典的元组

        Raises:
            ValueError: 当策略不存在或配置信息不完整时抛出
            ImportError: 当无法导入策略模块时抛出
            AttributeError: 当策略类不存在时抛出
        """
        if name is None:
            # 默认取第一个策略
            name = "MACD"

        strategy_info = self.config.get(name)
        if not strategy_info:
            raise ValueError(f"没有策略 '{name}' ")

        module_name = strategy_info.get("module")
        class_name = strategy_info.get("class")
        params = strategy_info.get("params", {})

        if not module_name or not class_name:
            raise ValueError(f"策略 '{name}' 缺少模块或类名信息")

        module = importlib.import_module(module_name)
        strategy_class = getattr(module, class_name)

        return strategy_class, params
