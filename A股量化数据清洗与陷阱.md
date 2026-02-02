# **A股量化交易数据工程：微观结构分析、清洗协议与偏差规避策略**

## **执行摘要**

中国A股市场作为全球第二大权益市场，其独特的微观结构、监管机制及投资者构成，造就了极其复杂的数据生态。对于量化交易策略而言，数据不仅是输入的原材料，更是阿尔法（Alpha）的直接来源。然而，直接沿用成熟市场（如美股）的数据清洗逻辑处理A股数据，往往会导致严重的“模型-实盘”偏差。

本报告旨在为专业量化研究人员提供一份详尽的A股数据工程指南。报告深入剖析了从交易所底层撮合机制到高层财务数据披露的各个环节，系统性地揭示了隐藏在行情数据、财务数据及事件数据中的结构性陷阱。我们不仅关注传统的统计学清洗方法（如去极值、填补缺失），更结合A股特有的涨跌停制度、集合竞价规则、停复牌机制及除权除息逻辑，提出了针对性的数据治理方案。通过构建严谨的数据清洗与特征工程体系，旨在消除幸存者偏差、前视偏差及流动性幻觉，为策略回测与实盘交易奠定坚实的量化基石。

## ---

**1\. A股市场微观结构与高频数据陷阱**

理解数据的生成机制是清洗数据的前提。A股市场的交易规则，特别是集合竞价与连续竞价的衔接机制，在数据流中留下了独特的印记。忽视这些微观结构特征，将导致高频因子构建的彻底失效。

### **1.1 集合竞价时段的“虚假”与“真实”**

A股每日开盘前的集合竞价（Call Auction）时段（9:15-9:25）是价格发现的关键窗口，但同时也是数据噪声最密集、欺骗性最强的时段。交易所规则在这一时段的细微变化，直接决定了数据的可用性。

根据上海证券交易所和深圳证券交易所的交易规则，集合竞价被严格划分为两个阶段，每个阶段的数据含义截然不同 1：

| 时间窗口 | 交易活动权限 | 撤单权限 | 数据特征与清洗逻辑 |
| :---- | :---- | :---- | :---- |
| **9:15 — 9:20** | 可申报，可撤单 | **可撤单** | **高噪声/诱多诱空区**。 主力资金常在此阶段挂出大额买单或卖单以制造虚假深度，并在9:19:59前瞬间撤单。**数据清洗策略**：量化模型应给予此时段数据极低的权重，或在计算开盘情绪指标时完全剔除，避免被“虚假挂单”误导。 |
| **9:20 — 9:25** | 可申报，不可撤单 | **不可撤单** | **真实意图锁定区**。 由于撤单指令被交易所系统拒绝，此时段挂出的每一笔订单都代表了真实的成交意愿。**数据清洗策略**：此时段的买一、卖一价差及匹配量（Matching Volume）是预测开盘价及当日日内趋势的高信度特征。 |
| **9:25 — 9:30** | 仅接收申报，不处理 | **不可撤单** | **数据盲区/静默期**。 交易所主机在9:25产生开盘价后，至9:30之间属于“连接期”。券商端可接收订单但暂存于本地，不发往交易所。**陷阱**：部分行情源会在此期间重复推送9:25的快照，导致数据看似静止但实则市场情绪在累积。 |

**深度洞察：** 许多初级量化策略在回测时，错误地将9:15-9:20期间的“涨停价挂单”视为强劲的买入信号。然而，实盘数据显示，这一时段超过60%的涨停挂单会在9:19左右撤销 1。如果回测引擎在此时段模拟撮合，将产生严重的“滑点幻觉”。正确的做法是构建一个“置信度衰减函数”，随着时间推移向9:20逼近，逐渐增加挂单数据的权重，并对9:20之后的挂单赋予“不可撤销”的属性标记。

此外，9:25产生的开盘价（Open Price）并非9:30的第一笔成交价，而是9:25撮合的均衡价。9:25至9:30之间的订单要等到9:30连续竞价开始瞬间（实际上是9:30:00-9:30:03）进行撮合。这几秒钟的时间差在极端行情下可能导致价格跳变。对于追求极致低延迟的策略，必须清洗掉9:25-9:30之间的重复Tick数据，并重点监控9:30:00的第一笔Tick与9:25快照之间的价差（Gap），这往往隐含了隔夜信息的超额反应 2。

### **1.2 涨跌停板制度下的流动性黑洞**

A股独特的涨跌停板制度（Main Board ±10%, STAR/ChiNext ±20%）创造了价格的硬边界。当触及这些边界时，价格曲线变平，但流动性曲线发生剧烈断裂。

**数据表现：**

当股票涨停（Limit Up）时，卖一价（Ask 1）存在，但量极小或为零；买一价（Bid 1）堆积巨量封单。此时，Tick数据中的成交价格虽然是连续的，但成交性质发生了质变——只有主动卖单能成交，主动买单无法成交。

**量化陷阱：**

1. **回测执行谬误**：标准的动量策略（Momentum）可能发出“买入”信号。在回测中，如果仅依据“当前价格 \<= 订单价格”来判定成交，策略会在涨停价“买入”成功。这在实盘中是完全不可能的，除非拥有极速通道排在队列最前端。  
2. **均值回归陷阱**：反转策略（Mean Reversion）可能在跌停板发出“买入”信号，赌其开板。然而，跌停板往往伴随着流动性枯竭，即使开板，成交价格也往往在极短时间内完成跳跃，普通限价单难以捕捉最优价格。

**清洗与规避方案：**

数据清洗管道必须生成一个衍生状态字段 trade\_status。

* 逻辑判断：若 Close \== Previous\_Close \* 1.10（或1.20），且 Bid\_Volume\_1 \>\> Ask\_Volume\_1，标记为 LIMIT\_UP\_LOCKED。  
* **回测引擎规则**：当状态为 LIMIT\_UP\_LOCKED 时，禁止一切开仓买入操作，且强制将滑点设置为无穷大或拒绝执行；允许平仓卖出。反之，跌停锁死时禁止卖出 3。

此外，ST股票（特别处理）的涨跌停限制为5%。数据清洗时必须引入“证券状态表”，动态识别股票是否被戴帽（ST/\*ST），动态调整涨跌停阈值，否则会导致对涨跌停状态的误判。

## ---

**2\. 停复牌与时间序列的连续性修复**

与美股短暂的熔断不同，A股上市公司的停牌（Suspension）时间跨度极长，涉及资产重组、收购兼并或监管核查，短则数日，长则数年。这种长时间的数据缺失对时间序列分析构成了毁灭性打击。

### **2.1 停牌期间的数据填充策略**

在处理停牌期间的“空洞”时，常见的三种错误处理方式及其后果如下：

| 填充方法 | 处理逻辑 | 量化回测后果 | 推荐场景 |
| :---- | :---- | :---- | :---- |
| **零值填充 (Fill with Zero)** | 价格=0，成交量=0 | **灾难性**。导致移动平均线（MA）骤降，波动率计算爆炸，收益率计算出现-100%的回撤。 | 仅适用于成交量（Volume）和成交额（Amount）。 |
| **前值填充 (Forward Fill / Pad)** | 价格=停牌前收盘价 | **误导性**。价格曲线呈水平直线，波动率为0。导致夏普比率（Sharpe Ratio）虚高，因分母（波动率）被人为降低。 | 适用于计算资产净值（NAV），但不适用于计算技术指标。 |
| **剔除 (Drop / Delete)** | 删除停牌日行 | **破坏时序**。导致时间轴错位，无法与其他股票对齐进行截面分析（Cross-sectional Analysis）。 | 仅适用于训练非时间敏感的机器学习模型 4。 |

