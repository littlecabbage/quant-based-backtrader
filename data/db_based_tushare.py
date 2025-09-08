import os
import tushare as ts
from dotenv import load_dotenv
from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy import text, Engine
from datetime import datetime, timedelta


class TushareDownloader:
    #TODO: token不存在的处理
    #TODO: logger

    def __init__(self) -> None:
        load_dotenv('config/.env')
        token: str = os.getenv('TUSHARE_TOKEN')
        self.pro = ts.pro_api(token)
        self.sqlite_file_name: str = "stock_db_based_Tushare.db"
        self.engine: Engine = self.db_init()

    def db_init(self) -> Engine:
        if os.path.exists(self.sqlite_file_name):
            print(f"数据库 {self.sqlite_file_name} 已存在")
        else:
            print(f"创建新数据库: {self.sqlite_file_name}")

        sqlite_url = f"sqlite:///{self.sqlite_file_name}"
        engine = create_engine(sqlite_url, echo=False)
        SQLModel.metadata.create_all(engine)
        return engine

    def get_trade_cal(self, start_date: str, end_date: str) -> None:
        """获取交易日历"""
        df = self.pro.trade_cal(exchange='', start_date=start_date, end_date=end_date)
        if df.empty:
            raise ValueError("找不到给定日期范围的交易日历数据。")
        else:
            df.to_sql('trade_calendar', con=self.engine, if_exists='replace', index=False)
    
    def get_stock_basic(self, exchange: str = '', list_status: str = 'L') -> None:
        """获取股票基本信息"""
        df = self.pro.stock_basic(exchange=exchange, list_status=list_status)
        if df.empty:
            raise ValueError("找不到股票基本信息数据。")
        else:
            df.to_sql('stock_basic', con=self.engine, if_exists='replace', index=False)
    
    def get_daily_price(self, ts_code: str, start_date: str, end_date: str) -> None:
        """获取每日交易数据"""
        df = self.pro.daily(ts_code=ts_code, start_date=start_date, end_date=end_date)
        if df.empty:
            raise ValueError(f"找不到股票代码 {ts_code} 在给定日期范围的每日交易数据。")
        else:
            df.to_sql('daily_price', con=self.engine, if_exists='append', index=False)

    def get_adj_factor(self, ts_code: str, start_date: str, end_date: str) -> None:
        """获取复权因子数据"""
        df = self.pro.adj_factor(ts_code=ts_code, start_date=start_date, end_date=end_date)
        if df.empty:
            raise ValueError(f"找不到股票代码 {ts_code} 在给定日期范围的复权因子数据。")
        else:
            df.to_sql('adj_factor', con=self.engine, if_exists='append', index=False)

    def frist_download(self, start_date: str, end_date: str) -> None:
        """首次下载所有数据"""
        date_list = self.__get_dates_between(start_date, end_date)
        for date in date_list:
            print(f"正在下载 {date} 的数据...")
            self.pro.daily(trade_date = date).to_sql('daily_price', con=self.engine, if_exists='append', index=False)
            self.pro.adj_factor(trade_date = date).to_sql('adj_factor', con=self.engine, if_exists='append', index=False)

    def __get_dates_between(self, start_date:str, end_date:str) -> list:
        """
        获取两个日期之间的所有日期，格式为YYYYMMDD
        """
        start = datetime.strptime(start_date, "%Y%m%d")
        end = datetime.strptime(end_date, "%Y%m%d")

        date_list = []
        current_date = start
        
        while current_date <= end:
            date_list.append(current_date.strftime("%Y%m%d"))
            current_date += timedelta(days=1)
        
        return date_list

    def update(self) -> None:
        """更新数据到最新"""
        with Session(self.engine) as session:
            result = session.execute(text("SELECT MAX(trade_date) FROM daily_price"))
            last_date = result.scalar()
            if last_date is None:
                raise ValueError("数据库中没有数据，请先进行首次下载。")
            last_date_str = last_date.replace("-", "")
            today_str = datetime.now().strftime("%Y%m%d")
            if last_date_str >= today_str:
                print("数据已经是最新的，无需更新。")
                return
            date_list = self.__get_dates_between(last_date_str, today_str)
            for date in date_list:
                print(f"正在更新 {date} 的数据...")
                self.pro.daily(trade_date = date).to_sql('daily_price', con=self.engine, if_exists='append', index=False)
                self.pro.adj_factor(trade_date = date).to_sql('adj_factor', con=self.engine, if_exists='append', index=False)


if __name__ == "__main__":
    downloader = TushareDownloader()
    # downloader.frist_download(start_date='20240924', end_date='20250908')
    # downloader.get_trade_cal(start_date='20240924', end_date='20250908')
    downloader.update()