import numpy as np
import backtrader as bt

class MACDStrategy(bt.Strategy):
    name = "MACD"

    def __init__(self, **params) -> None:
        
        super().__init__()
        default_params = {
            "ma_period": 15,
            "macd_fast": 30,
            "macd_slow": 50,
            "macd_signal": 6,
            "atr_period": 5,
            "zscore_threshold": 1.5,
        }
        self.params_dict = {**default_params, **(params or {})}

        # 指标计算
        self.ma15 = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params_dict["ma_period"]
        )
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params_dict["macd_fast"],
            period_me2=self.params_dict["macd_slow"],
            period_signal=self.params_dict["macd_signal"]
        )
        self.atr = bt.indicators.ATR(
            self.data, period=self.params_dict["atr_period"]
        )
        self.diff = self.macd.macd  # MACD线
        self.dea = self.macd.signal  # 信号线

        # 存储最近5根Bar的峰值检测数据
        self.high_window = bt.indicators.Highest(self.data.high, period=3)
        self.peak_detected = False
        
        # 交易状态跟踪
        self.order = None

    def next(self) -> None:
        
        # 获取必要数据（-1表示前一交易日）
        prev_close = self.data.close[-1]
        prev_volume = self.data.volume[-1]
        prev_ma15 = self.ma15[-1]
        prev_diff = self.diff[-1]
        prev_dea = self.dea[-1]
        prev_atr = self.atr[-1]

        # --- 开仓条件 ---
        condition1 = prev_close < prev_ma15                     # 收盘价低于MA15
        condition2 = prev_diff < 0                              # MACD差值<0（水下）
        # 水下金叉：放宽为当前处于水下且 diff > dea，不强制要求严格穿越
        condition3 = (prev_diff > prev_dea)
        
        # 成交量条件：今日量 > 过去2日平均量
        volume_avg2 = (self.data.volume[-2] + self.data.volume[-3]) / 2.0
        condition4 = prev_volume > volume_avg2

        long_signal = all([condition1, condition2, condition3, condition4])

        # --- 平仓条件 ---
        # 条件1: 收盘价 > MA15 + 0.5*ATR
        exit_condition1 = self.data.close[0] > self.ma15[0] + 0.5 * self.atr[0]
        
        # 条件2: 在 iloc[-5:-2] 区间（不含当前bar）是否存在局部峰值
        if len(self.data) >= 6:
            highs = np.array([
                self.data.high[-5],
                self.data.high[-4],
                self.data.high[-3]
            ])
            # 任意局部峰值：高于左右相邻（窗口内的内部点才具备左右）
            # 这里窗口长度为3，只有中间点可成为峰值
            self.peak_detected = (highs[1] > highs[0]) and (highs[1] > highs[2])
        exit_condition2 = self.peak_detected
        
        # 条件3: Bar的一阶导数为负（解释为价格短期下降）
        # 说明：使用当前Bar vs 前1Bar的收盘价判断
        exit_condition3 = self.data.close[0] < self.data.close[-1]
        
        # 条件4: 成交量显著性（Z-score方法）
        vol_zscore = (prev_volume - np.mean(self.data.volume.get(size=10))) / \
                    (np.std(self.data.volume.get(size=10)) + 1e-8)
        exit_condition4 = vol_zscore > self.params_dict["zscore_threshold"]

        exit_signal = all([
            exit_condition1,
            exit_condition2,
            exit_condition3,
            exit_condition4
        ])

        # --- 交易执行 ---
        if not self.position:
            if long_signal and self.order is None:
                self.order = self.buy()  # 默认使用全部可用资金
        else:
            if exit_signal and self.order is None:
                self.order = self.close()  # 平仓

    def notify_order(self, order) -> None:
        '''
        获取订单状态，这个函数一般可以通用。
        '''
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price： %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                    order.executed.value,
                    order.executed.comm)
                )
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
            else:
                self.log(
                    'SELL EXECUTED, Price： %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                    order.executed.value,
                    order.executed.comm)
                )
                self.bar_executed = len(self)
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled / Margin / Rejected')
        self.order = None
    
    def notify_trade(self, trade) -> None:
        '''
        追踪每笔交易的状态，这个函数一般可以通用。
        '''
        if not trade.isclosed:
            return
        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))
        
    def log(self, txt, dt=None, doprint=False) -> None:
        '''
        保存日志
        '''
        if doprint:
            dt = dt or self.datas[0].datetime.date(0)
            print('%s, %s' % (dt.isoformat(), txt))