**专家级解决方案：掩码矩阵（Masking Matrix）**

在构建因子模型时，不应修改原始价格数据，而应构建一个与价格矩阵同维度的布尔型掩码矩阵 is\_suspended。

* **数据获取**：利用Tushare等专业接口获取每日停复牌明细，包括 suspend\_date（停牌日）、resume\_date（复牌日）及 suspend\_type（停牌原因）5。  
* **计算逻辑**：  
  * 对于技术指标（如MACD、RSI），应在计算逻辑中跳过停牌日，即停牌日的指标值应继承上一交易日的值，或者在计算窗口中剔除停牌日（例如20日均线取最近20个“交易日”而非自然日）。  
  * 对于截面回归（Cross-sectional Regression），在每一期回归中必须严格剔除当日停牌的股票，否则其静止的价格将作为异常值（Outlier）扭曲回归系数。

### **2.2 停牌后的价格跳空与洗盘模式**

复牌往往伴随着信息的集中释放，导致价格出现巨大的跳空缺口（Gap）。这种跳空本身包含了极强的信息含量。 根据市场微观结构研究，复牌后的首日表现往往决定了后续数日的走势。例如，Snippet 3 提到的“洗盘”（Washout）模式：

* **恐慌性抛售**：复牌初期量能暴增，散户恐慌出逃。  
* **量能萎缩**：随着洗盘深入，成交量较前期高点显著减少，甚至低于20日均量。  
* **企稳信号**：当股价在均线附近震荡，且量能温和放大（增加20%-50%）时，往往是机构完成洗盘的信号。

**数据工程启示**：

在清洗复牌后数据时，需要构建“复牌日计数器”（Days Since Resumption）。对于复牌后N天内的数据，应采用专门的波动率模型。例如，复牌首日不设涨跌幅限制（针对某些特定类型的复牌）或限制放宽时，该数据点应被视为极端异常值处理，避免其破坏长期波动率的估计。

## ---

**3\. 除权除息（Fuquan）与价格复原**

A股上市公司极其热衷于高送转（如“10转10”），这会导致股价在除权日（Ex-date）发生断崖式下跌。如果不进行复权处理，量化模型会将这种下跌误判为暴跌。

### **3.1 前复权 vs 后复权：应用场景的分野**

数据清洗必须明确“复权”的方向，这取决于策略类型 6：

* **后复权（Backward Adjustment, Houfuquan）**：  
  * **机制**：保持上市首发价格不变，根据分红配股比例，调高现在的价格。现在的3000元股价可能变成30000元。  
  * **优点**：保持了历史投资回报的连续性。  
  * **缺点**：破坏了价格的心理锚点，且当前价格可能变成巨大的数字，影响某些对绝对价格敏感的因子（如价位因子）。  
  * **适用**：**量化回测、技术指标计算、机器学习模型训练**。这是最常用的模式。  
* **前复权（Forward Adjustment, Qianfuquan）**：  
  * **机制**：保持当前价格不变，调低历史价格。  
  * **优点**：符合当前的盘面直观感受。  
  * **缺点**：历史价格可能变成负数（如果分红总额超过股价），导致计算涨跌幅（Price/Prev\_Close \- 1）时出现除以负数的情况，产生逻辑错误。  
  * **适用**：**即时看盘、日内交易决策**。

### **3.2 配股（Rights Issue）的特殊陷阱**

与简单的送股（Split）不同，A股的配股（Peigu）要求股东**主动缴款**认购。

* **计算公式**：  
  ![][image1]  
* **陷阱**：主流数据商通常默认所有股东都参与了配股，从而直接应用上述公式进行复权。然而，如果有股东未参与配股，其实际持仓市值是直接缩水的（亏损）。  
* **清洗策略**：对于精准的账户归因分析（Attribution Analysis），不能简单使用通用的复权因子，而应根据策略是否实际参与了配股来构建“个性化复权价格”。但在一般因子研究中，采用交易所公布的标准复权因子是行业惯例。在Backtrader等框架中，必须正确导入 adjfactor 列，并确保系统按照 Adj Close 倒推历史的 Open, High, Low 6。

## ---

**4\. 财务数据与前视偏差（Look-Ahead Bias）**

基本面量化（Fundamental Quant）在A股面临的最大挑战是财务数据发布的**滞后性**与**修正性**。

### **4.1 “报告期”与“公告日”的错位**

A股财报分为一季报、中报、三季报和年报。

* **报告期（Reporting Period）**：财务数据截止的日期（如9月30日）。  
* **公告日（Announcement Date）**：财务数据实际对公众披露的日期（可能是10月20日）。

**致命陷阱**：

如果在回测中，将9月30日的财报数据在10月1日就纳入模型计算（例如计算PE或ROE），这就构成了严重的**前视偏差**。实际上，该数据在10月1日尚不可得。这会人为制造出惊人的超额收益。

**解决方案：PIT（Point-in-Time）数据架构** 必须建立Point-in-Time数据库 8。数据表结构应包含双重时间索引：

* ts\_code: 股票代码  
* end\_date: 报告期（20230930）  
* ann\_date: 公告日（20231025）  
* f\_ann\_date: 最终公告日（用于处理更正）

**回测取数逻辑**：

在回测时间点 ![][image2]（例如2023年10月15日），查询财务数据时，只能选取 ann\_date \<= T 的最新一条记录。上例中，虽然9月30日的业绩已经发生，但由于公告日是10月25日，所以在10月15日只能使用中报（6月30日）的数据。

### **4.2 业绩快报与预告的利用**

A股上市公司在正式财报披露前，往往会发布“业绩预告”（Forecast）和“业绩快报”（Express）。这些数据包含净利润范围或初步核算数据。

* **清洗难点**：预告通常是区间值（如“增长50%-80%”），且文本格式非结构化。  
* **处理策略**：需要专门的NLP清洗流程提取数值下限和上限，取均值作为临时代理变量。一旦正式财报（Actual）发布，立即使用精确值替换预告值，但在历史回溯时，必须保留当时只能看到“预告”的事实。

## ---

**5\. 幸存者偏差与动态股票池**

**幸存者偏差（Survivorship Bias）** 是指只统计当前存在的公司，而忽略了历史上已经退市或因重组消失的公司 9。

### **5.1 A股退市常态化下的数据挑战**

过去A股退市极难，幸存者偏差影响较小。但随着注册制改革，退市变得常态化。如果我们在2024年回测过去5年的策略，选股池只包含2024年仍在上市的股票，那么我们就人为剔除了那些在2020年、2021年因为业绩爆雷而退市的“垃圾股”。

* **后果**：回测结果会显著优于真实表现，因为规避了那些导致巨大亏损的标的。研究表明，幸存者偏差可能使年化收益率虚高3%-5%。

### **5.2 动态股票池构建**

**正确做法**：回测必须基于“当时存在的全市场股票池”。

