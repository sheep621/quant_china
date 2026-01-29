# **基于WorldQuant模式的中国A股量化交易体系构建与本土化深度研究报告**

## **1\. 绪论：量化投资的工业化革命与中国市场的独特挑战**

### **1.1 量化投资范式的演变：从作坊到工厂**

在过去的二十年中，全球量化投资领域经历了一场深刻的工业化革命。以WorldQuant（世坤投资）为代表的机构，通过将Alpha（超额收益）因子的挖掘过程标准化、流水线化，开创了“Alpha Factory”（Alpha工厂）的全新商业模式。这一模式的核心在于将复杂的金融市场预测问题拆解为无数个微小的、可定义的数学问题，并通过众包（Crowdsourcing）的形式，动员全球数以万计的研究员（Consultants）利用标准化的WebSim或Brain平台进行挖掘 1。

WorldQuant模式的成功建立在几个关键假设之上：首先是基于“主动管理基本定律”（Fundamental Law of Active Management），即信息比率（IR）与独立预测次数（Breadth）的平方根成正比。通过极大化因子的数量（Breadth），即使每个因子的预测能力（IC）很弱，组合后的整体夏普比率也能显著提升。其次是市场的微观结构允许高频的换手，以捕捉稍纵即逝的均值回归机会。然而，当我们将这一在成熟市场（如美国股市）验证成功的模式移植到中国A股市场时，面临着截然不同的生态环境与结构性约束。

### **1.2 中国A股市场的独特性与适配难题**

中国A股市场是全球第二大股票市场，具有鲜明的散户主导特征和独特的监管约束。对于试图在中国复制WorldQuant模式的量化从业者而言，最大的挑战并非因子的数学形式，而在于是市场微观结构的根本性差异：

* **T+1交易制度的硬约束**：与美股的T+0制度不同，A股当日买入的股票次日才能卖出。这一规则直接扼杀了绝大多数基于分钟级均值回归的高频Alpha。在WorldQuant的*101 Formulaic Alphas*中，大量因子的半衰期极短，直接应用于A股会导致严重的持仓被锁死风险 4。  
* **涨跌停板制度（Price Limits）**：主板±10%（科创板/创业板±20%）的涨跌幅限制创造了独特的流动性断层。当股票封死涨停（Limit Up）时，买单无法成交；封死跌停（Limit Down）时，卖单无法出清。这种非连续的交易环境使得标准的回测引擎失效，因为模型往往假设“收盘价可成交”，而现实中涨停板上的收盘价往往意味着零流动性 7。  
* **特殊的投资者结构**：尽管机构化进程在加速，但A股仍有大量交易由散户贡献。这导致了显著的非理性波动和羊群效应，使得基于行为金融学的因子（如情绪因子、资金流向因子）在中国市场的表现往往优于基本面因子 10。

### **1.3 报告研究目标与框架**

本报告旨在为用户提供一套完整的、经过本土化改造的WorldQuant式A股交易流程。我们将深入研究并综合High-Flyer（幻方量化）、九坤投资等头部量化私募的最新运作模式，结合AlphaNet、AlphaFormer等前沿深度学习论文，构建一个端到端的解决方案。报告将涵盖从底层数据清洗、因子挖掘（遗传规划与深度学习）、风险模型（Barra CNE6本土化）、组合优化到执行算法（T+0增强与拆单）的全生命周期。

## ---

**2\. WorldQuant Alpha Factory 核心方法论解构**

### **2.1 公式化Alpha（Formulaic Alphas）的数学本质**

WorldQuant模式的基石是“公式化Alpha”。与黑箱模型（Black-box Models）不同，公式化Alpha是由明确的数学表达式构成的交易信号。其优势在于可解释性强、计算效率高，且便于进行大规模的统计检验。

根据Kakushadze在*101 Formulaic Alphas*中的定义，一个典型的Alpha是一个将历史价格和成交量数据映射为目标仓位或预测收益的函数 ![][image1] 4。

**典型因子结构解析：**

以WorldQuant Alpha \#001为例：

![][image2]  
这个复杂的公式背后蕴含了深刻的市场逻辑：它捕捉了下跌过程中的波动率放大效应与价格反转的非线性关系。SignedPower 增加了对极端值的敏感度，Ts\_ArgMax 寻找了时间序列上的极值点，而 Rank 操作则将信号横截面化，使其不仅是一个绝对值的预测，更是一个相对强弱的排序。

### **2.2 模拟平台（WebSim/Brain）的工业化流程**

WorldQuant的Brain平台不仅仅是一个回测工具，它是一套标准化的Alpha生产流水线。其核心组件包括：

* **数据原语（Data Primitives）**：标准化的OHLCV（开高低收量）数据，以及延迟调整后的基本面数据。  
* **算子库（Operator Library）**：包括时间序列算子（ts\_mean, ts\_decay\_linear）、横截面算子（rank, scale）和逻辑算子。  
* **中性化与标准化（Neutralization & Standardization）**：在模拟的早期阶段强制进行行业中性化（Industry Neutralization）和市值中性化，以确保挖掘出的Alpha不是简单的风格（Style）暴露 2。  
* **性能评估矩阵**：不仅仅看年化收益（Return），更关注夏普比率（Sharpe）、换手率（Turnover）和适应度（Fitness）。Fitness定义为 ![][image3]，这直接惩罚了高换手但收益微薄的策略，迫使研究员寻找更稳健的信号。

### **2.3 遗传规划（Genetic Programming）在因子挖掘中的应用**

WorldQuant模式的自动化延伸是利用遗传规划（GP）进行因子挖掘。GP通过模拟生物进化过程（选择、交叉、变异），在庞大的函数空间中搜索最优的Alpha表达式。

传统的GP方法在A股应用中存在“过拟合”和“搜索效率低”的问题。最新的研究（如*AlphaEvolve*和*AlphaGen*）引入了强化学习（RL）来指导搜索过程。RL Agent不再随机变异公式，而是学习如何一步步构建公式（例如，先选择一个动量算子，再选择一个去噪算子），从而生成的因子不仅样本内表现好，样本外泛化能力更强 14。

**表 2-1：传统GP与现代RL驱动的因子挖掘对比**

| 维度 | 传统遗传规划 (Standard GP) | 强化学习驱动挖掘 (RL/AlphaGen) |
| :---- | :---- | :---- |
| **搜索策略** | 随机变异、交叉 | 策略梯度下降，有目的的构建 |
| **目标函数** | 单一的IC或夏普比率 | 综合考虑IC、多样性（Diversity）及互信息 |
| **过拟合风险** | 极高，容易陷入局部最优 | 较低，通过预训练模型（Pre-training）引入先验知识 |
| **生成效率** | 低，需要数百万次迭代 | 高，生成路径更短且有效率更高 |
| **因子结构** | 往往极其复杂，缺乏可解释性 | 倾向于生成结构简洁、逻辑清晰的因子 |

## ---

**3\. 中国A股市场微观结构与量化约束深度分析**

在将WorldQuant模式落地中国之前，必须对A股的特殊约束进行数学建模和工程规避。

### **3.1 T+1 交易制度的Alpha衰减模型**

A股的T+1制度意味着任何在 ![][image4] 日建立的多头仓位，必须暴露至少一晚的隔夜风险，直到 ![][image5] 日开盘后才能平仓。这彻底改变了Alpha的评估标准。

假设一个因子的预测半衰期（Half-life）为 ![][image6] 小时。

* 在美国（T+0）：只要 ![][image7]，因子即可盈利。  
* 在A股（T+1）：必须要求 ![][image8] 小时（或至少跨越隔夜时段）。

