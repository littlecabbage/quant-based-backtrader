import os
import tushare as ts
from dotenv import load_dotenv
from sqlmodel import create_engine, SQLModel, Session
from sqlalchemy import text, Engine
from datetime import datetime, timedelta
import pandas as pd
from tqdm import tqdm 


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
        """获取交易日历并全量替换"""
        df = self.pro.trade_cal(exchange='', start_date=start_date, end_date=end_date)
        if df.empty:
            print(f"警告: 找不到给定日期范围 {start_date}-{end_date} 的交易日历数据。")
        else:
            # 交易日历数据适合全量替换，以保证与数据源完全一致
            df.to_sql('trade_calendar', con=self.engine, if_exists='replace', index=False)
            print(f"交易日历已更新至 {end_date}。")
    
    def get_stock_basic(self) -> pd.DataFrame:
        """获取全量股票基本信息并全量替换"""
        df = self.pro.stock_basic(exchange='', list_status=None, fields='ts_code,symbol,name,area,industry,list_date,list_status')
        if df.empty:
            raise ValueError("找不到股票基本信息数据。")
        else:
            # 股票基本信息适合全量替换，以反映最新上市/退市状态
            df.to_sql('stock_basic', con=self.engine, if_exists='replace', index=False)
            print(f"股票基本信息已更新，总计 {len(df)} 只股票。")
        
        # 只返回上市状态的股票用于后续数据下载
        df_listed = df[df['list_status'].isin(['L', 'P'])]
        ts_codes_list = df_listed['ts_code'].tolist()
        self.ts_codes_str = ','.join(ts_codes_list)
        return df

    def _upsert_data(self, df: pd.DataFrame, table_name: str, unique_keys: list[str]):
        """
        将数据增量更新或插入到指定的数据库表中 (Upsert)。

        :param df: 包含新数据的DataFrame。
        :param table_name: 目标数据库表名。
        :param unique_keys: 用于判断数据唯一性的一个或多个列名。
        """
        if df is None or df.empty:
            return

        df_to_insert = pd.DataFrame() # 确保 df_to_insert 总是有定义的
        keys_str = ', '.join(unique_keys)

        try:
            # 简化处理：先读取所有相关的键，再做merge
            # 这对于大数据表性能较低，但对于本项目可行
            existing_df = pd.read_sql(f"SELECT DISTINCT {keys_str} FROM {table_name}", self.engine)
            
            # 使用 merge 来找出不存在于数据库中的新行
            merged = pd.merge(df, existing_df, on=unique_keys, how='left', indicator=True)
            df_to_insert = merged[merged['_merge'] == 'left_only'].drop(columns=['_merge'])

        except Exception as e:
            # 检查是否因为表不存在而出错
            if f"no such table: {table_name}" in str(e).lower():
                # 如果表不存在，则所有数据都是新数据
                df_to_insert = df
            else:
                print(f"在处理表 {table_name} 时发生错误: {e}")
                return # 发生未知错误时，不进行任何操作
        
        if not df_to_insert.empty:
            df_to_insert.to_sql(table_name, self.engine, if_exists='append', index=False, chunksize=20000)
        else:
            print(f"没有需要向 {table_name} 插入的新记录。")

    def frist_download(self, start_date:str, end_date:str) -> None:
        """首次下载所有数据"""
        self.get_stock_basic()
        self.get_trade_cal(start_date, end_date)
        ts_codes_grouped = self.__group_string_data(self.ts_codes_str, 50)
        
        with tqdm(total=len(ts_codes_grouped), desc="下载日线数据") as pbar:
            for ts_codes_str in ts_codes_grouped:
                try:
                    df = self.pro.daily(ts_code=ts_codes_str, start_date=start_date, end_date=end_date)
                    self._upsert_data(df, 'daily_price', ['ts_code', 'trade_date'])
                except Exception as e:
                    print(f"下载日线数据时发生错误: {e}, ts_codes: {ts_codes_str}")
                pbar.update(1)
        
        date_list = self.__get_dates_between(start_date, end_date)
        with tqdm(total=len(date_list), desc="下载复权因子") as pbar:
            for date in date_list:
                try:
                    df = self.pro.adj_factor(trade_date = date)
                    self._upsert_data(df, 'adj_factor', ['ts_code', 'trade_date'])
                except Exception as e:
                    print(f"下载复权因子时发生错误: {e}, trade_date: {date}")
                pbar.update(1)

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
    
    def __group_string_data(self, data_string: str, group_size: int, delimiter: str = ',') -> list[str]:
        """
        将一个由分隔符分隔的字符串，转换成一个列表。
        列表中的每个元素是包含指定数量原始数据的、重新组合的字符串。
        :param data_string: 原始的输入字符串 (例如 "a,b,c,d,e,f,g")。
        :param group_size: 每个分组中应包含的原始数据项的数量 (必须大于0)。
        :param delimiter: 用于分割和连接数据的分隔符，默认为英文逗号。
        :return: 一个新的字符串列表，其中每个元素都是一个分组。
                如果输入字符串为空，则返回一个空列表。
        """
        # --- 1. 输入验证 ---
        if not isinstance(data_string, str):
            raise TypeError("输入数据必须是字符串类型。")
            
        if not isinstance(group_size, int) or group_size <= 0:
            raise ValueError("group_size 必须是大于0的整数。")
        if not data_string.strip():
            # 如果字符串为空或只包含空白字符，返回空列表
            return []
        # --- 2. 核心逻辑 ---
        # 首先，按分隔符将原始字符串分割成一个包含所有独立数据项的列表
        all_items = data_string.split(delimiter)
        # 然后，将这个列表分块，并将每个块重新用分隔符连接成字符串
        grouped_list = []
        # 使用步长 (step) 为 group_size 的循环来遍历 all_items
        for i in range(0, len(all_items), group_size):
            # 从索引 i 到 i + group_size 获取一个数据块（切片）
            chunk = all_items[i : i + group_size]
            # 使用分隔符将这个数据块连接成一个字符串，并添加到最终列表中
            grouped_list.append(delimiter.join(chunk))
        return grouped_list

    def update(self) -> None:
        """更新数据到最新"""
        with Session(self.engine) as session:
            try:
                # 从数据库中获取最新的日期
                result = session.execute(text("SELECT MAX(trade_date) FROM daily_price"))
                last_date = result.scalar() # 格式通常是 'YYYY-MM-DD'
            except Exception:
                last_date = None # 处理表不存在或查询失败的情况

            if last_date is None:
                print("数据库中没有数据或'daily_price'表不存在，请先运行首次下载。")
                return

            # 计算更新的起始日期 (最新日期的后一天)
            start_date = (datetime.strptime(last_date, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
            end_date = datetime.now().strftime("%Y%m%d")

            if start_date > end_date:
                print("数据已经是最新的，无需更新。")
                return
            
            print(f"开始更新数据，日期范围: {start_date} -> {end_date}")

            # 1. 更新基础数据
            self.get_stock_basic()
            self.get_trade_cal(start_date, end_date)

            # 2. 增量更新日线行情
            ts_codes_grouped = self.__group_string_data(self.ts_codes_str, 50)
            with tqdm(total=len(ts_codes_grouped), desc="更新日线数据") as pbar:
                for ts_codes_str in ts_codes_grouped:
                    try:
                        df = self.pro.daily(ts_code=ts_codes_str, start_date=start_date, end_date=end_date)
                        self._upsert_data(df, 'daily_price', ['ts_code', 'trade_date'])
                    except Exception as e:
                        print(f"更新日线数据时发生错误: {e}, ts_codes: {ts_codes_str}")
                    pbar.update(1)

            # 3. 增量更新复权因子
            date_list = self.__get_dates_between(start_date, end_date)
            with tqdm(total=len(date_list), desc="更新复权因子") as pbar:
                for date in date_list:
                    try:
                        df = self.pro.adj_factor(trade_date = date)
                        self._upsert_data(df, 'adj_factor', ['ts_code', 'trade_date'])
                    except Exception as e:
                        print(f"更新复权因子时发生错误: {e}, trade_date: {date}")
                    pbar.update(1)

if __name__ == "__main__":
    downloader = TushareDownloader()
    
    # --- 首次下载 ---
    # 建议选择一个较长的历史周期，例如10年。
    # 注意：首次下载会清空并重新填充 'stock_basic' 和 'trade_calendar' 表。
    start_date = (datetime.now() - timedelta(days=365*2)).strftime('%Y%m%d')
    end_date = datetime.now().strftime('%Y%m%d')
    print(f"开始首次下载，日期范围: {start_date} -> {end_date}")
    downloader.frist_download(start_date=start_date, end_date=end_date)
    
    # # --- 更新数据 ---
    # # 首次下载完成后，日常应运行 update() 来获取最新数据。
    # print("开始执行更新任务...")
    # downloader.update()
    # print("更新任务执行完毕。")