1. **包含退市数据**：数据库必须保留所有已退市股票的历史行情数据，不能物理删除。  
2. **动态成分股**：如果在做指数增强（如对标沪深300），必须使用历史上的成分股列表。例如，2018年1月的选股范围，应当是2018年1月时的沪深300成分股，而不是现在的成分股。  
3. **ST摘帽戴帽**：股票变成ST后，机构投资者往往被风控强制平仓。回测引擎需模拟这一过程：一旦股票在 ![][image2] 日被标记为ST，策略应在 ![][image3] 日强制卖出，无论信号如何。

## ---

**6\. 统计异常值检测：告别3-Sigma**

在金融时间序列中，数据异常（Outlier）可能源于交易所传输错误（Bad Data），也可能源于真实的极端行情（Extreme Event）。如何区分二者是清洗的核心。

### **6.1 为什么放弃3-Sigma？**

传统的3-Sigma原则（均值 ± 3倍标准差）假设数据服从正态分布。然而，A股数据具有显著的**尖峰肥尾（Leptokurtic）** 特征，极端价格出现的概率远高于正态分布的预测。

* **缺陷**：均值（Mean）和标准差（Std）本身就不稳健（Non-robust），极易受到异常值的影响。一个巨大的错误价格（如价格瞬间跳变100倍）会拉高均值和方差，导致3-Sigma阈值变宽，从而反而把这个异常值“包容”进去了 10。

### **6.2 稳健统计方法：MAD (Median Absolute Deviation)**

专家级数据清洗推荐使用 **中位数绝对偏差（MAD）** 10。

**算法逻辑**：

1. 计算滚动窗口（如50个Tick）的中位数：![][image4]。  
2. 计算每个数据点与中位数的绝对偏差：![][image5]。  
3. 计算这些绝对偏差的中位数：![][image6]。  
4. 设定阈值：![][image7]。  
   * 注：![][image8] 是为了让MAD在正态分布下与标准差一致的比例因子。  
   * ![][image9] 通常取3到5。

**优势**：中位数对极端值不敏感。即使数据中混入了一个无穷大的错误值，中位数和MAD都能保持稳定，从而通过阈值精准地将该错误值识别并剔除。

**Python实现概念**：

Python

\# 概念伪代码，非直接运行  
\# 使用Rolling窗口计算MAD进行去极值  
rolling\_median \= df\['price'\].rolling(window=20).median()  
rolling\_mad \= (df\['price'\] \- rolling\_median).abs().rolling(window=20).median()  
limit\_up \= rolling\_median \+ n \* rolling\_mad \* 1.4826  
limit\_down \= rolling\_median \- n \* rolling\_mad \* 1.4826  
\# 生成清洗后的序列  
clean\_price \= df\['price'\].where((df\['price'\] \<= limit\_up) & (df\['price'\] \>= limit\_down))

通过这种方法，我们可以保留真实的剧烈波动（如连续涨停），同时滤除物理层面的数据毛刺。

## ---

**7\. 数据工程架构与实现技术**

处理A股全市场（5000+只股票）的高频或日线数据，对数据架构提出了高性能要求。

### **7.1 “长表”与“宽表”的转换艺术**

金融数据通常以两种格式存在 11：

