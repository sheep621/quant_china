# A股量化 Alpha 工厂 (Alpha Factory) 项目说明书

## 1. 项目概述

本项目是一个专为 **中国 A 股市场** 设计的量化因子挖掘系统的核心重构版本。它基于 WorldQuant 经典的 101 Alpha 理论，并针对 A 股的独特微观结构（T+1 交易、涨跌停板、板块轮动）进行了深度本土化适配。

核心目标是实现 **“自动化、工程化、持续化”** 的 Alpha 生产流水线。

---

## 2. 核心特性

### 2.1 A股深度适配算法
*   **T+1 专用目标 (Label)**: 摒弃传统的 `Close/PreClose - 1`，采用 `Open_T+2 / Open_T+1 - 1` 作为预测目标。因子挖掘的目的是预测“明日开盘买入，后日开盘卖出”的隔夜收益，完美规避 T+1 锁仓风险。
*   **涨跌停风控**:
    *   **算子**: 新增 `limit_distance` (距离涨停幅度)，捕捉“打板”与“封板”意愿。
    *   **数据**: 动态计算 `high_limit` (涨停价)，支持主板 (10%)、科创/创业板 (20%) 和 ST (5%) 的差异化阈值。
*   **行业中性化**: 内置 `ind_neutralize` 算子，在挖掘阶段即可剥离行业 Beta，提取纯 Alpha。

### 2.2 增强型算子库 (`operators.py`)
相比原生 `gplearn`，现已扩展至 **47+ 个量化专用算子**:
*   **多窗口时序算子**: `ts_mean`, `ts_rank`, `ts_sum`, `ts_min`, `ts_max`, `ts_std` 支持 3/5/7/10/15/20/30 日窗口。
*   **高阶统计**: `ts_skewness` (偏度), `ts_kurtosis` (峰度)。
*   **稳健统计**: `ts_mad` (滚动中位差)，抗噪能力远超标准差。
*   **向量化优化**: 全底层重写，利用 Pandas Rolling 和 Numpy，计算速度提升 10-100 倍。

### 2.3 WorldQuant 101 预定义因子库
新增 `wq101_factors.py` 模块，内置 **20+ 个经典 WQ101 因子**:
*   可直接用于回测评估
*   可作为 GP 算法的"种子因子"，加速进化收敛
*   包括动量、反转、成交量、波动率等多类型信号

### 2.4 持续进化工厂 (`run_continuous.py`)
*   **热启动 (Warm Start)**: 支持“接力进化”。新的一轮挖掘会继承上一轮的优秀“基因”（因子公式），随着时间推移，因子库质量会螺旋上升。
*   **Mock 数据模式**: 内置测试数据生成器，即使没有真实行情数据，系统也能跑通演示流程。
*   **自动质量门控 (NEW)**: 每个挖掘出的因子自动通过多维度评估：
    - ICIR > 0.5 (信息比率)
    - IC胜率 > 55%
    - 换手率 < 50%
    - 因子特异性 > 0.3 (与已有因子相关性 < 0.7)
*   **增量正交化 (NEW)**: 自动剔除高相关因子，保持因子池多样性。

---

## 3. 目录结构

```text
quant_china/
├── data/                   # 数据存放目录
├── output/                 # 挖掘结果 (JSON)
├── src/
│   ├── alpha_factory/      # [核心] 因子挖掘引擎
│   │   ├── generator.py    # AlphaGenerator 类 (GP 算法)
│   │   ├── operators.py    # 增强算子库 (47+ 算子)
│   │   ├── wq101_factors.py # WorldQuant 101 预定义因子
│   │   ├── combine_factors.py # 因子组合模块
│   │   └── run_continuous.py # 自动化主控脚本
│   ├── data_engine/        # 数据清洗
│   │   └── cleaner.py      # DataCleaner 类 (T+1 Label, Limit Calc)
│   └── infrastructure/     # 基础设施
│       └── logger.py       # 日志模块
├── requirements.txt        # 依赖库
└── README_CN.md            # 本说明书
```

---

## 4. 安装与配置

### 4.1 环境要求
推荐使用 Python 3.8+。

安装依赖：
```bash
pip install -r requirements.txt
```

### 4.2 数据准备
系统默认会在检测不到数据时生成 Mock 数据。若要使用真实数据，请准备 CSV 文件：
*   **路径**: `data/market_data.csv`
*   **必需列**: `date`, `code`, `open`, `close`, `high`, `low`, `volume`
*   **推荐列**: `preClose` (计算涨停价), `pctChg`, `isST` (ST标记)

---

## 5. 操作指南

### 5.1 启动挖掘工厂
运行主控脚本即可开启自动化挖掘循环：

```bash
python src/alpha_factory/run_continuous.py
```

### 5.2 监控运行
控制台将实时输出挖掘进度：
```text
INFO - Starting Alpha Factory...
INFO - --- Iteration 1/3 ---
INFO - === Alpha Mining Started ===
INFO - TOP 5 Discovered Alphas:
INFO -   Alpha#1 | Fitness=0.0951 | trunc(tsrank10(close))
...
```

### 5.3 查看结果
挖掘出的因子会自动去重并保存到：
`output/discovered_alphas.json`

格式示例：
```json
[
    {
        "formula": "trunc(ts_rank_10(close))",
        "fitness": 0.0915
    }
]
```

### 5.4 二次开发建议
*   **调整参数**: 修改 `run_continuous.py` 中的 `AlphaGenerator` 参数 (如 `population_size`, `generations`) 可平衡挖掘速度与深度。
*   **因子组合**: 挖掘出的 JSON 公式可进一步输入到 LightGBM 或线性模型中进行组合（Ensemble）。
    *   **新功能**: 使用 `python src/alpha_factory/combine_factors.py` 自动加载挖掘出的因子，计算特征矩阵并训练 LightGBM 模型。

---

### 5.5 GitHub Actions 云端自动化 (推荐)
如果您希望让项目在云端 7x24 小时自动运行，可以使用内置的 GitHub Workflow：

1.  **Fork 本项目** 到您的 GitHub 仓库。
2.  进入 **Actions** 页面，启用 Workflow。
3.  系统每 6 小时会自动运行一次挖掘任务 (每次 50 轮迭代)。
4.  挖掘出的新因子会自动 Commit 回仓库的 `output/discovered_alphas.json` 文件中。
5.  您可以随时 `git pull` 获取最新的因子库。

---

## 6. 常见问题 (FAQ)

**Q: 为什么运行初期没有产出高分因子？**
A: 遗传规划需要积累。启用 `warm_start=True` 后，运行代数越多，找到复杂高分因子的概率越大。

**Q: 缺少 `isST` 列会怎样？**
A: `DataCleaner` 会默认将所有股票视为非 ST（涨跌幅限制 10% 或 20%），这在回测中可能导致轻微的各种偏差，但在因子挖掘阶段通常是可接受的。