这意味着，WorldQuant 101 Alpha中大量的“反转因子”（Reversion Factors），其逻辑是“早盘跌多了午盘会涨回来”，在A股是无法直接交易的。如果早盘买入，午盘涨回来后无法卖出，必须等到次日。而次日往往受隔夜美股或政策消息影响，产生巨大的低开（Gap Down），吞噬所有日内利润。

**适应性策略：**

1. **因子筛选**：在挖掘阶段，将预测目标（Label）从“T日收盘价”调整为“T+2日开盘价”相对于“T+1日开盘价”的收益，强制因子预测隔夜跨度。  
2. **T+0工厂（Intraday T0）**：利用底仓（Bottom Position）进行日内回转交易。这是一种工程学上的变通。如果策略持有500只股票，每只股票有10万股底仓，那么日内算法可以卖出这10万股并买回，从而实现事实上的T+0交易。这成为了中国量化私募（如九坤、幻方）的标准配置 5。

### **3.2 涨跌停板的流动性黑洞与数据清洗**

涨跌停板制度不仅限制了价格，更摧毁了流动性。

**回测陷阱（Look-ahead Bias）：**

在标准回测框架中，如果某只股票在 ![][image4] 日涨停（收盘价=涨停价），简单的回测引擎会假设我们可以按收盘价买入。事实上，涨停板上往往堆积了巨额封单，买单成交概率极低。

**数据处理规则：**

* **输入端过滤**：在计算Alpha时，需剔除当下处于涨跌停状态的股票。  
* **执行端模拟**：构建“涨停概率模型”。如果模型预测某股票未来10分钟涨停概率超过80%，则执行算法应提前抢单（扫板策略）或彻底放弃（避免高位接盘）。  
* **因子修正**：涨跌停股票的成交量通常失真（缩量涨停）。在使用基于量的因子（如VWAP、Turnover）时，必须对涨跌停当日的数据进行插值或剔除，否则会引入极大的噪音。

### **3.3 散户行为与北向资金（Smart Money）**

A股的散户占比虽然在下降，但仍贡献了主要的流动性和波动率。这导致了显著的“非理性繁荣”和“踩踏式下跌”。

* **龙虎榜数据（Dragon & Tiger List）**：交易所每日公布涨跌幅偏离值最大的前五名买卖席位。这是A股独有的Alpha源。量化策略可以通过NLP技术分析龙虎榜，识别知名游资（Hot Money）的动向。  
* **北向资金（Northbound Capital）**：通过沪港通/深港通流入的资金被视为“聪明钱”。实证研究表明，北向资金的净流入与次日A股收益率呈显著正相关。WorldQuant模式中的“资金流因子”在A股应特指“北向资金流” 11。

## ---

**4\. 顶级量化私募（High-Flyer/DeepSeek等）的最新模式演进**

用户特别关注“最新量化私募模式”。目前，中国量化界正处于从“多因子线性组合”向“端到端深度学习”转型的关键期。

### **4.1 幻方量化（High-Flyer）与DeepSeek：AI的终极形态**

幻方量化是这一转型的领军者。其孵化的DeepSeek（深度求索）不仅是一个大模型团队，更是其量化方法论的自然延伸 16。

**从量化到AGI的逻辑跃迁：**

传统的量化模型（如WorldQuant）是“小模型、多因子”，即训练数千个小公式，然后线性加权。幻方发现，随着因子数量的增加，线性模型的边际收益递减（多重共线性严重）。为了突破天花板，他们转向了“大模型、端到端”。

**核心特征：**

1. **超级符号（Super-Symbol）**：不再为每一只股票训练单独的模型，而是将全市场5000只股票视为一个整体，训练一个通用的Transformer模型。该模型学习的是“市场普遍规律”（如：缩量三连阴后放量必涨），而非某只股票的个性。  
2. **端到端学习（End-to-End Learning）**：输入不再是人工挖掘的因子（如RSI），而是原始的Tick级行情数据（Order Book snapshots）。深度神经网络（DNN）自动提取特征，直接输出预测收益。  
3. **算力暴力美学**：幻方/DeepSeek拥有数万张A100/H800显卡集群。这种算力规模允许他们训练参数量达千亿级别的金融大模型，这是个人投资者或小团队无法复制的护城河 18。

### **4.2 九坤与衍复：T0增强与高频机器学**

与幻方押注AGI不同，九坤（Ubiquant）和衍复（Yanfu）在“中低频Alpha \+ 高频T0”模式上做到了极致。

**双层Alpha架构：**

* **Layer 1：选股Alpha（Holding Alpha）**。使用机器学习模型（如XGBoost/LightGBM）预测未来3-5天的收益，决定底仓持有的一揽子股票（通常对标中证500或中证1000指数）。  
* **Layer 2：交易Alpha（Execution Alpha）**。在持有底仓的基础上，叠加一个高频T0策略。该策略预测未来1分钟的价格走势，利用底仓进行日内高抛低吸。  
* **收益构成**：年化20%的收益中，可能10%来自于选股（Beta+Alpha），另外10%来自于T0交易的“辛苦钱”。这种模式对执行系统的延迟和稳定性要求极高。

### **4.3 最新论文趋势：AlphaNet与符号回归**

学术界与业界在2024-2025年的交汇点在于解决深度学习在金融时间序列上的“信噪比”问题。

* AlphaNet V4 20：这篇论文提出了一种结合了特征提取层（Feature Extraction Layer）和时间序列注意力机制的网络。它不是直接把价格扔进LSTM，而是先通过一层内置的算子（如ts\_corr, ts\_std）对数据进行预处理，让神经网络“学会像Quant一样思考”。这实际上是将WorldQuant的算子逻辑内嵌到了神经网络的层结构中。  
* AlphaFormer 15：利用Transformer架构进行符号回归（Symbolic Regression）。它将数学公式视为一种“语言”，通过预训练模型直接生成能解释市场的高IC公式。这解决了传统遗传算法搜索慢的问题。

## ---

**5\. 适配A股的“Alpha Factory”全流程构建方案**

基于上述分析，我们为用户设计一套既吸取WorldQuant精髓，又适配A股现状，且个人/小团队可落地的交易流程。

### **5.1 阶段一：数据工程与环境搭建（The Infrastructure）**

这是地基，决定了后续所有策略的真实性。建议使用 **Qlib** 作为核心框架 22。

**1\. 数据源选择：**

* **基础数据**：推荐使用 **BaoStock**（免费、基础日线）或 **Tushare Pro**（低成本、包含复权因子）。对于进阶需求，**AkShare** 是极佳的开源选择，覆盖了龙虎榜、北向资金等特色数据 24。  
* **高频数据**：若需做T0研究，需购买Level-2快照数据（千元/年级别）。  
* **风险因子库**：Barra数据昂贵，建议使用开源实现或通过PCA（主成分分析）自建风险因子库 25。

**2\. 动态股票池（Universe）构建规则：**

在代码中必须实现一个动态过滤器 Universe(T)：

* 剔除上市不满6个月的新股（避免新股炒作噪音）。  
* 剔除ST、\*ST股票（避免退市风险）。  
* 剔除当日停牌股票（Volume=0）。  
* 剔除流动性枯竭股票（如日均成交额 \< 3000万）。  
* 剔除涨跌停状态股票（对于买入操作剔除涨停，对于卖出操作剔除跌停）。

### **5.2 阶段二：因子挖掘工厂（The Mining Engine）**

这是WorldQuant模式的核心。我们采用 **遗传规划（GP）** 与 **人工逻辑** 相结合的方式。

**1\. 算子库的本土化改造：**

WorldQuant的标准算子需针对A股进行调整。