* **长表（Long Format / Stacked）**：  
  * 结构：\`\`。  
  * 优点：适合数据库存储（追加写入方便），适合处理不规则数据（如不同股票上市时间不同）。  
  * 缺点：难以进行截面计算（如“计算当日所有股票的均价”）。  
* **宽表（Wide Format / Unstacked）**：  
  * 结构：Index为Date，Columns为Stock\_ID。  
  * 优点：向量化计算效率极高（Pandas/Numpy原生支持）。计算相关性矩阵（Correlation Matrix）只需一行代码。  
  * 缺点：内存消耗大，稀疏性高（对于未上市的股票需要填充NaN）。

**最佳实践**：

底层存储使用**长表**（Parquet或Database），进入内存进行计算前，通过 pivot 操作转换为**宽表**。计算完成后，再 stack 回长表格式进行信号存储。

Python

\# 典型的Pandas数据重塑流程  
wide\_df \= long\_df.pivot(index='date', columns='ts\_code', values='close')  
\#... 执行向量化因子计算...  
returns \= wide\_df.pct\_change()  
\#... 转换回长表...  
long\_signals \= returns.stack().reset\_index()

### **7.2 存储格式的选择**

* **CSV**：仅适用于教学或极小数据集。读取速度慢，无类型安全，浮点数精度丢失。  
* **HDF5 / Parquet**：生产环境标准。Parquet支持列式存储，压缩率极高，且支持“谓词下推”（只读取需要的列），非常适合大规模因子库的存储。  
* **KDB+ / DolphinDB**：对于Tick级高频数据，传统文件系统难以支撑。国内头部量化机构普遍采用这些时序数据库（Time-Series Database），支持在服务端完成数据清洗和聚合（如直接请求“1分钟VWAP”而非原始Tick），极大减轻Python端的内存压力。

## ---

**8\. 结论与建议**

A股量化交易的数据清洗绝非简单的“去噪”，而是一场对市场规则、微观结构和统计特性的深度重构。一份高质量的A股量化数据集，必须是：

1. **微观结构感知的（Microstructure-Aware）**：识别并标记集合竞价、涨跌停、停牌等特殊状态。  
2. **时间点精确的（Point-in-Time）**：严格区分报告期与公告期，杜绝前视偏差。  
3. **生存偏差免疫的（Survivorship-Free）**：包含完整的退市股票历史。  
4. **统计稳健的（Statistically Robust）**：采用MAD等抗干扰算法处理异常值。

对于量化从业者而言，在这个充满噪声与非理性波动的市场中，数据治理能力往往比模型复杂度更能决定最终的夏普比率。只有避开了上述所有陷阱，策略逻辑才能在真实的市场博弈中站稳脚跟。

### ---

**参考文献索引**

* 3 OANDA. *Whipsaw Analysis and Volume Characteristics in Stock Markets*.  
* 9 Quant 10jqka. *Survivorship Bias and Delisted Data in Quantitative Datasets*.  
* 1 CFBond. *Mechanism and Cancellation Rules of Call Auction (9:15-9:25)*.  
* 2 21Jingji. *Secrets of the 9:25-9:30 Gap and Order Matching*.  
* 6 Backtrader Documentation. *Data Feeds, Adjustment Factors, and Binary Formats*.  
* 10 Data Science Tutorials. *Data Cleaning Techniques, Outlier Detection (MAD vs Sigma), and Python Implementation*.  
* 4 QuantInsti. *Data Preprocessing, Imputation Strategies, and Dropping Logic*.  
* 11 Medium. *Long vs Wide Data Formats in Quantitative Finance*.  
* 5 Tushare Pro. *API Documentation for Suspensions and Financial Data (PIT)*.

#### **引用的著作**

1. 重磅！上交所最新尾盘集合竞价机制，就从下周一实施！不可撤单、不接受市价委托, 访问时间为 一月 30, 2026， [https://www.cfbond.com/2018/08/16/wap\_99754541.html](https://www.cfbond.com/2018/08/16/wap_99754541.html)  
2. 涨姿势！集合竞价最全攻略，竟然藏着这么多秘密！ \- 21财经, 访问时间为 一月 30, 2026， [https://m.21jingji.com/article/20170617/herald/93d83e518ad1552e1cc3a7da34c01416.html](https://m.21jingji.com/article/20170617/herald/93d83e518ad1552e1cc3a7da34c01416.html)  
3. 什麼是洗盤？特徵與方式有哪些？ \- OANDA Lab, 访问时间为 一月 30, 2026， [https://www.oanda.com/bvi-ft/lab-education/invest\_us\_stock/whipsaw/](https://www.oanda.com/bvi-ft/lab-education/invest_us_stock/whipsaw/)  
4. Clean, Transform, Optimize: The Power of Data Preprocessing \- QuantInsti Blog, 访问时间为 一月 30, 2026， [https://blog.quantinsti.com/data-preprocessing/](https://blog.quantinsti.com/data-preprocessing/)  
5. A股停复牌信息 \- Tushare金融大数据社区, 访问时间为 一月 30, 2026， [http://tushare.xcsc.com:7173/document/2?doc\_id=31](http://tushare.xcsc.com:7173/document/2?doc_id=31)  
6. Data Feeds \- Reference \- Backtrader, 访问时间为 一月 30, 2026， [https://www.backtrader.com/docu/dataautoref/](https://www.backtrader.com/docu/dataautoref/)  
7. Data Feeds \- Backtrader, 访问时间为 一月 30, 2026， [https://www.backtrader.com/docu/datafeed/](https://www.backtrader.com/docu/datafeed/)  
8. Tushare数据获取方式, 访问时间为 一月 30, 2026， [https://tushare.pro/document/1?doc\_id=129](https://tushare.pro/document/1?doc_id=129)  
9. 算法交易策略回测Part1 \- SuperMind \- 同花顺, 访问时间为 一月 30, 2026， [https://quant.10jqka.com.cn/view/article/1580](https://quant.10jqka.com.cn/view/article/1580)  
10. Tutorial 1: Data Cleaning and Analysis in Python \- Dataquest, 访问时间为 一月 30, 2026， [https://www.dataquest.io/tutorial/data-cleaning-and-analysis-in-python/](https://www.dataquest.io/tutorial/data-cleaning-and-analysis-in-python/)  
11. Typical Data Cleaning in Quant Finance — Python | by John Bilsel | Medium, 访问时间为 一月 30, 2026， [https://medium.com/@jgbilsel/typical-data-cleaning-in-quant-finance-python-56ddaea335a4](https://medium.com/@jgbilsel/typical-data-cleaning-in-quant-finance-python-56ddaea335a4)  
12. Data Feeds \- Development \- General \- Backtrader, 访问时间为 一月 30, 2026， [https://www.backtrader.com/docu/datafeed-develop-general/datafeed-develop-general/](https://www.backtrader.com/docu/datafeed-develop-general/datafeed-develop-general/)  
13. 5 Useful Python Scripts to Automate Data Cleaning \- KDnuggets, 访问时间为 一月 30, 2026， [https://www.kdnuggets.com/5-useful-python-scripts-to-automate-data-cleaning](https://www.kdnuggets.com/5-useful-python-scripts-to-automate-data-cleaning)  
14. Data Cleaning Techniques in Python: the Ultimate Guide, 访问时间为 一月 30, 2026， [https://www.justintodata.com/data-cleaning-techniques-python-guide/](https://www.justintodata.com/data-cleaning-techniques-python-guide/)

[image1]: <data:image/png;base64,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>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAaCAYAAACHD21cAAAAsklEQVR4XmNgGAWDELAC8SwicQ0QC0G0MTCUI3OgIBqITwOxIJo4XIwTiNegyjEwAvF8IJ6EJg4CW4GYA8TQAeKlqHJgE0Emg2xFB3DDEoA4AyEOBsZA/BWINdHEQSAdXQAZgGz6z4DpP7xABIivMkA0kgRgznyLLkEIgPwAsg0UOEQDWDSANGKLCpwA2X/YogIr4AHiegaIpitArIAiiwWIA/FdBogGdAyyHeSKUUAXAAB8miZVdxhgdgAAAABJRU5ErkJggg==>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAC8AAAAZCAYAAAChBHccAAABMElEQVR4Xu2VvWoCQRSFr4WgaKFJMNgGUgRMlYewSmeXJmCR1Cm0EZInMKCdEEJKwU7yFGn1GVIlYKGV+TmXmyVyd9f9G0aE+eBrzs4wh9nLLpHD4XDYJA9HMe3BA9lmFT6zpkOmAVdwTP8lv+EXHMIW7PyteYcnss0abbiAXf2A4VDf5g98g9WN7Cogi6IET3UYkz78hGuSPr7yRThRWY5k8UDll/AVFlS+jQuSt5eGCsmovFBI+Wt4qzI+8AOeqfwO3qgsiizlPULLB5FmPMKwWp5H5pn8I5MWq+WP4Jzk9k1gtTwftiT/vMfhGNaVTfgUkLOHsi2SWOW9keGFprB2897I7GV5b2T4M2kKK+XL8J5k0Uw9y4KJ8lOSXo+U7AeZGRPld8Y5fNChw+FIzi+M3Etj8RqcqwAAAABJRU5ErkJggg==>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGUAAAAZCAYAAAAonOB1AAAFZklEQVR4Xu2YWcitYxTH/0LIPBPlHEkZCplDbigyJEOOnFAuUEoh09WRFHEhUzJ0SDKWC0Omi8+QDDcuiEghQy6kFJlZP+tZ9nrX93576Dv7pLz/+rf3fqb3WfN6tzRgwIABAwYMGPA/xhaN6wqbasbz9jHebXzL+IXxAeM2nRVdbG18SL72PeOdxhV5wYzY3viy/LxPjDunuQ2M2xk3TmPzxsfGw+tgwwHGewtPbHMo/pYy93CbA3vJz54KOxhPM15m/Mv4ndxQfUBJVxp/la8903iScfO8aEawlzNuNj5l3CjNXSF/ztNyoecNHO4GuZx92E1+px/l9/rauEeb494ntPH3jVfJ5cpYrdH6qXCc3PN/Mx5d5gKHyaOEh/5Z5paLqxsz7pcLiSLWBy42rqyDBRiM7MC9vixzKPxC44ZlPIDRkSk73lhcZ3xE/rBTylyAkDxL7in1QssBUfCcFjsDaQtB1gdImx9q6SjJONL4i1xXgV2ML2ny/u+N+9fBPuwurymXyx+ENSuIkk2Ma+VrqldX4C3jahOgniAEUUrkZQ9i/6SUxd6l6g1znJ/B2r6Cy1rkmsXRVsn1wCc1kXQ1ySDgdeOC+u/RAUohbxMhPAivzQrhgAfl9ecDjU9x+8r3/2D8yPiG3OgZRxnflqdL+IS6XrdCvu8n4+lpPEAdusn4rbxBuMS4xnhem0f5pJg35alvS+Ntxq+MvxsfUzcCtzW+a3wljU1CRNYfxlu1tHNUkP6/Me5ZJypulHv+wfLUxAW5aIAIOlduCAzyqbpdUuBS+fz1xs00yr+3t3l+s+ZneWPB72vlBmEfwLufl0fm53JF5UYCA3M/jMl38jhdDWfg7QDvvcO4lTxdvGM8Vf68C9rai9pagIJQFAqbBWs0QzpqQM8426F1IoOIIEqIlrgcYRzevZ88naHkSG+1Swowh9eH17DmUfnlwRlyz8prEAjBiEAQCkWBpDT2x7OIWPI2+fyYNgbu0kjRyPOk3IGIbJ7HcwORDXL6DWfEOacF96fGchaONi24I3uWqtv/AEOQ52j3Ij1xQS6KITAIhgEYo3pZYKW6aQ3lcGlq1a5tLLo2HCBAn8+ZNBmA7uVAuSFYS5sZoDuq6ZUoIpriztQx8juf3OUFuRwBFF9lCKNMqpMB6h0RjjNzFjJO25CEU4w1CqmFCAgQwmxijJefXJBQEkbDeBUIhGLHFTvOzU0EZy9opNAMvG9NGaNOQV7iAqQlzl2r7rMxKk6UHQAQZdVQsxiFGvWiRkbAIDw/R/Q4UCPHGoUCyANy0eZibKJ4HZTGQZ/wAfbRVo9D9dBIl1HD4u0YgRGW1EaaOF/u+SiuOkV4PjUPpezYxon8z9pnBmsj3RzbPsMo2WH6gNxklUjtgLM4c9raEvoNWReBQ15VV0iEY1N9OSRdhPB9oBb0GYVUdI085KuHrG5jYegwWLwH4M0o7PH2nX8bFtSNXop4RA9GDlmiKcney1x0Phj+2TZOeqWpILKWAvc7W4vfyEnb1GDk4N+AScCJarT/C5SEsHRSGCe8n3DHIOTpAHMoF0Ux3xcpOxlfUze3niNvGw9pvym6kSI4A+9CGMbYj4Ag8i5Rco/x+Db+jLrez/9i3BWFolhqTiCakoy9NTIqDkGDAKIuEbEVOCP6uU9+Xn1bJ8LpFpnjb5c+3WRg+BrtcwUXoqVFQSi5DwjJfLxYIiRr64smBskREYhn0JJHB8e6/DvG6pmAvbAqL6Jz3uB/w9y8DBgD0iORmBuAdQ0cYZZObYD83SdS5TzAqwXd4oAZgCcvaD6eTGqlockpdsCUQGm8GJ5cJ5aBI+Tvg/nvogH/dfwNqwosvl04Zf0AAAAASUVORK5CYII=>

[image5]: <data:image/png;base64,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>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAT8AAAAZCAYAAABHJCk0AAANAUlEQVR4Xu2ceahkVxGHf6JGReMS9wVmRqOgJi6YGBMVBXdccSGKMQ5oXCAYNG7jH/GNIm6DiiYqEjOjEmJMQMUlLiF2NBiXwSjEBRd8Iy6oBCGouMTlfNat6brV597uN+/1e89wPihm+m59Tp2qOlV1e0ZqNBqNRqPRaDQajUaj0Wg0Go1Go9FoNBpVbpM+3zx9btx4OabITfLBdXC7fCBxa/Xt65aatb+53L/IB4t8q8iviny0yO17V/RhUB+TXfv9IucW2RkvGOE/RV6TDwbeXOQzsmf78xnPRzrZW+TYw1dvLa43H+sy9VbjjkW+WuQPRX5W5K7hHEaIMW5W8DmhyE+LnJSOPz19dm5W5Bz11xZ5h0yHpxS5MJ17e5GjuHkbkO30If3TM7yyyC9k1/LnU/qn18xbZM/6dZEb0jkgEGwW2PVlqge+exW5QP11RF7SnX+d+jaAfzy7O4d9X13kbNWfzbXZvogN2KE/Yy53KvKsImfJgtN1MseuwSBeW+QfsmufW+Spsig8DxTBPW/IJwKPK3JakZ9o+vwoODrH92nzHHsI19tftTa9fVZr09sQ3Msz+O5LZQHFwWA4/ulwbFlg/JcXeatmjTQbp8NYH1vk+UW+IBsrxsz6s673LPLuIv+W6eyFRY7nxm0C42Ts18jG/vL+6RlWZdcdKrK7yI548ghgczijyJ+K/C6de0aRH8iCx7JhvV8vS5xqsAE/s8jLZPP/uyzg+Voyj690594m8yf8ynm0LMg/PBxzasEPiB8/zgfn8XhZRvLPIo9K5xwGwZdeKzPMRUFJ79PUyMcgg2F35NoMDv9J2TmcbTvwHa1Nb+h5I6ltKOd3xwmCy+YVMgPdlU+obpyZ42RjXQnH3KmulG2a2xGc9CpZBojjDsHmcIlsju9P59bDw4r8pcgkHaey+pD6m+GyeGCR38s2gnl48Ds5HEM3VC97w7EIc7hIs3OEoeDHMwnGa5r/m2SlBoOsPRRITZ8nUzop96IQwQ9qseBHACGQ5B3NwVnY8ZDtAOXYmN5YjKi3jXRmypta0CV7mtcz2SjYZSnhc9YHNX1kMFJ0x3O8dN9d5BvaWF1tNCcWuaLISzVs0+jk1TLnZY4Ll2MLQLbpGVPkpqqvxUbDd7Ducd3GIF4wXrcVEhn0Nq+Ke7Is+88MBT84UxYnFgIjI1qyazBAMocM2cstiuxXPdsYgszgYtkEuQ+jPrp3xRQcgRKutqgOTc2J7JqtBr3dW+N6+7D6epvHXTTeO2T+lDQYEFlkLnm5f6znw31j/UCeHRvHXIdx15rJPAujHgpSQ8aZwfbQzZeKvEjrLwuXDfNmw6Mcf7CsUskBwHu8x8rmNlFdhxHWnfUbgrXgPFnnD2UJAvYHjCmvXY2x825bjj+zVkJTXq8loJPxkflxD/5CQjBkgxHXNa2QyFjwI75MND7Xw+BE9Id4GIOjDxMdiIcc0FTptWyjBgt/UJYeA88+VOTuh6/owwRXZSU1Y6pxhyLf1WKBZNkwRvQU9RZBb+gg6m2IB8jun8h6nldpNqg8ssiPZGU28in1+007ZQ5BH7JmlOy2lCkTWalKI/50TTMFjPGbsp2Wkhkj+o2mjXVaDhHW4nIN9y6HjDPDTo3+kF+mc9sR1vNrsh4vtnxd9/cIDk5wBOY1tJnDO4v8UdYW+bpmX4jcTfZigLWdyLInbMn9lM0MW+A8a+fr6fD5ObIsDbvhJQSbDN/rFQL2gl/xDNb1VNlaYCd/1uxLHeZzvSz4L8KtZJsbusC/11KZkGjleDMW/CBuDKMwEb7A+wgoAQU4vpBektZ2uhr0HmKGyMTHBhVL3qFrMDKMbV7wO16zL0zGJDdbF8ENOuotgt4g6i2DYeL8nN8bjmHg3iPya/7W/R3ZI9OBGwW78xdlzsgGk4MSgZTxeUDdIXsztl9TZ6F3c1uZg9FWoJ/p53ZrVuesEUY4xJhxRnapXxZtd9A5umZzQ3Iy8FBZxs9mgh8xrxzQHIIKAS9udNeob4sEIHqLHjCwtRhQPy4Lboxlolnf3Ceznad1n8m6uH9VlnCgfwIT9+GvV8vuIWDBfTWbEF2q8USmBvblwW8tYEd5M58X/EgAaE2MwoTI+shiMGYCTyxlyNrOlynCyzsmHkutIVjUmDIzIBaOYFEDxfP8rOiIp9vzFLjs4Od6g6g3x/UGUW8Z2gKcY+f2MgDdXqTpSwAM+1/dNc5xsgDlY8awPiDrkaAb7vc1wil4q0bZETlP08yR+dCY53lkqXwf3+t4dhthHccymjHjjNBSYS48n+xkDIIxb1u3EnTmGxM6ZtzROVl3r3bIjIY2c64h46M6iJB9e6Bjk/qt+tdcpn51hF3hn24TOatifPFt/BNl97ufMR9fR+aVS1IC3ET9MpLPOUkag+/mJRZjQXwsi8A8c5ttXvDjO8bO/w8WhT4cO4AbvgcoFBoXEiXzUHeYMQh6T0jHeO5YScti8Pw8UQeF7ddiTrJsXG8Q9QZRbzjHmN4ImDFzYJfF+OiDYXT0eK7VrN7IJKIR8dspsgiCHtcSBB0PsOjXISskO/SNiH4TxulZKpmA7/yAc9SC39BawVzj6/h2kXdp2hMag+yEknwMnBTdLSprcURgE2ITdrLNxnWmYqpt5r7B+Xx5UcFYzijypO4Y4+JXEh5oHSqImKB4VrmiWf1hg7ks983Yx+y24y0lgmgEm8hzmHQSA+IYp8r85YDsu8k2F6VmZxsS/FCsl2fAQ7mRY59Qf3I4FU4+L0NC4QfzQVma7M+uwblVzTY3nT2ya3DavLttNkN6Y+5RbwSsMb1xz4UadkCCKNd4Fgk8e6JpsI1w7Ur4TOZxfSexP+MZdP5eAnUOtCfLAhMBMVIzysg849uhfqvAyyK+bztD5sXm4bhNsr4HwnHfFGubvbdKCGJD+AZHwI/EwOXEjN/xDS7722on2c8I1Dw7gp+xEeeAOOlkkeBHVsxagwd9nrmoD5+o2fmuO/gdXeTL6vcr+BJu3CfrXUQ4vl+zDhMhXb5Ylm1kJqovnMM5nA8F1SClp0/lihyDEpDnLSrZ4ccY0xu9nqg3z5j2q643zvEzoyE8qMZswstsAgc7uu/8GBM6wlBZhxdr6mQ5+Pq40PULity5O77aSXSMFdm1ZxZ5jKbZIn/GoJwZMz6a+JTiPNPBycnoz9WsrpgPY75C/Yx0K8ilPvplLV6lfqDxLDoHGfB18eqhhrcaYsbFenmlQOA5vTsWM37aFTu78xPN2jX3u5+d0h1D39go3xfxjQ+dk2nSIiJLnWix3j/f/b10zAN1rE7GQA85gC8S/NwvquAkV6rvFB79c0+NBeA458cgvcWoazvCRPYMBp7hes7lSQILQymAY8T0fasY01seP+XCmN6Ggh9lyBtlGSbXxIU+rTuGseKIHhgxVC9XcS42IfRF2TPRdE1oSfAyg2yQQMp6+VyiY4BnLwRbrv28plkAZdrYZjVknMfIMhLK7BzkVjTb4wKcjr4sGes8h1sm6DYHE3TDepARRrtnXThe088uWdZXC3705+6hadUQQS+rsoBKALxE02fhH+gGm+NPfJa/+2YF6Nvt1IMmeMnLXCJuf7Ci6WaFD7tNDEFgJVmhpxthk+aZsc89Br6TA9m84JcrnR5Eb5yD6I0xuxG6wjFOh3M4IzsA57PBOuxC7Gbv1WyPAz4nmzR/xrKBsaCoG2SZhYMhsTvgnIyJN5FbzX3U15vjeoupPHrin+SN6Y1+Hi+G/D50QSaGIZ8g65vy8sGzZZyf7A49cgzjxvjBd0gMigyUe3FW9L0qcxgCDw7DWA/JMvRzNIXnxizzfrKm/ES2Hudp6sysIQ4z1PTOxsn86WH+vJOdvbM2d8926AFGG6J0IhDjrDU9bgZsGmR3/EwkOi2bA2sSnZz1dHuvOThzoJ+Hv0T4ydPZmuoK+/CAulNWLk5kvvAeWavAs0iycO6LVRd/9/4k+j1L082UFg1vkcHbI9iTc5TsPM8m6OKHZH+AnXkGmmG+e2U/u7mg+xzxRAq/wL8Z1xhs8DnpGQt+2GeudBrbFAwWxyKTGjIEDIbzDtfhHBl2/FrW7d8RDZHrsmHy4iPj9yIZDDgGy8iQcR4pfA/B9kGqZ1P/r7CuSC1hANYZcdtgjeJncHuorR/rzPPdLljzbCccI1jU7K9mJ94LJFgOjXsj8MolMxb8SDQWLakbjSOG7Ca/GXaGjPNI8BKOLIDspbH1kFUSmGIFtNFQZlPSZ4aCHxs1PeNFX6Y0GkcM/26bko8SO1MzziPFy0T+pUMz7O2B945Zl2VAJsv/UEMbIDMU/Cjl+VF4o7F0CEq8uJhoNijVjHM98F1D/cXG1kCfs/Yvl9YLa71Hwz9rqwU/SnNeAvI72UZj08DwMNbISelz48YL7YiN7MPy8oafQw3B/5YT7esRsjfT8UVqo9FoNOC/2vIi0+lPPYEAAAAASUVORK5CYII=>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAZQAAAAZCAYAAAAWnNgSAAAPzElEQVR4Xu2dCahuVRXHVzRQlGUa2WC8Z6kNmllp0kRlaUYDUoZKljdN0pCiBMuCvBohlWSUZYR1zRAbhBJtMul9lmhWZIFllNE1NLGoKCoabNi/t87fs771nXO+4d77Lj73Dxb3fWfvs88e1rT3OaJZpVKpVCqVSqVSqVQqlUqlUqlUKpVKpVKpVCqVSqWyBu5bZPfm73pw/yIPyxcrlYrZ/Yp8ag45wW/bztlFflPkP0VeGa5vJq8379O/irwzlc3LE4pcV+SPRa4u8uDx4jH2LfIj82dPq7vRnFnkK+Z9QQ4cL57glCK/Mq/L35eNF8+N9OK2InelMnhgvrCB4Pw/3fzNoPvvtUkd37Upf06RS1LZOU0ZAer6Iqc1vxdll3xhJ+GhRR6XL87BAUXeU+QhuaDw6CLPbv72JQnct38j03hkkRcU2dP629to6G+02+/ZsN3ex1q7Rb5gs9vtb23YR73VvD35hJ8X+ay1NvDBIs8078MEjzcPCJdbe8OfivzPfFAnFvloke82177qt21vDIM7qcgfijy5ub7ZPNV8Av5b5CWpbF4wCgIl42YOhnhEkSPNHdD7U9mO5sVFjilyo3nf3zxePMGqeb1biywV2RILF0B6gR7dkcpeVeQn5g55R/CaInvniw0ElBea6zTjRzAcBZ/HFvmQeXJycZHXmeuXeL65wS0KTgQHsrNxrLkuMZeLwO7vO+ZtEDQiBxcZmfsp9PtOm3Rs2Cq6x9r8tcj3zRO+LmjvdvO+0t6148U7DHROditdHLLbQ6y126UiR9lsdovOc8/IuoM1YL+0xxpQlz7xW3JLc/1L1rFTp9PZ4HAC3IDxCwb8ZZt0rESqkfV3bjNYbQSHsFZQ1jwXfVB3xWaru9EQ4DAOHNZQgEMhUIxZguY8oBd/M9eNyDuKXGCu2BsNmedN+WIHZLFKopbDddbzdPPMtQvGcKktrvs7W0D5sLkD/7u1wXkR3mdtghMDytOL/CL8Zn2Otkk/dVaRBzW/+UtbrO+zVKmBZAMdZVdCW28xTx42E+wWnaDPfXaLzRJQZbfzcJh1z22G3Qu7mK72mWOt0RdjAUcPBIkMFQkq7F4iKEiOmmRtfQPfLP5d5DJbH6fFAnfNRRfU/anNVnejIfP6dpE3Wb9hY0RvN3f6rPmrx0rXBnrSZRQy3h3BqeaOZBoKDPT35uYafVwy35kPcUQji7CzBRSOCgniHDWvJaD8zvyEITo9JWufUKUG1i7aOqcS59j4cc43zPuDr9NxK8EF3biw+c1ajKzbge5IsFtsdmj+sNkTbP7+ciqgXce0gIIPw+/hS7vYw9xWWKe7oVPL8YL5mS4PfHe6zoQTEePRVnSgLDgd1vlzhHvj9fw7g1IOlRMhGVBXHRSGSXhe85s60xwYTq7vmTjG7BQzuk9OdLNhvBy9EeyfZn4WynxFyHJQWHan9Hlk0zNtOYw+WBfKpRcxEEs/pj1jqJyyeFSmNrvWVzukrMd9MB8c8TIXvIfjWG7LWI1uePaqLbYbXo+Agu7md1I4inxtiKuK7JYvNtD+5214XTKLBhT055PWrl10egoctMtRtGD947tSAgqBgt2MUH/+Ym4Pav826999DsERGjujLr2DG4q8NF+cAdktfaSvfXaLzbIrk93Own5Ffmh+L2NnF0nw6gOfR/vMeR+sL3UGE3cCxqzvH+gQHeMlzq+tPbPM71NuNHcuBKQnmb+85tpF1m5N4Snm59kj8/cg19rkgjOhKAxZx6pNnnlSn8h5fJGfmffp9iKHxkoBnqn2qKcMFaTEXXPB4rNlpj59/VaRbZYi9iaBQ6cvrAMG2fWOi6MnAg6gFENB8wNFfm9+fESGk1/+Pcr8xTdrPCpyvnlQZy1xbDgrtsaUc6SQDTHO5Y+LfMbcqfNc1hvYPf3AvI2Hmxu0dI4z3QObeoKxMa7c1yFONb+HdnN7Q8QEZh7WGlCYG/TzH+bzwzrwMpWXrrwXZf5w0tNg3AQV7o9w77nW//K2j0UDCjpwpXUHFMCJMq4/m7+nQQ9wwNIRkYMpR7n0hyQH21Dihz4ReNgR4cA/YuPBqg98DDvXJZvUZfSmy1/MguyWMTP2PrsFjWnIbgXriF6c3PwmkHJv34dU6OXIvA5z1UUM8Hm+x8AQV222jEsLc6a1gQHDutTaqLWXeZSVkuGYtpg7J2UMLApKjWGe5bdtv4Zjiuf6POOK5i8o+46wmDj1z1mrHDghss+oePGZao+JX7E2u+k7wpKhYcivaH5zH+PjWUPQ5lFzyrywBl8zVwwkOzzGRyZIvzFK+t3neDEQgkgM7CQDjEPg1HGMml+cQVT2i82dhRQ1Z11xLoHzYe5fNddDdIiALz263vwerRsOQcFL8Gz6gXOaFZ6DsaF32VEMQV+Hjgu1A8ZRRCFb/GbH9Vl3GMvmOozzYQ2uM0/y6DvBZNbEULaAg8U2Ad24wHwt5mWRgMJzrzHPpPsCivpJ25LzQnkfvzSve1rzW86YwLutucZa8H6GOZgF7AGfojbhIPMkdlGi3Y6s326xWfo5ZLcRAjF6RrvAvHKvEspMPO7qS5Swf3wj7fTCgq3YbO8fYoSKxocyjKztvCIcZ5XUPcP8qI1/32RuaEROfpPFKqOifQLTcvMbGByDFExuHhCOJLYDTGBWThwc2Q7jjeAYFMT0vGzcp5s/lxdTGvvh5gaMYxuChcgBY5rMC3OuMTCP9DU6PNYCwwWCMsqTgyZQhwQAY4vguBQ8tpgbZqzzdRt3ZugJzn9/891gziiH5pK5ZzwKTowLJ5fXd2TjxzI4s75x9aFzdXZKOegNQV9xon3wNZg+wYxC8Lqr4zpy9vY7+0GP2FUwPjJZ+k3/hZx6XxaaYe6XzI/6WCt0BFHQnod5AwpryQ73uOZ3X0ABkkTmm/YlURcyjIs6UWfoF9do54jmGmhXG/3ZEOzorjFPGPgyioDE30WR3UbfKrvVmmCT2CzJ+Kz6TQKGDgp2V7Tdp7M6TtOOrgutEfV64WYa0bZqCAwOI1lN1+kMAxcnWhtRtYVjcl5krbJgWDEa7mOuAGQAUaH0CS9fYzzBfCsez/T5fbVNZqUMnOvauuP8cIIYIU4uwgIqoMowMjjZvB1lzqg765n9RkJAjV++ZOVRkAeMKGf3oICu8WM0rMVJ1p4PY3gcE8RdJKAXrOmezW9lUcs2OZ8YSN9cqs/oEDsl6VFeM3QnjwGn0eWQ+kAnbjD/xp5nHzNePAj61WecQxAAFz3y2mqerTNm+nu+tY5QDmnWHYrg/qPNEwJ2J0OOeoh5AwrPvMTa5/UFFHRg1XzMx5offfEc+sqYuyBxJPGMgVEBJeooKIGcxUmL3cyP8tmZHJTK5oH+R7vVLkp6hc3KbhX4ss53IRuNQXJkfn+2W6Fnr1h/cNUa40N7ocNU6otKETUYDUkBaa9wDTQByjIzlKFQfZ2PEEhWze9BCDpCkTW2w4T/0/w/hBIsRO47aKuJoXLUstpIhKDEvTHoxrr8e7PBISh4Av0loLI+F4XrWq8upyOjxuj6IFDQ9h7petfckgni4AhSQglATmBWG8lzKT2KsNvpSgzmCSgEKRyP4BlZZ4bgPWIe7yysJaAIgmwOyARDxhCDzCzgHFkPHOtaHOS8AYX3anF3xhGm7JvEj//2hzGxJko6BYkO9WKSBOzW0N3XNr9x2M81H6P83MjGd7XS+Xl2dQRD+kcCvJYgjA1Gu1XyzHpcZOMfGWCzsyQLBNHL80VrA2pMsiPsfpiHnJgLxszz2ZFtSWV3o6yGB01TQtXNZ2xyGpSj4FrMFfN2Y9YcoWwos6c/R5p/566Mgl0MmTBOQxCwssPB0RB0cDw4lzdaG6Gz4lAX50RAZLEYC+M8xHybCShgXkxlNtrZUL8P7pOxzCrzkgM3yoHT5OOJ6LzV7+y4QcbF9rgPKX3Mkhi/9IK5ekNzjUCiIwac99amfGSThhHnUkcI6MCKTc4HTp/3KxgPuqEjQowGw9C69cGxBQlE1PmbzZ8zq0Ombg6Ks7AeASUfMUOca/q/JZT1wTxss/adAMGEoLLIEc68AQW7jILOcP/t5uuHk6ZNAkTcUQj0NAYUfA+7zahXtDtq/kq3ccwxeT7YPDmYpjPAvC5Z+86FPhJQFnnnBPi/aLfqI+1n3cI+Vq3bbiPHWXdA0fqMbFxvBGU8l2SlCwJJPmKdQFl2NtguVDd+1hadBpP9MWuPDejcHda/leSZXQGFLe67rD0zpJ6OT3Yxd3bsNkDOiXqRZXOHAfzlN44pB0MUAmXgvQrQHzkKxiXlxHnm6M35P3VZKOYhO8gdCY41P5+5p39kQFGBlKnR5wxBFQPuCiiM9zHWBt3I3tYqO/PLcYDawlGjL6wZf5lL/h3nEt3RvEunQMddjCXC9pydCyxbu9asRV7jjDLyHDSWzfuQ3w31EfVyHtYjoDD2nECwY5FDYO5lo33gpFnnHFixP77InJdpAYUE7xSbnHehROVWa3eY+sKLIJlhvHE3yVhebuNBiuT2KvM5x0ZIQrJP0nO7nGyEfjNXPCcGOHzIudad9Q9Bf66wcbulX7Lb3B+uXWbddiu2mn8m3LXL0PrE+RWyvwvTdXGA+ZH/obkggmEz4TgHtpVsI4fIGTnIoeM4iFx8rbB7U4aTx3H0nffdZP4lkV7W8vxjzR0QmRIB5U5zQ2fRGPTR5hOuKKkFUMYgUGoyjy3mzgMHcZi5cuIYaYvn8aKdrbccknY7KNmVNv4imXnSbot7+UJJdfezyZfOOwrmm10In9zGrTeZWM4o6CNKTL+7tunMC2evBM8In1mTxVLO+yvWTgq/1dxZjMxfnrKjJKlQtoWSct/JXn07/DvO5dtsfC7lcJVUKIGAB5iX0z7risOQges4TsEmQr/p1y2NZHj2Xeb3805lGvnIaVbWI6Awp9ERAbqN3jPXZ6WyLrCZJet28IwL5zwP55nPHclEdoY4W8pwSvumMsGaUYcdyhOba+gr9kt2HCEpIBGUDmPn3NslzIlQgDqj+c39KzblnUAD+r/NJj+zBtrhXcg8PgCbxYdEu9VxdO4P7TKWc6zbbuEZ5l9iIsxHhmBOGxwtEiAE679PU7YUruO32alebO77YhBdFxgIA+4KPChQHmhf3QiDwSESMfvq0i7Z1q65wPwenpOfDbTZFczUXlZ6ofIuuId2de+0tu7JKMvrmkPAQSNaN9Yn/gb+zbWutZtlLod0jrp53bW7wSg3EhyukpDNoGs+h+b6ng5+guPv480Df599zgo+h7YOt/l3FpVK5V7EYeaZ30ZCMNkrX6xUKpXKzoWOHzij3gjYBfDfbVQqlUrlXgBnyLxvW284euH8nXP9SqVSqdxL4D3Hx239/mdWfADCy/Cul7KVSqVSqVQqlUX5P7JE+KpiwTxJAAAAAElFTkSuQmCC>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADYAAAAWCAYAAACL6W/rAAACs0lEQVR4Xu2WS6hOURTHlzAQkkfKoxhIUV4peRQGEoUSRZGJASMTSYxuyUBJyKNEMpKUkgFFuWWijBSRR13yyAClmHn8f9be96xz7vm+7vcRk/OvX/fstff59v7vvfY616xRo0aNGtVriJgtrou+ctegNVxcFK/EpErfOPFMXBC94ov5nFHrxAfxRnwSL8SK0ohCxOm/ZP67Z83nL2mO+C6+iZ/mC+tGW8QPG2iMCa+IoSG2VGwPbfRQzEjPmGZNn8Wi/hGuTeKr2Gn+20fM510bByE6R4mF5i90a4yF1RlbIh6HdtYdMTI9jxA3xcyi206Zb/St1I8WmJs9L4aZz8N8jNuVxgzQnxhjF6eZv1s1xk4y8dwQY6HHrUhH2ozZ2z/CbH2KsSbWht6bp+rUPGgw6tYYhtj9vHtVYxPFI/NFnjS/bz2VMWh0pc0J8E6fmJJitB+IxeKu+Z3cZ8WJ1qobY6TDabHbWhtD880XBaTrjXJ3rUhBxh+y4mRpvxS3ze8jd5XUPGc1xSOrG2MbxFXzHWtnjMKRi1Mm369WYgPIhDEhljdmTYgdTvGtIVZSp8aOmZ9UVitj3JvnoY0hUpKqtzLEs0htSnidcQxQiCaEWL6LLdfdqTFS4p14neA5nwbPfEZYAAthV6NILcbtr8Q5HdLsaGqT6svM7yXinXtWvo9/3RhFgZPJzBNvEzyT8/kUqwYQ1S3GSWfuygErvnljxTUrqiBVsZoRuchQVGrVzhg7ecb8Sx9zPqouFRl73/w/kqowtiq0McVJTbZis+jnBDGILouPYlZqo4PmxnpC7Lf4gXipM73mH25E3lOyn1r5I5qV0yGSvz3s/h7zFOLvCfMyHTeo1RqA+5hFCu8wL0QULdb0xMpG/7lWi21is5he7upY48VGsdzalPlGjf6zfgEimLoHKTVhxwAAAABJRU5ErkJggg==>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAwAAAAYCAYAAADOMhxqAAAAwElEQVR4Xu3PQQpBQRzH8b8oG0URCwtxAYmlsrFgwQnsHcEJLN/KASxtHEFxBUVWilIWSlkrfMe8mfdfuMHzq89ifv8382ZE/olfikiqde5H59PCETtU0MEFdzzQjz4V6WKBMd5YIRvOMtjgHK6/MbuNJV7oqVkNV+xV52PKE8qqG4r961x1PmYwUeuq2HccUMIIaTdM4Ym2KyR60zRcz5BwQ3OCuVLBFSQQu2GAPBpqJk2x9/QnkDpuWGOr+vjlA3TkIJmR9OlTAAAAAElFTkSuQmCC>