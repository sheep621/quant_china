# **A股量化交易全流程优化策略深度研究报告：从因子挖掘到危机风控的系统工程**

## **1\. 引言：A股量化交易的生态结构与核心挑战**

中国A股市场作为全球第二大股票市场，其独特的微观结构、投资者构成以及监管制度，孕育了一个与成熟发达市场截然不同的量化交易生态系统。与机构投资者主导的美股市场不同，A股市场长期呈现出显著的“散户化”特征，个人投资者贡献了主要的交易量。这种投资者结构的差异，叠加涨跌停板制度、T+1交易机制以及独特的停复牌规则，使得直接照搬西方量化模型往往面临“水土不服”的困境。

近年来，随着股指期货市场的逐步恢复、融资融券标的扩容、互联互通机制（沪深港通）的深化以及场外衍生品（如雪球结构、DMA业务）的爆发式增长，A股量化交易进入了“军备竞赛”阶段。2024年初发生的流动性危机更是对整个行业的风控体系进行了一次残酷的压力测试，暴露了由于策略同质化、风格因子过度拥挤以及基差风险管理缺失所带来的系统性脆弱。

本报告旨在从系统工程的角度，对A股量化交易的全流程进行详尽的解构与优化重构。我们将深入探讨因子挖掘中的数据清洗与正交化数学原理、回测引擎在T+1约束下的状态机设计、组合优化中的协方差矩阵收缩技术、算法交易在“M型”成交量分布下的执行策略，以及基于2024年危机反思的深度风控框架。

## **2\. 因子挖掘与数据处理架构：信号的源头治理**

量化策略的超额收益（Alpha）本质上来源于对市场无效性的捕捉。在A股市场，数据的“信噪比”往往较低，且存在大量的异常值和结构性偏差。因此，构建一个鲁棒的因子工厂（Factor Factory）是量化流程的第一步。

### **2.1 高维数据的清洗与预处理策略**

在处理A股数据时，传统的均值-方差标准化方法（Z-score）往往失效，因为A股收益率分布具有显著的尖峰肥尾特征，且频繁受到涨跌停板和停牌的影响。

#### **2.1.1 稳健去极值：MAD方法的工程实践**

面对数据中的离群值（Outliers），如小盘股在被炒作期间的连续涨停，使用标准差（Standard Deviation）进行过滤极易受到极端值本身的干扰。工业级的最佳实践是采用中位数绝对偏差（Median Absolute Deviation, MAD）法。MAD法利用中位数作为中心趋势的度量，具有更高的崩溃点（Breakdown Point）。

对于因子序列 ![][image1]，其MAD定义为：

![][image2]  
在实际工程中，通常将偏离中位数 ![][image3] 倍（通常取3或5.2，对应正态分布下的![][image4]）MAD的值进行Winsorization（缩尾）处理，即将其通过边界值拉回，而非直接剔除。这保留了样本的完整性，同时抑制了极端值对线性回归等后续步骤的破坏性影响。

#### **2.1.2 缺失值填补的行业逻辑**

A股上市公司的停牌频率远高于成熟市场。简单的时间序列插值（Forward Fill）在面对长停牌（如重组停牌数月）时会引入严重的“陈旧价格”偏差。更科学的方法是基于行业分类（如中信一级行业或申万一级行业）进行截面插值。

当某只股票在截面期 ![][image5] 数据缺失时，应使用其所属行业的同期中位数或加权均值进行替代。这种方法隐含的假设是：在缺乏特质性信息的情况下，个股的预期表现应收敛于其所属的行业贝塔（Beta）。这种处理方式有效避免了在因子标准化过程中因缺失值导致的分布扭曲。

### **2.2 因子中性化与Barra模型应用**

在A股市场，市值因子（Size）和行业因子（Industry）解释了绝大部分的股票收益差异。一个未经中性化处理的“估值因子”（如EP），往往本质上是一个“银行股”因子或“大盘股”因子。为了提炼纯粹的选股能力（Pure Alpha），必须剥离这些风险因子的影响。

#### **2.2.1 截面回归中性化**

Barra CNE6（China Equity Model）是目前A股市场最主流的风险模型框架 1。因子中性化的核心数学工具是截面回归。对于任意时刻 ![][image5]，我们建立如下回归方程：

![][image6]  
其中：

* ![][image7] 为股票 ![][image8] 的原始因子值。  
* ![][image9] 为行业哑变量（Dummy Variable），若股票 ![][image8] 属于行业 ![][image10] 则为1，否则为0。Barra CNE6模型通常包含32个中信或GICS行业分类 2。  
* ![][image11] 为市值因子的暴露，通常采用对数市值并进行标准化。  
* ![][image12] 即为中性化后的纯因子值（Residual Factor）。

这一残差 ![][image12] 代表了剥离了行业属性和市值大小后的特质性因子暴露。例如，一个中性化后的EP因子，衡量的是该股票相对于同行业、同市值规模股票的估值高低，而非绝对估值。

#### **2.2.2 风格因子的标准化**

Barra模型特别强调对风格因子（如波动率、动量、流动性）的标准化处理。在A股市场，市值加权的标准化（Cap-Weighted Standardization）尤为重要 2。由于小微盘股的数量众多且波动极大，如果采用等权重标准化，因子分布会被小票主导。市值加权标准化能确保因子暴露更能反映市场资金的真实分布，防止因子在回测中被微盘股的极端收益所绑架。

### **2.3 因子正交化：格拉姆-施密特与Löwdin对称正交的较量**

多因子选股模型面临的最大挑战之一是因子间的共线性（Multicollinearity）。例如，动量因子（Momentum）与成长因子（Growth）在牛市中往往高度相关。如果直接将相关性高的因子投入线性模型，会导致系数估计极不稳定，且难以进行业绩归因。

#### **2.3.1 格拉姆-施密特（Gram-Schmidt）正交化的局限**

传统的格拉姆-施密特正交化是一种序贯方法。假设有因子集 ![][image13]，该方法首先保持 ![][image14] 不变，然后将 ![][image15] 中与 ![][image14] 相关的部分剔除，接着将 ![][image16] 中与 ![][image17] 相关的部分剔除，依此类推 3。

这种方法的致命缺陷在于**顺序依赖性**（Order Dependence）。排在前面的因子保留了全部信息，而排在后面的因子被“层层剥削”，面目全非。在量化投资中，我们往往无法在理论上断定“估值”比“动量”更重要，因此人为规定正交顺序缺乏逻辑基础，可能导致有效的Alpha信号被错误地清洗掉。

#### **2.3.2 Löwdin对称正交化的优势与实现**

为了解决顺序依赖问题，Löwdin对称正交化（Symmetric Orthogonalization）成为高阶量化策略的首选。其数学目标是寻找一组正交基 ![][image18]，使得这组基与原始因子 ![][image19] 之间的欧几里得距离（Frobenius范数）最小 5。

数学推导如下：

设原始因子矩阵为 ![][image19]（![][image20]，N为股票数，M为因子数），计算其重叠矩阵（Overlap Matrix）或协方差矩阵 ![][image21]。

由于 ![][image22] 是实对称矩阵，可进行特征值分解（Eigen Decomposition）：

![][image23]  
其中 ![][image24] 为特征向量矩阵，![][image25] 为特征值对角矩阵。

Löwdin变换矩阵为 ![][image26]。

最终的正交化因子矩阵为：

![][image27]  
通过这种变换，所有因子都受到了“平等”的调整，既消除了相关性，又最大程度地保留了各个因子原始的形状和信息含量。Python实现中，利用 numpy.linalg.eigh 或 svd 可以高效计算这一变换 7。

| 特性维度 | 格拉姆-施密特正交化 (Gram-Schmidt) | Löwdin对称正交化 (Symmetric) |
| :---- | :---- | :---- |
| **顺序敏感性** | 高度敏感，结果取决于输入顺序 | 无，结果与输入顺序无关 |
| **信息保留** | 前序因子保留完整，后序因子严重失真 | 所有因子均等变形，整体信息损失最小 |
| **计算复杂度** | 较低，![][image28] | 较高，需进行矩阵分解与求逆 |
| **适用场景** | 剔除明确的风险因子（如先剔除市值） | 多个地位平等的Alpha因子融合 |
| **数学性质** | 生成上三角变换矩阵 | 生成对称变换矩阵 |

### **2.4 因子拥挤度与失效预警**

随着A股量化私募规模的激增，策略同质化导致因子拥挤（Crowding）成为显著风险。2024年初微盘股崩盘便是小市值因子极度拥挤后的踩踏 10。

有效的拥挤度监测指标包括：

1. **估值价差（Valuation Spread）：** 计算因子多头组合与空头组合的市盈率/市净率之差。历史高位的价差往往预示着因子过于昂贵，回撤风险加大。  
2. **两两相关性（Pairwise Correlation）：** 因子多头股票内部的收益率相关性。当多头股票开始齐涨齐跌时，说明资金性质高度一致，拥挤度高 11。  
3. **因子波动率（Factor Volatility）：** 因子收益本身的波动率上升，通常是资金分歧加大、拥挤度提升的前兆 12。

在组合构建中，应对高拥挤度的因子赋予惩罚项或直接降低权重，以规避“阿尔法衰减”（Alpha Decay）。

## **3\. 严苛约束下的回测引擎设计**

A股独特的交易规则使得通用的美股回测框架（如基于Zipline的默认设置）完全失效。一个合格的A股回测引擎必须是对交易规则的精确仿真，而非简单的收益率计算器。

### **3.1 T+1 交易制度的状态机模型**

A股实施“T+1”交收制度，即当日买入的股票当日不可卖出。这一规则彻底改变了日内交易的逻辑，使得“日内回转”交易（Day Trading）必须通过持有底仓（Rollover Position）来实现 13。

在回测引擎中，必须为每个持仓标的维护一个精细的状态机，而不仅仅是一个简单的持仓数量变量。

定义持仓对象 Position 包含以下状态变量：

* total\_shares: 总持仓股数。  
* sellable\_shares: 可卖股数（即T日之前建仓的部分）。  
* locked\_shares: 锁定股数（T日新买入的部分）。  
* frozen\_shares: 冻结股数（已挂卖单但尚未成交的部分）。

**状态流转逻辑：**

1. **开盘前（T日）：** 将前一日的 locked\_shares 全部并入 sellable\_shares，重置 locked\_shares 为0。  
2. **买入成交：** 增加 total\_shares 和 locked\_shares。注意：sellable\_shares **不变**。  
3. **卖出委托：** 检查委托数量是否小于等于 sellable\_shares \- frozen\_shares。若是，增加 frozen\_shares。  
4. **卖出成交：** 减少 total\_shares、sellable\_shares 和 frozen\_shares。  
5. **撤单：** 减少 frozen\_shares。

若回测引擎缺乏此逻辑，策略可能会在同一天买入并卖出同一笔股份，从而制造出虚假的“日内高频”收益，这在A股现货市场是物理上不可能实现的 14。

### **3.2 涨跌停板的流动性黑洞**

A股主板10%（及科创板/创业板20%）的涨跌停板制度不仅限制了价格，更切断了流动性。

**涨停（Limit Up）：** 买一价上的封单量通常巨大。在回测中，如果策略发出买入信号且价格触及涨停，**必须假设成交量为0**，除非策略拥有极高的排队优先级（通常仅做市商或极早期挂单拥有）。绝大多数回测引擎默认“只要有成交量就能成交”是严重的错误，因为涨停板上的成交量大多是封板资金内部的换手或极其靠前的排队单，后进资金无法成交 16。

