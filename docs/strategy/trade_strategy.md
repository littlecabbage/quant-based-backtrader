# TradeStrategy 类说明

## 1. 类概述

`TradeStrategy` 是一个基于 `backtrader.Strategy` 的抽象基类，为量化交易策略提供了统一的框架和基础功能。该类旨在简化策略开发流程，让开发者能够专注于策略逻辑本身，而不是复杂的工程实现。

### 核心功能

- 提供统一的数据收集机制
- 支持动态生成交易结果汇总表格
- 封装了订单通知和交易通知的处理逻辑
- 提供标准化的日志记录功能

## 2. 类定义

```python
class TradeStrategy(bt.Strategy):
    strategy_name: str | None = None  # 用于标识策略名称(可选)

    def __init__(self, **params) -> None:
        # 初始化逻辑
        pass

    @abstractmethod
    def next(self) -> None:
        # 策略逻辑实现
        pass
```

## 3. 类属性

| 属性名 | 类型 | 说明 |
|--------|------|------|
| `strategy_name` | `str` 或 `None` | 策略名称，用于标识不同的策略，可选 |
| `daily_trade_data` | `list[dict]` | 存储每日交易数据的列表，每个元素是一个包含当日各项指标和条件的字典 |
| `order` | `backtrader.Order` 或 `None` | 当前订单状态，用于跟踪订单执行情况 |

## 4. 类方法

### 4.1 初始化方法

```python
def __init__(self, **params) -> None:
    """
    初始化策略参数和属性

    Args:
        **params: 策略参数，由子类根据需要定义和使用
    """
```

### 4.2 抽象方法

```python
@abstractmethod
def next(self) -> None:
    """
    策略逻辑实现方法，子类必须重写

    该方法在每个交易日被调用，用于实现策略的核心逻辑，包括：
    1. 获取交易数据
    2. 计算交易信号
    3. 执行交易操作
    """
```

### 4.3 数据收集方法

```python
def add_daily_data(self, date=None, data=None) -> None:
    """
    添加每日交易数据

    Args:
        date: 交易日期，默认为当前日期
        data: 交易数据字典，包含当日的各项指标和条件
            - 示例：`{"收盘价": 100.0, "MA值": 99.5, "买入信号": True}`
    """
```

### 4.4 数据解析方法

```python
def _parse_trade_data(self) -> PrettyTable:
    """
    解析交易数据，生成PrettyTable表格

    Returns:
        PrettyTable: 生成的交易数据表格，若没有数据则返回None
    """
```

### 4.5 策略结束方法

```python
def stop(self) -> None:
    """
    策略结束时调用，打印交易结果汇总表格

    该方法在策略回测或实盘结束时被调用，用于生成和打印交易结果汇总表格
    """
```

### 4.6 订单通知方法

```python
def notify_order(self, order) -> None:
    """
    获取订单状态通知

    Args:
        order: 订单对象，包含订单的状态、价格、成本等信息
    """
```

### 4.7 交易通知方法

```python
def notify_trade(self, trade) -> None:
    """
    追踪每笔交易的状态

    Args:
        trade: 交易对象，包含交易的利润、佣金等信息
    """
```

### 4.8 日志记录方法

```python
def log(self, txt, dt=None, doprint=False) -> None:
    """
    保存日志

    Args:
        txt: 日志文本内容
        dt: 日志日期，默认为当前日期
        doprint: 是否打印日志，默认为False
    """
```

## 5. 使用示例

### 5.1 创建自定义策略

```python
from strategy.trade_strategy import TradeStrategy

class MyStrategy(TradeStrategy):
    strategy_name = "MY_STRATEGY"

    def __init__(self, **params) -> None:
        super().__init__(**params)
        # 初始化策略参数和指标
        self.ma = bt.indicators.SimpleMovingAverage(self.data.close, period=15)

    def next(self) -> None:
        # 获取必要数据
        prev_close = self.data.close[-1]
        prev_ma = self.ma[-1]

        # 计算交易信号
        buy_signal = prev_close > prev_ma

        # 收集每日数据
        self.add_daily_data(
            data={
                "收盘价": prev_close,
                "MA值": prev_ma,
                "买入信号": buy_signal
            }
        )

        # 执行交易
        if buy_signal and not self.position and self.order is None:
            self.order = self.buy()
```

### 5.2 运行策略

```python
import backtrader as bt
from strategy.my_strategy import MyStrategy

# 创建回测引擎
cerebro = bt.Cerebro()

# 添加数据
# ... 数据添加逻辑 ...

# 添加策略
cerebro.addstrategy(MyStrategy)

# 运行回测
cerebro.run()

# 策略结束时会自动调用stop方法，打印汇总表格
```

## 6. 继承关系

```
backtrader.Strategy
    ↓
TradeStrategy (抽象基类)
    ↓
具体策略实现类（如MACDStrategy、MyStrategy等）
```

## 7. 使用注意事项

1. **抽象方法实现**：所有继承自 `TradeStrategy` 的子类必须实现 `next` 方法，否则会抛出 `TypeError`。

2. **数据收集**：在 `next` 方法中，建议使用 `add_daily_data` 方法收集每日交易数据，以便在策略结束时生成完整的汇总表格。

3. **策略名称**：建议为每个具体策略设置 `strategy_name` 属性，以便在汇总表格中区分不同的策略。

4. **日志记录**：使用 `log` 方法记录重要的交易事件和信息，便于调试和分析策略。

5. **订单管理**：在策略中管理好 `order` 属性，避免重复下单。

## 8. 输出示例

策略结束时，`stop` 方法会生成类似以下的汇总表格：

```
=== 策略执行汇总表格 (MY_STRATEGY) ===
+------------+--------+-------+--------+--------+
| 日期       | 收盘价 | MA值  | 买入信号 | 持仓大小 |
+------------+--------+-------+--------+--------+
| 2024-01-01 | 100.00 | 99.50 | True   | 0      |
| 2024-01-02 | 101.00 | 100.00 | True   | 100    |
| 2024-01-03 | 99.00  | 100.10 | False  | 100    |
+------------+--------+-------+--------+--------+
总计交易天数: 3
```

## 9. 版本历史

- **v0.1.0**：初始版本，提供基本的策略框架和功能
- **v0.2.0**：添加了数据收集和汇总表格生成功能
- **v0.3.0**：优化了表格生成逻辑，支持动态表头

## 10. 贡献者

- 开发团队：backtrader_trading 项目团队

## 11. 联系方式

- 项目地址：[GitHub 仓库链接]
- 文档地址：[项目文档链接]

## 12. 许可证

- 许可证：MIT License

---

以上就是 `TradeStrategy` 类的详细说明文档。该类为量化交易策略提供了统一的框架和基础功能，便于开发者快速开发和测试自己的交易策略。
