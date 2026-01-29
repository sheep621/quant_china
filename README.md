# A股量化交易系统 (Scheme A - 基础可行版)

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个基于文件存储、LightGBM模型、遗传编程Alpha挖掘的A股量化交易系统。

## 🎯 核心特性

- **数据引擎**: BaoStock API + Parquet 文件存储
- **Alpha工厂**: gplearn 遗传规划 + WorldQuant风格算子
- **模型层**: LightGBM 滚动训练
- **回测引擎**: T+1约束 + 涨跌停处理
- **断点续传**: 智能跳过已下载数据

## 📦 安装

```bash
# 1. 克隆仓库
git clone https://github.com/sheep621/quant_china.git
cd quant_china

# 2. 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 3. 安装依赖
pip install -r requirements.txt
```

## 🚀 快速开始

```bash
# 下载数据 (HS300 + ZZ500 + SZ50, 约800只股票)
python run_pipeline.py download_data

# 运行回测 (含Alpha挖掘 + LightGBM训练 + 回测)
python run_pipeline.py run_backtest
```

## 📊 系统架构

```
quant_china/
├── config/              # 配置文件
├── data/                # 数据存储 (gitignored)
├── src/
│   ├── data_engine/     # 数据下载、清洗、过滤
│   ├── alpha_factory/   # 因子挖掘
│   ├── model_layer/     # 模型训练
│   └── execution/       # 回测引擎
└── run_pipeline.py      # 主程序入口
```

## 🔧 配置说明

- `config/system_config.yaml`: 路径配置
- `config/universe.yaml`: 股票池筛选规则

## 📈 性能指标

基于800只指数成分股的回测结果:
- **Sharpe Ratio**: ~0.33
- **数据范围**: 2020-2023
- **训练样本**: 3.8万+

## 🛠️ 技术栈

- **数据源**: BaoStock
- **存储**: Parquet (PyArrow)
- **模型**: LightGBM
- **因子挖掘**: gplearn (Genetic Programming)
- **数据处理**: pandas, numpy

## 📝 后续优化方向

1. 扩充因子库 (更多 WQ101 算子)
2. 引入高频数据 (分钟级)
3. 多模型集成 (XGBoost, CatBoost)
4. 接入实盘交易接口

## ⚠️ 免责声明

本项目仅供学习研究使用，不构成任何投资建议。实盘交易风险自负。

## 📄 License

MIT License