**跌停（Limit Down）：** 这是风险控制的梦魇。如果持仓股票遭遇跌停，卖出成交概率极低。回测引擎必须强制规定：**跌停价不可卖出**。2024年微盘股危机中，许多量化产品正是因为无法在跌停板出货而导致净值回撤远超模型预期 10。

### **3.3 数据偏差的系统性剔除**

#### **3.3.1 幸存者偏差（Survivorship Bias）**

直接使用当前的CSI 300成分股进行过去10年的回测是初学者最常犯的错误。这会剔除掉那些因业绩下滑、财务造假而被剔除出指数甚至退市的股票（如康得新、由于股价低于1元面值退市的股票）。研究表明，忽略退市股票可能导致年化收益率被高估1%-4% 18。 **解决方案：** 必须使用“点时”（Point-in-Time, PIT）数据库，严格依据历史每一天实际存在的指数成分股名单进行选股。

#### **3.3.2 前视偏差（Look-Ahead Bias）与财报滞后**

A股财报发布存在显著的滞后性。例如，一季报（截止3月31日）通常在4月底才发布。如果在回测中于4月1日就使用了3月31日的财务数据，就构成了“偷看未来”。

**解决方案：** 因子计算必须基于财报的**公告日期**（Announcement Date）而非报告期（Reporting Period）。

#### **3.3.3 分红除权处理**

A股高送转（送股、转增股本）频繁。回测中的技术指标计算（如均线）需要使用**前复权**价格以保持连续性。然而，在计算账户实际盈亏（P\&L）时，必须使用**不复权**的真实价格，并显式模拟分红现金流的入账以及相应的红利税扣除（持股期限不同税率不同）21。

### **3.4 防过拟合：CSCV组合清理交叉验证**

为了评估策略的真实稳健性，传统的Walk-Forward（向前滚动）测试往往样本利用率不足。在金融机器学习领域，**组合清理交叉验证（Combinatorial Purged Cross-Validation, CSCV）** 被证明更为优越 22。

CSCV通过将时间序列切分为 ![][image29] 份，生成所有可能的训练集/测试集组合。关键在于“清理”（Purging）机制：在训练集和测试集的衔接处，剔除一段数据，以防止金融数据特有的序列相关性（Serial Correlation）导致信息泄露。CSCV可以计算出策略的过拟合概率（Probability of Backtest Overfitting, PBO），为策略上线提供量化的置信度指标。

## **4\. 组合优化：从均值方差到鲁棒控制**

因子挖掘产生了预测信号，而组合优化则决定了如何将这些信号转化为持仓权重，以在风险和成本约束下最大化收益。

### **4.1 凸优化目标函数与约束体系**

现代A股量化组合构建通常建模为一个二次规划（Quadratic Programming, QP）问题：

![][image30]  
其中：

* ![][image31] 为目标权重向量。  
* ![][image32] 为预期收益率向量（即合成因子得分）。  
* ![][image33] 为协方差矩阵。  
* ![][image34] 为风险厌恶系数。  
* ![][image35] 为交易成本惩罚项。

**关键约束（Constraints）：**

1. **换手率约束（Turnover Constraint）：** 为了应对印花税（卖出千分之五）和冲击成本，必须严格限制单次调仓的换手率。通常设置为硬约束 ![][image36] 或作为软约束加入目标函数 25。  
2. **风格因子暴露约束：** 限制组合在市值、行业等Barra因子上的暴露，确保Alpha来源于选股而非风格漂移（Style Drift）。例如，要求组合的市值因子暴露相对于中证500指数偏离不超过0.2个标准差 27。  
3. **成分股权重约束：** 避免个股过度集中，通常设置单票权重上限（如1%或5%）。

### **4.2 协方差矩阵的Ledoit-Wolf收缩**

样本协方差矩阵（Sample Covariance Matrix）在股票数量 ![][image29] 远大于时间窗口 ![][image37] 时，存在估计误差大、条件数高的问题，导致优化器输出极端的权重配置。

**Ledoit-Wolf收缩（Shrinkage）技术**是解决此问题的标准方案。其核心思想是将含有噪声的样本协方差矩阵 ![][image38] 向一个结构化、偏差大但方差小的目标矩阵 ![][image39]（如常相关矩阵或单因子模型矩阵）进行加权平均 28。

![][image40]  
其中 ![][image41] 为最优收缩强度（Optimal Shrinkage Intensity）。这种方法在A股市场尤为有效，因为A股个股间的相关性往往受宏观政策驱动明显，结构化特征强，收缩处理能显著提升组合在样本外的稳定性。

## **5\. 算法执行与微观结构：毫秒级的较量**

当优化器输出目标仓位后，交易执行（Execution）环节负责以最低的成本完成建仓。A股的微观结构特征对算法逻辑提出了特殊要求。

### **5.1 “M型”日内成交量分布与VWAP优化**

与美股的“U型”成交量分布（开盘收盘大，中间平滑凹陷）不同，A股呈现出典型的\*\*“M型”\*\*特征 31：

* **早盘（9:30-10:00）：** 消化隔夜信息，成交量巨大，波动剧烈。  
* **上午休市前（11:00-11:30）：** 成交量逐渐萎缩。  
* **午盘重启（13:00-13:30）：** 也就是“下午开盘”，往往伴随第二波成交量高峰，这与港股通（北向资金）的流动以及上午休市期间的消息发酵有关。  
* **尾盘（14:30-15:00）：** 机构调仓与日内回补操作导致成交量再次放大。

传统的VWAP（成交量加权平均价）算法如果直接套用U型曲线，会在13:00左右低估流动性，导致执行滞后。针对A股的VWAP算法必须基于历史分时数据（如5分钟或15分钟bar）拟合出特定的日内成交量季节性曲线（Intraday Seasonality），并动态预测午盘的“第二高峰” 33。

### **5.2 冲击成本模型：平方根法则的修正**

交易成本不仅包含佣金和印花税，更主要的是冲击成本（Market Impact）。Almgren-Chriss框架下的平方根法则（Square-Root Law）是主流模型：

![][image42]  
其中 ![][image43] 为交易量，![][image44] 为日均成交量，![][image45] 为波动率。 在A股市场，参数 ![][image46] 需要根据散户参与度进行修正。由于散户交易往往是噪音交易（Noise Trading），在某些情况下提供了额外的流动性，使得机构在中小盘股上的冲击成本可能低于同等流动性的美股市场。但在市场恐慌（如跌停潮）时，流动性会瞬间枯竭，冲击成本呈指数级上升，模型必须引入流动性黑洞的惩罚项 36。

### **5.3 队列优先权与限价单博弈**

A股遵循“价格优先、时间优先”的竞价原则。在算法交易中，对于大单拆分（Slicing），不仅要考虑盘口深度（Depth），还要估算自己在LOB（限价订单簿）队列中的位置 39。

* **Level-2数据应用：** 通过逐笔委托数据，算法可以重构订单簿，估算在某个价位上前方堆积的挂单量。  
* **被动成交策略：** 在非急迫情况下，算法应尽量以挂单（Maker）方式在买一价等待成交，以赚取买卖价差（Spread），而非一味吃单（Taker）支付价差。这要求算法具备精准的短期价格趋势预测能力（如使用微观结构的Imbalance指标预测未来10秒的价格变动）。

## **6\. 2024年量化危机的启示与风控重构**

2024年初的A股量化危机（“Quant Quake”）是一次典型的流动性螺旋与衍生品负反馈共振事件，为行业留下了惨痛的教训。

### **6.1 雪球与DMA的负反馈机制**

危机的核心在于“雪球”衍生品与DMA（Direct Market Access）高杠杆策略的连锁反应 10。

1. **雪球敲入（Knock-in）：** 雪球本质是卖出看跌期权（Short Put）。券商作为对手方持有看跌期权多头，随着市场下跌接近敲入线（通常是指数点位的75%-80%），券商的对冲盘（做多股指期货）Delta会迅速增加。一旦跌破敲入线，期权变为实值，券商需要大幅减持股指期货多单以降低Delta，这通过期货市场传导了巨大的抛压。  
2. **基差（Basis）走扩：** 期货抛压导致期货深度贴水（即期货价格远低于现货），基差大幅走扩。  
3. **DMA策略崩溃：** DMA策略通常持有小微盘股（CSI 2000或更小），同时做空股指期货（CSI 500/1000）进行对冲（市场中性策略）。  
   * 正常情况下，这是一个赚取小票Alpha的策略。  
   * 危机中，虽然做空期货赚钱（因为期货跌了），但持仓的小微盘股遭遇了更惨烈的流动性崩盘（Alpha变为负数且幅度巨大）。  
   * 更致命的是，DMA往往带有4倍杠杆。随着小票跌停无法卖出，账户保证金迅速枯竭，触发强平。  
   * 强平导致不计成本地抛售小票，进一步压低现货价格，形成“股价下跌 \-\> 期货贴水 \-\> 净值回撤 \-\> 强平抛售 \-\> 股价再跌”的死亡螺旋。

### **6.2 风险管理的升级：流动性与基差风控**

基于此次危机，量化风控体系必须进行以下维度的升级：

| 风控维度 | 传统做法 | 优化后的做法 |
| :---- | :---- | :---- |
| **流动性风险** | 仅关注日均成交量（ADV） | 引入**流动性黑洞测试**：假设跌停无法卖出时的保证金压力；限制持仓在流动性底部的股票比例。 |
| **基差风险** | 视为对冲成本，被动接受 | 将基差波动纳入VaR模型；设置动态对冲比例，在基差极端走扩时通过ETF换仓或降低杠杆。 |
| **风格拥挤度** | 限制行业/市值偏离度 | 监控**全市场拥挤度指标**；对微盘股（Micro-cap）暴露设置硬性上限，防止策略在追求高Alpha时不知不觉演变为纯粹的“微盘贝塔”策略 12。 |
| **杠杆管理** | 固定杠杆比率 | **动态杠杆机制**：依据市场波动率（VIX）和基差水平动态调整杠杆，拒绝在市场脆弱期维持高杠杆。 |

## **7\. 结语**

A股量化交易已告别了“捡钱”的草莽时代，进入了拼细节、拼工程、拼风控的精细化运营阶段。全流程的优化不仅仅是数学模型的升级，更是对市场微观结构深刻理解的体现。

从因子挖掘端的**MAD去极值**与**Löwdin对称正交**，到回测端的**T+1状态机**与**PIT数据治理**，再到执行端的**M型VWAP优化**与风控端的**流动性压力测试**，每一个环节的疏漏都可能成为阿尔法的“漏斗”。特别是2024年的危机警示我们，没有任何Alpha是能够脱离市场Beta和微观流动性环境而独立存在的。未来的胜出者，必将是那些能在捕捉超额收益的同时，对极端尾部风险保持最高敬畏的量化团队。

### ---

**主要参考文献索引**

* **因子处理与Barra模型：** 2  
* **回测引擎与数据偏差：** 13  
* **组合优化与协方差：** 25  
* **算法交易与微观结构：** 31  
* **2024年危机与风控：** 10

#### **引用的著作**

