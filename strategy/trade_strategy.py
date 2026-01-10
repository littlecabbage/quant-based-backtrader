from abc import abstractmethod

import backtrader as bt
from prettytable import PrettyTable


class TradeStrategy(bt.Strategy):
    strategy_name: str | None = None  # 用于标识策略名称(可选)

    def __init__(self, **params) -> None:
        """
        在这里初始化信号和策略参数。
        """
        super().__init__()
        # 存储每日交易数据，使用字典列表
        self.daily_trade_data: list[dict] = []

    @abstractmethod
    def next(self) -> None:
        """
        在这里实现策略的逻辑。

        步骤：
        1. 获取必要数据（-1表示前一交易日）。例：
            prev_close = self.data.close[-1]
            prev_sma = self.sma[-1]
            prev_diff = self.diff[-1]
        2. 计算信号。例：
            # 开仓信号
            condition1 = prev_close < prev_sma
            condition2 = prev_volume > prev_volume_avg
            long_signal = all([condition1, condition2])
            # 平仓信号
            exit_condition1 = prev_close > prev_sma
            exit_condition2 = prev_volume < prev_volume_avg
            exit_signal = all([exit_condition1, exit_condition2])
        3. 执行交易。例：
            if not self.position:
                if long_signal and self.order is None:
                    self.order = self.buy()  # 默认使用全部可用资金
            else:
                if exit_signal and self.order is None:
                    self.order = self.close()  # 平仓
        """
        pass

    def notify_order(self, order) -> None:
        """
        获取订单状态，这个函数一般无须重写。
        """
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f"买入成交, 价格: {order.executed.price:.2f}, 成本: {order.executed.value:.2f}, 佣金 {order.executed.comm:.2f}"
                )
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(
                    f"卖出成交, 价格: {order.executed.price:.2f}, 成本: {order.executed.value:.2f}, 佣金 {order.executed.comm:.2f}"
                )
                self.bar_executed = len(self)
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log("订单取消 / 保证金不足 / 拒绝")
        self.order = None

    def notify_trade(self, trade) -> None:
        """
        追踪每笔交易的状态，这个函数一般无须重写。
        """
        if not trade.isclosed:
            return
        self.log(f"交易利润, 毛利润 {trade.pnl:.2f}, 净利润 {trade.pnlcomm:.2f}")

    def add_daily_data(self, date=None, data=None) -> None:
        """
        添加每日交易数据

        Args:
            date: 交易日期，默认为当前日期
            data: 交易数据字典，包含当日的各项指标和条件
        """
        # 准备完整的每日数据字典
        daily_data = {}

        # 设置日期
        daily_data["日期"] = str(date or self.datas[0].datetime.date(0))

        # 添加用户提供的数据
        if data:
            daily_data.update(data)

        # 添加持仓和订单状态
        daily_data["持仓大小"] = self.position.size
        daily_data["订单状态"] = str(self.order) if self.order else "None"

        self.daily_trade_data.append(daily_data)

    def _parse_trade_data(self) -> PrettyTable | None:
        """
        解析交易数据，生成PrettyTable表格

        Returns:
            Optional[PrettyTable]: 生成的交易数据表格，若没有数据则返回None
        """
        if not self.daily_trade_data:
            return None

        # 获取所有数据的键集合，作为表头
        all_keys: set[str] = set()
        for data in self.daily_trade_data:
            all_keys.update(data.keys())

        # 将日期放在第一个位置，其余按键名排序
        headers = ["日期"]
        other_keys = sorted(all_keys - {"日期"})
        headers.extend(other_keys)

        # 创建表格
        table = PrettyTable()
        table.field_names = headers

        # 设置对齐方式
        table.align["日期"] = "l"
        for header in headers[1:]:
            table.align[header] = "r"

        # 添加数据行
        for data in self.daily_trade_data:
            row = [data.get(header, "-") for header in headers]
            table.add_row(row)

        return table

    def stop(self) -> None:
        """
        策略结束时调用，打印交易结果汇总表格
        """
        if not self.daily_trade_data:
            self.log("没有数据可生成汇总表格", doprint=True)
            return

        # 生成表格
        table = self._parse_trade_data()

        # 打印汇总表格
        self.log(
            f"\n=== 策略执行汇总表格 ({self.strategy_name}) ===\n{table}", doprint=True
        )
        self.log(f"总计交易天数: {len(self.daily_trade_data)}", doprint=True)

    def log(self, txt, dt=None, doprint=False) -> None:
        """
        保存日志
        """
        if doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print(f"{dt.isoformat()}, {txt}")
