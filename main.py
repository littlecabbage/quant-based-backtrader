import sys
from datetime import datetime
import tomllib
import pandas as pd
import matplotlib.pyplot as plt
from backtrader import bt
import akshare as ak
from pprint import pprint as pp

from strategy.config_loader import StrategyConfig
from commission.commission import MyStockCommissionScheme
from data.akshare_data import get_stock_data


def main():
    with open("config/config.toml", "rb") as f:
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

    pp(config_info)

    platform = sys.platform.lower()
    if platform.startswith("win") or platform.startswith("linux"):
        plt.rcParams["font.sans-serif"] = ["SimHei"]
    else:
        plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['font.sans-serif'] = ['Hiragino Sans GB', 'Hiragino Sans']  # 优先冬青黑体，其次ヒラギノ角ゴ
    plt.rcParams["axes.unicode_minus"] = False

    start_date, end_date = (
        datetime(config["date"]["start_year"], config["date"]["start_month"], 1),
        datetime(config["date"]["end_year"], config["date"]["end_month"], 1),
    )

    raw_data = get_stock_data(
        symbol=config["stock"]["symbol"][0],
        adjust=config["stock"]["adjust"]
    )

    strategy_cfg = StrategyConfig()
    strategy_class, strategy_params = strategy_cfg.get_strategy(
        name=config["strategy"]["name"]
    )

    comminfo = MyStockCommissionScheme(**config["broker"])

    cerebro = bt.Cerebro()
    data = bt.feeds.PandasData(
        dataname=raw_data,
        fromdate=start_date,
        todate=end_date,
        plot=True
    )
    cerebro.adddata(data)
    cerebro.addstrategy(strategy_class, **strategy_params)
    cerebro.broker.setcash(config["cash"])
    # 使用自定义佣金信息
    cerebro.broker.addcommissioninfo(comminfo)
    cerebro.run()

    port_value = cerebro.broker.getvalue()  # 获取回测结束后的总资金
    pnl = port_value - config["cash"]  # 盈亏统计

    result_info = f"""
回测结果:
       初始资金: {config["cash"]}
       回测期间: {start_date.strftime('%Y%m%d')} ~ {end_date.strftime('%Y%m%d')}
       总资金: {round(port_value, 2)}
       净收益: {round(pnl, 2)}
    """
    pp(result_info)

    cerebro.plot(style='candlestick')

if __name__ == "__main__":
    main()