1. "Combinatorial symmetric cross validation" vs "Combinatorial purged cross validation" : r/algotrading \- Reddit, 访问时间为 二月 1, 2026， [https://www.reddit.com/r/algotrading/comments/m7mdmq/combinatorial\_symmetric\_cross\_validation\_vs/](https://www.reddit.com/r/algotrading/comments/m7mdmq/combinatorial_symmetric_cross_validation_vs/)  
2. Barra Risk Model \- Medium, 访问时间为 二月 1, 2026， [https://medium.com/@humblebeyondx/barra-risk-model-776eb1e48024](https://medium.com/@humblebeyondx/barra-risk-model-776eb1e48024)  
3. Gram–Schmidt process \- Wikipedia, 访问时间为 二月 1, 2026， [https://en.wikipedia.org/wiki/Gram%E2%80%93Schmidt\_process](https://en.wikipedia.org/wiki/Gram%E2%80%93Schmidt_process)  
4. Gram-Schmidt orthogonalization \- Ximera \- The Ohio State University, 访问时间为 二月 1, 2026， [https://ximera.osu.edu/linearalgebra/textbook/leastSquares/gramSchmidtOrthogonalization](https://ximera.osu.edu/linearalgebra/textbook/leastSquares/gramSchmidtOrthogonalization)  
5. Comparison of Gram-Schmidt and Löwdin symmetric orthogonalization methods., 访问时间为 二月 1, 2026， [https://www.researchgate.net/figure/Comparison-of-Gram-Schmidt-and-Loewdin-symmetric-orthogonalization-methods\_tbl1\_394540280](https://www.researchgate.net/figure/Comparison-of-Gram-Schmidt-and-Loewdin-symmetric-orthogonalization-methods_tbl1_394540280)  
6. Löwdin Orthogonalization \- A Natural Supplement to Gram-Schmidt \- Find People, 访问时间为 二月 1, 2026， [https://people.wou.edu/\~beavers/Talks/LowdinJointMeetings0107.pdf](https://people.wou.edu/~beavers/Talks/LowdinJointMeetings0107.pdf)  
7. Orthogonal Collocation for Symmetric Problems in Python | by Jonas Weitzel \- Medium, 访问时间为 二月 1, 2026， [https://medium.com/@jonas.weitzel/orthogonal-collocation-for-symmetric-problems-in-python-614140c0f1b3](https://medium.com/@jonas.weitzel/orthogonal-collocation-for-symmetric-problems-in-python-614140c0f1b3)  
8. symmetric\_orthogonalization.py · GitHub, 访问时间为 二月 1, 2026， [https://gist.github.com/a1a804377e0c0c90cbb368e6e703c9c5](https://gist.github.com/a1a804377e0c0c90cbb368e6e703c9c5)  
9. How to do Lowdin symmetric orthonormalisation? \- Chemistry Stack Exchange, 访问时间为 二月 1, 2026， [https://chemistry.stackexchange.com/questions/85484/how-to-do-lowdin-symmetric-orthonormalisation](https://chemistry.stackexchange.com/questions/85484/how-to-do-lowdin-symmetric-orthonormalisation)  
10. China's Recent Liquidity Crisis \- Another Quant Quake Tale, 访问时间为 二月 1, 2026， [https://www.sowellmanagement.com/commentary/chinas-recent-liquidity-crisis-another-quant-quake-tale/](https://www.sowellmanagement.com/commentary/chinas-recent-liquidity-crisis-another-quant-quake-tale/)  
11. Full article: The Impact of Crowding in Alternative Risk Premia Investing \- Taylor & Francis, 访问时间为 二月 1, 2026， [https://www.tandfonline.com/doi/full/10.1080/0015198X.2019.1600955](https://www.tandfonline.com/doi/full/10.1080/0015198X.2019.1600955)  
12. QUANTITATIVE STRATEGIES: FACTOR-BASED INVESTING \- Portfolio Management Research, 访问时间为 二月 1, 2026， [https://www.pm-research.com/content/iijpormgmt/51/3/local/complete-issue.pdf](https://www.pm-research.com/content/iijpormgmt/51/3/local/complete-issue.pdf)  
13. 访问时间为 一月 1, 1970， [https://www.joinquant.com/view/community/detail/a51e6002f23b2c611593c6f0e386888c](https://www.joinquant.com/view/community/detail/a51e6002f23b2c611593c6f0e386888c)  
14. Backtesting Engine for Trading Strategies and Performance Evaluation \- GitHub, 访问时间为 二月 1, 2026， [https://github.com/rsafiry/backtesting](https://github.com/rsafiry/backtesting)  
15. 访问时间为 一月 1, 1970， [https://github.com/Ricequant/rqalpha/blob/master/rqalpha/model/position.py](https://github.com/Ricequant/rqalpha/blob/master/rqalpha/model/position.py)  
16. Instinet Execution Experts, 访问时间为 二月 1, 2026， [https://www.instinet.com/sites/default/files/public/documents/2022/Instinet\_APAC\_Extract\_Electronic\_Trading\_and\_Training\_Pack\_Dec\_2021(updated\_-\_18022022).pdf](https://www.instinet.com/sites/default/files/public/documents/2022/Instinet_APAC_Extract_Electronic_Trading_and_Training_Pack_Dec_2021\(updated_-_18022022\).pdf)  
17. Basics of Algorithmic Trading: Concepts and Examples \- Investopedia, 访问时间为 二月 1, 2026， [https://www.investopedia.com/articles/active-trading/101014/basics-algorithmic-trading-concepts-and-examples.asp](https://www.investopedia.com/articles/active-trading/101014/basics-algorithmic-trading-concepts-and-examples.asp)  
18. How Survivorship Bias is Hurting Your Returns \- Quant-Investing, 访问时间为 二月 1, 2026， [https://www.quant-investing.com/blog/avoid-investment-mistakes-survivorship-bias-tips](https://www.quant-investing.com/blog/avoid-investment-mistakes-survivorship-bias-tips)  
19. Survivorship Bias Market Data & Hedge Funds: What Traders Need to Know \- Bookmap, 访问时间为 二月 1, 2026， [https://bookmap.com/blog/survivorship-bias-in-market-data-what-traders-need-to-know](https://bookmap.com/blog/survivorship-bias-in-market-data-what-traders-need-to-know)  
20. Survivorship Bias in Backtesting Explained \- LuxAlgo, 访问时间为 二月 1, 2026， [https://www.luxalgo.com/blog/survivorship-bias-in-backtesting-explained/](https://www.luxalgo.com/blog/survivorship-bias-in-backtesting-explained/)  
21. Beginner's Guide to Quantitative Trading | QuantStart, 访问时间为 二月 1, 2026， [https://www.quantstart.com/articles/Beginners-Guide-to-Quantitative-Trading/](https://www.quantstart.com/articles/Beginners-Guide-to-Quantitative-Trading/)  
22. Interpretable Hypothesis-Driven Trading: A Rigorous Walk-Forward Validation Framework for Market Microstructure Signals \- arXiv, 访问时间为 二月 1, 2026， [https://arxiv.org/html/2512.12924v1](https://arxiv.org/html/2512.12924v1)  
23. Backtest overfitting in the machine learning era: A comparison of out-of-sample testing methods in a synthetic controlled environment | Request PDF \- ResearchGate, 访问时间为 二月 1, 2026， [https://www.researchgate.net/publication/385070377\_Backtest\_overfitting\_in\_the\_machine\_learning\_era\_A\_comparison\_of\_out-of-sample\_testing\_methods\_in\_a\_synthetic\_controlled\_environment](https://www.researchgate.net/publication/385070377_Backtest_overfitting_in_the_machine_learning_era_A_comparison_of_out-of-sample_testing_methods_in_a_synthetic_controlled_environment)  
24. Advanced Financial Model Testing | PDF | Cross Validation (Statistics) \- Scribd, 访问时间为 二月 1, 2026， [https://www.scribd.com/document/725401650/SSRN-id4778909](https://www.scribd.com/document/725401650/SSRN-id4778909)  
25. THE MEAN-VARIANCE APPROACH TO PORTFOLIO OPTIMIZATION SUBJECT TO TRANSACTION COSTS 1\. Introduction, 访问时间为 二月 1, 2026， [https://orsj.org/wp-content/or-archives50/pdf/e\_mag/Vol.39\_01\_099.pdf](https://orsj.org/wp-content/or-archives50/pdf/e_mag/Vol.39_01_099.pdf)  
26. Portfolio Optimization: Minimize risk with Turnover constraint via Quadratic Programming, 访问时间为 二月 1, 2026， [https://dilequante.com/portfolio-optimization-minimize-risk-with-turnover-constraint-via-quadratic-programming/](https://dilequante.com/portfolio-optimization-minimize-risk-with-turnover-constraint-via-quadratic-programming/)  
27. MSCI Barra Factor Indexes Methodology, 访问时间为 二月 1, 2026， [https://www.msci.com/eqb/methodology/meth\_docs/MSCI\_Barra\_Factor\_Indexes\_Methodology\_Mar18.pdf](https://www.msci.com/eqb/methodology/meth_docs/MSCI_Barra_Factor_Indexes_Methodology_Mar18.pdf)  
28. Improved estimation of the covariance matrix of stock returns with an application to portfolio selection \- | Department of Economics | UZH, 访问时间为 二月 1, 2026， [https://www.econ.uzh.ch/dam/jcr:ffffffff-935a-b0d6-ffff-ffff9961f70f/jef.pdf](https://www.econ.uzh.ch/dam/jcr:ffffffff-935a-b0d6-ffff-ffff9961f70f/jef.pdf)  
29. Honey, I Shrunk the Sample Covariance Matrix \- Olivier Ledoit, 访问时间为 二月 1, 2026， [http://www.ledoit.net/honey.pdf](http://www.ledoit.net/honey.pdf)  
30. Honey, I Shrunk the Sample Covariance Matrix | CSSA, 访问时间为 二月 1, 2026， [https://cssanalytics.files.wordpress.com/2013/10/honey-i-shrunk-the-sample-covariance-matrix.pdf](https://cssanalytics.files.wordpress.com/2013/10/honey-i-shrunk-the-sample-covariance-matrix.pdf)  
31. (PDF) Intraday Trading Volume Patterns Of Equity Markets: A Study Of US And European Stock Markets \- ResearchGate, 访问时间为 二月 1, 2026， [https://www.researchgate.net/publication/242770982\_Intraday\_Trading\_Volume\_Patterns\_Of\_Equity\_Markets\_A\_Study\_Of\_US\_And\_European\_Stock\_Markets](https://www.researchgate.net/publication/242770982_Intraday_Trading_Volume_Patterns_Of_Equity_Markets_A_Study_Of_US_And_European_Stock_Markets)  
32. Intraday Volatility-Volume Joint Modeling and Forecasting: A State-space Approach \- EURASIP, 访问时间为 二月 1, 2026， [https://eurasip.org/Proceedings/Eusipco/Eusipco2023/pdfs/0001395.pdf](https://eurasip.org/Proceedings/Eusipco/Eusipco2023/pdfs/0001395.pdf)  
33. VWAP Strategy Optimization | PDF | Day Trading \- Scribd, 访问时间为 二月 1, 2026， [https://www.scribd.com/document/585069244/VWAP](https://www.scribd.com/document/585069244/VWAP)  
34. Improving VWAP Strategies: A Dynamic Volume Approach | Request PDF \- ResearchGate, 访问时间为 二月 1, 2026， [https://www.researchgate.net/publication/222535631\_Improving\_VWAP\_Strategies\_A\_Dynamic\_Volume\_Approach](https://www.researchgate.net/publication/222535631_Improving_VWAP_Strategies_A_Dynamic_Volume_Approach)  
35. Mastering VWAP: Common Strategies for Informed Trading Decisions \- Investopedia, 访问时间为 二月 1, 2026， [https://www.investopedia.com/ask/answers/031115/what-common-strategy-traders-implement-when-using-volume-weighted-average-price-vwap.asp](https://www.investopedia.com/ask/answers/031115/what-common-strategy-traders-implement-when-using-volume-weighted-average-price-vwap.asp)  
36. Full article: Do price trajectory data increase the efficiency of market impact estimation?, 访问时间为 二月 1, 2026， [https://www.tandfonline.com/doi/full/10.1080/14697688.2024.2351457](https://www.tandfonline.com/doi/full/10.1080/14697688.2024.2351457)  
37. arXiv:1905.04569v1 \[q-fin.TR\] 11 May 2019, 访问时间为 二月 1, 2026， [https://www.cfm.com/wp-content/uploads/2022/12/167-Impact-is-not-just-volatility.pdf](https://www.cfm.com/wp-content/uploads/2022/12/167-Impact-is-not-just-volatility.pdf)  
38. Three models of market impact \- Baruch MFE Program, 访问时间为 二月 1, 2026， [https://mfe.baruch.cuny.edu/wp-content/uploads/2012/09/Chicago2016OptimalExecution.pdf](https://mfe.baruch.cuny.edu/wp-content/uploads/2012/09/Chicago2016OptimalExecution.pdf)  
39. High Frequency Dynamics of Limit Order Markets \- Stochastic modeling and Asymptotic Analysis, 访问时间为 二月 1, 2026， [https://www.imperial.ac.uk/media/imperial-college/research-centres-and-groups/cfm-imperial-institute-of-quantitative-finance/events/imperial-eth-2016/Rama-Cont-1.pdf](https://www.imperial.ac.uk/media/imperial-college/research-centres-and-groups/cfm-imperial-institute-of-quantitative-finance/events/imperial-eth-2016/Rama-Cont-1.pdf)  
40. A Model for Queue Position Valuation in a Limit Order Book∗ \- Ciamac Moallemi, 访问时间为 二月 1, 2026， [https://moallemi.com/ciamac/papers/queue-value-2016.pdf](https://moallemi.com/ciamac/papers/queue-value-2016.pdf)  
41. Snowballs and the Chinese Market Meltdown \- Validus Growth, 访问时间为 二月 1, 2026， [https://validusgrowth.com/snowballs-and-the-chinese-market-meltdown/](https://validusgrowth.com/snowballs-and-the-chinese-market-meltdown/)  
42. Chinese stock markets witness a free-fall \- due to "snowballs", 访问时间为 二月 1, 2026， [https://asiafundmanagers.com/chinese-stock-markets-witness-a-free-fall-due-to-snowballs/](https://asiafundmanagers.com/chinese-stock-markets-witness-a-free-fall-due-to-snowballs/)  
43. 'Snowball' derivatives feed China's stock market avalanche \- The Business Times, 访问时间为 二月 1, 2026， [https://www.businesstimes.com.sg/companies-markets/capital-markets-currencies/snowball-derivatives-feed-chinas-stock-market](https://www.businesstimes.com.sg/companies-markets/capital-markets-currencies/snowball-derivatives-feed-chinas-stock-market)  
44. Beyond the Beta: Actively Seeking Small-Cap Alpha \- Goldman Sachs Asset Management, 访问时间为 二月 1, 2026， [https://am.gs.com/en-au/advisors/insights/article/2025/beyond-beta-actively-seeking-small-cap-alpha](https://am.gs.com/en-au/advisors/insights/article/2025/beyond-beta-actively-seeking-small-cap-alpha)  
45. 衡泰研究| Brinson、多因子归因模型对比及创新应用\_2022\_新闻动态 ..., 访问时间为 二月 1, 2026， [https://www.xquant.com/xinwendongtai/2022/1444.html](https://www.xquant.com/xinwendongtai/2022/1444.html)  
46. A more symmetric orthogonalization procedure for three vectors? \- Math Stack Exchange, 访问时间为 二月 1, 2026， [https://math.stackexchange.com/questions/4953700/a-more-symmetric-orthogonalization-procedure-for-three-vectors](https://math.stackexchange.com/questions/4953700/a-more-symmetric-orthogonalization-procedure-for-three-vectors)  
47. Seven Sins of Quantitative Investing \- Hudson & Thames, 访问时间为 二月 1, 2026， [https://hudsonthames.org/wp-content/uploads/2022/01/DB-201409-Seven\_Sins\_of\_Quantitative\_Investing.pdf](https://hudsonthames.org/wp-content/uploads/2022/01/DB-201409-Seven_Sins_of_Quantitative_Investing.pdf)  
48. Survivorship bias: an investment decision trap | Quantdare, 访问时间为 二月 1, 2026， [https://quantdare.com/survivorship-bias-an-investment-decision-trap/](https://quantdare.com/survivorship-bias-an-investment-decision-trap/)  
49. Optimal execution in a limit order book and an associated microstructure market impact model \- Columbia Business School, 访问时间为 二月 1, 2026， [https://business.columbia.edu/sites/default/files-efs/pubfiles/25463/fluid-ms-2015.pdf](https://business.columbia.edu/sites/default/files-efs/pubfiles/25463/fluid-ms-2015.pdf)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAAZCAYAAAA8CX6UAAAA7UlEQVR4Xu2SzwoBURTGj6LIQlkpC0sbO6UsvIINxd472NhYs7IQKW9gT7GRpQcgryDZKQt/vq9zp64bzcxSza9+Nfd+M2funDkiEf9PDS7gzHIMiyafOxnXX8nDJuzBB9zBBkybfAif8AansG32f5KCKyOvPbpwC3PWni982xWWrL09LFjrwLzgAdbhyclCcRctdoYVJwsFe8RC/JNxJwvFRrSQ26tQZOAIHkWL9T/SACREH+KckKporzg/gYmJzspa9ETEmymeKlCfWKQFlzDrZJwpFvLtEz9nInpzR7SoB6/L8AIHMGllEX/NG9k5LRRzo2/6AAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,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>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAYCAYAAADOMhxqAAAAwElEQVR4Xu3PQQpBQRzH8b8oG0URCwtxAYmlsrFgwQnsHcEJLN/KASxtHEFxBUVWilIWSlkrfMe8mfdfuMHzq89ifv8382ZE/olfikiqde5H59PCETtU0MEFdzzQjz4V6WKBMd5YIRvOMtjgHK6/MbuNJV7oqVkNV+xV52PKE8qqG4r961x1PmYwUeuq2HccUMIIaTdM4Ym2KyR60zRcz5BwQ3OCuVLBFSQQu2GAPBpqJk2x9/QnkDpuWGOr+vjlA3TkIJmR9OlTAAAAAElFTkSuQmCC>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABUAAAAaCAYAAABYQRdDAAABVUlEQVR4Xu2UvytFYRjHv0IREW6kSLfYbJIMFt2BQWRShruaDdcfIJOUlX9AyqoMhrtRFtZbBhaj6aq74Pv1nB/PPZ0zHDLcOp/6dO77vG/PeZ/nPe8FCgr+jS46RifpeGLuV0zRLTdW8i+652K52aDvdN7FlPSWDrhYLiq0RZddTEnrdNDFcqF+zrpxPyzpiYv9mRXaoDPJCdJLd+gj7MXeB9h5RIzSTbpLb+gqrAKPevxKF4PxEm3SC9oTLspCu9Gba4gT6/lJ18JFsH7XYTsccfFMlNQfXpne0+FoBTBBn5GRVB98KRFTWUq8H4zX6VE8/cMCbN0VEuWrsU/0mva5+Acs6UEw1nM7no5iWqODa0O9OqVzLhb29Dz4LabpIeIe61KobN3GVNQn3agzWLl39Bj2vXpeYAdzSd/oUNtsCtqJ7n8Vdm3T6Ib92eiAwgoKOpVvFxo4DoFk/CAAAAAASUVORK5CYII=>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAcAAAAbCAYAAACwRpUzAAAAmElEQVR4XmNgGLlABV0ABhSBeCG6IAy0ArELuiAIcADxViCWRhbMA+L/aPgnEFuCJHmAWBKII4D4H5QtBsTMIEkYKGeA6MIALEC8Boifo0uAgDgQ3wXiA2jiYFDEADEyiAFiCsh+YZAEzMi3QKwJxMZAvBiIOcHaGCCh8pAB4tJVQGwGkwABXyD+CMQbgNgTWQIGYP4dvAAAZkEYQOdHRHcAAAAASUVORK5CYII=>

[image6]: <data:image/png;base64,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>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABsAAAAZCAYAAADAHFVeAAABl0lEQVR4Xu2VvStGYRjGL0khEin5GCSLAYNsCqUwWGSz+AOYDBZisTFQCjFLPspgYve1WGQyMCiDgSglcV3u87w979MJ73teZfCr33Du+znd57mfjwP8889fpZ+u/sAFWm+vZE8zHaJ79J2ORM/OTfpGn2mbvZKcRVixvDAB+4BrWh3Es6KcnsGKxaEZHcDGJWYYVkgFHZWw1opuOuflEuFauObF+uiG95wT/BYuwzbFJH2gE964nNBE72HFbukNfaKvtMMbJwroWBDLCH+93AZop+e01g2KaKV3Qcyni17QqiD+id9CFXWoiM5fJhTSfToTxFPoSx/x/YEtoyv0hM4HOaHb5RR2+C/pVnraiGthHOOwj9GGOQxyjh56RevChGMHVmyXFgc5h9ozCFuHYzqank4xC2ujxidGZ3GbloYJ0gC7zjQ70eLlMka3iXaZ2t4bxTphR2YAVkTFVLQRCc9nEazlmt1UFFOBF7oOW6cjOk2XYBsqEfmwTeT/FbSOum2EDnwF4v8aiamBzbQkTPwGmoFm+yUf24FPUceEot4AAAAASUVORK5CYII=>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAcAAAAaCAYAAAB7GkaWAAAAhUlEQVR4XmNgGNZAEIgZ0QVBQBiInwOxJroEDHCgCxAEzAwQYzGAChCfBuLXQCyPLOECxP0MEBemA3EEsqQnEJsCMScQ7wBiRWRJGNAB4vcMOPzYAMT/0AVBgB+ITwDxdSBWBuJAZElfIP4PpZczoHlJhgGiaz8QmyBLwAAo2CTRBQcVAAASQQ9WYi6BuQAAAABJRU5ErkJggg==>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC0AAAAXCAYAAACf+8ZRAAACAUlEQVR4Xu2WzyumURTHjwaNKDR+pJSsRA1T0yxlYcGGbPEHWFgSUZYWmgWLaWpkaighlnYkCzsLKWUhC4piIwsbC3y/zr3e+x4Pxuv12Dzf+vQ+95zz3Pc89557nkckUaJEiTJVD/gLpg0NYVCGOnZcg2Hjy4qOwC0Yt443isly3ndNOtuTJ0lbPZf0Z5ATXFcFvigVgUp3HWvS/ONNZyNfwZrowToHEyDPxXq1gH3Rg7cFlsBviTFpL64qfe3GztiZYHwqmrBfYa/nVjrfGl6rl5KuNnbGzprxCsgNbFRU0mynfMC+wPaUWJa9oNU6qJeStnUclXQ49opKmqoHP4wtSty5AzBgHVTcSXP1yozt1fJJjxr7/yZ9IdE1zZeVTboUbIse5H6wCP4Ffi/euyFadgXGd68T0cmXRduaV6Not6gLbJ/kcewQuAEjzk+1iT4MY+ecjfoOzsCg6PzrDqsu0ClaHmmL4bfP0izpLY9wzG8VG8s5mGg3uAR7ot8vf8DPIK5DVCyNK9HDzYPWBGqcLxTLZwH8ktR74l3E5CskVU7s97wueYjQVsny2AHfArtVLTiUx+02dvl6ZrubF30AtkmWiRVjGFsu0f7YxBLZBV9E29gqmBItD7ZBni3WN3eIdn42T4Ji3vxRYscoDMYsm/Dg0zfmflnH3Bl/sO91B87FkY4MWQuUAAAAAElFTkSuQmCC>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAZCAYAAADnstS2AAAA6klEQVR4XmNgGAXYgT4QPwLiX0CcjiaHAUSA+DQQfwNiUzQ5rACk+C4Qi6NLYANvgXgNELOgS2AD/4DYBYnPCMSsSHw44AXiJ0AsA+WD3H0RiLcDMQ9MEQxoAvFWIOZggJg+GYi1gfghEEsiqQMDPyBuBWIrIO4CYk4g9gTiE0DMj6QODEAKVwHxVCDmhoqB3IthKsidIPcKAnEqEP8F4ukMOEIF5EZQSIAAyDMHGBBujYOKwUE5EP+HsmGKrzJAYnUhA8TTYACyChQRoAgBAZB79zBANPABcQRUHA4EGJB0QwHIBjE0seENANxTIZ7yDV1cAAAAAElFTkSuQmCC>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFAAAAAZCAYAAACmRqkJAAAD6klEQVR4Xu2YS6iNURTHlzwi73ce5ZHIO8kjkfIoEwYeUWSiMGCkyEDdkjAQSSZeGYgiE3kk5YaBMFEeRQbkEZIIhcL6Wd++Z991v33uPfccOXL+9e+cb629v73X2muvtfcnUkMNNdRQQw1VhvbKNl74DwIbeirbekWMecpnym/KLU5XKrorLyq3ekWGAco9yvfKT8o3ytfKjcqpyjtZm2oCTtwuZlsuBilXKn9KeQ5koM3Km8reTgdWiy3SB+WaSN5NeVBsEZ9K9TkQYA+2Fd1V5TpwrFg0rfAKsYF5/yPlCKcDQV+tDgQflZO9MEa5DjygfKjs7xWK+cqvylleEeGWVLcDsQ0bk1GY58COYuFLJ/5jHL95oP9iL1TMVH5XrvMKB9o9kMYO7JI9w9TESfB9sv8ULxaQfpUGtmHjIq8IiB3IBHiG9crxYjmKpP9DuTtrF4MQn+iFYu/kPRSrYsBJm6RgPMXonvKQ8ohYBMzOdOC4FOb4WXlD+Ur5UmyOIwtNKwK2L+Ps8IqA2IGs9jKxbceErkZywpi2MdpJevsFQ4vmjxzQ54kUUsI1seo9KXvuoZwuNi5tx2RywGLRlspeKWAbY52QxG7wWzh0YDUXRPIQyjGImttiZyaP1jrwrfKCFCKSFMB79je0MF298kskA6EonVN2crrWgjRxX2y83BSRcuBz5eBIvlDyHVif/XoQ8rSf4hUlgmMQ72FBAsK4bC0PnIq81IVLIYwF8+xMOtBvzVIdyBZstoIpRivPKrtmz0QgDlglVhzCuC11YNja9AOMzXl3bkOL0sC8rkvazrIdGOcrj/ViuTTvDBiwQVmX/e8nljriqh47sJdY3i3mQGRxBDK3x2KFKg+jxLZoXiEEwR9XlJ2d7jfKcSCgAg73wgxEEH1OSWJwsYkFB2O0HxcHBweix3mVzIFEJw4MRyIPbMPGw14BgoF1Urg4TxA7trwQWx2Abq1YW38e5KzHWS6FY2L9cNQwpxuqXBI9hwhcHsnuivU/o5whNn5wIPL4rkoV5tYzJJI1B4rTSbHIzkNLz7OtBnfg89LUsR5Ex0Dl0ozkvtTXDo4qRGG4W9M3/joSb2FkOJ72PkcxDgdgtnAqzZCCihU6bLskLY/okkGee6cc5xV/EMVyYAxyKdFVrJAV274A2/Lu+RUDUcJ9dp+kJ1lptNSBgAiLz7MeyQOymPyyNI3sioOTPxOd5hV/AHwSOy32iYwcuEtsy6fAQb+vWG73eY60EHIbhYwqHwN7KnmraRZzpOkk/yaIIO7Te6VQbCiOFLRQzXcqj0rjwtNB7AMw9vz38J/mOU5ty34BKShVzJL4BTmj4pxJshS4AAAAAElFTkSuQmCC>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABcAAAAaCAYAAABctMd+AAABNUlEQVR4Xu2UvytHYRSHjxBKJEqUWVIMMijFoExfScpgMMpstZssyqDsUmz+BAOZDDaKP8Aqg+L5eN97O/d16375st2nnno773l/3HPPvWY1NTU1X3TiJK7jYnGqNXbxFT+cirX5pN8wbeHWVShnKg1WMYPDFkqhksxju0+I6BIradBxgCdpsMuK5Xi0cNhPGMBb3PbBDjzCPhyJ9vqEJpnAJ5zzQZXkzAdK6MdjvLHvL3gcL/EB3y3k5CXVSXdWXDSGp3HcjWsWynSdZxQpLYnQpmo5X3O555MsXOI5iWWoJHpPs+lExipuYQMHkzlxiOdW3oqbeI9D2JPMVaJFWqxN1KpiAV/iODtYzbERY02j21xY2CT72JbwLY7V+1e4jzsx1jLLaeCvGLXwJP+CuqzsF5HzCbZmLyuKvzAUAAAAAElFTkSuQmCC>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHIAAAAZCAYAAADt7nrkAAAEI0lEQVR4Xu2ZX8hOSRzHf1qrxZZkWxT5c0FCSK1E3LhBKLYo5bVXWvZic2Ej6XHhxv8kCiUkyRa1y4VVJBfClbjbvVgtklBbLtgsv0+/M+2ceec8z3nOO4/ex55Pfet9Zs45c77zm5nfzHlFampqampqamr+p3ytGq36Iqyo+ahUisMA1UHVe9XgoK6IMapbqt9VR1Wf56uTsVh1RfVctTKo6yb+kmo+pqj+UE0NK2KMFLuYxspAsH9R3RUL/p9ioyc1vDzGT4u1cypf3TXgY49U97FNtTksjEEQCAYqw1zVG9UJsRc7Jp2ZkQ2x519UvVOtytV2Dw2xWVjVx0+ZWtJuIHkoHVxqlFTkS9UN1d9BebfhfMwIytuhI4EcLrakPlVNDOpSMl/1j+rnsKLLcD4GhhVtkDyQDbGZ6IuOHuRd01eGSe82UI9/URdwW3p7qOqj7UCy4WkGy8Q6sRe6IHYfZSlhB81zeT7t0B6bsU7k4E4yQvI++LuqD1JYqUCuVv0rdoxoRbP8+JlqfFhYAT8/+rmF5y9VHVLNEQt6fyZVnp+luiM2OKJw2OT8+Fasc4bmq6OcFQsk5zvHTNUlsbw52yuvCmdUjkKsEIxiIMfsFtvxbRB75x+zuv6K76OvPFY9UK2QgoCOUt0U65gyB9UXYpsdNj0hyyRNIAkUg2WXVzZZ9Uy1L/vNyvBa0rTXKWI+qsC+gWPLemmxCk1TvRJL0K1gCWZWxh6YKpCsDnRAOLCGiC2vtH1SbLRPyF3Rv4j5IChHVD+otqvOiH0ha5Y716gOS7zPc5TdtUJRfoSiQPKSO8QGysKgLsY16Z0fffhSwuzcInlzrpMmeWUhtP+95O87oPpNbCl08Izrkp9NzkcZD6SpmA9SA0cSJs43WRkfWJp9GWt719oqkJhnRi4KKzKKAokRDDEIysx6ZtpD1VdhRQadvlVsdvqQt2njnMTPba5z+eznB5t7kFu2wX21YklzOB94YNA0w+XH0MeS7LcfmLVZWRHJA8kH3MtS/EW+KJAO8mqZAz4dSH4JYSCxJLnZtEnis5ZApj4W+eCh2QwClx9jPpgIbvaTGtgMjRXbr8RIEkga3KmaJzbiYy/maBVIcvGpsFAsMAvE2sEMGyoGjQ/XsJQeV32r2qi6Kv/tan32hgWJwUNsMPs+mNExH8By7e6nT5m1DSnO90kCyQxkZPHyvAAjJ4QR9kj1MtN91fTcFWZyv1jiDsEspmmnR6wTwqXRX56dWCbDIxP/mSHndAp8xDyA74OdfcwHAaRPHZwR74mdj4soHUh3cH0TlAONPlF9JzZyqkKS/1XiS57rANribDguX10aN2vDzksJPmIewPfBma/IB7tvn9jsdrDBOqlaHlY0g4PmebE1u60ba5LDho5NFR9BmqWrmk+BD5/t84mOly40AAAAAElFTkSuQmCC>

[image14]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABEAAAAZCAYAAADXPsWXAAAA7klEQVR4XmNgGAVDExgA8QUg3gbEr4HYF1WaOHAFiJcC8Qwg/g/EC1GliQMgjSlAvB6I/wKxH6o0ceA3ENugC5ICZID4MBDzoksQA3oZIN5Ax0nIiggBHiCWBOIqIG6GssWBmBVZEbFgEhB7ogsCASMQuzFAoh8v4AbiPUCsiSauAMT3GSDeI5hmjIH4KxCzoEswIOQIGhLEALENGyDakFYGCg0BeWENEH9Cl4ACogzRZ4AYMB9dAgrwGiIBxNYMiPDAlU/wGjKHAZJLQenjFBALo0qDgS4Qv2KAWPIFiB+hSkMMSQXiqwy4XTEEAAAULDK9jhIPcAAAAABJRU5ErkJggg==>

[image15]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABEAAAAZCAYAAADXPsWXAAABGklEQVR4Xu2Tr0tDURTHj+iSzqBBB8qKKEtOjO4fMLjgDGbRbBdMYhzIWBARxWAT1kwmbUsKrtiWbQPTEP1c73t4z/HJrnHgBz5wOd/zftzDvSL/DCdlfMRbfMUNHcfxjNd4ih94peM43IO72MJ3rOo4jj5WbPEvzOED5m0QQ138Nqw7YdMgJrCAB3iUrGcwFzbF0sB1W4RDPMN9nDSZYhzvsGTqKziPi3iPTzrWrOIbjpm6m9dSsnbb7AbZDzbFD9MyGqzTD/3KsWS/JGUET/DFBiluCzfYs0FATfw8FmyQsiz+BZc2SGjiVLJ2B1Ixi2vyPY+se1IUf5e2cBsvdCxyLv6WuvPRxmkdf+F67ElWuIY97Ej2XwwJnyEJM59F6FmxAAAAAElFTkSuQmCC>

[image16]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABEAAAAZCAYAAADXPsWXAAABL0lEQVR4Xu3UPUsDQRDG8SkUFE0gWqgQEGyCVQTt9AtYaGGrlTHY+QGEVMHSRgRFBF/AThALray0s5AUEWvbpBMsRET/k83L7hzBtVPwgR9cZi7L3dztifznb2YKFVyjjoWwHZcqzrCPT5yE7bjoH9dwgQ8shu24vGPOFn+SLO6Qso2YbIu7DWvVP+m7DGIMmyg3j0fQ658Umx3M2yIp4QAFpE0vyABuMGnq45hAP47xFHRNpvGKHlMfFTdwzTrevF4iS+KG2S1DuMWebfjZku6L7OIZl8iYXjt6C+d4sQ2TFdRssZW8uAWOTF0XP0Wu+bs1N30I7ejQZqUzD7tP+nAlncHqdtBtEeRQ3C7V9+Mew2G7Ef00bGAZD5K82sYiRTxK8ir8zIj7ruhb/AvzBYyjNCRjMaIeAAAAAElFTkSuQmCC>

[image17]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACsAAAAZCAYAAACo79dmAAACIklEQVR4Xu2WzUsVURjGH0kXUpIgVIqQtAkhMWgVtXBT6MKIEtpIiyj6H9pKC0U3QRHRBxK2Ctq1EEGhjahQgu6EMAKxECEKAhF7Ht8Z7jln5s5c751284MfXM97nPPO+XjnACUlJSV5XKRf6Ef6kw774cIYp5/pCmysE364NtboDH1OD+i0Hy6MX/Qh3aV/6CU/XBtK8D79QPfpDT9cCCfpMr0NG2MWdc7sHr0aNhZMP31Pm8PAUeimn2hbGCiYR/RW2FgrU7DlD73ndmqQ83QbyTFWaYfTLxftl07YG49Fv0/TFrdTgxyjp+gFugHbChqn3e10FJ7QobCRNNHrsLLWKL10hx4P2lvpCzoBW4VM9M9zsIe59NCvsCUrouZqMvQsF63sK9jMa2X/Imcs1TnVu7QTGscyH1AjqtuqOC4DQZv6bDp/J9DpDN84pqhkVWVUbb6HAVS2hWZ5gS5WQkkeo75kdQjn6bkwkIL6bMGSqcY12Fj6YKSipVeR1icwjaxkFdNLvoEdxCz0sdFyvwwDEWdhpewOMp6lMqJENWAaWckKzdhbJE94iJKsdg/QCl2OfitRHTSPM/QKKvu12j0gL9lBOhk2Rmjgm7QLtl8XkLwHKNFndCRS9f6d1wP2pjp5qq9LSP+S9NEfsJf5Tb/54UNeozIrIfGq3YVdOUf98CFxOXNNbBU1PKDrqD6reWjmniK95Ik4WR3gum9XJf+DfzlMcDvFXE9dAAAAAElFTkSuQmCC>

[image18]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACcAAAAZCAYAAACy0zfoAAACEUlEQVR4Xu2WT0gVURTGv8ggIlEjAjFQIhAtcxG60Y1QoAgtokXhpo24cBWBQbRw0yJwUS1CRIlWIWgRKC4UMlq6CVFbSItCdFVgVJuQ+j7OHOYyb4THm5hHMD/4wZt777w5c879M0BBQcH/yQCdKsMntMVuyY8OeoO+oX/o7ejanaUH9Ce9bLfkz1NYcEeSHbCAP9PGRHsuNNA1WHBpKGPLsHG5MwQLTAE6p2GlFn10IujLFS/pdNDWT18G11UhLOkkbBE8oPv0XjCuKrTRr7DgdukX+oP+pr3BuH+Bpsp7HD63Swjnm0/4LvqBNvmgCjlOXyfaFOBmoi2VsKQK0lFQ2v+ycoV+SrSN0NVEWyqd9DvK32Db6XO6AFtEx2gz/Ujv0Fd0ifbAAtijv+gwjBo6R9/SGbpOr0Z9JaSV9DAG6Vb0u5a+ozfpKF2kK7QVcaZUUrXfj66Fl9R3hRfB7xLmYcHpjU8k+kLO0A06Hl2fhGVGWbxOt+k12OnSHY05BztVVFpHC2yHXkR68BWhLSU8vrQHfkM8FVZhAYc8hD1cQZxHXFJNB6GqKYv6z0tRW0X4xD5L62BH2RgsU3qoP9DxrChAjbmAuKS+8LxfgWfaTzXxH8GOMwV2ix6N+vRQlTTJXdg2ok8toSyr/NpXxWPYF88z2KLKjErnQYWkfcmIelgWhe7TQnJ0zynYixdk5i8mBmpynHYZiwAAAABJRU5ErkJggg==>

[image19]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAaCAYAAABozQZiAAAA0ElEQVR4XmNgGAVDFHgC8Swi8EQgVoBowQSTgPg/EM9Hl4CCh0AsiS4IAoJAfJoBojkaTQ4GdjNA1GEATSB+C8SfgFgfTQ4GlgExB7ogCIBsA9kKsh1muggQbwRicSi/B0pjAJh/5yCJeQDxciBmQRLDADAngzQ/A+JHQPwFiH8DsQ2SOqwAm5NNgfgCEEvDFOECIKfCoogRKgaycREDASeDALYoAtmoi8THCUDR8xWIjdElCAF+Boit64CYC00OJ7AE4p8MEI3oGJTWR8GgAACg8y9yd3OpQwAAAABJRU5ErkJggg==>

[image20]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAD4AAAAZCAYAAABpaJ3KAAACk0lEQVR4Xu2WzatOURTGlzDwlZSJmJCJ8pmP8jVjIJFkoPwBlBkDQ3ciA0x8dDERJRMzkhBJCQNKKSkDMpUoIoXnZ53du/e+73vec0656rZ/9XTvOWuf/e6117PXOWaFQqFQmLhsk55I76VH0vI0bJul69LFSCuTEf+eedIp663zuDQtGZFCTq/Nx76trsewTNojnZd+S9ekKVF8vrRPui+dkXZJc6P4eDBD2i4dkD5L78w3YxAvpF/SJ+mgDVnvaesNXprFYL80Kb85zmySHktfpBVZLEDRLpgXEafGRRzDHOmWuZV4YCSJesKXsnv/Azb/hHmBtmSxwFbpsnkejK8FK1PxhdIH84f2RvHV0t3oug52mLnOSVOzGNAfntrgig0Cu96RFpmv70ga/lucQ9JO6av0yoZYHFgoyfPwWfOJb0fxsDFNIeHQCHOeS+vymw1YK92QZpqvj6rGrDJvgPw28as25GgGmy+prtdLPypBsDnJtyEkH1edandJGrDtser/n9I986YHdHia82Lz9TayOQmTOBsATEK1eZhJ8o1pQ5w8SVPtLrCOK+Y2ho+WWpmihERZ7zdzh9TSz8acbxLnzHO+b0qzkhHNIfGH1t3iEJ9v4HVGL1pQXVNtjgCw3qHnm91hwn6NZkR6Zn6udqehVryRNkonzRfYhdjmwGuKwuwwd0E4y+FYtrZ5DNVmcmzVxeZAhUOVsTvJ9+v0deQ2BxzK2o6af3AFqDLVbmRzdqhf9wtNgs/YLjYnYaodQ9JUvU3yJPPA0s3ntcXavlu6IdicV1mtzflxPu3YzdlZLEBnz89/E9ZIL6u/OcHyTZJn8/lgwXUbpMnVfSxO4qPW+zJjvsPV/enVvUKhUChMWP4AL9+CPA8h7yUAAAAASUVORK5CYII=>

[image21]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFAAAAAZCAYAAACmRqkJAAACqklEQVR4Xu2Xz6sOURzGH6H8lpDESiwkWSAlpFiQspCiSMrCxhYli7uxtCAbUvf+AcKCjSzEjgUbWdlIFFnQZXHlx/M453vPmfPOfWfmvmbeuzifenpnzjnzPmfOfL/fOQNkMpnMjOQi9a6PtoahmTLuUzv88SzqBbXMny+nNvrjzBSciY5XUKNwCykW+bbWmE+NU5+o99QEnOFt6kg0rkvOU7dq6qC/xjhLbUnaypiH+j6pxyRr4cJ9Q9S2hPpJfcHwQn8fdRxubn+oU9TRSGPUD98XP+Q51B2E9O3HXAQf/c9bFH1OIPiUBpJC+xH1NO2Ai8Rn1OK0o0PkrTno5srYTX2j9kdtypzX0Xkd5COPS2mHRz6xxyS28lrplIfU9bSxYxT9yoLfaYdnNfUSxXTdBZc9TZCPPEoXCc6npyQspB7DLeBYsesfh6mVaWPHqAZrfkpJQxGmrBHrqZtwmSQsfZX2TZCPrtP1hjzW+WP5mEcBRZgmKF2DewIqrDMB1TCrf9rjGQeoe9G5ofr1AW78L7htjWp5FeYTewh5VK6FQvcjwiKa7saDpkARfAjFwl6lnQhbiyq08f0Ol1ojcNdfpr5SV8KwgTGfEYR5yqe2h/L7KnoXsTRkI9peQG1FLJr0QtPXxAT616rpYD7mYT6NPbRgSo/ncH+4vdjdOaMI9c9qk+b0ilpjgwZED9N84vonn0qPNOcNLeQTDP/bUW9SpVY8D93U5uh8UOyNLZ+YysVTcTydNnpWUW+opWlHwibqM3pTv58eUAt0cQ00Pv6ebQMFkfk0Qq/nGyivRyfRfB/1v1E66ca0vWgL2/JMy0cFUsX5GMIi6ld7v3Hqgm8bBpqHNq26sXNwn1ttIA/b9sinNrOpvf5Yk9sG90Wyx59nMplMJpNpg7+SqKw/3LRoLQAAAABJRU5ErkJggg==>

[image22]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA0AAAAZCAYAAADqrKTxAAAA9ElEQVR4XmNgGAXUBzJAvAqInwDxOyC+A8T2QLwUiFmQ1MGBCRC/AuIJUD4jELtDxYpgipAByIbrDBANIMXIoAGIbdDEwKABiL8CsTGaOAj4ArE0uqAkED8E4v9AnMCAaZMmGh8MOIB4KwNEEwifB2JlIGZGVoQN+AHxXwaERhD+CMThDJg2owAtIF4BxL8YEBpBBrkiK8IFQCbnM0ACBqRxDqo0BIBCBxsAiYM0TUKX4GXArSkaiP8BsQe6BCg4c9AFgYAfiA8B8S4g5kGTYwgC4vdAbIUmvhiIbwGxPJo4OB4soWxuIHZjgDgphIFAMI94AAD31ip1jnxN7QAAAABJRU5ErkJggg==>

[image23]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAAwCAYAAACsRiaAAAADmElEQVR4Xu3dTahtYxgH8FcMCAMfJV1ShKQYGJFukkK+SgqJbhkwNmBioGRwy0hMRB0DE5kqSSgDiWQiA6mbAUURYUA+3n9rLfvd717r3sk59+yT36/+3b2etc7ae9/R0/uxdikAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAwP/HQzVnjK9/H4/jyPgvAAD76LSa55rj32quG1/f1dQBAPbVlTU/jjlcc2rZ+9Gl+7pcNdbPrLmjqd9Uhqaq91PNY31xdKhs3n+6xw1d/dyxHufXvNIcAwBshafLMA14Sc2FNcdq3qu5sblmt51e803NrzX/1Hxbc+d47oqaz8Z68tJ4fS/n3uqLo4drvi/DNWlCvy6re+yMtencZWM98p2n6VAAgK1wdc3RmlOa2tk1H5b5Ua3ddE7NJzVP9SdGH9Sc1RdHl5ZVQ7ck05w5P3ePi8pq2nOS7/tmGT4XAMDWeKZsrtNK8/Z6V9sL19b8UpZH8tp1Zb0Ha74sQ0O21Fi+W5YbulvKZmOW6dAvuhoAwL6aRpQyNXlrd+5kyFqxpYYrI2jJnKxPy6jcbTV/19y9fvo/ufd3fbGsvvckU6U7ZTU9m/+Pe5rzAAD76vGymlr8uCwv4t8LmQ5dGgFLE5bNB3PSXN5ehsbtWM2LZX1Kd7K0xi1/92lfBADYZlnkn3VsU+OWqcYL1q5Yd14ZNiecKHNrx1p5r2wG6OXv3u+LjefLagPBAzV/ls1p1WmNWxq7Xkbn7AQFAA6kjGg9W4Zpxqzx2mtpqNqpyUmarYy+LXmieT01Zv16tzRqmQ6dm1bNe9oJCgAcCHO7MzO6lY0A2RCwZDdG2HJ+qTHMFOfcZ4tsFOibsDRsedht67WaF7ra5J1y/M8GALAVMpo2t14t67veLqufaZqTZ6RlYf6JslPmn58WadjaXxRofVRzcV8cXV82d3fmAbr9Wrg0bHNNXxq1e/siAMA2ypThXzWPNrUjZVgPNreAfy/k/Xea42tqPi/z75/a/WVoztLkTY1gGrCMyKVhy2jdtPYuz1nL+rjLx+NIE/dGcwwAsNWy5is///RDGRqZV2t+LkNTdLI8UvNHWb3/VzU3r12xksZs2hSRTM+OyyhaW2+nRrN5Ik3hy2X45YYny/FHDgEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAOhH8BxD+YR3e2qHgAAAAASUVORK5CYII=>

[image24]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAaCAYAAABozQZiAAAA0klEQVR4XmNgGAVDDJgD8UognoWGk6HyakC8GoccHPwH4tNALIguAQWeQLwfXRAEGBkgmiehSyCBVijGACDbQJqj0SWggAOINzNAbMcAxkD8Fog10SWgQIkB4iUQjQFANh4GYl50CShwAeLtQMyNLgFyMsjUIHQJKCDo5K8MFDgZFFi4ogink0FgDgNEMy4Aip4GdEEYwKdZBYhPQGmsQAyIrwCxApq4DBBXAjEzmjgGUADibwyINA4KIFC8g1IeUQAU6hEMkAA0AWJWVOlRQBEAAIWUJkYpmUL8AAAAAElFTkSuQmCC>

[image25]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA0AAAAYCAYAAAAh8HdUAAAA4UlEQVR4XmNgGAUEgTm6ACEgCMSngZgHXQIfsATin0Csgy6BD5QD8X8gTkeXwAVAphcBcQYQPwdiJVRp7CCGAeI8TQaIbdGo0piAA4ibGSABwckA0bQciFmQFaEDkFPykPggTQ+AWBpJDANEArEnEv8rEP8DYg8kMRQAckI/A6rHTzBAbJuEJIYC/IB4ApqYDRD/hmIQGwNMYcAMKREgvsoAsa0VTQ4MjgOxKZoYIwPEMJAmkFNRgDADxAmgFAAKdhhgBeIcBogmULKCA1+oIAwfYEAkVGRxEAaFpjFUblgBAAslKmZjmFdmAAAAAElFTkSuQmCC>

[image26]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAJ0AAAAZCAYAAAArBywYAAAFaUlEQVR4Xu2aa6htUxTHhzzy5soz4tKlhJBXCslbIqGo63GRlOSdR3w4hUiXvD94XT6IJD4pIR3cIpQoKZJHIkpKh3LlMX7GnPZcY8+59j57r73P4cxf/btrz7nP2nONOeYYY851RSqVSqUyPS7zDZWxWU91k2pX37EU4OEP8I2Ow5PrnVSPqK5UbZm0V5psozpftbHvCOygmlFtED6fonpYdb/qsNDWFfzG1y16p/fVybJctUb1herUZleDrVSbh+sDVY+q9lK9qfpQtUvoq/S4WPWralZ6tvOcLT274xRnijnqpap18UsdsYfYfMMWqrek5+x7ql4L1xNnQ9VGqoOk3enSKMcqXJu0/6a6odddCWymekranW5GLNrB3mLOBjjDM6qdw+cuwMEj/NaPyWcyFxG2lU1Uc6ofVN+IrYptVY+pzki+NyxtTodR7kk+r6/aNFzzd7+IGW8hwA53qR4XS/epYrlwpOp510cUynG72CJKF9k4DHK649xnbAuUO2Sg3ZM+ILs8Lf3Peqdq6/Cdm8V+N2eLCIHjc9fWCqnsPbGQGKGu+l3Me/Hi+dLmdCeqzvKNYoa5V/WpajfXNy2I1MeqzlH9JWYXrk8XW4RAtFipel31SrjeL/R5+HvuM+PaR6XN6VgwlC059lF9L2bjFJ6JZ7tKLHU/JDY32ABbALXgFarvxJwrtQUsE3tOFuJQMHgMRy3lIeKRp8nXDJbBlHRE+JtIyekI86ulf8UB9Qf13ArfsQBgVJylLc3jbLnJT2Hhch+K6pxDxEn39owiTaW0OV0pmvK7r4rtaksQIf8Um7cczFvJqWJqvcZ3lIgrGgN6XhLzbOjK6XC226R/xcGLqh194wLB+HEY/1wp0TZtfCZm31KK7dLprvUNYtHqAdUqyds8wuJinEStHIzzXd8YwHcG2epfKEzZYfBjTza7/uE01Xa+cUhyTkf4J33yACmkUsaBkVkET6gub3xjujA51DnUQKWJ2l/1vm904GQcbbB4sfFso3c0Sk53kuoi18bYORWIDsy5aNxkpFBekdUYYwmiGPbwpKk17lwHwmrlx9B9YmG2dAY0DNQ2H4ltSObEzmticbuv6rpwncJmJY4h6uTGN6YLi+JjyUf/CH2ldBO5JPzLAuKZ2CCNA5uvdWL3+lb1bGjHuW4RO8JIYWF4uxJoPDG1UrPliKnV2+M8sXnmvoyLuR7K8cjH/Jgf3AvplzoC4+dSzKgMSk05lQr+FNIE6YJJy8Ekr5H2eo9IRBkBLLafxOw6CdjYsNscasIzsMNmbKVzNe7/gZTrvZGgbrhb+h3Ph/BxWS3d3nNSTjeovqH9DWmvYZig6JSUFS+L3ZPrrkkPhOcL8zErNjacLwfPyfOW7DEWDIDagIKRQRzS7B6bC33DIiSmkraohEOtlf7aNOVqaZ6ZxRRL1OsSxjsj+VptGEjJZDrSazreFBbPMJumoSilh+j9nYbT/wjxcPpn3xFgkp8T2/CUwLEo+NPaONqUTcU4NXPXxKhOas3Vezglxz2cOowND77KNwZYNZ9I/lxpMRELYF8WtInjgzai033lOwK8jXhbtb3vSCCq5VIVEzzqYfukiE7HIslxq9iJQ2kXPy/w4Aclf7NzxQrppQhF85dS3slxeH28b0yI9Vvu1SEOzQTH96GLAY7FGBMlRW4jwnFI2wKbF0SJP8SK0Oh4/Msg5lTXh7alCIesRNB0QXJ9jOSdKYVTf+x6h/RnihViE8zbgcXy37dI+7yRYnd9aNLO4rlROnwdyUvgo8M1J9YHi9UoR4XPFYMd4QViO+Tlks8K/xd4Nl7+cxZ3gvQvmEqlUqlUKpVKpVKZLn8DLg4hu6HVaRQAAAAASUVORK5CYII=>

[image27]: <data:image/png;base64,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>

[image28]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEMAAAAWCAYAAACbiSE3AAADjElEQVR4Xu2XS6iNURTHl1BE3pEMuAwQhbwGDCiKxAADxeDOTIwUInQnykQJIXl0lTwyEwoDDBBTUsrgSkmSEXkU1u/sb92zvvV93zm32z0R51f/zjn7vddea+19RNq0afMPsk51UnVMtTTU/XWMVg2NhQPEENUm1TjVdtX3fHVrYVOTVJNjRQU7VMeldcaYLckIgGEuq6bUq1vDINVj1RfVG9Vb1VPVMt+ohGeqibEwY4vqtaTxnqgW56tz4F3dUm97WDVGNVN1xLXbo1rofhu0JZRsvoOSP6BhksLsnOpMpl2uvsZ8SZ3ZVIRNPld9Ui0IdRjvqGp4KI9cU11U/VKdDXUGY2MI5voR6jxzVO8lzV0FnvRI0nwnpNh2gupBKKuxSPVB9Uo1NdQZhyQNjFU9c1UfQ1kZd1SdkjZ5M1/Vy2lJXvRZ9SLUGXjOXdXeWBHYKmmtrBnv7shX17yKcQo8lNRpW6xwrJfUBs8Z68rJFe/c7ypuqJZIMlyZ9wE5gU0wz6VQB7g7ealTiicdwRCM9VLSeKzTY8YqQGPiE6tXYcbokXpSJf445XvWqAF4Fv3ojyLTVKNUFyTNY8nSw4Y2S90Q81ydh8O6JSlUuqS4P/ozDwbJQQG5AHevwjpHz8DVcGmSWSOIz+mSboHrksbxrFbtl/p4hAh9PGycfl4jci3q+FO3m4f2fIKFiPfw2iZxx+j6ERbGAhkQo9jJrM3KNma/q+D2GJl9tzg2xqvOS0rSPkSahUEjLESMNaqfkg4dSkOEBd6X5pOvkjQYC93gyi10+GyEd3m8yIzBnDulPqZ5X1mI9BUfIgbhQZgwtnl54QDNGN2hPMLVxEAxr/TFGEzOlWpYH+Aq5e1g7wC8j/dNo3dIMzACxoieTr5h3llSNFYvJDaSIMmwDAzGILul6D3LJV2VnG4VbIybxGAR3CgHpOgBrQgRT5ekOQohYpBMqhIoJ3YqU9kz2za2L1Y42LCfnCc+r8PbUs8jgAEGIkRIjGUvU2CPzFEIEcMWcUXy2ZlrjvD5qhrsyj2WWMveBHjaCkkb53lsWGjGl+wM1TdJ+am/nsFDjMfjSilfMzcLh1caIgbxRKz2SAqbq5L+FfKE7nDtIpaMyl6LlnBN/sTpYxsmxHw7EzdVX2HjrNn35xDwwggvYe+RpdhJEm98Nu2QwU3AibbJ4BnfyIP+K0iu/HPtb6z/cX4D+uLPDat0ZAUAAAAASUVORK5CYII=>

[image29]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABIAAAAZCAYAAAA8CX6UAAABCklEQVR4Xu2SrQoCQRSFr6DBICLYTEbBPzAp+ABWMQg+gK/hM6hBLILFYlNUFCwWm+8gVjEbRM9hZnFm/K0Le+CD3T2z9557d0UC+V81sAdHTd62pQqmYGhQtE5o5UADDMAdTEDY8FOgBbbgBnogafgv6oIluICs41Ft0Ach1zCVAAtQEZWqY7nq5ZGoZF/FA0xEnUQVaz5tKYGNqIZfxSJeN8ZnoRWI6mdmo4/yxsro+zK4anj991gswEJebKZgGqZiOrfRR72Lzf2wEPfF/cxBzDrhiN3WoOAaor4ci81A3bZe5Y5lKi0q0Vn+HIuLfPeT8Rl3tJMfY0XAAYxB3PE88au5+wvkaz0ALa0yjiqq6wcAAAAASUVORK5CYII=>

[image30]: <data:image/png;base64,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>

[image31]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAZCAYAAAA4/K6pAAAAzUlEQVR4XmNgGAWjYNgAAyCehYY9sYhxALECEE9EEgPpZXAB4idA/B+K3wFxBhC/QhL7AsTcQKwLxFeA+C9UD0gvHLxngCgGSSgCsQ6S2E8kdTlQcQywgwFhYwQQNyDxQRgE+IH4BBAvh/JRAEgTTDHIsOtAvBmI90HFxIHYA4h/QWkMAFIA0gRzMkwhzOBYBojNIDUgtVhBAwPCFSCngpwMM/g1A8RgkBqcgJMBERaaSOKWUDGQC1iQxLECmJORFYIMBkWdK5LYKKAWAADmWD7au6KtggAAAABJRU5ErkJggg==>

[image32]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAYCAYAAADKx8xXAAAA5klEQVR4XmNgGAWjgFLACMThQHwViDOhfBiQAOJWIE5FEoMDRSB+AsT/gfgAEPNAxUEGzIeKv4eKoQBPBogkCE9CEhdhgLgCJA6iMQDIKTCN0UjixkD8FSq+BkkcDp4zQCRPA7EgVAzZmb+B2AYqjgL+MUAULGVABAzIAJBBIPG7QCwOFUcBMGeWI4mhOxMUYJ1I8gwcUEl0/1UiiVcxQEI+Akke7HaYAmRsAMTtQPwXyn8N0wADRVCJdAaIcySBWABJnhWIxaA0HLAwQNyPM9RwAVgEPwBiaVQp/ECeAaLJHU2cNgAA6Oc6BGc1QkIAAAAASUVORK5CYII=>

[image33]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAYCAYAAADzoH0MAAAA0UlEQVR4XmNgGAWDBxQB8X8SMQdYJxTwo0m+R5aEAlUg7gPiXwwQNbyo0gwMt6ASMCyPKg0HTkD8E4gl0SXMGCA2wwzYwwBxGTpgBOIpQKyPLgEDwUD8lwFhUBkDRBMyUABiAzQxOAApBmmCGQAyDGQoSYCVgXCgEgSgMIAZMB9NjiBQYIA4PYEB0/8g4AnFWAEocB4BsTe6BBTAYsEYXQIEXBgg/n2NLoEEYNEtgy4RygBJZXeBWBNNDgSkGCCx85EBEi4iyJLxUEFS8CigFgAANhFFE3kaAaoAAAAASUVORK5CYII=>

[image34]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAbCAYAAACqenW9AAAA1UlEQVR4XmNgGAVUAr+A+AEQhwMxI6oUJlAB4mdA/ASIFdHkMADItPlA/B+Io9HksAJxIL4OxG+BWBNNDgOATJ/CADE9HU0OK3AB4n9AvBVdAhsQAeKrQPweXQIbADllKQPEKXgBSGExA8RUkFM4UaURAKbwGhCbMECcYoyiAgpACr8CcTCSmCUQHwBiHiQxsMIcIC6DsmGAH4h/MkA0gQFIEpQW/gIxK0wQCYA82QDjiAHxLSDeAxNAA6+B+AoDRB3YZGEg5kBWgQQEGCBJAJutwwsAAMTkH7Tu0AqLAAAAAElFTkSuQmCC>

[image35]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABwAAAAWCAYAAADTlvzyAAABVUlEQVR4Xu2ULUsFQRSGXxFB8ANBQbRYLGarIIhGDWITLAYNNoP4A/wHYhAMBpPZJnKDyT+gwaLBZjAYRPx4X8+ZnXXufgjecMM+8MDOzLtz5u7uPUBDQxcwQidoTzLfGy766QW9pyf02P2ib/TMxy2fe6YzutHRxhv0hW7SAZ8fpkew+x5hh/hh0CezEzja/AG5IFmgT3TWxyq2C8tOh1AOre/D1rN9xuh1GORQqAU7UGCIXtFFHy/RD9iTKGOU3iBXUI/nPFuOFBUUB3SdztF3WG7rV6IdZfNPqpCygoE9WOYT8ReXoWJl+2TUFTyFZV4R3+m/6LqCK7CMXE3WUsbdSuoKaoNbWO4wWUvRh6kvvJK6gmIbltN/s4qddKKIvxTsQ+xKocOkTNHLdFLo01VnCe8ldTlG21CXCvfewVpky6/nY6yzqI1Nwg62Bntvabts6DzfO/5PcznajhkAAAAASUVORK5CYII=>

[image36]: <data:image/png;base64,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>

[image37]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAaCAYAAACHD21cAAAAsklEQVR4XmNgGAWDELAC8SwicQ0QC0G0MTCUI3OgIBqITwOxIJo4XIwTiNegyjEwAvF8IJ6EJg4CW4GYA8TQAeKlqHJgE0Emg2xFB3DDEoA4AyEOBsZA/BWINdHEQSAdXQAZgGz6z4DpP7xABIivMkA0kgRgznyLLkEIgPwAsg0UOEQDWDSANGKLCpwA2X/YogIr4AHiegaIpitArIAiiwWIA/FdBogGdAyyHeSKUUAXAAB8miZVdxhgdgAAAABJRU5ErkJggg==>

[image38]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAZCAYAAAAFbs/PAAABBklEQVR4Xu2SP0vCURSGX6lBIWgICkUQojlwCoMWaW0RAofWcA/ET9DS2KzgB2hwifAb+A2aAnMJHHRpcRB9D+fc37m/6+QaPfAM99zzwrl/gH/244Be01c6oS/0yuoX9MRblTHd0F86ogtbf9IfWvZWoGGbd3HRuKErJIEONNCKi8YhfUMS6EEDX/Qy3jCe6FlcuIUGglPoeKe04G3OMfKBWDl001udKh3QNXZDYt1b88gIFTqkS3jgOepBjZbigiG1PjTwTothQ27pPCwSpC4PtxN4CIsEuf9v6JfJCO8gftB76CW06czq8oAZEpAv0KVzawjK+tFblWw24wg6ijyc/NY/xRbEUDyOlhm/WwAAAABJRU5ErkJggg==>

[image39]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAZCAYAAAABmx/yAAAAsElEQVR4XmNgGAW0AUJA7A/EIURiFog2BgZjIP4KxP+JxIIQbQiwECoBwg+BWBJVmoEfiPcwQCxCAYQ0goAfENugC2LTKAbEh4E4A6pGE4h9oWw4wKZRBoifAHE5VI0wA8IQOMCmsRLKh2nECpA1/gTipUD8F8onWiPMRkcg/s1AhkYQBrFJ1sgJxJ4MkNDECbBpxAtgafUQA0LjeyBOhYqD5LECfGkVJI6RxEYBAQAAQwFMzit42BsAAAAASUVORK5CYII=>

[image40]: <data:image/png;base64,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>

[image41]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAkAAAAaCAYAAABl03YlAAAAy0lEQVR4XuWQMQ4BQRSGnyCREBqRiILo1FqJExAlN1Co3ELnEuISClGIA6gkEhRUGolGge+Zmc3MJi7Al3zZnff+nTezIv9GHjvYw2Ss96GKa5zhER/YDhIwxjmm4g2fFt6wG2/4FHCDOzGjvzLCFy7iDUVvMsATPsUEA3TMFkt2XccLNqMEDLHvrXO4FC/kDqtfOxJi/lUUauAVM64AWTEHL7qCpu9R21DBg5gdP+jLFGt2reNXthag25/FnGOPE0wHCYveqGyfv8Eb1YkdRTLi2aoAAAAASUVORK5CYII=>

[image42]: <data:image/png;base64,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>

[image43]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAaCAYAAABozQZiAAABNElEQVR4Xu2TvytFYRjHH0n5FUldGRRRUgZmpbsYLSbFbhGDYjFY/AMmWfwDSgar7qZYbTKQzWD3+/O9z3tO73m7zsnE4FOfuuf5cc5zn/ccs3/+FkM4jL1p4jvacB4v8QEf8Q2vcC6qKzBjXnyDE0lOjOAtzqYJ8YR3OJrEY/bxIA324yeupomEFbzGgTi4gw2rXswi3psvscmY+VJ01yrWLGrWZo/NR+6JilqhqRrm9erLA2quYhqfcTkL/KR5z7xuMAt04nkIlpGd8Xua0Nmpufk/oA83cSNcd+BRqNkOsRw1KaiCXVwKcU11iq8hr5u0pB1f8ANPzJdyiGc4GdV1R78L6El186dITZBNIbpwK7ouRSdxgeM4ZT7FeqGiBL00WlKmvrZaoaKCBfP3OT/b3+cLcV02sRFL0ekAAAAASUVORK5CYII=>

[image44]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAYCAYAAADzoH0MAAAA5UlEQVR4Xu2SsQ4BQRCGR0KnEUKj0ipFI9FRCQWFVqkXhQfwEkJBo/EOhI5KISotvYQS/2R25W4usddIFL7kK3b/udnbmyP68zv04UiZ9lUQzeHEZGzNBhFYgjv4hGfYhTFbYGjBA0nNDKb8MdGQJORGCZUxcbiEHZJDA9RJGtxgQWXMHub1phd+iB9+wIrK+Do9tRcgBy8kb9FUWZvkCh/hghVJg7HZ45P5iw/M2smUpMHCrBtwDZPvCgd2EhuYhVtY9lU4sJO4koxT/0xOivBO0qSqslB4JxFVWSgy8ASPOvjzRV6HyixE4BDL7QAAAABJRU5ErkJggg==>

[image45]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAYCAYAAADOMhxqAAAAi0lEQVR4XmNgGAWjgCigBcQrgPgZEP9Hw71I6hhYgfgvEOcDMTNUbD4Q/wNiD5giZOAHxBOAmBFJzJcBYnI5khgYcALxDiDWQRNPZ8ChwRKIf6ILAsF1KBZHl9AH4k/oggwQPwWjC4IAyEmbgZgfygf5A+SnYigbK5AB4jtAPBeIzwHxSQY8ikccAABj2BkqMv0/JAAAAABJRU5ErkJggg==>

[image46]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAaCAYAAACD+r1hAAAAx0lEQVR4Xu3RPw4BQRTH8SciIZFQUqolFAqVXqOSSMQBOAGJ1hEcYKNFKaFUOoMonEFCNP58n7ezJtup7S/5NL+dN5mdEUmS5KfkkY2X8aTRwxFn3LBEyVsTJYMHul6XQoAn2tih4j6OwiLnijATvDDFXGwTKeCA4XddlIHYgG5WdWUdFzRc4aUjNqA+u2t04RVlV3hxA1u/1MkZWn5J1mJH0c326KPmPurP6jWusMAJTbGrHuOOjdj/RtGH0mOp+KMVxYb/M2/yxiBIxFzgzQAAAABJRU5ErkJggg==>