import backtrader as bt
import numpy as np
from scipy.signal import argrelextrema

from .trade_strategy import TradeStrategy

"""
# 指标：
MA15
MACD 30 50 6
ATR 5

## 开仓信号：
1. 满足close< MA15
2. diff <0
3. diff > dea 其实就是水下金叉
4. 最近1日成交量 > 过去2日成交量平均值

## 平仓信号：
1. 满足 close > MA15 + 0.5atr
2. Bar>0 且 iloc[-5:-2]的bar存在peak（用numpy的库）
3. bar的一阶导数为负数
4. 成交量具有显著性，这个可以用z-score或者用 最近1日成交量 > 过去2日成交量平均值
"""


class MACDStrategy(TradeStrategy):
    """基于MACD指标的交易策略。

    该策略使用MACD指标结合移动平均线和ATR指标进行交易决策。
    """

    strategy_name = "MACD"

    def __init__(self, **params) -> None:
        """初始化MACD策略。

        Args:
            **params: 策略参数，包括ma_period, macd_fast, macd_slow,
                     macd_signal, atr_period, peak_window, zscore_threshold
        """
        super().__init__(**params)
        self.params_dict = params

        # 指标计算
        self.ma15 = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.params_dict["ma_period"]
        )
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.params_dict["macd_fast"],
            period_me2=self.params_dict["macd_slow"],
            period_signal=self.params_dict["macd_signal"],
        )
        self.atr = bt.indicators.ATR(self.data, period=self.params_dict["atr_period"])
        self.diff = self.macd.macd  # MACD线
        self.dea = self.macd.signal  # 信号线

        # 存储最近5根Bar的峰值检测数据
        # 存储最近的高点数据用于峰值检测
        self.high_buffer: list[float] = []
        self.min_bars = max(
            50, self.params_dict["peak_window"] + 3
        )  # 最大指标所需最小bar数

        # 交易状态跟踪
        self.order = None

    def next(self) -> None:
        # 获取必要数据（-1表示前一交易日）
        prev_close = self.data.close[-1]
        prev_volume = self.data.volume[-1]
        prev_ma15 = self.ma15[-1]
        prev_diff = self.diff[-1]
        prev_dea = self.dea[-1]

        # --- 开仓条件 ---
        condition1 = prev_close < prev_ma15  # 收盘价低于MA15
        condition2 = prev_diff < 0  # MACD差值<0（水下）
        # 水下金叉：放宽为当前处于水下且 diff > dea，不强制要求严格穿越
        condition3 = prev_diff > prev_dea

        # 成交量条件：今日量 > 过去2日平均量
        volume_avg2 = (self.data.volume[-2] + self.data.volume[-3]) / 2.0
        condition4 = prev_volume > volume_avg2

        long_signal = all([condition1, condition2, condition3, condition4])

        # --- 平仓条件 ---
        # 条件1: 收盘价 > MA15 + 0.5*ATR
        exit_condition1 = self.data.close[0] > self.ma15[0] + 0.5 * self.atr[0]

        # 条件2: 在 iloc[-5:-2] 区间（不含当前bar）是否存在局部峰值
        # if len(self.data) >= 6:
        #     highs = np.array([
        #         self.data.high[-5],
        #         self.data.high[-4],
        #         self.data.high[-3]
        #     ])
        #     # 任意局部峰值：高于左右相邻（窗口内的内部点才具备左右）
        #     # 这里窗口长度为3，只有中间点可成为峰值
        #     self.peak_detected = (highs[1] > highs[0]) and (highs[1] > highs[2])
        # exit_condition2 = self.peak_detected

        ################# 改用scipy的find_peaks方法检测峰值 #################
        exit_condition2 = False
        window_size = self.params_dict["peak_window"]

        # 维护一个固定长度的价格窗口
        if len(self.high_buffer) >= window_size:
            self.high_buffer.pop(0)
        self.high_buffer.append(self.data.high[-1])

        # 当有足够数据时检测峰值
        if len(self.high_buffer) >= window_size:
            # 使用scipy检测局部极大值
            highs = np.array(self.high_buffer)
            peak_indices = argrelextrema(highs, np.greater, order=1)[0]
            # peak_indices = find_peaks(highs)[0]

            # 检查指定区间[-5:-2]是否存在峰值
            # 转换为缓冲区内的相对位置
            target_range = range(window_size - 5, window_size - 2)
            exit_condition2 = any(i in peak_indices for i in target_range)

        # 条件3: Bar的一阶导数为负（解释为价格短期下降）
        # 说明：使用当前Bar vs 前1Bar的收盘价判断
        exit_condition3 = self.data.close[0] < self.data.close[-1]

        # 条件4: 成交量显著性（Z-score方法）
        vol_zscore = (prev_volume - np.mean(self.data.volume.get(size=10))) / (
            np.std(self.data.volume.get(size=10)) + 1e-8
        )
        exit_condition4 = vol_zscore > self.params_dict["zscore_threshold"]

        exit_signal = all(
            [exit_condition1, exit_condition2, exit_condition3, exit_condition4]
        )

        # --- 交易执行 ---
        if not self.position:
            if long_signal and self.order is None:
                self.order = self.buy()  # 默认使用全部可用资金
        else:
            if exit_signal and self.order is None:
                self.order = self.close()  # 平仓
