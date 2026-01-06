# 贡献指南

感谢您对 backtrader_trading 项目的关注！本指南将帮助您了解如何为项目做出贡献。

## 项目简介

### 核心目标
backtrader_trading 是一个基于 backtrader 框架的 A 股量化交易回测系统，专门为散户投资者设计。该项目旨在简化量化交易策略的开发流程，让用户能够专注于策略逻辑本身，而不是复杂的工程实现。

- **易用性**: 提供简单直观的接口，降低量化交易入门门槛
- **模块化**: 将数据获取、策略实现、佣金计算等功能模块化，便于扩展和维护
- **配置化**: 通过配置文件管理策略参数，方便调试和优化
- **专注A股**: 针对A股市场的特点进行优化，支持T+1交易规则等本地化需求

### 投资者使用流程
#### 进行回测
回测过程只需修改配置文件，即可进行不同策略的回测。
- 在 `config/config.toml` 中配置回测日期、股票代码、复权方式等参数
- 在 `config/strategy_config.toml` 中配置策略参数
- 运行 `main.py` 启动回测系统
- 查看回测结果和交易记录

#### 开发新策略
开发策略只需编写一个python脚本，原则上支持任何形式的策略，包括但不限于：基于技术指标的策略、基于深度学习的策略等等...

- 在 `strategy/` 目录下创建新的策略文件，并继承 `bt.Strategy` 类，实现策略逻辑。
- 在 `config/strategy_config.toml` 中添加策略配置

### 项目结构和主要模块
```
.
├── commission/          # 佣金模块
├── config/             # 配置文件
├── data/               # 数据处理模块
├── strategy/           # 策略模块
├── test/               # 测试模块
├── docs/               # 文档模块
└── main.py             # 主程序入口
```
#### `commission/`
用于佣金计算模块，模拟真实交易成本。

#### `strategy/`
策略实现模块，提供常见技术指标策略。
`strategy/config_loader.py`用于加载策略配置文件，将配置参数转换为策略参数。
`strategy/trade_strategy.py`是策略类的基类，所有策略类都需要继承该类，实现策略逻辑。
`strategy/macd_strategy.py`是一个具体策略的示例。MACD策略的实现类，继承自`trade_strategy.py`，实现MACD指标的计算和交易逻辑。

#### `data/`
数据获取模块，负责从数据源获取股票数据。

## 提交规范
提交前请注意检查以下事项：

### 代码规范
遵循[Google Python](https://zh-google-styleguide.readthedocs.io/en/latest/google-python-styleguide/contents.html)风格指南，确保代码的可读性和可维护性。

### 文档规范
- 所有策略类应当在`docs/`下建立详细的策略文档。
- 文档使用 markdown 格式，所有外部资源，如图像等，应当在`docs/assets/`目录下。

### 依赖管理
- 使用uv管理依赖
- 确保符合依赖最小原则
- 确保向前兼容
- 可选依赖必须添加依赖组。本项目会有诸多可选项，如数据部分，可选akshare或tushare等数据源。应在`pyproject.toml`的`[dependency-groups]`中添加。避免强制用户安装无用的依赖。

### 测试规范
- 使用 pytest 框架编写测试用例
- 外部依赖的测试用例必须使用 mock 进行模拟
- 新增功能必须包含相应的测试用例
- 测试用例应覆盖主要功能路径
- 运行`uv run pytest`，确保所有测试通过，而不是只检查新增的测试用例。

### pre-commit
初次 commit 时安装 pre-commit 钩子：
```shell
uv run pre-commit install
```
这会使每次 commit 前自动检查代码是否符合规范。如果不符合规范，提交将会失败。

### git 提交规范
- 每个提交都应该有一个清晰的提交信息，描述所做的更改。
- 提交信息应该遵循[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)规范。
  - 提交类型：`feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
  - 提交信息格式：`<类型>(可选作用域): <描述>`
  - 例如：`feat(data): 添加新的数据源模块`


**感谢您的贡献！**
