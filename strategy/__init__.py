# 策略模块包初始化文件

from .macd_strategy import MACDStrategy
from .trade_strategy import TradeStrategy

__all__ = ["TradeStrategy", "MACDStrategy"]