* rank(x) \-\> industry\_neutral\_rank(x)：A股板块轮动效应极强（如“煤飞色舞”）。如果不做行业中性化，你的Alpha可能只是在赌板块。  
* ts\_decay(x, 10\) \-\> ts\_decay(x, 5)：A股节奏更快，衰减窗口应缩短。  
* **新增A股特色算子**：  
  * limit\_distance(x)：当前价距离涨停价的百分比。  
  * north\_flow(x)：北向资金净流入。  
  * retail\_sentiment(x)：基于东方财富/雪球帖子的情绪指标（若有爬虫数据）。

**2\. 挖掘流程（基于gplearn的改良）：**

* **目标函数（Fitness）**：![][image9]。  
* **Label定义**：Ref(Open, \-2) / Ref(Open, \-1) \- 1。即预测“明天开盘”到“后天开盘”的收益。这完美规避了T+1限制，因为我们在T日收盘前决策，T+1日开盘买入，T+2日开盘卖出。

### **5.3 阶段三：因子合成与机器学习（The Combination Layer）**

不要使用简单的线性加权（Linear Regression）。A股市场存在显著的非线性效应（例如：市值越小，反转因子越强；市值越大，动量因子越强）。

**推荐模型：LightGBM / XGBoost**

* **特征（Features）**：输入阶段二挖掘出的前500个低相关性公式化Alpha。  
* **标签（Label）**：行业中性化后的超额收益。  
* **训练方案（Rolling Training）**：  
  * 训练集：过去24个月。  
  * 验证集：随后3个月。  
  * 测试集：再后1个月。  
  * **滚动频率**：每月重新训练一次模型，以适应市场风格切换（Regime Change）。

**关键技巧：特征正交化（Orthogonalization）** 在输入树模型前，必须对所有Alpha进行施密特正交化或PCA处理，剔除共线性。否则，树模型会随机选择相关性高的因子，导致特征重要性（Feature Importance）失真，且模型鲁棒性下降 25。

### **5.4 阶段四：风险控制与组合优化（Risk & Optimization）**

这是活下来的关键。

**1\. 风险模型（Barra CNE6 Lite版）：**

如果买不起商用Barra数据，可以用以下逻辑自建：

* **市值因子**：Log(Market\_Cap)。  
* **行业因子**：One-hot编码的中信一级行业。  
* **Beta因子**：过去252天相对于沪深300的回归斜率。  
* **动量因子**：过去500天收益（剔除最近20天）。

**2\. 组合优化器（Optimizer）：**

使用 cvxpy 或 scipy.optimize 求解以下凸优化问题：

![][image10]  
**约束条件（Constraints）：**

* **![][image11]**（满仓）。  
* ![][image12]（个股权重上限1%，分散风险）。  
* ![][image13]（行业偏离不超过5%）。  
* ![][image14]（日双边换手率限制在20%以内，控制T+1冲击）。

### **5.5 阶段五：执行算法（The Execution）**

对于个人或小资金，不需要复杂的拆单算法，但需要智能执行。

VWAP/TWAP的简化实现 27：

* 不要在9:30开盘瞬间满仓买入（流动性差，冲击成本高）。  
* 将订单拆分为10份，在9:35 \- 10:30, 13:00 \- 14:00等流动性充裕的时段，分批以限价单（Limit Order）挂在买一档。  
* **集合竞价策略（Call Auction）**：除非Alpha极强，否则避开9:25的开盘撮合，因为存在大量的“虚假申报”和价格操纵 29。

## ---

**6\. 技术实现细节与代码架构建议**

为了实现上述流程，建议采用以下技术栈：

**表 6-1：推荐技术栈与工具**

| 组件 | 推荐工具 | 理由 |
| :---- | :---- | :---- |
| **数据库** | **DolphinDB** 31 | 国产高性能时序数据库，内置了WorldQuant 101 Alpha函数库，计算速度比Python快10-100倍，适合存储Tick和分钟数据。 |
| **回测框架** | **Qlib** (Microsoft) 22 | 专为AI量化设计，内置了A股数据源、LightGBM工作流和Rolling Training机制，完美契合本方案。 |
| **因子挖掘** | **gplearn** (Python) | 基于遗传编程的符号回归库，易于扩展自定义算子。 |
| **优化器** | **CVXPY** | 凸优化标准库，语法接近数学公式，易于编写Barra约束。 |
| **交易接口** | **vn.py** / **XtQuant** | 连接券商柜台（CTP/QMT），XtQuant支持Python直接下单，适合A股。 |

**核心代码逻辑示例（Qlib配置）：**

Python

\# Qlib 初始化与A股数据加载  
import qlib  
from qlib.config import REG\_CN  
from qlib.contrib.model.gbdt import LGBModel  
from qlib.contrib.strategy import TopkDropoutStrategy

\# 1\. 初始化环境，指定A股数据目录  
qlib.init(provider\_uri='\~/.qlib/qlib\_data/cn\_data', region=REG\_CN)

\# 2\. 定义数据处理器（Label \= T+2 Open / T+1 Open \- 1）  
data\_handler\_config \= {  
    "start\_time": "2020-01-01",  
    "end\_time": "2024-12-31",  
    "fit\_start\_time": "2020-01-01",  
    "fit\_end\_time": "2022-12-31",  
    "instruments": "csi500",  
    "infer\_processors":,  
    "learn\_processors":,  
    "label":  \# 关键：跨日Label定义  
}

\# 3\. 训练LightGBM模型  
model \= LGBModel(loss='mse', colsample\_bytree=0.8, learning\_rate=0.05, sub\_sample=0.7)  
model.fit(dataset)

\# 4\. 回测策略（TopkDropout：每次换仓只换掉评分最低的，减少换手）  
strategy \= TopkDropoutStrategy(topk=50, n\_drop=5, hold\_thresh=1)

## ---

**7\. 结论与展望**

将WorldQuant模式移植到中国A股市场，绝非简单的复制粘贴。它是一场\*\*“降维打击”与“本土化生存”的结合\*\*。

1. **降维打击**：利用WorldQuant的工业化挖掘体系（GP/AlphaGen）和高维非线性组合模型（LightGBM/AlphaNet），相对于传统A股基本面选股或简单多因子模型，具有显著的信息处理优势。  
2. **本土化生存**：必须深刻敬畏A股的T+1制度和涨跌停规则。通过调整Label定义（预测隔日开盘价）、实施严格的流动性过滤、以及引入日内T0增强，才能将理论上的Alpha转化为落袋为安的利润。

对于个人投资者或小型量化团队，未来的机会不在于与幻方、九坤比拼算力和高频速度，而在于**中频（2-5天持仓）的深度挖掘**。利用开源的先进架构（如AlphaNet、Qlib），结合对A股特色数据（北向、龙虎榜）的深刻理解，构建一个“小而美”的Alpha工厂，是当下最优的路径。

此报告不仅提供了一套方法论，更是一份实战指南。请遵循“数据为王、逻辑为骨、AI为翼”的原则，开启您的A股量化之旅。

---

**参考文献引用索引：**

* WorldQuant方法论与WebSim平台：1  
* 101 Formulaic Alphas及DolphinDB实现：4  
* High-Flyer/DeepSeek及最新私募模式：16  
* 深度学习模型（AlphaNet/AlphaFormer）：15  
* A股T+1与微观结构：5  
* Qlib框架与工作流：22  
* 风险模型与PCA：25

#### **引用的著作**

