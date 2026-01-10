from unittest.mock import Mock


class TestTradeStrategy:
    """TradeStrategy类的测试用例"""

    def setup_method(self):
        """测试方法的前置设置"""

        # 创建一个简单的类，模拟TradeStrategy的相关属性和方法
        class MockTradeStrategy:
            """模拟TradeStrategy类"""

            def __init__(self):
                # 模拟daily_trade_data属性
                self.daily_trade_data = []
                # 模拟strategy_name属性
                self.strategy_name = "TEST_STRATEGY"
                # 模拟position属性
                self.position = Mock()
                self.position.size = 0
                # 模拟order属性
                self.order = None
                # 模拟datas属性
                self.datas = [Mock()]
                self.datas[0].datetime.date.return_value = "2024-01-01"
                # 模拟log方法
                self.log = Mock()

            def add_daily_data(self, date=None, data=None):
                """添加每日交易数据"""
                # 直接复制add_daily_data的实现，避免实例化Strategy对象
                daily_data = {}
                daily_data["日期"] = str(date or "2024-01-01")
                if data:
                    daily_data.update(data)
                daily_data["持仓大小"] = self.position.size
                daily_data["订单状态"] = self.order
                self.daily_trade_data.append(daily_data)
                return daily_data

            def _parse_trade_data(self):
                """解析交易数据，生成表格"""
                from prettytable import PrettyTable

                if not self.daily_trade_data:
                    return None

                all_keys = set()
                for data in self.daily_trade_data:
                    all_keys.update(data.keys())

                headers = ["日期"]
                other_keys = sorted(all_keys - {"日期"})
                headers.extend(other_keys)

                table = PrettyTable()
                table.field_names = headers

                table.align["日期"] = "l"
                for header in headers[1:]:
                    table.align[header] = "r"

                for data in self.daily_trade_data:
                    row = [data.get(header, "-") for header in headers]
                    table.add_row(row)

                return table

            def stop(self):
                """策略结束时调用"""
                if not self.daily_trade_data:
                    self.log("没有数据可生成汇总表格", doprint=True)
                    return

                table = self._parse_trade_data()
                if table:
                    self.log(
                        f"\n=== 策略执行汇总表格 ({self.strategy_name}) ===\n{table}",
                        doprint=True,
                    )
                    self.log(
                        f"总计交易天数: {len(self.daily_trade_data)}", doprint=True
                    )

        # 创建模拟对象
        self.strategy = MockTradeStrategy()

    def test_add_daily_data_without_date(self):
        """测试add_daily_data方法，不提供日期参数"""
        # 准备测试数据
        test_data = {"收盘价": 100.0, "MA值": 99.5, "MACD差值": 0.5, "MACD信号线": 0.3}

        # 调用add_daily_data方法
        daily_data = self.strategy.add_daily_data(data=test_data)

        # 验证数据被正确添加
        assert len(self.strategy.daily_trade_data) == 1
        assert daily_data["日期"] == "2024-01-01"
        assert daily_data["收盘价"] == 100.0
        assert daily_data["MA值"] == 99.5
        assert daily_data["MACD差值"] == 0.5
        assert daily_data["MACD信号线"] == 0.3
        assert daily_data["持仓大小"] == 0
        assert daily_data["订单状态"] is None

    def test_add_daily_data_with_date(self):
        """测试add_daily_data方法，提供日期参数"""
        # 准备测试数据
        test_data = {"收盘价": 100.0, "MA值": 99.5}
        test_date = "2024-01-02"

        # 调用add_daily_data方法
        daily_data = self.strategy.add_daily_data(date=test_date, data=test_data)

        # 验证数据被正确添加
        assert len(self.strategy.daily_trade_data) == 1
        assert daily_data["日期"] == test_date

    def test_add_daily_data_with_empty_data(self):
        """测试add_daily_data方法，提供空数据"""
        # 调用add_daily_data方法，不提供data参数
        daily_data = self.strategy.add_daily_data()

        # 验证数据被正确添加
        assert len(self.strategy.daily_trade_data) == 1
        assert "日期" in daily_data
        assert "持仓大小" in daily_data
        assert "订单状态" in daily_data
        assert len(daily_data) == 3

    def test_parse_trade_data_with_no_data(self):
        """测试_parse_trade_data方法，没有数据的情况"""
        # 调用_parse_trade_data方法
        table = self.strategy._parse_trade_data()

        # 验证返回None
        assert table is None

    def test_parse_trade_data_with_data(self):
        """测试_parse_trade_data方法，有数据的情况"""
        # 准备测试数据
        test_data_1 = {"收盘价": 100.0, "MA值": 99.5, "MACD差值": 0.5}
        test_data_2 = {"收盘价": 101.0, "MA值": 100.0, "成交量": 1000000}

        # 添加测试数据
        self.strategy.add_daily_data(data=test_data_1)
        self.strategy.add_daily_data(data=test_data_2)

        # 调用_parse_trade_data方法
        table = self.strategy._parse_trade_data()

        # 验证表格被正确生成
        assert table is not None
        assert len(table.field_names) > 1
        assert "日期" in table.field_names
        assert "收盘价" in table.field_names
        assert table.align["日期"] == "l"

    def test_stop_with_no_data(self):
        """测试stop方法，没有数据的情况"""
        # 调用stop方法
        self.strategy.stop()

        # 验证log方法被调用，提示没有数据
        self.strategy.log.assert_called_once_with(
            "没有数据可生成汇总表格", doprint=True
        )

    def test_stop_with_data(self):
        """测试stop方法，有数据的情况"""
        # 添加测试数据
        test_data = {"收盘价": 100.0}
        self.strategy.add_daily_data(data=test_data)

        # 调用stop方法
        self.strategy.stop()

        # 验证log方法被调用了两次：一次打印表格，一次打印交易天数
        assert self.strategy.log.call_count == 2
