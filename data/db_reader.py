import pandas as pd
from sqlalchemy import Engine, create_engine


class StockDBReader:
    def __init__(self, db_name: str = "stock_db_based_Tushare.db"):
        """
        初始化数据库读取器。
        :param db_name: SQLite 数据库文件名。
        """
        self.db_path = f"sqlite:///{db_name}"
        self.engine: Engine = create_engine(self.db_path)

    def get_raw_daily_price(
        self, ts_code: str | list[str], start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        从数据库中获取指定股票在指定时间段内的日线数据。

        :param ts_code: 股票代码。可以是单个股票代码（如 '000001.SZ'）或一个包含多个代码的列表。
        :param start_date: 开始日期，格式为 'YYYYMMDD'。
        :param end_date: 结束日期，格式为 'YYYYMMDD'。
        :return: 包含查询结果的 pandas DataFrame。
        """
        if isinstance(ts_code, str):
            ts_code_tuple = f"('{ts_code}')"
        elif isinstance(ts_code, list):
            if len(ts_code) == 1:
                # 如果列表只有一个元素，SQL IN 子句需要 ('code',) 格式
                ts_code_tuple = f"('{ts_code[0]}')"
            else:
                ts_code_tuple = str(tuple(ts_code))
        else:
            raise TypeError("ts_code 必须是字符串或列表类型。")

        # 移除日期字符串中的 '-' 以兼容 YYYYMMDD 和 YYYY-MM-DD 两种格式
        start_date_formatted = start_date.replace("-", "")
        end_date_formatted = end_date.replace("-", "")

        query = f"""
        SELECT *
        FROM daily_price
        WHERE ts_code IN {ts_code_tuple}
          AND REPLACE(trade_date, '-', '') >= '{start_date_formatted}'
          AND REPLACE(trade_date, '-', '') <= '{end_date_formatted}'
        ORDER BY trade_date ASC;
        """

        try:
            df = pd.read_sql(query, self.engine)
            return df
        except Exception as e:
            print(f"查询数据时发生错误: {e}")
            return pd.DataFrame()

    def get_adj_factor(
        self, ts_code: str | list[str], start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        从数据库中获取指定股票在指定时间段内的复权因子。

        :param ts_code: 股票代码。可以是单个股票代码（如 '000001.SZ'）或一个包含多个代码的列表。
        :param start_date: 开始日期，格式为 'YYYYMMDD'。
        :param end_date: 结束日期，格式为 'YYYYMMDD'。
        :return: 包含复权因子查询结果的 pandas DataFrame。
        """
        if isinstance(ts_code, str):
            ts_code_tuple = f"('{ts_code}')"
        elif isinstance(ts_code, list):
            if len(ts_code) == 1:
                ts_code_tuple = f"('{ts_code[0]}')"
            else:
                ts_code_tuple = str(tuple(ts_code))
        else:
            raise TypeError("ts_code 必须是字符串或列表类型。")

        start_date_formatted = start_date.replace("-", "")
        end_date_formatted = end_date.replace("-", "")

        query = f"""
        SELECT ts_code, trade_date, adj_factor
        FROM adj_factor
        WHERE ts_code IN {ts_code_tuple}
          AND REPLACE(trade_date, '-', '') >= '{start_date_formatted}'
          AND REPLACE(trade_date, '-', '') <= '{end_date_formatted}'
        ORDER BY trade_date ASC;
        """

        try:
            df = pd.read_sql(query, self.engine)
            return df
        except Exception as e:
            print(f"查询复权因子时发生错误: {e}")
            return pd.DataFrame()

    def get_daily_price(
        self,
        ts_code: str | list[str],
        start_date: str,
        end_date: str,
        adj_type: str = "qfq",
    ) -> pd.DataFrame:
        """
        获取并处理指定股票在指定时间段内的日线数据，返回符合 Backtrader 要求的格式。

        :param ts_code: 股票代码。可以是单个股票代码（如 '000001.SZ'）或一个包含多个代码的列表。
        :param start_date: 开始日期，格式为 'YYYYMMDD'。
        :param end_date: 结束日期，格式为 'YYYYMMDD'。
        :param adj_type: 复权类型，可选 'bfq'（不复权）、'qfq'（前复权）、'hfq'（后复权）。
        :return: 包含处理后数据的 pandas DataFrame。
        """
        df = self.get_raw_daily_price(ts_code, start_date, end_date)
        if df.empty:
            print("未查询到数据。")
            return df

        if adj_type in ["qfq", "hfq"]:
            df_adj = self.get_adj_factor(ts_code, start_date, end_date)
            if df_adj.empty:
                print("警告: 未查询到复权因子，返回不复权数据。")
            else:
                df = pd.merge(df, df_adj, on=["ts_code", "trade_date"], how="left")
                df = df.sort_values(by=["ts_code", "trade_date"])
                df["adj_factor"] = df.groupby("ts_code")["adj_factor"].ffill()
                df = df.dropna(subset=["adj_factor"])

                if not df.empty:
                    price_cols = ["open", "close", "high", "low"]

                    if adj_type == "hfq":
                        df[price_cols] = df[price_cols].multiply(
                            df["adj_factor"], axis=0
                        )
                        df["vol"] = df["vol"] / df["adj_factor"]
                    elif adj_type == "qfq":
                        last_factors = df.groupby("ts_code")["adj_factor"].transform(
                            "last"
                        )
                        qfq_factor = df["adj_factor"] / last_factors
                        df[price_cols] = df[price_cols].multiply(qfq_factor, axis=0)
                        df["vol"] = df["vol"] / qfq_factor

        # 选择并重命名所需的列
        df = df[["trade_date", "open", "close", "high", "low", "vol"]]
        df.columns = ["date", "open", "close", "high", "low", "volume"]

        # 将 date 列转换为 datetime 类型并设置为索引
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")

        return df


if __name__ == "__main__":
    reader = StockDBReader()

    df = reader.get_daily_price(
        ts_code="000063.SZ", start_date="20250901", end_date="20250908"
    )
    print(df.head())
    print(df.info())
    print(df.describe())

    # # 查询单个股票的数据
    # print("--- 查询单个股票 (000037.SZ) ---")
    # single_stock_df = reader.get_daily_price(ts_code='000063.SZ', start_date='20250908', end_date='20250908')
    # if not single_stock_df.empty:
    #     print(single_stock_df)
    # else:
    #     print("未查询到数据。")

    # print("\n" + "="*50 + "\n")

    # # 查询多个股票的数据
    # print("--- 查询多个股票 (例如 '000037.SZ') ---")
    # multi_stock_df = reader.get_daily_price(ts_code=['000037.SZ'], start_date='20250908', end_date='20250908')
    # if not multi_stock_df.empty:
    #     print(multi_stock_df)
    # else:
    #     print("未查询到数据。")