1. Finding Alphas.pdf, 访问时间为 一月 20, 2026， [https://asset.quant-wiki.com/pdf/Finding%20Alphas.pdf](https://asset.quant-wiki.com/pdf/Finding%20Alphas.pdf)  
2. World Quant Brain: How to Build Alphas & Explore Quant Research \- Cognitive Story, 访问时间为 一月 20, 2026， [https://cognitivestory.co.in/worldquant-brain-guide-to-build-alphas/](https://cognitivestory.co.in/worldquant-brain-guide-to-build-alphas/)  
3. WorldQuant BRAIN: Crowdsourcing Quantitative Research, 访问时间为 一月 20, 2026， [https://www.worldquant.com/brain/](https://www.worldquant.com/brain/)  
4. 101 Formulaic Alphas \- ResearchGate, 访问时间为 一月 20, 2026， [https://www.researchgate.net/publication/289587760\_101\_Formulaic\_Alphas](https://www.researchgate.net/publication/289587760_101_Formulaic_Alphas)  
5. The Future of Trading: India's Leap into T+0 Settlement \- m.Stock, 访问时间为 一月 20, 2026， [https://www.mstock.com/articles/t0-same-day-trade-settlement](https://www.mstock.com/articles/t0-same-day-trade-settlement)  
6. 1 rule really reduce speculation? Evidence from Chinese Stock Index ETF, 访问时间为 一月 20, 2026， [https://www.liuyanecon.com/wp-content/uploads/T1ETF\_pubv.pdf](https://www.liuyanecon.com/wp-content/uploads/T1ETF_pubv.pdf)  
7. Rule 3100\. Limit Up-Limit Down Plan and Trading Halts on PSX \- Rules | Nasdaq PHLX, 访问时间为 一月 20, 2026， [https://listingcenter.nasdaq.com/rulebook/phlx/rules/phlx-psx-legacy-3000](https://listingcenter.nasdaq.com/rulebook/phlx/rules/phlx-psx-legacy-3000)  
8. Market Structure \- Research and Analysis \- SEC.gov, 访问时间为 一月 20, 2026， [https://www.sec.gov/securities-topics/market-structure-analytics/research-analysis-market-structure](https://www.sec.gov/securities-topics/market-structure-analytics/research-analysis-market-structure)  
9. In-Depth Analysis of a-Share Stock Transaction Rules: From Bidding Mechanisms to Practical Strategies \- Oreate AI Blog, 访问时间为 一月 20, 2026， [https://www.oreateai.com/blog/indepth-analysis-of-ashare-stock-transaction-rules-from-bidding-mechanisms-to-practical-strategies/de1f7c24ba5fa8c9cc44257dbbc46d1b](https://www.oreateai.com/blog/indepth-analysis-of-ashare-stock-transaction-rules-from-bidding-mechanisms-to-practical-strategies/de1f7c24ba5fa8c9cc44257dbbc46d1b)  
10. (PDF) Innovative Alpha Strategies for the Chinese A-Share Market: Stable Turnover Momentum Enhanced by Idiosyncratic Volatility \- ResearchGate, 访问时间为 一月 20, 2026， [https://www.researchgate.net/publication/391504090\_Innovative\_Alpha\_Strategies\_for\_the\_Chinese\_A-Share\_Market\_Stable\_Turnover\_Momentum\_Enhanced\_by\_Idiosyncratic\_Volatility](https://www.researchgate.net/publication/391504090_Innovative_Alpha_Strategies_for_the_Chinese_A-Share_Market_Stable_Turnover_Momentum_Enhanced_by_Idiosyncratic_Volatility)  
11. The Impact of the Shanghai-Hong Kong Stock Connect Program on the A-H Share Premium \- International Journal of Business, 访问时间为 一月 20, 2026， [https://ijb.cyut.edu.tw/var/file/10/1010/img/838/V26N1-5.pdf](https://ijb.cyut.edu.tw/var/file/10/1010/img/838/V26N1-5.pdf)  
12. Finding Alphas: A Quantitative Approach to Building Trading Strategies \- ResearchGate, 访问时间为 一月 20, 2026， [https://www.researchgate.net/publication/308096314\_Finding\_Alphas\_A\_Quantitative\_Approach\_to\_Building\_Trading\_Strategies](https://www.researchgate.net/publication/308096314_Finding_Alphas_A_Quantitative_Approach_to_Building_Trading_Strategies)  
13. World Quant Brain Alpha Documentation | PDF | Stocks | Technical Analysis \- Scribd, 访问时间为 一月 20, 2026， [https://www.scribd.com/document/728780335/World-Quant-Brain-Alpha-Documentation](https://www.scribd.com/document/728780335/World-Quant-Brain-Alpha-Documentation)  
14. Alpha Mining and Enhancing via Warm Start Genetic Programming for Quantitative Investment \- arXiv, 访问时间为 一月 20, 2026， [https://arxiv.org/html/2412.00896v1](https://arxiv.org/html/2412.00896v1)  
15. AlphaFormer: End-to-End Symbolic Regression of Alpha Factors ..., 访问时间为 一月 20, 2026， [https://openreview.net/forum?id=TOMU10xBZA](https://openreview.net/forum?id=TOMU10xBZA)  
16. DeepSeek founder Liang's funds surge 57% as China quants boom \- The Business Times, 访问时间为 一月 20, 2026， [https://www.businesstimes.com.sg/startups-tech/startups/deepseek-founder-liangs-funds-surge-57-china-quants-boom](https://www.businesstimes.com.sg/startups-tech/startups/deepseek-founder-liangs-funds-surge-57-china-quants-boom)  
17. High-Flyer posts 57% gain as China's quant hedge funds outperform ..., 访问时间为 一月 20, 2026， [https://www.hedgeweek.com/high-flyer-posts-57-gain-as-chinas-quant-hedge-funds-outperform/](https://www.hedgeweek.com/high-flyer-posts-57-gain-as-chinas-quant-hedge-funds-outperform/)  
18. 10+ DeepSeek Facts and Statistics You Need to Know \- InvGate's Blog, 访问时间为 一月 20, 2026， [https://blog.invgate.com/deepseek-statistics](https://blog.invgate.com/deepseek-statistics)  
19. How does DeepSeek-R1 work? \- Caro Robson, 访问时间为 一月 20, 2026， [https://www.carorobson.com/post/how-does-deepseek-r1-work](https://www.carorobson.com/post/how-does-deepseek-r1-work)  
20. (PDF) Alphanetv4: Alpha Mining Model \- ResearchGate, 访问时间为 一月 20, 2026， [https://www.researchgate.net/publication/384902540\_Alphanetv4\_Alpha\_Mining\_Model](https://www.researchgate.net/publication/384902540_Alphanetv4_Alpha_Mining_Model)  
21. ALPHAFORMER: END-TO-END SYMBOLIC REGRES- SION OF ALPHA FACTORS WITH TRANSFORMERS \- OpenReview, 访问时间为 一月 20, 2026， [https://openreview.net/pdf/fd934e6d454debb520e20356ad2e1205a04d2ac1.pdf](https://openreview.net/pdf/fd934e6d454debb520e20356ad2e1205a04d2ac1.pdf)  
22. Python \+ Qlib AI: Algorithmic Trading \- Modbus & Embedded Systems, 访问时间为 一月 20, 2026， [https://modbus.pl/2025/02/07/python-qlib-ai-algorithmic-trading/](https://modbus.pl/2025/02/07/python-qlib-ai-algorithmic-trading/)  
23. Quick Start — QLib 0.9.7 documentation, 访问时间为 一月 20, 2026， [https://qlib.readthedocs.io/en/stable/introduction/quick.html](https://qlib.readthedocs.io/en/stable/introduction/quick.html)  
24. A curated list of insanely awesome libraries, packages and resources for Quants (Quantitative Finance) \- GitHub, 访问时间为 一月 20, 2026， [https://github.com/wilsonfreitas/awesome-quant](https://github.com/wilsonfreitas/awesome-quant)  
25. Build a PCA Machine Learning Model in Python, 访问时间为 一月 20, 2026， [https://insidelearningmachines.com/pca\_machine\_learning/](https://insidelearningmachines.com/pca_machine_learning/)  
26. Build statistical factor models with PCA \- PyQuant News, 访问时间为 一月 20, 2026， [https://www.pyquantnews.com/the-pyquant-newsletter/build-statistical-factor-models-with-pca](https://www.pyquantnews.com/the-pyquant-newsletter/build-statistical-factor-models-with-pca)  
27. Trade implementation \- Algorithmic strategies vwap twap and pov \- PastPaperHero, 访问时间为 一月 20, 2026， [https://www.pastpaperhero.com/resources/cfa-level3-trade-implementation-algorithmic-strategies-vwap-twap-and-pov](https://www.pastpaperhero.com/resources/cfa-level3-trade-implementation-algorithmic-strategies-vwap-twap-and-pov)  
28. VWAP and TWAP: Optimize Your Orders with Alpaca's Trading API, 访问时间为 一月 20, 2026， [https://alpaca.markets/learn/optimize-your-orders-with-vwap-and-twap-on-alpaca](https://alpaca.markets/learn/optimize-your-orders-with-vwap-and-twap-on-alpaca)  
29. AI-based algorithmic trading strategies (with Python tutorial) | by Dave Davies | Online Inference | Dec, 2025 | Medium, 访问时间为 一月 20, 2026， [https://medium.com/online-inference/ai-based-algorithmic-trading-strategies-with-python-tutorial-ff419449f8cb](https://medium.com/online-inference/ai-based-algorithmic-trading-strategies-with-python-tutorial-ff419449f8cb)  
30. The influence of call auction algorithm rules on market efficiency \- ResearchGate, 访问时间为 一月 20, 2026， [https://www.researchgate.net/publication/222084163\_The\_influence\_of\_call\_auction\_algorithm\_rules\_on\_market\_efficiency](https://www.researchgate.net/publication/222084163_The_influence_of_call_auction_algorithm_rules_on_market_efficiency)  
31. WorldQuant 101 Alphas, 访问时间为 一月 20, 2026， [https://docs.dolphindb.com/en/Tutorials/wq101alpha.html](https://docs.dolphindb.com/en/Tutorials/wq101alpha.html)  
32. 101 Alphas | PDF \- Scribd, 访问时间为 一月 20, 2026， [https://www.scribd.com/document/660475741/101-alphas](https://www.scribd.com/document/660475741/101-alphas)  
33. AlphaForge: A Framework to Mine and Dynamically Combine ..., 访问时间为 一月 20, 2026， [https://ojs.aaai.org/index.php/AAAI/article/view/33365](https://ojs.aaai.org/index.php/AAAI/article/view/33365)  
34. A Comprehensive Guide to Qlib's Portfolio Strategy ... \- Vadim's blog, 访问时间为 一月 20, 2026， [https://vadim.blog/qlib-portfolio-strategy](https://vadim.blog/qlib-portfolio-strategy)  
35. qlib/examples/tutorial/detailed\_workflow.ipynb at main · microsoft/qlib \- GitHub, 访问时间为 一月 20, 2026， [https://github.com/microsoft/qlib/blob/main/examples/tutorial/detailed\_workflow.ipynb](https://github.com/microsoft/qlib/blob/main/examples/tutorial/detailed_workflow.ipynb)  
36. Barra Risk Model \- Medium, 访问时间为 一月 20, 2026， [https://medium.com/@humblebeyondx/barra-risk-model-776eb1e48024](https://medium.com/@humblebeyondx/barra-risk-model-776eb1e48024)  
37. Study On The Style Factors Of Barra CNE6 Model \- Globe Thesis, 访问时间为 一月 20, 2026， [https://globethesis.com/?t=2530306770462714](https://globethesis.com/?t=2530306770462714)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIgAAAAZCAYAAADqgGa0AAAEgUlEQVR4Xu2ZXahVRRTHV6iQ2oemFH1RV0yIlAo1CQwMCirIJA1CQS76kIoQGFoIiiCSmqCVIX3RB0SZYkpUIj3pg0pgPij2eBFRKEiI8iGpXD/WzD1z5uy9z97efezc4/zgz9l79sc5s2atNWvmiCQSiUQikchgneq86j/VrUH7UtVZ1RnVkqC9Hfepjos9m6X3VCMG7x6+YDdsdkwadsNmF6Rht55htuqE6pmofYtUH8xFqrdVo1UzVZdcG/Sr3nHHvQA2+0ea7TZdrs5uXc1i1UuqL1Ujg3Y/sGXh2U2qO9z5K6q/xIwGz7u2XgGbkSlCu70obez2iOqDkhrnnhkKy6Q1jXv9KBaxDMxY/0DERNVGsQ5eVO1U3aC6SXVzcB/wDrLDYznnMadVH8WNXcI0abWX10nVx6p7B+9uBbths6nSsBs22yytdmuCOXiBar3YHMUAce61RvWzu1b4ogrcqNrqjp8S6xyDhzf/5K4xWFlpj2lghTsmEs6p+lQPDt7RDPPt+2JOUeQccFnaRNP/zHNi0wEw4PQZWz6s2q86qPpKdZu7JwS7AU7i7cbz1CalYHB46J74gjJK9bXYj6mL190n2cIfw8uq1WI1wWtBu4fphRoEmEv/Va1UzR28o5XQSYr4Q8zY3QpT37vu+E6xDOAhSG5RvaD6JroG2M3j7YbN5gXthZA5vpN8JwgHsQ7yHASv3iXm6XvEIsXDVELNcLc7x4mIGirzHf6mDMo4CN9H9hofX+giihyEcZskZqPtYpnZ4+3m8XbDZnmZtwmihujxkekJX1o6FZUkz0Ho5IdiHd4tjQISnlStCs6B6xReWauNuOaIz0Po+7WcXhhsBqoKRQ6Cg/vBpkZ7NriWZ7csm2WCYagxfGQCPz70wjKwpn5TbEpqR56DkP62iXn9W+4Tpogt0f4Wm2fDInaD2BQZ86pqRtRGv6iryEw44adihd6fqt/dMWm60/A7no4b21DkIAw4fXpI9a3qdjGbUcB6u8WFf5bNWmAAPhFzEOZ/ClMc5pBYNJdljNg7qJCpuNuR5SBzVL+IRflRae1Qr/G9akLcWECWg+DkD4hl289Uh8UcozbwOlYMDK5fNv3qzvPqkTwYXKalqhmE6MXDKYQHVAuleZe0V6G4/kGyVx1ZxA5CMGI3VjDY/n5pZNza4EvZHGKJ5+FLvgjOO0GcQZ4QiwjmSlYxtXe0w/DbGbQquku1Viwoyd7tiB2ELQqy0KNOtQcVhc1esWzBNBO2Px6cd4LYQWCfWEcni0VWr8OWwhGxmqhM1o0dBKckkN4Q2xL4XKrXNYVQlA6IOci1rOAhy0FmiS1t6fh8KWe04QzbCvSzLFkOAmQOgouMcsB91gJLO6aWujaI2I9YLuWmhywHCaOBYyKrzLuGKyxHq/Qvz0GA4OKcDILj1TLdsKVN9jglVuAMBVYcvOs3KVdFM/cCDuKPgY5RrDLVUAf1SzUjDhdYlvbFjW1gu5z/UAAHCf/6wEbUb3xS/Hbrf0qJklRdISYSiUQikUgkEtcvVwC8H9yUzRFt9QAAAABJRU5ErkJggg==>

[image2]: <data:image/png;base64,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>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAREAAAAZCAYAAAAWsBpXAAALs0lEQVR4Xu2bCahuVRXHV1RSNNicUeE1tWwAiwYbJC0aNCsqe1go8SIiKyMaLUu8j7KQDJqkiOqVkVrZhEoDEh8WmRUNUBkNdM1XUVFBWJSN++c6f8866+5zvnO9N9571/2Hhe/sfYa11/Dfa+3vatbQ0NDQsO1x5yIrTZrsY3KQNezzOLTI2UVOyhMNDQ0Nc3BqkTOK3DdPNDQ0NCxDq0IaGho2BaqQdxR5cBi7dZHbheubM26ZByZwB9vY/Q1bgNsWua7I74vsKXJ9kbsV+VCR53T33L/Id4v8qsifity+G2/YGpxpQwIBzyjysTQmnFXkcnN/IJ8s8sEg+OsWN969/+PhNi/mnlnkgiK36q4fb0O7TMlbi9zdH2vYCO5T5NtFDg9jdyzyzyJ/LPLAbgxSeVaRTxT5bzfWsDW4S5HX5kGbJpHji5xS5Cfm/nhukBcV+U+RT5m/e6OAfI7Mg3sZc0gE4sBex4Xri83t8z3ryeIH3dgZ5vbaVeTTNoz3hpnAKV8pckWeMK9IvmZeGgoE125rJLLVeJ6tr0LAFImAexb5hdX9AYEwfqH1u/JcPKbIP2zfagnmkAgEsDC3i65/bX7OpKosEkuu1H5kvlk2bAAEL8Y8OU8UXFbkPWmMv1+gavltGm/YHM7NAx2WkcjR5hVjzR/ssvj2miL3SnPLcLrViWlvYg6JnGZ+OC28xLwljyR67yJrVl8fMX+bPNgwDg7s6Kkx5keHUzeA3jL3hziF+3EUxobxOfybAvfdKQ92YO6u1u8I+RqwG94jXDPHPVNAp2UBB7jn0iJvzBMdaAW+WOSleWILAYG8Jg92mCKRuKPGxBF+Yz73Flu/4wJsWvOLkuzqNA6w+xy7Zh/layH7mus8Jswhkc+an+8Jny9yYLgGIleq7AziOwIbzanGFLdj14D3ZIKC3PNYhmyX3wfwX34eG43ZibwgZ/M8usUKLF9PgkoDgyLvLvIkW6+UwGI4D6HXfrF5u0OgXl/kTeE+4XFFriry4yLfL/LsIueZn8GARxX5jnk5TnWDLgQuzlV7RQCQ5D80P+A9xry3/UaRL9vwL+jQj0O0K4v82fyw8SJbH0QZzFP6ZzJET3TZafWg3go8xdzuT80THaZIRMmOP/BbBBsEPv2ADZMKPMh8x12Yn6d83XytOifIgg4AQqXiwd+QnmxCQH7B/GAXYMf3m/uByuAJ5m0C/npBdw/An7wPkqbCpeXAZxzw/7zIQ/tbb8AyEkEfvjcFYpu1s65cZUfwrh3mPyAQeweHuROK/M48FkGM4wfYMI6V+MQYhP9383UTt9iL/Pl3kXNsffyBDxf5i/W+im0Z/iCv/ma9Px5mHvvonDdecoO5L1mfGwDd8B+5+nTzb6x191HpLgU9I47MgQOjZ8BMBAPzP+3GtBvSP0egNAZ7ZfdvhOf+ah4MAHJ4iHmQMkcAEEwEFdeAMXZSEoZkoXISCeGoS6xPknPNS3sOFWFSxjFE3l1qwJAEfnQkxBad9v/AO81/EeAgu4YpElErw2EgZxjYkkNCdtprijzRhroryXhmVxh7n3ngE3TsjAQ09n+d9ZUmAiFxPkZykDDMAelBHABa5PearwmfQfj4jOTBfxDcIea+Od38WxAO/gOHm/9KSLJHLCMRYoT3TuF+1sc7lfYYjiryGXOduffV3bjinfWybm1yimMSPsbx8f6YrXbj+IUExiaPNLc/9q5tBJAVm7Zig3shHPQe8wdz3BPzjHuVG6qqlBtg1Vw3fM+zkAv6Q0y0grPAwwRzJpLsMAUL7HlYGCfIlfQCi8m7OywYD64uNHcKDuJ57j3WfCF/sKGDcD6GWrEeC3OnHWk9ScXSnedxFkE9Bx83NxoGZn2bJZAVGycHQBCh71gVAqZIRAn4S+t/dSCgGKs9c6r5XPQL9scPq921dmp2N/QTICmSB1/gx4X18SE98CPP8ysHsUJQE8wk5AHmrcW7zG0KsZ9tfSWM7tKJeCTZFt21sIxE8DPrmQJxyfcgEmKqBt6B/Y4zJ9hIOKr+lLQkfozj3TaMYw7LiXd+vOB7ED72o3oRZD9VfIB57stVNH7BP8dY3R/Yltac71AgcI3NlRuCciPqRh4px6igqEyJmQ0BJTDct8w/GoMIKNlZtMAzC/NkFtjRKKcys/IsRlZiwtJidpgYwJQEIEnMe15mntQ4MT4LqBR4JzoT5DEw0AtjkzBTgRfBdyARym4MuBmgP458YZ4IeLP5bj9FNFMkwvqyPxREjOeE2mP9DgrY8Uneb1p/8KqdOpI9wFfIqvm72bmA/Kf30qO/vvsv1+io9phvqGqkWqRdwYckAckgaLPaSCXCNz6XBysQaakiqiGuAZtdbfWqi7XLLrKDYl5xDFbM7YWOfBtiUhzH+NezJDA5qJyIgESw2Q6r+wOQt181rybIC7oE5Qb2gyyUGyvW63ayDVs8YliVyyhi8EWIGFQOCWudwMYCOwqLWA1jJCJjEbyTXSm/MzplDNKHxUfwDQU7iUYZvxk81rxNQycSMe8Cc0CfSgXD7nttkZ8VOXFwR49lBAKmSIT1r9nQH0A+ETEIjFEeRyLOoDrgPgKqBiW3iIHAJ9iVVIKSQ4k0Br4VAxebQ2qZWMAUiax2sgwQe611qIE15HtZeyRiQXEcbZBBUqtCEKieMrGI6Hbrpg7M53uzPxinlVTlROzwzLLc0K+uY9VZFXx0Zx7sAOvCvjmJIgMD9VUwHYzHrkvgSvEIlENJlMWIsChQKTdGaID7MT7PCugQyYtv0r9uBhwAP6L7N86gzIMUbiroqdGb3jKTBeXqVBsjLCORseRljn45Ylkwiawj2WPTg3WDrfeV/EeVis1EXCr7M8FFKCni2YR2TuKK+OKMR7vhGIkQp9yfN6ga+N4e68/VpkAerNlwDVyrlYnvkB2mgH4LG66BVgiioprGHtha+ZNzgm8q14Ts00PMbaHKSe9alhvoht9r9h0FSR0ZLeIUc8LIULAI2eGcX+BQMWkE76RCAex27JYK+BqzR7Ar5vfRa9Iy6QR61eqGgqwgt2XgECv/GnCaOZEclMbn4hXm1chVRZ6c5s60eYE8RiI4O/sDUJVRnTGngICECc4ccALrfoP1rYzIHlxiw58WeUfs3ePOTOAq4ebuzLEFBYodVUL4QBgjERIQPdUqjUGkFXfuKUCICxt+M1Zd0i3G8RRYE7EfwSYje0MA2FCEJBsAdKfFQmLOZn9Q3cZzjFUbJxFt5KCWY0tBicbBz0nWK8V/2RWuM1c2AkPlZEd5BSaHSRAFIGF4N9A7KU8xDkmPE2UwWF0tyRgUWGJXiOpyG5aFkMpuGx7ksgZKYxJoChi4dgaC7jvNDyvnJHzGUeYklM9GqELiIdcUaiTCzkzr9a8iT7NhUGUSIbE40MQnkO4V1leYvOf55lUnFZgqvou6OaowdI3gvdoh+S5+1s6OHaUL5LYsKNWbx4RGV1VCh9nQ7jUS4XtshjHhamA9R5jrdI7NIxHstGY9MaKL4h09qDRBjOMpsImSdxHYD/+yjl3dGLHMDwucWQDmdpj/2hnjG6BPJCaeiR2E3hVzg5hQbgjoVjuDGQUGPbb7Ny8mgOjN+B05KxmRHQh4F8TAIVQGTB7H8308S9BPfVNl1sL8+7yzpgeQLtwTd8+9CXbJK82TE5CU55mX6XNQI5E5ILD5BqQfD8cISGyDjeJ4BD7i+TG/MB/9QEJyHROTuVpMRPD+mg48W/t+jUQgj7GKeiuADuhCXKGr7Ifom3PiGNTsMZU/zOUcqkF5MRXz+k7UO4JvZNtuG+iQkGpkfwS7+UfM18BO9nLz1mFuZXNTSWQ7okYitDF5d29ouBEwJmUYCTj1h0H7OuidrzUnj7fb/CoENBLpUSMRncM1NFRxvnkrQ6/G3wDkANpfQG9/sfkfhb3N5lchoJFIjxqJ6HymoWHbg7OQC8z/v5WNgMPZV+XBmykOteG5C9dTv/40NGwrcDby6DzY0LA/4n+pX8Xe/TSKagAAAABJRU5ErkJggg==>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAaCAYAAACHD21cAAAAsklEQVR4XmNgGAWDELAC8SwicQ0QC0G0MTCUI3OgIBqITwOxIJo4XIwTiNegyjEwAvF8IJ6EJg4CW4GYA8TQAeKlqHJgE0Emg2xFB3DDEoA4AyEOBsZA/BWINdHEQSAdXQAZgGz6z4DpP7xABIivMkA0kgRgznyLLkEIgPwAsg0UOEQDWDSANGKLCpwA2X/YogIr4AHiegaIpitArIAiiwWIA/FdBogGdAyyHeSKUUAXAAB8miZVdxhgdgAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC8AAAAZCAYAAAChBHccAAABMElEQVR4Xu2VvWoCQRSFr4WgaKFJMNgGUgRMlYewSmeXJmCR1Cm0EZInMKCdEEJKwU7yFGn1GVIlYKGV+TmXmyVyd9f9G0aE+eBrzs4wh9nLLpHD4XDYJA9HMe3BA9lmFT6zpkOmAVdwTP8lv+EXHMIW7PyteYcnss0abbiAXf2A4VDf5g98g9WN7Cogi6IET3UYkz78hGuSPr7yRThRWY5k8UDll/AVFlS+jQuSt5eGCsmovFBI+Wt4qzI+8AOeqfwO3qgsiizlPULLB5FmPMKwWp5H5pn8I5MWq+WP4Jzk9k1gtTwftiT/vMfhGNaVTfgUkLOHsi2SWOW9keGFprB2897I7GV5b2T4M2kKK+XL8J5k0Uw9y4KJ8lOSXo+U7AeZGRPld8Y5fNChw+FIzi+M3Etj8RqcqwAAAABJRU5ErkJggg==>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAAZCAYAAAA8CX6UAAAA3UlEQVR4Xu2RIQ7CQBBFB4EhIYSkl0CgkJwARwiuBgcH4CRIBCgkGI6ARPcAaEJQCBIS+D+zDcuUbFvZpD95ovOms52uSJ3qZwp2YG0YOW/rZOjcT/ryHfYGCzAGkfO+u4CZ5/5mJdrcMHU+p4PYE0wbnESbbXh6IuomxmXCBjaerUDmoo4H8cBg0rW2VojWSq91l+wNXZ3LXasHbuAJlqK35PNynn3B+P+naxxT6P/wRQ5gc2wcwxsrtdYDDIxjWCu0Fr8itBavPnctZi866ABaxnXAEWxA07g6lc0HK1s9RX9RtNMAAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,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>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD8AAAAZCAYAAACGqvb0AAACg0lEQVR4Xu2WTahNURTH/0L5lo9e+epRPjKgpBgYmBDKV1KUmQkzAyXK7I30XgZiYsDI4BVSFKG8UgwMRJlRSArJiPLt/2/tfe95657j7nsP18D+1W9wzjr33L32XnvtA2QymUzm/2M3vUDPOreEuL8v14VYrxlPl9BZdIyLlTGdHqUL3f0GK9CcgNf0IN1JZ4d4jP2kL1ysVyjRrfQNfQUby1O6vviQQ785Rj/S1S7Wwil6Hq0zquuYvJ75F2ynj+jicL2Hfqcf6Jr4kGMtLPG2yU+ld+k+H4Ct8hNY8rtcrIyJsD8b6wM1uEGv06XhWgtyGjYmxfSfntv0CxKSV1J60QwfIAdgMU2OJikV7ctBepxOc7FOuQobw+HCvW3hXllyqoZ+OoLy+ChUznqRL3mhrVCn5A/B9ulJOsfFUlEV+YmPi/KczivcV5O7QqcgIflY8nrRMFo7+7sQSyn5KlSW+2ENVZNZF71P5a5xDWD0oqk6NNFJyS+n7+lnWGf3fgtxPVcXHVV76WW6zMU6QQ3vB2xfa6Ujq+gd2ofE5ON+f+ADgW72ezt2wJroTbrSxVJQl1cDLCauZK/RjYXrEfwmeTU4Ja0Eqzp93ZL3aP8+hg1eiZf1mSqU7C1YBYlxsA+umbAVf0tfBtVndBxq/Lq/IfymQSz5qtnRvT9d8s/oIhdLQftcPUgfLhEtnrbQfNjpooYa1TfBffqJbqITwm8aaLVjyVcdc3VLfjKs4+vr7Ay66/iaOCU+ROeimaBWU5VQNva2ZX8Jlrxmb5KLqcR0vp5Ds8w6Ree7yu8EbGW65QhsnGVehJW/p58+pF/pZhf7ayyg92BHW9mXVyaTyWR6wS9yZZRV4/hE8wAAAABJRU5ErkJggg==>

[image9]: <data:image/png;base64,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>

[image10]: <data:image/png;base64,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>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEoAAAAZCAYAAACWyrgoAAACL0lEQVR4Xu2YzytEURTHj1Bk4VeRqImdUmyQhT/AxgILZWHJwk6xk42FhR9JkaQsFVkpv0rJhp2tpZRSyEZRfny/3Xm5bm/e3PtmambevE99a+4983r3nnfOuec9kZiYmJiYyFADNYVUA1QqRUIC+oHOoWrD5kcJtAx9irpuPTkXBepEPfyUfIja9IzYb7oFuoQeoFbDVohUQW/QrGnQoYPoqC9o0LAFwQg8g0ZNQwHB7HgRtXf6INBR3DBTj3+8M2zp6If2zMkCgjXaq7VpHeUxLMqz06YhA7iAenPSgOmeD4eCtaPKoA3oFeoxbGHogm6hJ6hTm+d9TkVFMp20Ktl9OGGxdhTh4nnBjaSPhCAYzheiHN4NzWu2NlGpzgJaAR1Cu5rdj15oxFGuODmKMKJ40RZUbthsYYGfS/6egiY0Gw+MBW3cCG1rYz/y0lGT8ncKsm6FYRxqhyqhY6hDs61BA9qY6I7MFc6OIoyIE7FrQoPgjbkAD6bdo6i082iGarVxrnB2FOvKlaiuPRNYtPehd22OkaQ7jtj0bpuirnORK86OopOyceoxali02b17DMn/TbAG7mjjXOLkKKZa2LrkxxL0nfytN7beqxLvxfYg1/Chcl0rok7ilHDhfJVhiLvQJ3adOb82sAvWx2w/bN8t8wIulg2fa/H2ImTMNEQVhj876IRpCICfJA6gZ1FtQFHAF2Hb4u2lKD9JMKePJE1OR4VF6D6krsUtCmOizC9K+39fg5sJ8gAAAABJRU5ErkJggg==>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHMAAAAZCAYAAAACLBHaAAAEN0lEQVR4Xu2YW6iOWRjHH5kJzTjPOERsU8iMjGaSaDA5RWgwU5Q5lBrczcWUSc2V0iQ5JEoizYUIuaIkFzuEMs2FyIXUJkwuTFFckMPza31rf+t79nv61rvt7fD+6l/f+671ft/6ntN61itSUVFRUVFRUVFR8a4wQDVdNcoOVBRmrOorcbZshh6qIappqp5mzDJI3NxUjqjaVPtVJ1QLG0bL00c10958w8HAa1Qf2IEEmLtYnO2wYZvqcDghgxbVBdVV1V7VDdXkcELAR6qHqj/sgAdDX1Z9WrtmYY9UU9tnxNNPtV51p/b5bYDMWKT6R/W5GUtjnuqZONsBtsSmH7bPSAcnHhPnB/hLdVOckz3bVP+rnqteSoYzF6jWmnvXVKek/gMxbFHdV/0pb48jV4oz5HHVeDOWBjbCVtgsBJti2zxeqOYG1xNUD1S7pB4clG1KK4GW6syB4iLoa3P/b3EPLTH3s+DPYwSMgVHK8LG9kUCROXkQZAQbQUfwxbBKnK2wWQg2bZXsdX6muqUaHtxjfqvqsXT0C6Q6ky/hy+xD3pmJDxmIntPiIvM7yd/As6AsUWbuiovMcL8iSH6off5CdV01sj7cNIOlcyoHNkpzpnWUJWmOd2ZaMqX6xad0rDO/VF1UzZZyTvSsU+1R9VLdU40OxliPb8y+lfTIzYNukEDBkTQUZdkp8c6kvNo50c7kB5OMUtSZs1RXVJOkXt9j6a86qhqjGiou0z+pjfEH/xNXljw0aQSTh3I3J7hOY5i47p3MLtKg5OFtFeNMnGXnRDsTY2CUWGcCGUnnR4bSAcc6tUX1q7jSSuMQNgBUkDPSmEnnpe5soKX/PbjOg6Ah+1dLuUZvn8Q7k0pj50Q7M60BOijuoeXmfhF8I0QTFBP5I8Sd00JHbZKOZ18ysbPwjdBmcXtpM6Q1QFNU51R9zf2QpAaI+Tz3RNx3WFKdSRZwxrGGapXk8tsMByQu8r+RxjMb2UhWhiWW6CVbgYDB2eFZLZbfxO2luyU7o0L8elljCFmFDbIqFclktwvflLaJC2xLqjOBDLJRzn51Sdw+VgYWxoGXlwZFDU1gsWCPj9TQuDOk3unS4S4VV2bZa8vCOn8W1z0X6ZaxEbaiwoVwzrRHNObZxCEQCAgPQUpTekiS3z5lOpOyclYaHfdUtSK4LgtlzB8r8qBMkx3e+d+Le/MxsXbNOmlgPGwFlORwj+0M6AU2qnrbgQR+FLdGD2u0NqWa4IjW2mcP1YsM9lvSBnFVkf7DQpXiO7ZLxrr4It6dkqHLzFh3QZYh/ycJOrIz6U+QBbxCo6tOiuaugoDFhmxPzRzVcNJ81S+1z+8tOPekuMxlz6uI5CfV7YLi5fXrgNK6Q1zpKbLHj1P9Kx3Xl6St0r2Z3qWQFZS+Ioo5phQFhxYta8zjpbVdX5Ky3qtWVFRU5PAKa9nhRgQI9BoAAAAASUVORK5CYII=>

[image13]: <data:image/png;base64,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>

[image14]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIIAAAAWCAYAAAAM9ESoAAAEh0lEQVR4Xu2YTchUZRTHj6igZCmZVmJILSIpUBGLCgqihWFCZEHRUkgIJUw0cKWYSLVrFaFJgQm6aiGIhg4V2McqqITURSKFSopQCwXT83vPPc6ZM3fmzrzvvNni+cGfuff5/jjPec5ckUKhUCgUCoVCoVBoYobqkOq0ao/qk0o3VFdV+6r3VpX2l2oxFQsTYrrq1ZzYwH2q86rPVF+K7cXUjhL13KH6SHVZ9bfYPv6gejgWmiW2yblBCv+uuj+kPaf6Q7U8pBWGg015W2wdF6a8fsxWfaWaF9LWqDaF9zowuI9V21UzK/HM/mIYt7hH9W1MqKBgS8xQnDtVx1TPh7TC4HwodqLfV81NeU28JrYnEbz5OdWDKT3CXv2j2iVmhIAxHBZrjzbGwM0f9JdAnSHATtUb4X2OdJfBu2CJEQyONPJ4zsQ2eL43vGemiC3kfOn2ZMPibeH5cls+Vh93nlMTT6lOqH5RvZTyhoGx4Z3Z0Az7tDsnBjCEa2Knf1lIf1es7pKQVksvQ3DId9GoXzGe5teHd8gk3lT9JOYWX5b2BL3OCtWPqrOqS6q3xDbK4fkF1RmxvhBtvVjlMSkWnfropLQnzx3p6RuqtGfFYqOfxeIjnkmDunGzoIy7CQyGE3xE9YR0zmE8sJaMo5chEOPdOtk1sDc5n/Wgbt2h7KDJEBaJDcANwU/W06oL0jYE6uN1KMcmPCIW7CBOGad6Y5WPZ7rbqo25L4LVJ6t34D5kM7gbHZ5JI48NwJN4ewRDfooXiBkJ4/I5UY9A2Mt8rbqoerQq8510jptnxt0L2lkvZpyfp7yJ0GQILem9T3U8oDolVreRQTrwU8Ov454hB5SUwwqBDUKOT/SxkAbUeSe8U4a7DSNx/L6LgQ/GgDeI7XEiVoZ3DJA6sQxXHn1uq97Z9DjuDyRF2gnGwtXJvU0cMCpGaQgc2B1i9TgEjQzSwbCGsDqlOT7R3Fdsm0An9+VsFcuL7g9PgjFgFLCtnTUG7XD690r7L7Nrs1hbbgi9xt0EcQFeiDiBK2K8jNIQmPMW6Y6HejJIB/+lIZCX+3J8HB4VA6fzXzEvgDEcDXmAp2lJd5+RiRoCcAIxAuIFDGPYgBOagsV+11XkcbFvFx6zTJP2VdyT8RoCfzG/kdEbgr/XRci+YRnS9ovFEV+kPKJpFjd+J8mMwhAie8Xih7XSabRNUJZvCBh2hvGty4k1EKd9n9KYe7/5jzFeQ3hI9adMjiEQPLaksxwfWgjqyMucFGv3V+mMD4A23GNEeP9UzHWO2hBgrlj8QBxxV8rrx3rpNnaurxznHBeLU6LnWSR2OFdJe/MR3iGveddfuay6xaAzJnVd7O8XG/K6WPRNHdp7r3qOcldW1yd5bmC5f1wap5u/eXyYQTzzl9LdXYQFYqFYxDr4sndAbPy085vY11OoG8PtZqnYp2GCWq425pY9yxWxD4R+0uvmMWlzwjK5hzEMNgSr77K0EcOHLNQPxsId2HQvM1YWbuAA6jbyjJghvCL2N7BQKPxfcW8Y7+F+mmyvWSgMx0298D9wvD9S3gAAAABJRU5ErkJggg==>