import sys

import backtrader as bt

sys.path.append("..")
import calendar
import tomllib
from datetime import datetime

from data.db_based_tushare import TushareDownloader
from data.db_reader import StockDBReader
from strategy.trade_strategy import TradeStrategy


class SMAStrategy(TradeStrategy):
    name = "SMA"

    def __init__(self):
        super().__init__()
        self.sma = bt.indicators.SimpleMovingAverage(self.data.close, period=15)

    def next(self):
        if not self.position:
            if self.data.close[0] > self.sma[0]:
                self.buy()
        else:
            if self.data.close[0] < self.sma[0]:
                self.sell()


if __name__ == "__main__":
    data_downloader = TushareDownloader()
    data_downloader.update()
    # 实例化cerebro
    cerebro = bt.Cerebro()

    with open(
        "/Volumes/DataVol/05_PersonaProject/quant/backtrader_trading/config/config.toml",
        "rb",
    ) as f:
        config = tomllib.load(f)

    config_info = f"""
配置参数:
       初始资金: {config["cash"]}
       股票代码: {config["stock"]["symbol"]}
       复权方式: {config["stock"]["adjust"]}
       回测区间: {config["date"]["start_year"]}-{config["date"]["start_month"]} ~ {config["date"]["end_year"]}-{config["date"]["end_month"]}
       策略名称: {config["strategy"]["name"]}
       佣金费率: {config["broker"]["commission"]}
       印花税率: {config["broker"]["stamp_duty"]}
    """

    end_month_last_day = calendar.monthrange(
        config["date"]["end_year"], config["date"]["end_month"]
    )[1]
    start_date, end_date = (
        datetime(config["date"]["start_year"], config["date"]["start_month"], 1),
        datetime(
            config["date"]["end_year"], config["date"]["end_month"], end_month_last_day
        ),
    )

    # 处理数据
    db_reader = StockDBReader()
    raw_data = db_reader.get_daily_price(
        ts_code=config["stock"]["symbol"][0],
        start_date=start_date.strftime("%Y%m%d"),
        end_date=end_date.strftime("%Y%m%d"),
        adj_type=config["stock"]["adjust"],
    )

    # 加载数据源
    data = bt.feeds.PandasData(dataname=raw_data, fromdate=start_date, todate=end_date)
    cerebro.adddata(data)

    # 加载策略
    cerebro.addstrategy(SMAStrategy)

    # 加载Analyzer
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="SharpeRatio")
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name="DrawDown")

    # 在Broker中设置初始资金和手续费
    cerebro.broker.setcash(10000.0)
    cerebro.broker.setcommission(commission=0.0006)

    # 设置Sizer
    cerebro.addsizer(bt.sizers.PercentSizer, percents=90)

    result = cerebro.run()

    print("夏普比率", result[0].analyzers.SharpeRatio.get_analysis()["sharperatio"])
    print("最大回撤", result[0].analyzers.DrawDown.get_analysis()["max"]["drawdown"])
    cerebro.plot()
