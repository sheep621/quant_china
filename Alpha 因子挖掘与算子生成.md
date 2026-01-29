# **量化交易中的Alpha算子体系与自动化因子挖掘工厂：架构、算法与评判标准深度研究报告**

## **1\. 引言：从手工作坊到Alpha工厂的范式转移**

在现代量化金融领域，尤其是竞争日益激烈的中国A股市场，投资策略的构建方式正在经历一场深刻的范式转移。传统的“宽客（Quant）1.0”时代依赖于研究员基于经济学直觉和统计套利逻辑手工编写交易规则，而“宽客 4.0”时代则标志着向高度自动化、智能化的“Alpha工厂”模式的演进。在这一新范式中，核心竞争力不再仅仅是单个因子的发现能力，而是构建一套能够持续、高效地从海量数据中挖掘、评估并组合Alpha算子与因子的工业化流水线 1。

Alpha算子（Alpha Operators）作为构建因子的基本原子，其丰富程度与表达能力直接决定了挖掘算法的搜索空间边界。而因子挖掘（Factor Mining）则从单纯的统计回归演变为涉及遗传规划（Genetic Programming, GP）、深度强化学习（Deep Reinforcement Learning, DRL）乃至大语言模型（LLM）的复杂搜索问题 3。

本报告旨在全面剖析这一体系，特别是针对中国A股市场的独特微观结构（如涨跌停限制、T+1交易制度、停牌机制等），详细论述Alpha算子体系的构建、最佳的自动化挖掘实现路径、严格的因子评判标准以及实现因子持续产生的系统架构。报告将结合最新的学术研究与工业界实践（如WorldQuant、Qlib、AlphaGen等），提供一份详尽的技术实施指南。

## ---

**2\. Alpha算子体系的数学结构与分类**

Alpha因子本质上是通过特定函数（算子）对输入数据（量价、基本面、另类数据）进行的数学变换。算子的设计不仅仅是编程技巧，更是对市场逻辑的数学抽象。一个完备的算子库应包含从基础算术到高维张量运算的多层次结构。

### **2.1 基础算子分类与数学性质**

#### **2.1.1 截面算子（Cross-Sectional Operators）**

截面算子处理的是同一时间点上全市场或特定股票池的横向比较信息。在A股市场，由于行业轮动和风格切换迅速，截面算子的标准化和中性化处理至关重要。

* **Rank (排名):** 将数值映射到 $$ 区间。公式为 ![][image1]。其核心作用是去极值化。A股市场常因游资炒作出现极端价格行为，原始数据的分布往往呈现尖峰肥尾特征，Rank算子能将非正态分布强制转换为均匀分布，增强因子的稳健性 5。  
* **Scale (缩放):** 通常指Z-Score标准化，即 ![][image2]。与Rank不同，Scale保留了数据的相对距离信息（即分布的偏度），这对于捕捉“异常交易行为”非常有效。  
* **IndNeutralize (行业中性化):** WorldQuant体系中常用的 Neut 算子。数学表达为 ![][image3]。在A股，由于政策导向导致行业Beta波动剧烈，不进行行业中性化的因子往往退化为行业Beta的代理变量，而非真正的Alpha 7。

#### **2.1.2 时序算子（Time-Series Operators）**

时序算子捕捉单一标的在时间维度上的演变规律，核心在于“窗口（Window）”的选择。

* **Ts\_Delay(x, d):** 滞后算子，获取 ![][image4] 时刻的值。  
* **Ts\_Delta(x, d):** 差分算子，![][image5]。  
* **Ts\_Rank(x, d):** 滚动排名算子。计算当前值在过去 ![][image6] 天窗口内的百分位。这是一个强大的非线性算子，它剥离了价格或成交量的绝对水平，只关注相对强弱。例如，在牛市中，股价创新高是常态，单纯的 Close 值没有预测力，但 Ts\_Rank(Close, 20\) 持续维持在1.0则意味着极强的动量 5。  
* **Decay\_Linear(x, d):** 线性衰减加权平均。![][image7]，其中 ![][image8]。相比简单的移动平均（SMA），衰减算子给予近期数据更高的权重，这在信息效率较低、反转极快的A股市场尤为重要，能减少信号的滞后性 9。

### **2.2 高阶与张量算子（Tensor & High-Order Operators）**

随着深度学习的引入，传统的标量算子已无法满足对复杂市场结构的建模需求。高阶张量算子开始被引入Alpha挖掘中。

#### **2.2.1 张量相关性与分解**

传统的 Correlation(x, y, d) 仅计算两个序列的线性相关。在多因子视角下，市场数据可以表示为一个三阶张量 ![][image9] （时间 ![][image10] 股票 ![][image10] 特征）。

* **张量分解算子:** 利用Tucker分解或CP分解提取潜在的因子结构。例如，通过张量分解可以同时捕捉“时间-行业”交互项，这在处理A股的“日历效应”与“行业轮动”共振时具有独特优势 11。  
* **高阶矩算子:** 如 Ts\_Skewness(x, d) (偏度) 和 Ts\_Kurtosis(x, d) (峰度)。研究表明，A股个股收益率的偏度与未来收益存在显著的负相关关系（博彩偏好理论），这类高阶统计量算子是挖掘非线性Alpha的金矿 13。

#### **2.2.2 图神经网络算子（Graph Operators）**

考虑到A股市场显著的产业链传导效应，图算子被用于捕捉股票间的关联。

* **Graph\_Conv(x, A):** 基于邻接矩阵 ![][image11]（可以是产业链关系、股权关系或基于收益率相关性构建的动态图）进行卷积。![][image12]，意味着将关联股票的特征聚合到当前股票。这对于挖掘“补涨”类Alpha因子极为有效。

### **2.3 逻辑与状态控制算子**

为了应对A股的微观结构限制（如涨跌停），逻辑算子必不可少。

* **If-Then-Else (三元运算符):** Condition? Value\_True : Value\_False。  
* **SignedPower(x, e):** 保持符号的幂运算 ![][image13]。这在处理动量因子时非常有用，可以放大大幅波动的信号权重，同时保持方向不变 5。

| 算子类别 | 代表函数 | A股市场应用场景与逻辑 |
| :---- | :---- | :---- |
| **基础时序** | Ts\_Rank, Ts\_Mean, Decay\_Linear | 捕捉短期动量反转；平滑高频噪点。 |
| **基础截面** | Rank, Scale, IndNeutralize | 去除风格与行业Beta；适应全市场选股。 |
| **高阶统计** | Covariance, CoSkewness | 捕捉风险传导；挖掘崩盘风险因子。 |
| **逻辑控制** | Condition, Cutoff | 处理涨跌停（LULD）状态；过滤停牌数据。 |
| **张量/图** | Tensor\_Corr, Graph\_Agg | 挖掘产业链传导效应；多维数据降维。 |

## ---

**3\. 因子挖掘实现的最佳方式：算法与工程**

“最佳”的实现方式并非单一算法的选择，而是算法策略与底层工程架构的完美结合。目前业界的主流趋势是将符号回归（Symbolic Regression）的可解释性与深度学习（Deep Learning）的搜索能力相结合，并部署在高性能的计算集群上。

### **3.1 核心挖掘算法演进**

#### **3.1.1 遗传规划（Genetic Programming, GP）的深度优化**

GP是挖掘公式化Alpha（Formulaic Alpha）的基石。它通过模拟生物进化过程（交叉、变异、选择）来生成因子表达式。

* **最佳实践 \- gplearn的改进:**  
  * **算子集定制:** 针对金融数据引入 Ts\_Rank、Decay 等专用算子，而非仅使用数学符号。  
  * **适应度函数设计:** 传统的MSE（均方误差）并不适合金融预测。最佳实践是使用 RankIC（秩相关系数）或 RankICIR 作为适应度函数，直接优化因子的排序能力。  
  * **膨胀控制（Bloat Control）:** GP容易生成极其复杂但过拟合的公式（如嵌套10层 Rank）。必须引入“简约压力（Parsimony Pressure）”，在适应度函数中对公式长度进行惩罚：![][image14] 14。  
  * **岛屿模型（Island Model）:** 为了维持种群多样性，防止早熟收敛，应采用岛屿模型并行进化，不同岛屿间定期交换个体。

#### **3.1.2 深度强化学习（Deep Reinforcement Learning, DRL）**

以 **AlphaGen** 为代表的DRL框架被认为是目前最先进的挖掘方式之一 4。

* **建模为马尔可夫决策过程 (MDP):**  
  * **状态 (State):** 当前生成的公式树的状态（如当前的根节点或叶子节点）。  
  * **动作 (Action):** 从算子库中选择下一个算子（如 \+, Close, Rank）。  
  * **奖励 (Reward):** 生成公式在回测集上的夏普比率或ICIR。  
* **优势:** DRL agent（如使用PPO算法）可以学习到算子的“语法结构”，例如它能学会 Ts\_Delta 后面通常接价格数据而非成交量数据，从而比随机变异的GP更高效地探索有效空间。  
* **实现细节:** 使用LSTM作为Controller网络生成序列，利用Policy Gradient优化网络参数，使其倾向于生成高回报的公式结构。

#### **3.1.3 基于大语言模型（LLM）的交互式挖掘**

**Alpha-GPT** 展示了利用LLM进行因子挖掘的潜力。这不仅仅是让GPT写代码，而是利用其语义理解能力 3。

* **思维链（Chain-of-Thought）提示:** 引导LLM像研究员一样思考。例如：“在市场剧烈波动（高VIX）时，流动性可能会枯竭。请构建一个因子捕捉这种流动性溢价，使用量价背离的逻辑。”  
* **代码即策略:** LLM生成的不是黑盒权重，而是可解释的Python/C++表达式代码。  
* **反馈闭环:** 将回测结果（如“换手率过高”）作为Prompt反馈给LLM，要求其修改公式（如“增加 Decay\_Linear 以降低换手”）。

#### **3.1.4 神经符号回归（Neural Symbolic Regression, NSR）**

**AlphaFormer** 等模型结合了Transformer与符号回归 17。

* **端到端生成:** 预训练Transformer模型学习大量数学公式的嵌入表示，直接预测给定数据分布下的最佳数学表达式骨架，再通过梯度下降微调常数参数。这解决了GP在常数优化（Constant Optimization）上效率低下的问题。

### **3.2 针对A股市场微观结构的工程实现**

A股市场的特殊规则（T+1、涨跌停、停牌）要求在因子计算引擎中内置特殊的逻辑处理，否则回测结果将完全失真。

#### **3.2.1 涨跌停（LULD）处理逻辑**

在A股，涨停（Limit Up）无法买入，跌停（Limit Down）无法卖出。如果因子在涨停价发出买入信号，这就是无效的“虚幻Alpha”。

* **算子级屏蔽:** 最佳实现是在算子底层（C++层）引入LULD掩码。  
  Python  
  \# 伪代码逻辑  
  def effective\_signal(raw\_signal, price\_data):  
      \# 判定涨跌停状态  
      is\_limit\_up \= (price\_data\['close'\] \>= price\_data\['pre\_close'\] \* 1.095) \# 考虑精度，通常设阈值  
      is\_limit\_down \= (price\_data\['close'\] \<= price\_data\['pre\_close'\] \* 0.905)

      \# 修正信号：涨停时不买（信号置0或负），跌停时不卖  
      \# 假设 signal \> 0 为买入意愿  
      adjusted\_signal \= np.where(is\_limit\_up & (raw\_signal \> 0), 0, raw\_signal)  
      adjusted\_signal \= np.where(is\_limit\_down & (raw\_signal \< 0), 0, adjusted\_signal)  
      return adjusted\_signal

  此逻辑应在因子生成的每一步或最终合成阶段强制执行 18。

#### **3.2.2 停牌（Suspension）处理**

停牌会导致数据缺失或价格僵化（波动率为0）。

* **数据清洗:** 必须维护一张动态的“可交易状态表”。  
* **算子逻辑:** 对于时序算子（如 Ts\_Mean），不能简单地对停牌期间的价格（通常填充为前收盘价）求平均，这会低估波动率。最佳方式是使用 **“真实交易日窗口”**。即 Ts\_Mean(Close, 20\) 应取该股票最近**有交易**的20天数据，而非日历上的最近20天。这需要在底层数据结构中支持非对齐的时间索引访问 20。

#### **3.2.3 高性能计算引擎：KunQuant与Qlib**

面对全市场5000+只股票、毫秒级数据和数万个因子，Python（Pandas）的性能已不可接受。

* **KunQuant:** 这是一个专为Alpha101/158设计的开源高性能算子库。它利用LLVM生成针对SIMD指令集（AVX2/AVX512）优化的C++代码。  
  * **核心优化:** 自动进行“公共子表达式消除”（CSE）。例如，如果10个因子都用到了 Rank(Close), KunQuant只会计算一次并缓存结果。  
  * **内存布局:** 支持从 到 的内存布局动态转换，分别优化截面算子和时序算子的缓存命中率 22。  
* **Qlib:** 微软开源的AI量化平台，提供了完整的数据准备、模型训练（LightGBM/LSTM）和回测流。最佳实践是将Qlib作为数据管理和实验编排层，底层挂载KunQuant或自定义的C++算子库进行特征计算 23。

### **3.3 分布式计算架构**

为了实现持续产生，系统必须是分布式的。

* **Ray框架:** 利用Ray构建分布式挖掘集群。  
  * **Actor模式:** 每个Actor是一个挖掘Worker，负责跑GP或RL的一个Episode。  
  * **Object Store:** 利用Ray的共享内存对象存储，在Worker之间零拷贝传输巨大的市场数据张量，极大降低IO开销 25。

## ---

**4\. 挖掘出来的因子评判标准：多维评估体系**

在A股市场，高收益往往伴随着高风险或不可交易性。因此，对因子的评判必须超越单一的夏普比率，建立多维度的严格筛选标准。

### **4.1 统计效能标准（Statistical Power）**

* **IC (Information Coefficient):** 因子值与下期收益率的截面相关系数。  
  * **阈值:** 在A股，通常要求 RankIC \> 0.03 (3%)。  
* **ICIR (IC Information Ratio):** ![][image15]。衡量预测的稳定性。  
  * **标准:** ICIR \> 2.0 被认为是优秀因子的门槛。如果IC很高但波动极大（ICIR低），说明该因子可能只在特定风格（如小盘股爆发）时有效，容易失效。  
* **t-value:** 回归系数的t统计量。通常要求 ![][image16] 且在长时间窗口内保持显著。

### **4.2 交易成本与换手率（Turnover & Cost）**

这是A股最致命的约束。由于印花税（卖出千分之五或一，视政策而定）和佣金存在，高换手策略极难盈利。

* **双边换手率 (Turnover Rate):** 每日买卖金额除以总资产。  
* **适应度得分 (Fitness Score):** WorldQuant提出的综合指标：  
  ![][image17]  
  该公式惩罚了利用高换手换取微薄收益的策略。在A股，对于日频策略，通常要求换手率控制在单边20%以内，或者必须有极高的Alpha来覆盖成本 26。  
* **盈亏平衡点:** 计算扣除所有成本后的净收益。对于高频因子（Delay 0或1），必须模拟滑点（Slippage），通常A股设为单边千分之二左右。

### **4.3 相关性与正交性（Orthogonality）**

新挖掘的因子不能是现有因子的重复。

* **相关性矩阵:** 计算新因子与已有因子库的RankIC矩阵。如果相关系数 \> 0.7，通常直接剔除。  
* **残差正交化:** 将新因子对Barra风格因子（市值、动量、波动率等）进行回归：  
  ![][image18]  
  取残差 ![][image19] 作为“纯Alpha”。如果残差的IC显著下降，说明该因子只是在赚取风格暴露的钱（Smart Beta），而非真正的Alpha 28。

### **4.4 稳健性与概率过拟合（Robustness & PFS）**

* **PFS (Probabilistic Factor Score):** 由Bailey和Lopez de Prado提出，用于调整由于多次回测（Data Mining Bias）导致的夏普比率虚高。尝试的公式越多，这就要求最终因子的夏普比率门槛越高。  
* **分层测试:** 在不同市值的股票池（CSI300 vs CSI1000）、不同市场环境（牛、熊、震荡）下测试因子表现。A股特有的“大小盘分化”要求因子不能仅在微盘股有效（流动性陷阱） 29。

## ---

**5\. 实现因子和算子的持续产生：Alpha工厂的生命周期管理**

要实现“持续产生”，必须构建一个闭环的自动化系统，称为“Alpha工厂（Alpha Factory）”。这不仅仅是代码，而是流程管理。

### **5.1 算子与因子的自动发现流程**

1. **算子元学习 (Operator Meta-Learning):**  
   * **目标:** 自动发现新的算子函数，而不仅仅是组合现有算子。  
   * **方法:** 使用AutoML技术，在基础数学原语（加减乘除、指数、对数）上进行搜索，寻找能够提升因子表达能力的新函数形式。例如，发现 ![][image20] (Sigmoid-like) 这种非线性变换比单纯的 ![][image21] 更适合处理A股的成交量数据。  
   * **实现:** 这是一个高算力消耗的过程，通常在低频（月度/季度）进行更新，将发现的高效新算子加入标准库 30。  
2. **因子持续挖掘 (Continuous Factor Mining):**  
   * **种子库机制:** 系统维护一个“优质种子公式库”。每次挖掘不是从零开始，而是从种子库中随机抽取公式进行变异（Mutation）。  
   * **对抗生成:** 设计一个“对抗者（Adversary）”网络，专门寻找当前因子池失效的市场场景，倒逼生成器（Generator）挖掘能覆盖这些场景的新因子。

### **5.2 因子生命周期管理系统（LCM）**

因子是有寿命的（Alpha Decay）。A股市场的Alpha衰减极快，通常只有3-6个月的半衰期。

* **孵化期 (Incubation):** 新挖掘的因子通过回测后，不立即上线，而是进入“模拟盘（Paper Trading）”观察期（如1个月）。只有在样本外（Out-of-Sample）表现与回测一致的因子才能转正。  
* **生产期 (Production):** 因子被纳入实盘组合。系统实时监控其IC衰减情况。  
* **退休与回收 (Retirement & Recycling):**  
  * 当因子滚动ICIR低于阈值（如0.5）或与新因子高度相关时，触发退役流程，权重逐渐归零。  
  * **回收:** 退役因子不应直接丢弃，而是作为“失效样本”存入数据库，供挖掘算法学习“什么是不好的因子”，或者作为反向指标使用 3。

### **5.3 自动化流水线架构设计**

推荐采用如下的分层架构来实现这一工厂：

| 层级 | 核心组件 | 技术栈 | 功能描述 |
| :---- | :---- | :---- | :---- |
| **数据层** | 历史数据仓, 实时流数据 | **DolphinDB / KDB+** | 存储Tick级高频数据，提供高性能的时序聚合查询。 |
| **算子层** | 表达式引擎 | **KunQuant / C++ SIMD** | 将Alpha公式编译为机器码，处理LULD与停牌逻辑。 |
| **挖掘层** | 搜索Agent集群 | **Ray \+ PyTorch (AlphaGen)** | 分布式运行GP/RL算法，大规模搜索因子空间。 |
| **评估层** | 回测与风控 | **Qlib / Alphalens** | 计算IC、换手率、正交性，执行PFS检验。 |
| **管理层** | 因子数据库与调度 | **MLflow / Airflow** | 记录因子元数据、版本控制、调度重训练任务。 |

## ---

**6\. 结论**

在中国A股市场构建最佳的Alpha挖掘体系，是一个跨越数学建模、机器学习算法与高性能计算工程的系统性挑战。

1. **算子层面:** 必须超越基础的时序截面算子，引入**张量分解**与**图卷积**算子以捕捉复杂市场结构，并内嵌**LULD与停牌处理逻辑**以确保信号的可交易性。  
2. **挖掘层面:** 放弃单纯的随机搜索，转向\*\*深度强化学习（AlphaGen）**与**大模型辅助（Alpha-GPT）\*\*相结合的混合驱动模式，利用AI理解市场“语法”。  
3. **工程层面:** 采用 **KunQuant** 等编译型表达式引擎替代解释型计算，利用 **Ray** 进行大规模分布式搜索，是突破算力瓶颈的关键。  
4. **评判与管理:** 建立包含 **Fitness Score**、**ICIR** 及 **PFS** 的多维严苛标准，并实施全生命周期的自动化管理，是应对Alpha快速衰减、实现持续超额收益的唯一途径。

这一套从底层算子到上层管理的完整体系，构成了现代量化投资机构的核心护城河。

## **表格索引**

### **表 1: Alpha算子分类与A股应用特征**

| 算子类别 | 数学形式示例 | 市场含义 | A股特有优化 (LULD/停牌) |
| :---- | :---- | :---- | :---- |
| **基础截面** | **![][image22]** | 去除绝对价格，保留相对强弱 | 需排除涨跌停无法交易的标的参与排名 |
| **时序动量** | **![][image23]** | 捕捉趋势突破 | 遇停牌需使用“真实交易日”窗口计算 |
| **线性衰减** | **![][image24]** | 强调近期信息，降低滞后 | 应对高频反转，权重设为 ![][image25] |
| **张量交互** | **![][image26]** | 捕捉“行业-风格”共振 | 需处理缺失值填充，避免矩阵奇异 |
| **逻辑控制** | **![][image27]** | 状态依赖策略 | ![][image28] 中必须包含 ![][image29] 检查 |

### **表 2: 自动化挖掘算法对比**

| 算法 | 搜索机制 | 优点 | 缺点 | A股适用性 |
| :---- | :---- | :---- | :---- | :---- |
| **遗传规划 (GP)** | 进化变异 | 探索能力强，无须梯度 | 易产生复杂冗余公式 (Bloat) | 中 (需强力正则化) |
| **强化学习 (RL)** | 策略梯度 | 能学习公式语法结构 | 训练不稳定，样本效率低 | 高 (AlphaGen表现优异) |
| **大语言模型 (LLM)** | 语义生成 | 具备经济学逻辑解释性 | 推理成本高，易产生幻觉 | 高 (作为Idea Generator) |
| **神经符号 (NSR)** | 梯度下降 | 常数优化极其高效 | 结构搜索空间受限 | 中 (用于微调) |

### **表 3: A股Alpha因子核心评判指标**

| 指标维度 | 具体指标 | 阈值标准 (建议) | 业务含义 |
| :---- | :---- | :---- | :---- |
| **预测能力** | RankIC | ![][image30] (日频) | 剔除运气成分后的预测力 |
| **稳定性** | ICIR | ![][image31] | 因子在不同时间段表现一致 |
| **可交易性** | Turnover | ![][image32] (单边) | 即使高IC，高换手也会被印花税吞噬 |
| **拥挤度** | Correlation | ![][image33] (与现有库) | 避免同质化竞争，降低失效风险 |
| **稳健性** | PFS | ![][image34] | 调整数据挖掘偏差后的置信度 |

## **参考文献引用**

5 *101 Formulaic Alphas* 18 *Limit Up-Limit Down (LULD) Plan Overview* 20 *Handling Stock Suspension in Quantitative Factors* 3 *Alpha-GPT: Human-AI Interactive Alpha Mining* 4 *AlphaGen Repository & Methodology* 16 *Generating Synergistic Formulaic Alpha Collections via RL* 17 *AlphaFormer: End-to-End Symbolic Regression* 14 *Deep Symbolic Regression vs GP* 29 *Probabilistic Factor Score* 1 *Quantitative Alpha Factory Pipeline Design* 23 *Qlib: AI-oriented Quantitative Platform* 11 *High-order Tensor Operators in Finance* 33 *Handling Stock Suspension in Code* 19 *Custom Operator Logic for LULD* 15 *gplearn Documentation* 28 *Evaluating Factor Models in China* 27 *WorldQuant Alpha Acceptance Criteria* 30 *LLM-Meta-SR for Selection Operators* 22 *KunQuant: Optimized C++ Operator Library* 6 *NumPy Optimization for Alphas* 7 *WorldQuant Neutralization in China* 25 *Ray for Distributed Computing*

#### **引用的著作**

1. Quant 4.0: engineering quantitative investment with automated, explainable, and knowledge-driven artificial intelligence \- JZUS \- Journal of Zhejiang University SCIENCE, 访问时间为 一月 25, 2026， [https://jzus.zju.edu.cn/iparticle.php?doi=10.1631/FITEE.2300720](https://jzus.zju.edu.cn/iparticle.php?doi=10.1631/FITEE.2300720)  
2. \[2301.04020\] Quant 4.0: Engineering Quantitative Investment with Automated, Explainable and Knowledge-driven Artificial Intelligence \- arXiv, 访问时间为 一月 25, 2026， [https://arxiv.org/abs/2301.04020](https://arxiv.org/abs/2301.04020)  
3. Alpha-GPT: Human-AI Interactive Alpha Mining for Quantitative Investment \- arXiv, 访问时间为 一月 25, 2026， [https://arxiv.org/html/2308.00016v2](https://arxiv.org/html/2308.00016v2)  
4. RL-MLDM/alphagen: Generating sets of formulaic alpha (predictive) stock factors via reinforcement learning. \- GitHub, 访问时间为 一月 25, 2026， [https://github.com/RL-MLDM/alphagen](https://github.com/RL-MLDM/alphagen)  
5. 101 Formulaic Alphas \- ResearchGate, 访问时间为 一月 25, 2026， [https://www.researchgate.net/publication/289587760\_101\_Formulaic\_Alphas](https://www.researchgate.net/publication/289587760_101_Formulaic_Alphas)  
6. Improve the implementation of worldquant 101 alpha factors using numpy \- Stack Overflow, 访问时间为 一月 25, 2026， [https://stackoverflow.com/questions/73694527/improve-the-implementation-of-worldquant-101-alpha-factors-using-numpy](https://stackoverflow.com/questions/73694527/improve-the-implementation-of-worldquant-101-alpha-factors-using-numpy)  
7. World Quant Brain Alpha Documentation | PDF | Stocks | Technical Analysis \- Scribd, 访问时间为 一月 25, 2026， [https://www.scribd.com/document/728780335/World-Quant-Brain-Alpha-Documentation](https://www.scribd.com/document/728780335/World-Quant-Brain-Alpha-Documentation)  
8. Worldquant Report | PDF | Private Sector | Financial Markets \- Scribd, 访问时间为 一月 25, 2026， [https://www.scribd.com/document/733973604/Worldquant-Report](https://www.scribd.com/document/733973604/Worldquant-Report)  
9. GTJA\_Alpha191.py \- GitHub Gist, 访问时间为 一月 25, 2026， [https://gist.github.com/kangchihlun/7850f07c11bdea022b2d49f1d4ed9802](https://gist.github.com/kangchihlun/7850f07c11bdea022b2d49f1d4ed9802)  
10. A Simpler Way to Calculate WorldQuant 101 Alphas | by DolphinDB \- Medium, 访问时间为 一月 25, 2026， [https://medium.com/@DolphinDB\_Inc/a-simpler-way-to-calculate-worldquant-101-alphas-c55dac54e9f7](https://medium.com/@DolphinDB_Inc/a-simpler-way-to-calculate-worldquant-101-alphas-c55dac54e9f7)  
11. Tensor-Based Learning for Predicting Stock Movements \- AAAI Publications, 访问时间为 一月 25, 2026， [https://ojs.aaai.org/index.php/AAAI/article/view/9452/9311](https://ojs.aaai.org/index.php/AAAI/article/view/9452/9311)  
12. Mining Alpha Factors in Financial Markets using Multi-Frequency Timing Residual Networks, 访问时间为 一月 25, 2026， [https://www.researchgate.net/publication/380227560\_Mining\_Alpha\_Factors\_in\_Financial\_Markets\_using\_Multi-Frequency\_Timing\_Residual\_Networks](https://www.researchgate.net/publication/380227560_Mining_Alpha_Factors_in_Financial_Markets_using_Multi-Frequency_Timing_Residual_Networks)  
13. Understanding Corporate Actions: Why Assets May Be Suspended or Have Limited Trading, 访问时间为 一月 25, 2026， [https://www.quilterinvest.com/article/understanding-corporate-actions-suspended-limited-trading](https://www.quilterinvest.com/article/understanding-corporate-actions-suspended-limited-trading)  
14. Genetic Programming and Symbolic Regression, 访问时间为 一月 25, 2026， [http://static1.1.sqspcdn.com/static/f/454091/25716268/1417204066717/2014-11-27+ADC+gp+and+sr.pdf?token=IMad4vqkL9WCz4mLRwVaTw%2BuxUU%3D](http://static1.1.sqspcdn.com/static/f/454091/25716268/1417204066717/2014-11-27+ADC+gp+and+sr.pdf?token=IMad4vqkL9WCz4mLRwVaTw%2BuxUU%3D)  
15. Examples — gplearn 0.4.3 documentation, 访问时间为 一月 25, 2026， [https://gplearn.readthedocs.io/en/stable/examples.html](https://gplearn.readthedocs.io/en/stable/examples.html)  
16. Alpha2: Discovering Logical Formulaic Alphas using Deep Reinforcement Learning \- arXiv, 访问时间为 一月 25, 2026， [https://arxiv.org/html/2406.16505v2](https://arxiv.org/html/2406.16505v2)  
17. AlphaFormer End To End S | PDF | Time Series | Applied Mathematics \- Scribd, 访问时间为 一月 25, 2026， [https://www.scribd.com/document/966264950/15375-AlphaFormer-End-to-End-S](https://www.scribd.com/document/966264950/15375-AlphaFormer-End-to-End-S)  
18. Limit Up Limit Down, 访问时间为 一月 25, 2026， [https://www.luldplan.com/](https://www.luldplan.com/)  
19. Limit Up/Limit Down (LULD) Plan | FINRA.org, 访问时间为 一月 25, 2026， [https://www.finra.org/filing-reporting/trf/limit-uplimit-down-luld-plan](https://www.finra.org/filing-reporting/trf/limit-uplimit-down-luld-plan)  
20. A Sustainable Quantitative Stock Selection Strategy Based on Dynamic Factor Adjustment, 访问时间为 一月 25, 2026， [https://www.mdpi.com/2071-1050/12/10/3978](https://www.mdpi.com/2071-1050/12/10/3978)  
21. Fund Flows in the Shadow of Stock Trading Regulation \- American Economic Association, 访问时间为 一月 25, 2026， [https://www.aeaweb.org/conference/2022/preliminary/paper/3kQkz9GT](https://www.aeaweb.org/conference/2022/preliminary/paper/3kQkz9GT)  
22. Menooker/KunQuant: A compiler, optimizer and executor for financial expressions and factors \- GitHub, 访问时间为 一月 25, 2026， [https://github.com/Menooker/KunQuant](https://github.com/Menooker/KunQuant)  
23. microsoft/qlib: Qlib is an AI-oriented Quant investment platform that aims to use AI tech to empower Quant Research, from exploring ideas to implementing productions. Qlib supports diverse ML modeling paradigms, including supervised learning, market dynamics modeling, and RL, and is now equipped with https://github.com/microsoft \- GitHub, 访问时间为 一月 25, 2026， [https://github.com/microsoft/qlib](https://github.com/microsoft/qlib)  
24. Powering Quant Finance with Qlib's PyTorch MLP on Alpha360 | Vadim's blog, 访问时间为 一月 25, 2026， [https://vadim.blog/qlib-ai-quant-workflow-pytorch-mlp](https://vadim.blog/qlib-ai-quant-workflow-pytorch-mlp)  
25. LLM training and inference — Ray 2.53.0, 访问时间为 一月 25, 2026， [https://docs.ray.io/en/latest/ray-overview/examples/entity-recognition-with-llms/README.html](https://docs.ray.io/en/latest/ray-overview/examples/entity-recognition-with-llms/README.html)  
26. Finding Alphas.pdf, 访问时间为 一月 25, 2026， [https://asset.quant-wiki.com/pdf/Finding%20Alphas.pdf](https://asset.quant-wiki.com/pdf/Finding%20Alphas.pdf)  
27. WorldQuant International Quant Championship | James T. Glazar \- GitHub Pages, 访问时间为 一月 25, 2026， [https://jglazar.github.io/projects/wq\_project/](https://jglazar.github.io/projects/wq_project/)  
28. Evaluating Factor Models in China \- QuantPedia, 访问时间为 一月 25, 2026， [https://quantpedia.com/evaluating-factor-models-in-china/](https://quantpedia.com/evaluating-factor-models-in-china/)  
29. AlphaEval: A Comprehensive and Efficient Evaluation Framework for Formula Alpha Mining \- arXiv, 访问时间为 一月 25, 2026， [https://arxiv.org/html/2508.13174v1](https://arxiv.org/html/2508.13174v1)  
30. LLM-Meta-SR: In-Context Learning for Evolving Selection Operators in Symbolic Regression, 访问时间为 一月 25, 2026， [https://arxiv.org/html/2505.18602v2](https://arxiv.org/html/2505.18602v2)  
31. SR-LLM: An incremental symbolic regression framework driven by LLM-based retrieval-augmented generation | PNAS, 访问时间为 一月 25, 2026， [https://www.pnas.org/doi/10.1073/pnas.2516995122](https://www.pnas.org/doi/10.1073/pnas.2516995122)  
32. Life Cycle Management (LCM) | www.dau.edu, 访问时间为 一月 25, 2026， [https://www.dau.edu/acquipedia-article/life-cycle-management-lcm](https://www.dau.edu/acquipedia-article/life-cycle-management-lcm)  
33. Building Alpha in the Backtest: Index Signals × Multi-Factor Rebalancing | by DolphinDB, 访问时间为 一月 25, 2026， [https://medium.com/@DolphinDB\_Inc/building-alpha-in-the-backtest-index-signals-multi-factor-rebalancing-a080a78b0a0e](https://medium.com/@DolphinDB_Inc/building-alpha-in-the-backtest-index-signals-multi-factor-rebalancing-a080a78b0a0e)

[image1]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAKkAAAAaCAYAAADMi3z0AAAEvElEQVR4Xu2aW6h1UxTH/0IRcs2dzy0lSpFEPLg8kPCAKPJ95QElD4R4EA/epOjzQIQHIYpCLimnFKJciijUIZcQD4pyN37GGt+ae+x1zj72t/c5R41f/Tt7zbn2XOuc9Z9jjjHXkYqiKIqiKP5XbG/aw7RN7pgCxto1NxbF1oChnjZdkDumhPEeNV2j2Zi+mBFHme4zvWf6ovv5oOn+TleY9txy9nx5R34PP5peSX1DvGC6WbM1FL/rG6brc0exdhxgutB0k+kv063dMbrF9LnpN9O18YU5cr48kv1tuif1ZTDmm5rPBDpVPlmKdcYdpqdM26X2XUyvyY0zb/YyfWj6QR7hlwKDbjbtkztmyFmdinXCTvLllWiaOcz0jVbHpCeYfjEtmHYe7RqB6L+YG2cME+YxjU/aYo0II56SO4zL5Ab9NXfIIxqVNVXxECzFrdk4j+i3lAGvlF+LqB7sIB+nzTvP0+RJw/e2XeZ4ElxvUT4hinVAPHSiRwtL7mfynPSi1Ef0/VYe9cjfrjZdrt5MGPJ1+XcpQkgbvjJ9afrD9Hh3XgvpBvdxdnd8o+lj00eme+MkuYl/ao5bmDTktVyLtOEc+X19LS8KN/SnTuR3DU/cYpUhqi3IzREVPdU9BdNGjVfOnP+yxiMrJiISAlHrSfU55p8a3SY6V8OREFM8b9pfvYkfkZ/L0gtxv293xy1XmW5Xf89RhDEJ9+s+X9L1rQQKyaEUqIXJykSIYnMlOlnjf9diGYiWRJyfUzt7hpiLB9yCEXjYmCmInPb47ng3eRQkCmG8F007dn1AJBwyKW2Yj/OjcMJcZ8ivAWFSlGG77PDmmLFIY0hnMMWx3c/gQPl9LrWBz99kkkmLVeBSuTmIeBnaiWQBD5NtH9ojakLktLs3bRA5Zvugw2R5UhB9ORexVN892r2FuIeF1D4E12AyMfYQ18lTCcw6RJl0nfCA3BgPpfYwTWtSIhG5IOJzEDltXsLIMVkyz2zaTpKnCkTLFoyyaDpIvk9JLjyUDy4XSTPcE3u908JOQ5l0jWF5Jlpk0wHGaqMgWzHHyVODBfUVOpX3W/IxiKjkq1GAsdS3e6+Ro8YS/JzpmK4PMxHZAq4bx0T72/qufycOY2Q+kN8zOS9VOUVaGyWfUX/f/C6faHQCZRgrirhijbhB/iB4uHnJyybFTAebnlW/NUMlTYFEtKTQIl/ljVWQ04IjTd+rNznFFgYmarMst5ETg2I2lneucXTqYwJkmHCMz4TjXlqT7qt+fMa8U34f7cTITHqpUMyRWLYjBwwd2pxDoUMb20gb5W+dgIdOG8b+1HSxaZPcNJyzoTsPME0UU4AhN5u+M72kvmBh75TlvX3FyThsP72q8X/4iJQh87DpXXmERtwjekKjOfchptPkEysieYZJlAu+Yh1CFIltkyOadgyDodpNfB5q3tSnys/Ed/M796Fz99ZwexRPuSBqx+Yzm/eMgYY28pczIb87k6MopoblfKkouBLIj8l1SVuG3iph0HZlKYqpIEU4MTeuEHLcu+R5bwsRmH//Y9+3KLYa3mK9r//2qrMlKv0WxuQlwLRjFsUYp8vfYM3iv5XYFmPfmJ2AoiiKoiiKYn78A60x9+zk3LYmAAAAAElFTkSuQmCC>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIIAAAAZCAYAAAD9ovZ9AAAFVElEQVR4Xu2aa6imUxTHl4ZiXGPcoqZx+YAZlEuRa5kilw+IKZIvxqVRQsQHnVzKBwoRMTWkSSE+4IukE0KUKFKkzkiEpDTkksv6nbXXedez3vd53ou3M+97zvOrf+/z7L2f295rr7X2PkekpaWlpaWlpaVl2jhe9YLqGdWtqudUB1Ra9GdX1cuqm8v5OaoXVbsvtFiC7KdakQv7sItq71w4ARyquld1sGqbapPYYB4XGw3AYWLXYwDwiGqraqeFFg3sptqu+kH1jepP1SrVZtXFod04OFz1rupr1RsymqUymI+X31HAgN6TATtnkaG/PxPr/8g61aU1Wi82hnCf6jUxzwAYxWnluBEs8UPVkaFsL9Vfqp9UR4XyccC9LxSzUqx1FC5RfZULh+R01cm5cAeCUTP4cQajnWOjAcAI7gznGBVe5hhp8J57qF5XvZUrxDzD26o9c8UY4AO3qC7KFQNAzPxUNZPKh4UOnhXrg0lgRvWj2KS8vZQxeMN6re+kcz3GRX5wrOrGhRY92KD6V3VFrhCzrFFnbD+wfCyVeDYsxM6fVWtzxQgQAs/NhTuIa1TPi7l2Jud1qgcqLQbjb9UXqo2qp1TviIXRWs9ObCZGYwhPV6vmYbbunwsDzMw6V4MVN8Xva8We2wQzNd/jBNWvUnV9Gd6Jd/MYmc8juOA51SGpfFrhG5v6phZmPAOCHhbLNHt1mENCgov5VizZI4e4QTruC+O6X/V9qb9ezOVdVeoBl4y7+ieUOX5/rp2T7vvjuXjX88p5Bm/Bteg3sYz7Y7Ewx70yuFByoYGSqSmAfM9XC0OBuyCmuDG4XoqNCp5UkqQRc1arPhLrZOq8no7nmHpcFPcjH3A8LPDcTLw/4P4/l45bw23iEfAMGYzlSelkz2TfxFwSQo4JAzkfIGnl/fqtjDDw86U7W2/SqfNXLi68Z/aiA0NG+aB0G0PuNAad2OyZNrOJdp+ILceIa3+IZePOY6UNocBh9jELyUEiuO98/SlihrCmnLPRggH1yi1IrHgPh8HFADEQruM9cgbO7MEzeXJVx7QYwlhg4EmcPhDrtJNCHZ1J2aPlGFapLhAzJKA+rl89B8kz2A0od/6MWMhgsHgGg4pHIbw4DOg26Twzkjse7+FJMO3PDnWO5xz5XRYT9lWeXUR1UffxGMSsVAePmeMhoBfE4l/Kr0Oy6WHBjYekbK4oJmi+mxaNrxdNhhAhlJAT9Fv68jxyibq+WPIwa6/OhYUDxdxx3IYlls5Kd7hwMBriPl7CYUZiCMxKZjkrEHfFPvPdcNwQ6gzNwRCywTkrpPN+nlRGzkzn4DmC78vXQdgh3/CwOYhenb9ywiHGRjcfuVIshkcYaB+8CMZyj1gnz0rVUAgxPmg8DyNhaeMdz708w+U+70u3IZD43CG2vQp1WT7f8ZCYoXC8RaqGwP1fCedOv1XIkocBYOPhcukYA7+48+2q20qZw4CwZDwilB0ttl9/i2qlVN39vmIz3904myPgXoKZyIogeh3a8D4RjI+E0zNhBozr8waYh7ObxGavr4SAa+8qyvA+hJDazZalDC70rHJMJ50otsN4RjlvYh+xgSV8ZDAkEjzq/D4MUDwHjinrFWYIWdwf9arHi/Cn2RyGnPws7tO0L4IRbMqFLdPBetXvMp6tYRLgNblwwrlMbK/GN87Q3ZUWywRmPHvyvWL+MLBvQVibJvh2lugslQmjJLB13nNZsFrsL5CjQhgjCZ3Ef1BpgkTeN834hq2hbllDItlvryDDCmaz6qBcMeEw878M5yTb//d/MlqmELzXm+WYEPGEdK/uBuY/VTciCmm5Y+QAAAAASUVORK5CYII=>

[image3]: <data:image/png;base64,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>

[image4]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACkAAAAZCAYAAACsGgdbAAABaUlEQVR4Xu2VvyuGURTHv0JR8qNEYjIoGQ0imWQjZTAYDQxKGfgDZJOBP8Aki8FiotiVjEabQWyKFL7f99z7Ou9jIPXcd7mf+tTz3HPrnufce88DZDKZTEqG6A19pheFGNrpFG0tBhLTTefpJ93xgSZ6TN/ouA/UiQZYknN+sJ/eB/Vcb1TNBzroB7dgma/5wcR0BsUK3FYvw5Ir2hYnJEBbu0Bv6R09p5d0Ok5QMn2w0mrCSHhPRTPdpa/u/RBWqJqtFh/0CPZVqdBam7CEtt34DCyfFjdWQRN1Dn6jkfbAqv0Xfyzk0K490ic67MY3YPnUoLJe065ioGTUqJWMkor4LlODepHOQdzqAVjFyuYKtq3VC0Im6Ts9oRN0LAZ01ZfCsxLdi4GSOaMvdDS8a22dTVVXLVE/l+oH7MP+Mpq0SA9ioGRWYZWMf5V12C1XkrP0lHaEWIVefDfS1MQ2GFEbUj6ZTOa/fAGWrD+H8AboVAAAAABJRU5ErkJggg==>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAAAZCAYAAAD5VyZAAAADy0lEQVR4Xu2YS6hOURTHl1Ceeb9JHiV5DUgRA2UikVCETAxQBkaU0JUkA/JOUjdKBibKq1CUgTwKRYoU8ijCyEAJ62ed7exvf+d89/vc+53v5u5f/evsc/a5d+21115rfUckEolEIpFIJBKJRByTVJ8ScR3pYBxV/Up0MHgW6QA8Vz0QCwCyQKQD0UXs1M9QfRMLgk4lMyL/LWz+KUk3fLLqq1hJaCkIeqkGSDovHDeCzqrBFcbtgW5iduWNC2W66qk3ZvPYfIKAYMjjpuqt6qPqhWp7co2uePOKAgduUr1JtE81TfVIzM6l6dSG0V91VvVO9Vm1ULVW9V7MztHp1GJwp78puM/GUwZ4xpwQDJ2dXPdW3VadUA1SXRV7txJTVMtr0BJ7rSJbVCdV3ZOx62Vmim3+LbEM1Sj6qC6rVogdMgLhp+q6mN+wd+vf2W1LbnaZpXqmGhPcx0AMoh8gQ4TPDnhjFwDMQ7zz3XueRT0C4KJY+XFgf7OYvadV5yQ7mItig2qXpOWRAMDGxaphyfXK5FlbMU/sEBBoZeAMnJIXdbyYlQV6iqVax1jVB1U/sUiboxrvPS8KHOmD7auTaxzsMoODsjckuBdCbebdakSfkXvSlHWqcd74vpjf8B9BQbnye6f9Yr5vLQtUr8ObUGnzwX0YckGQx2FpOeUXzUSxrER2yoKNbQpvFgw+2xbe9HgllqFbA4f1huT8n4eqUeFND6Jxt6SlwIdaSrRz6olkGhoHtW6NN87iiNjfrVaZKSyAE+hqPCefwPShPPVQHVLdEyt951XD/Ul1hKAj43QVy6isab73fJVYCZuguqT6oborVjYqZZYQ9o1Tf0Z1TfVFSv/PHzBih6Tpy6+dPqRyOlQ2wZUBlxn8ms9pc9DkHPfGReB6Fmo9181S2vUTlH4vg0NGeuMieCJm4yLVCLFfJr4NF6S0SaVH8EtCtSxTPU6uKdWuzJQwV8pPWUty6YgFMCZ70AwSyS4ASL2knLJ/WGdwHDZtFgtQFu0CgGDfKaXO3CN2IouEg8LBodbTEPoBMFSsd3KQWdd7Y6ARDpvjsEkmw5DZXGlnnfzyaPO1kpL6emOc3OgPQASBS7GAfWS3cPEEp2uKpkp5c1gv8A0+cn7Ch5StrOaREjZQzDZsrBY2/qWYH9w6yXaUlUgCDsExlDcc1sigzYP+hZJLOS2r3xXglxD9DRmE7yKUb77p0MtFEki7d1THxHqD9ggbuVe1UWoLUNZD78C7dP40kQQTXxsjHpSJWhzbCP71q6UrNcA622uQRyKRwvkNQAnEO6n8RC8AAAAASUVORK5CYII=>

[image6]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAoAAAAaCAYAAACO5M0mAAAAzUlEQVR4Xu2RPwtBYRSHj6QY5c9iUhaTweprmHwO+R5GGViZDMpopkz+DBaDUswmhefc917eezIZ5akn9TtO57znivz5kjQO8Iz7eOkzD+zY0JLAGzZswZLFA5ZMHpDCPCaxjlNx+8YY4QVX4h7QFbNfEddY8bIC7sSM1S59nY+OvYo3VvfZ4D0KQlpimqPOox9CX0xz9Me5l+lZluJOU8WmhhmchQVFH6Sr6NghjrEc1oKuLU5wgTXs4Qnb4r7QCz2wnkl/FS3m3uUf4gnWGSUAYIsNpgAAAABJRU5ErkJggg==>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHYAAAAhCAYAAAAMLF9eAAACeUlEQVR4Xu2a32tPYRzHP4qyzGhkLRpKSRSSrWlKcjHFFcW92lIu3EiUC0mUXLBdreFiudCWEu60CyQiuVESpf0DbrZa+fl+7/Oc7fkey86pfb+dp96verXzPM85te1znl+f55gJIYQQQgghhBBCVIg1sDlfKdJlGRyAK+EL+BW2hbY9cAo+DeWirIDHS7pv5kmxaHTDMbgDfoev4arQ1g//wPOhXBQFtgIcDjJ4DOKZUL/UPOC/4aFQJxKEPZU9lj2XrIffgrwmN+FwuBaJwN56MSpnPTgbhreZB5lD90JsN3+2jE9mnhSLDv+5R6MyF0w/YA/cCr/An/ANvBzdJypO3DuXhPJHuDbU3Yb3Q5tIiLtwGo7Ct+aBvWdzgWQdV8kiQVbDdvNEBQN7Mmrj/nZvVBYVh8kIBi3b5jBhMQQ7Z+9wuPXhFuiEafuTBE3wMewwX/k+ghM1dzgv4TV42jTPJkOLeTqRiyNmgRjsPByelUsWQogk4Py7DnblG0TacOV8xMqfCHF1fjZfKaoFDw2KbomWw3PwhpV/GUQDYGLjErwAr5gHrAxccSuwdWK/eeKfx3dMUsTegR/gpHlWatBq97PcC7eaz6386qIsCmwdYaDY43i4/j82m2ersnPaLbA3XLPuc7gugwJbZ/hZzDO4O9+Qg2e3WS6ZAclOgXjM9ylcb4K37N/enxkP1wpsg/hlPlcWSR9eDT/5Ujw3D/rBueZCKLANgj2KwT2Wb5iHjbDP/MyWXzzya4gy6cdTcNx8bn8Ad9U2z/IQvjfPaRM+wz3zAaud13fCd1F5g/mxJD8e4O85Al9F7Xx5Fxqh5oN/7/V8ZRX4C+8ge3J1hwQDAAAAAElFTkSuQmCC>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAZCAYAAACrWNlOAAACpUlEQVR4Xu2XS6iNURTHl1CEPCMlYSZiIMljQHkmRpJirkSKgSh3ZmBgIgNKiZISMyIMTpmQCeUxMhEJAyXkkcf/d9bevsfxOffmfl+n0/7Vv3v3XvvcvfY6a6+1r1kikUgkEolEPzJVui29kN5KM4rm2hlTnugXxkmbpePSL2lU0Vwrs6Rn0urSfF9xyDywTbJY+mAe4L6E63hd+l42NMDE8gRMsu41YrQ0RRpRNvQA4839Wiv9lK4UzbXC3tT3jrgQrFfSN+mgZQvmS4+lPeYfvmV+xbYHey+wUrovPZUeSpfNfdydX1Qj+81j91G6kTeQhaelCdJd6bll3TTWKpzkG3kUxswPhdhUtg1BK9qf/Dd7pS/mhyMZDpv7RxlYlVtXJ8SOGHbU9eXm12ah9F5qmWdnrFWfpaVh7TLpk3QgjPmD+6RFYVxFXYH9YZ6h+AHxDE+kaXFRjVBT2XOsdFP6mjduCooRJwtgnvTaik7GckAdAzrhG2lrGDfJdPNaGn0BzsEZLtpf6l2AeW7fzEGKM1cxxzwBSU6CSnA7iAaiD8fMndz5Z4VfrwvW7PuwirNBeVrmN2pJab5OKJu8X19Kc0u2NgTxSG58x4plAAakHeH3M+ZN44RVZ0dkgfTOfI/B6lr7k9Wct84GxQ17IE02b7xNQDzw95R5HNYXzW7MNyUaGd1udhjzzVCLY2MjK1jPF0ANbZqT0pbSHGc4Z35AblwTXDIvSRvN9+VnAYwx6kBjoLuuCWO6367wO3WFAN+zrCY3zTrLEgGfqfMxOai/NN4maFn2kqK5x1JagIBRsHEswj8OzJUhY8hgnmndXgV1Ef3FRxhp7nscNwX7sS/7/ze8FmhsG8yfR4lh4qp51h617B2ZGAZIe7pvtxdBIpHoeX4DAsuHQqWMOlwAAAAASUVORK5CYII=>

[image9]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAG0AAAAYCAYAAADwF3MkAAAD0ElEQVR4Xu2YWahNURjH/0IZQyTiAaHImCnixVAkkjzIVK5kSBkeDElOJDxQKFNkKBkyvJjzcPFiKnkwPPBASlchuhQyfP++tex119n7nr3PPVfde9av/p291tpnn32+b63v+9YCAoFAIFCGvBC9qUVZ6S16JKoW/XH6O4lui16Jbph2FtqIDkLf6YGo0ojtu6LO9sZyYI2oqbmeKRprrpuIdprrrDQTHRVViVp6Y0O8dlbeiXo57fGiK1CnlgUdUNOoe0XdnPZq5zoLXEVbod8f7fS3hf5msbSAOoiflq6iHdBJViu8YRl0+VOfREOdcRripOi3aKLTX1/QSDNEl0WzRAtFL0WzRYdFP0RfoLMy6c/1E33wOx1ai/bU0nZZAF2x/C3aZoDpn/7vjgjahyu6eULbhWPWnl1E+52xgkyCGoIz6RfUcduccYYbhhr2T3H665t95pOz74TTP050RHRJtBbxjpsr+ul3erQTjUTkMF778Nm0hV2x30U5c73JfPpMFe2COirJYYTPfQ/NY7Q/I0NqGD/bQ5c7kyCdc6rGHUAf0U3831ib5DS+J9s0+kVEM9+FBmCRUIhD0BAV5zBiQyPzGrkueg4tUBjGkqDjWKAkOcwPjRsQv3JTQWPQaZVO3yDoi9JIWZgjugedRTb0Us+QrtpKchpnvw0l60TTnDHCPPNQdN7rj6OQ00aIljvtydBotB3JK40UchqLDxYhlgpRX6edCRqBhn0NLUUfi/rXuKMwDKV0TF1JchrD2THo7GeYdIsDYkOjrRzj8HOY37bwHbp7fSug+ZJ508fPYX7bwtDoOq1OLEG0Ipgv/BK3EAwbT5A8c7OQ5LRRorOizaIDiAzSEVF+4PszXww3Yz4rkT/G/+pGgC2InuMWYD1Fp6Fh2mcj8h3EScUiiswXvUVUOzANtTJjRcGwswj6sG/eWFpyRqXAddo16Ao6Dn03zlLOeN9AZQeTup0BX72xNDDEXBAN8weKxHfafeiMZa5y80zZweTH3EWRwdA9EB2XFRqXBcBi6P4qSROQboX44ZGhl87jEQ8rrTTPaHRw0/hZtB5R7qKBWIQU47T6XGk2py0V7YbuHeeZvrKBs/Qj8k84mIifojinkZxRKYhzGicXiwBusK+iNAVPg4Ez1q3ILFwtt6BO476M5W4O6fcQPaC5pxTGjHMa4RGbddg5ZN8/NlhWie4gfw9CBkLP+qqgJSwdmRVuSnleyRzpHoimYQz0NKMaWsLbEvkMoneho9hvx1hNZt1PBmKwJyI0vt37UWlPRAKBQCAQCDQy/gLDKs5vhb6jkAAAAABJRU5ErkJggg==>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAXCAYAAADUUxW8AAAAhElEQVR4XmNgGAWjgETAii6ABjigGCvYAsT86IJQIAPEB4DYF00cDsqAeDcDpgEgjYeBOBhNHAMwMqAaQpQmZAAz4BwDiRphQAGI7wKxMJo4QSAPxBeBOBSItzJghgFWANOE7FSQF3IYiDDkBBAHoQsyEGlAALoAEgAZkAnEYegSIwkAAMO5EUt9FerlAAAAAElFTkSuQmCC>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA8AAAAZCAYAAADuWXTMAAAAy0lEQVR4XmNgGAWDD8QA8X8g9kWXIATEgPgKA0RzEZocQdDMANEIwuVocgTBSSgGaV6IJocX+AExDwPERpDmA1A+QSAMxPug7CAGEjWDbJsAZYNCGaT5IRBLwlXgACoMEFsUoHxTIP4GxE+AWAYqhhWwAPEsIM5AEjMG4q9QDGJjBSD/7ARiVzRxkFNBTsabUEC2zQViVjRxQSA+zQDRHI0mBwdngFgbXZAB4qIDDDgSCsgmIyA+D8TSaHIgIMEAiTaQ5plocqOALgAA2mYm4qySNNYAAAAASUVORK5CYII=>

[image12]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHsAAAAZCAYAAAAR+1EuAAAENUlEQVR4Xu2ZW6hVVRSG/7BC84aoXVDwKGaImdFNkECSQnvIoITEIgQf7EFE8kEoiCgiisDoRRBDEiSLiES0SB/EIIJ6sIgKM9Dw8hApBPWgmI2vMcfec6+ztp6z3efCdn7ww5przrXXWnOMOcaYa0uFQqFQKBQGyBhTX/Vkobe41/SZ6azp/kpfoce42XST6QkVY484N5o2mj4y/Z70i+kD0/akt3XthroWYz9numx6sdpRGBw3mJaYVskn9FvT6tRGOMLx1Dc5XdMJnRp7puln+f23VPoKHTJe7SeUMPy66eN0DDhJOESdHk7jgk6N/a78uRDRptAF5pguqr+RgttM/5pWpPZwGfs70zfqsrHHmm6VbxHq2r3OG6ZP5Dm8HUz41ca0oxNjvyCPJEQb7v1Va3cDbIStsFldu4XdptOmM6Y/Tc+nY3Q0G9erTDAdNq2vnM/BwEz4frWZxDY8Ki/6ziX9YFrYMqKeufJVDU/J732y2d1gg5qF5T+mRXKbnZLbsgWKjmfkYQlh+IOm6aZt8puMNFcLmXUiBw8UQjj74GrozZmmLofSK4BjMfdRPxAVuDfPmMO8sFsYl9o4xR+mh9LxBbkjNyBUcBGEsVea7pB70vVgbN6X98Sg7SAEM+ZKq79bPGY6Ypqa2g/KV+3fjRHOAjXHAAbeKZ8vnJLnbaQcYvu6aBhT5FsPPJ0LCAmo13lPPjHh9HWwys6b7q52dBmMh6ExeICjYWgKxBy2jDnUHc+mYxbrI1lfP/Da0bCShxOc+S/1XzU5pDkmela1o8uwUsnT5OucgUTZ+fIcPbHakUOxQcXHcqfSzL2H82vSMXnjc9PX8v3mLtOvpgdSP6timbzQIZSEh90n/10KFaBK/MJ0l7wAzCNLO26Rv+hgxMQNBJ6T8US0OjDwMfmqHmr4ikdarRIFZNXYRObIyfEeOUvzBhP/o9yQM0wn5FVcsFj+EZ/w/rJpnrxIwAm40R41i4inTd+r6f1vyou/d+SeGZ/6MDpeSt8h1X/EGC5w0J3ySdpR6YN7TL/Jix4ceaj5UpWCKlFnbJ6dDy7k5vw9AuZ3X9Zu5AJCGR51SU1j3y4fTIXaJ6/wMBReDpHfCf2z5de9JTcsuYSc0yfPG9wn9pjkFbYvgDdSVIwUd8q/gzNJa7PzRDvegSj3qfyT5VCCMdnublX9to48ji14zig8wwE2yaMYizCMzWJ8JakFvIIfi+IkNuTVjyk8BEZ6KbVflYdjPOhJubHrJiWuAxzhhOlx+XV8goxtQ6Ez+LKHcQPmuM5hBgUVOuGX1Y13EYLZ0Meq/SmNCV6T/70XY4FKFqcgWiyXb5EKo5AI4eT22PS/L//7j6iw2bRXHprZykzyy/6HUM2/Rx+aDshDEiEm98jCKIKwTlUcYGDydh7uCR/VsBKQGuJ8XRFSKBQKhUHxH1VX3Fse+dKgAAAAAElFTkSuQmCC>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGsAAAAZCAYAAAA2VdDGAAAFDElEQVR4Xu2YW+hnUxTHl1A07iYSIqGENLk1bin3NMrlQQZv02hmkkuZxtNEXiWXkkjzgMSL3IfyDw/iZZqSIkW5NAlRZMhlfay9+q3f+u0zv/+5/KeG86nV75x9zj57n/1de611fiIjIyMjIyMjI/9T9lI7NDcukn1zw4AwL6wr9D0wNw4JAxyWG5cIxrpH7SW1/dO1xUL/t9QOzhcG4AC1o3JjC+i/JbXtrfau2lNqr6qdP325HXer/Z0bl4gL1T5XOzVfaMHhah+IidZnF9QYWix3TneslWrrJ5fbsY/ac2p/5gtLxMtqj0r/Rb5RbYf0E73G0GIhzk6xZ16p9oLa6eF6a8gBSxFSavws9gJ9OVLtE7XNqb0vQ4t1l9qPajeIOdbcfEvMPEJmvZlzQsp+qT3DAPSvDbRcptsPEXtmHgu498ncmGCcOB/6MP8aq9X+yI09QagmsXg3DJrWjr4L4fwatQ/DOY5K2pmBl9yg9r1Ygtumdly4/o7at2o/qV0R2iMkRe6h/1cyvY151qdq36mdpXZ2uecHta9LW+RMMU+rwcvfItaf3bdO7Wq1b2R23g7j/Zobe1IT6xSxBfe5sUNYO85Z2+smt86IhSM/JuZYOOrt0lBY3az2mdpJ5fx9tYfLMR2uVztGbNDnS3uESSKOh0iKg7/ULhVb3AfFBPhF7BmvlPv8mVQ+kVXFatyk9ng5xsEoeD5We6Ac10Q+QcyRhqQm1ptqJ5bj09R+E1u7y8Qc/e1yDbJYDhGjKUL8CxXTMzIJSbz05nLMglNckPQQwEV0EIjd5JP0NhaHRSI8USzwHPqTPxAJmPCXMjtpFpzdkDlWTFh+Ya3YXDeKVY48n3lmfJx58N2zy4UKZLFYo7hzcOAFsdzETmGeFExOk1hz4UV+FxOCrRvj/1ViIjIQcf+C0u64d8fcw0TxomVqx6utEVtQ7mObO2eIhYu8s7iXnZg5We3Wcsx4T8tkTjgLz6vlQBcr540M89sqtsDzyGLxrp6ngBzEboeD1C6S6bDWWSwGulNtu1hpTlhBMIcFdg+OIAqxOIcYRGeykS/UPpLJvxF44otioTEL0yRWxMMqz+BZu8LFqgkZYXEvl/n3QRYrgtgLYpGliU5i4a2XhHP+oUAAhHDeECsricNMBHHBF+y9cg6EEs7zRAlRscJzoXk2HndtuIZzsKMzXq0yBw+BnqMQjG8qKq/MYsNgG2pieXXr7+brBOfJtAO2FosX5EM3l8nksPg9hVCEKsIIIcc9+WixHbNQzuFcMQFzKMkh0BebMOrnDvktxn/nNrE+zIUdFcMyjkThUvsO9HA7JFks0oc7uUciB2dkvitDW2exPOHDOWIVTMRDIAI8G9rxoofEymaOqXooz+NEgXFYLBbNIVRSTlNIkG/YMQ4vfG84d7aIPfsOsXF2ykSs12U29DqIP/Q/L1ksqtfXxNaS/yOJJEA02CRWlsdw3Vosh+1LZ9/GGb4B+Ccg75aMx+qcw6CW3GnjubWPaK8mM4xBH2CuzNnPazAGOxGnHJIsFuQ14nrTmnUWqwssFPkuluweq3N114UdYjmoL4RHnlUr6ftQE6sNu1Wsi8VCC983eBTb/ZHS1hSO2nC/zObOtniY5jsvls1DsEeJhdeTP/jngo/UJ8S+2Pn7pxZK20J4QyyKiq5Q7OBMK/KFAdijxNpdEFpJzl2olf9DQS6KH8Ftof99uXHkP8A/pF7sHgRxR1QAAAAASUVORK5CYII=>

[image14]: <data:image/png;base64,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>

[image15]: <data:image/png;base64,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>

[image16]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEQAAAAZCAYAAACIA4ibAAACw0lEQVR4Xu2XT6hPQRTHj1Dkv6cQEoWUUoQs9Eo2FigsFElRqFdWWFla6K1lQ2JlJZJIFr+sFBsLrNRjQRJWlOTP9/vmHr+Zc2d+9zf359Gt+6lv73fPnDt3zpk5M/NEWlpaWlomhFnWUEGuf+O4Bc20xh7k+v9tpkGroA3QkGnrB77H96faBiUV4CRovTVK2v9fwCA+Qm+gT9AvaDjwSLMIugldg26L62ck8ChIBbgV+gZNNvaU/0TDCToDzS6eOa6j0A9onzolmAM9hJ54Nr7z3Xv+QyrAs+JmwJLytyyFllnjAKyF3oubaYVJ4hifSe/yOSDO76BnY+ndhVZ4tnFiAS6BxqCXxk5i/ik4YC7TV9BhaHrYnAUT8g7abewMlNpp7Mpi6DX0Bdpo2jjpl40tCJBZ1g/42lW0k5yEKBzURXF122smq+CsWjg+9suExWASmIxUQrhKgn79AFmXHPwFcR86DS2UcEeukxCF9c9lf0UiS7UGHAfHeQmaYtqUqoR0xMRjA9Ta+gpt8uyK9c+FyWVNj0EPxJVVXQ6J2yy5aaYYOCErxdXqc2iBZ1esf124GrdDT4u/9jSrYjP0GZpvGwwDJ+S8lHdkH+tfBwa/R1zSt0jeKlkOvRB3BGsS2QcPghhVmyrvJQE2wI6EL+8VNwjF+ufCu8Nb6Dq0xrT1A8vsiHSTyLFwTDZYZYa4svoJ7TBtPGGOG1spQJYLLzDziuc7Ep4M1r9f2Ac369Hidx24VxwTN+uqbeLKjr/JMPQYOindpI1IedXrXrnOs41jA+QRdkPccmR9slZ9rH8VPE2uilsVp0xbDkzGPSlfCaiOdMfE1UDbB2h1YeMlkXeqR8UzYZmxEkrlGgtwrpSPWyXmH+MEdF8iH/yPMB6ukv3S4xbdb4BKrn/jyA0w179x5AaY6984zkn8f4QUuf4tTeQ3jeiPD14rpQAAAAAASUVORK5CYII=>

[image17]: <data:image/png;base64,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>

[image18]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAmwAAAAyCAYAAADhjoeLAAAFW0lEQVR4Xu3dW6hmYxgH8FcOkXNEThmKUqQcc7iYck4kp4hy4UIxuSCUCyYlhyuR3DgMhUIhh4SLyY0LIuVwwwWJKKkJkeP79641e82yZ/a3D/PtPfr96ml/37u+b+/9rabm3/O8a+1SAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAJvBqrZ9q3Vtr19GxhTij1qVz1EUbXw0AwGZdUuu1wfPbam0YPF+MfWt9Utr3HEogfKzWz6N1AABGDqn1eq1Vg7WEq98Gzxfj+NJC2enjA6WtfTpeXCYJkM+MFwEAVoI3ax0+Wvum1iOjtYXYrtYTtf6utUO3tluta7vHCXMrJSTl93ppvAgAbDv2KS1k3F9ayPg/eb7WzqV9xtW1Dq71Xvd1sfYu7XslsPXSVcvPjIxLV8r5XExgSzA9u7Q9eQDAMniw1i+17q51c61fa+3YHTutzHSOtlUZf66u9WdpwSqVMelS6Mehvw/W1tW6ffB8pVhIYNu+1pW1vq/1VVcAwBQliGUsuGa0ng7RC7V2qXXu6Ng0JFgcMGGl87Ml6XAdNF6sfqh11Hixk899Vpn7e0c/Dn2ntO5TupRfl6Xp3vUm+T0mMd/Alp+bz/ZA9xgAWAanlLbx/rDRerpGueoxYW3P0bFtTcLnbB3CBJHzxoudtaUdz/mZS85TXnvTYC1Xo2YEuxQ+LpuOWyeVoJrbiQxvL3J1rQ9Ga6ljuveMHV3rj9K6hXO9FgDYSt4us4eBdK6ynu7RcliqDluC2lPjxWr3MlmHbRI5TwltCUi9ScLaVeW/75vNhbW+GC8u0Hw7bBklPzleBACma33ZfGDLnqUjxgemIGFnXZnZLzVXHfnvu2a3f633x4uldc5eKS2YLUY/Msz4eLYu3pZk3+CzZe73ZV9hvv9SWEhgu3O8CABM18mlbZjPxvLeQ7Xe7dYzGr2mtFti3Fja+PTW0sakeU0vN6U9tHt8T2nHE/rWlzYqPLPWl916unrTkp/9bdl0rJuuYcLoYuXzXVDrr1pXdM+H53EoATFdvRNrHdutpWuW55ELPXKuc25yr7QEtAS1+LzM3N8tnyPnv+8qzvfq0/kGtlx48mOtk7rnCbiXzRwGAKYl+7g+LO2O/NkvdXlpwSP/UWf9hNL2LWV8uL60//QT4BLAIvvfssk+geXU0kaJq0oLE+mA5WvCR/9XBjIKnJZ0sPL5cs+1jPYSVh4uc48h55JzkM7auMZ7AXsJdneUFtb6sDUch17cPe7/UkLCXEah/eP+oom1tY4rLRzfUNrvMR/zDWyRCw5yBfHLtb6rdd+mhwGAacnoMIFrr8FaRpNZ62V0lzFeDPdVJRCl85YN6X0nJhI+3iitK5Ow1t/mYrg5f2vLDXMTdvo9cfttenhqcsVoH+r6wPb04HGkC5dN/pGA2e+v68et6bylA5fznAB4YHd8PhYS2KL/t9Df6gUAWKEylutDxGelXUGa8JAO2vBPL91Va6fSwkXfMUoHLu8/p0z3xqvjv+25HB6t9VH3eE33Necx5yM38l3breV3TTBLKOqDcUJSxskJuQl3w4tA0gVNRxMAYKPryswILh2zjMoSLhIksgcro84EjT2612TMlyCXvW/5O57Z5J+x4LS6NAk//d6v5XR+rRdLO18ZO0fOY/b6PV5m9v5lXJouZF7bj0Pzurym38+W1+ZcX1/auHdLV8gCALCEcrPdDaVdVPBWEcQAAFacdNTStXyu1i2jYwAArBC54GOSG+4CAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAALId/AGpV0Dw4tMtYAAAAAElFTkSuQmCC>

[image19]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAgAAAAYCAYAAADH2bwQAAAAaUlEQVR4XmNgGAUDABiB2ByIVwDxMyB+DcTaMEl+IP4LxMEwAXRQDsTrgZgVXQIEeID4ABD/R8OqMAWSQPwQiJVgAuiAE4h3ALEpugQycAXiWQyobgD5CAVcB+I7QDwXiE8DsTWq9CAGALa9ENcXiAQwAAAAAElFTkSuQmCC>

[image20]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFAAAAAZCAYAAACmRqkJAAADF0lEQVR4Xu2YTahNURiGP6EI+f+L0mXkpyRhwoiBEgMTQiYGDIwoYqBrYG6glJQMMCAUSjG4MqAMUMpIXfKTdFOKAfl5X2sve+33rnWO87Pb59R+6u2e/X33nLPeb6/1rbWPWU1NTU1NTQ8wBRqrwYAJGugjxmugDC5D4zQItkPPNRgwEVqswR7kEXQYGqOJbsDCbdYgWAS9hPZowtxd3Qg9hYaKqZ5kA/QGWquJbrAUmisx3qnT0GNoquQOQL+hL9nfoUK2NWZByzRYApwkV8yNdXIx1TkHNQBWQJ8tnuMAOAO3WucF5Gdc1GBJcJV9z/5GYaOfY/lmoNcx1kPXNWiuKA/NbS4peqWA9Bl61GsPV9UlaFjif2HiHfQeGoH2Zq+pZ8H/hfADz1h8ln2AzmtQqLqAMyz3Tc9bLPdNz+zhylHohwbZo3aYK4iv8j1oNnTWnMkYC6AH0IAmzH0Jv6wRVRaQnu9Y7puef1num+OKjd+PuQCbut+e/Ydtg+ZDry3yhoydlj6+8D27NShUWUB6Pmm5b3rmWLxvvqY/ZZO5Qv+Da31fcD0demLubMYPX5lJYZ+4YemGygHQXCNaKeA0c8ZUXHJXI/FmvZuelwTX9My2E/r2xQ1ZDX3VYMh+S8+4kMFMKbpdwBTtzkCF4ziuwQhroG8a5GzisYJL8ZoVpyjju4Jrz11zdyMFB3RIg0KVBaRnnl29b3rm8vTQ88zg2jOqB3Kqv8gS3BSGobdBfh10M7j23DL3GJaC0/yUBoUqC0jPfpXQNz0vDPL0HDsws68XCujXNNc8G+tPyws4z1yheNYLYW9otkG8MjebYxsM4Z33TyR8zmyXdgtIz58s9x0WkL7Vs4eTYkSDLAinq2+abL6NmjCLF2uwIdzBeDPCZVEG7RbQe/a+vedGvvnIyuLFzr3/DZctZ2UzfGvgQbtZsTuBD/knNFgSLBxn6oAmWoHPuLc1mIC/wnyElmuiD+GE4M9y/EmrIwYtfkKPwT53DrqgiT7kGHTfRv+y1BI8eB6x9MaQYhK0SoN9BA/X3Fhqus0f8cOb26P9/eIAAAAASUVORK5CYII=>

[image21]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAaCAYAAABhJqYYAAAAs0lEQVR4XmNgGAUjGAgAMQ8SnxWImZH4cKAGxE+A+D0QdwKxORBfA+ILQCyPpI6hDohjoGxTIP4GxPOBmA+I/wGxB1SOgQOIU4FYGMpPB+L/QBwN5esDMSOUjQJAgiATPzFAFOEFgkB8GopBbKwAFAIgZxgD8VcGiOkwqyOgcmAAU7ANiA8xoLqXH4j9oGy4wE4g3gLEuUBcCsRvgXgpEF9lwOI5UMCLIfFBkSPJAAmpkQMAx5QaPmOGGsEAAAAASUVORK5CYII=>

[image22]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEAAAAAWCAYAAABwvpo0AAADoklEQVR4Xu2XW4iNURTHl1Dkfr8nTEqUIokURUrhAeValAcelCLE00geFIV4oIQHuRYPhCinlITwQHmRQy5FKEUkl/Wz9p5vf2u+YzBmijn/+jdnr7Vv67q/Eamiiiqq+H/QVtld2corWgK6KE8r53rF72CEcp/yrvJJ+HtAuT9wubJH3eymxW2xO7xRXna6IpxXbpS/FP0ZyrJygJPXKJ8rvzl5UwBDDoqdNdvpPEYqF3hhY7BVeUrZxsk7Ka9K8zigp/K+8rVYZlYCjtqj7OMVf4oOYim3wSsUQ5UvpHkcME75QVlSdsyrciBLy17YGEQjJ3mFYomY8Z+8IoCLVrosvSPV0bGJWqX5K8TOIhsj2ontk9Y55dFQQFjX+ifjHDiQDQcp+ymniNUX0TihHFg304Ah25UzkzENsyxZD2F9Z7FovlXekMyIZVJsQFksEASEDo+hcyTLCkCJUqqPwzgFa84p54uddUT5VXlJ2UvszHpZTjRKYsrY+XkFOGCpFHfYtWLzU910scPxNDwpWU1/kfxTNUuKHfBZbI/+ymNBdlhs7tEwjve9GcYpVio3S3YvHBAbKoHld73GSbOh6bx3crzJxX03pvu+EluTYo1k3u2qXC9WUhh1Qdk+6EDMOA9kGMb82AS5+FSxPgWiA6AHT/awZMxeMaNwyujwN4fFYgcTKQ/kRCBFbZATqYiYlr6HxJpO0y4a4B1O1jAXPlPuyqvrQGCuS7EDPDgjZmUhuol5iUNxRAq8hnxTIouXp66mJfIYaRwxUTk+yMuB6bdFrdi+q5STlWODnP3SZ5j77Ai/qd+F4Xe8w8MwToGhNFl6Evv4ey4S91HH4XjpnVh6pGBhGj02ZDEeZU28OCm1RWwuc6jVeChOSY2KPSGm5VnlqKDD0ZRRBOfGMc6ozVQ/spI9PO6J3YMeg9OfSr6BnxH3Aq0TW8BC3+m9A7hob7FGg2fpDTwrq5Ufw1z6A4eQpgAZZRAxXKx/lMQuslfMOUQOx6YlhPEYwl40VPZOdTjXg8CwP8HknqkD+kqyPxOIeqy5yCFxgljTQnZN7DXgaxCQXtvEmuAd5W7lGOUj5S2xZysizRSAsXzBvVRelMxRpC0pnabnYOUD5RWxckmb1wQp/i45JHYnMgsSWHhcintcg6ATzwuscToimKYTjsmll9hr4IEhGOr/wSqaS8YVyWMj9M0t3ZvfZCh7wIofQf8qMHKnFDxrLQmUTXxxfhnfAd5Xzh3428j5AAAAAElFTkSuQmCC>

[image23]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAG4AAAAWCAYAAAAhKqlXAAAFL0lEQVR4Xu2Ya6hlYxjH/zJC7mNyL0MohZnJZVJKyjWRXHKbJF8ImZr5oJBIcouET27TfEC5y60kjnwg5FJESR0SISlF5Pr8POs5+13PfvfZe8+cdfJh/evf2eu9r+fyf591pB49evTo0aNHj8mws3Gb3Njj/4/njDvlxq6wxHj/FLzEpy04OMdVxmeNXzXkd+x7u3G1ccuY0DHY/2vjn8ZTUl8NZxqX58YucanxgNT2rfEf4+lF21bGZ4z3FG1dYDvjq8arU/sWxpvk53o79XWBw42/GGeM27e7WuBcd2txzjQH9BhnZGAcnLd/at8od3SXYE/2PiZ3yKOas2HQrsF7ste4QD3E+JPxytzRJQ42Pp8b5Qd+Ue2LFil7zHh80dYFkCX23zt3GG6W9/2cOzrAIxpWnRpQhh/ltlw0cF/dkNp2kB/4mtSOXDyh+gGppnaXy+nmIpxDoJTY1fhO0/d46gPcfYwZdQfupnYfZ85tJT5RW3WQRNYvgxmbzBjflNuthpgXcpufFwwXGmdVj/iME+QyAXDarcbPBt1TI2SSgmBP44HGM4yXG783nq9hQ6+UFxJRzR0lP1PckbS/YDxN7vT3jI82fRjwfbmTMhhLEIFTjfvJ16GdtQBy/oeG7+PAy8alze8jjb8ZzzIeYfxB/o6TAoczf23uAHRuMD6p4YjPoJ9xbzXPh8oN9tHciOmBLGEYXiqqyTDWXsW4wD7GT43fFG3byg0Wks5fJD7uLAqfcHJkzJfNc4B3+1semOfI77koVn43Ht2Mi2Ag2DPI5rLow3Ez8j1xNPOm+XTA4ShNVdWWyaNvXe6oIF6aA2AcpGJzJQADsR7BU+Jc4ytqrx3VHOPLAgLJ/kIDxeDOhAQZzji5aQeR4TnjmPurPACukxuLTCfDDpLvDcJxkYElynEA50YG72g8qegbB4LgY81TX0RU1Sq6jLI8D96mERExAXYxvitfJ1eucS7+BpAuvrNwRvlCIV9ZMXDOrNpXQGR4DhTWo/0v42vGC9rdczhPox1XIpRspOHHIPYhsYYQ0seAMlJq2EMePUQRY4lGIpO5o/R+HFiL+TgPJ5ZgL5yENAYi2svqN94Bx5GdF8mlE+SzheORWrJ0jXFr+VqsGcEbAUUGAbI3CrQ4Q02hsAsFEIhgKgubw4rf47BRvk8VROKs5hlQ4EH5OO4LPpgB31g5+qcBEcmarF0iDMk9FJc5Z2Uf9uOlAtwp3HdIJcaiCmY+DsVwpZLEnRfyda/c2AQHDsWZgD3Zm2ec+LTc6SCUINYocZmG77QAqsT9XT5fbzy2aCsRV8gQeDkuYQzB5ZsrtwyM+6FxRfNM5YSkcJhNkUoMRjXK4a5Qe//sOMZi5ND9Gblxlsv/e8EatN0llxiA0ZHKUmrulI8la7ibVzXtERAhtXFnsgd37R0aKFL01Yo5Auo+eZB9oIHhmXux8eHmGWBHvk05f61goUhCtsF/e0cxwqI11qolsK+8rMbYD8k3pVCI7JsGkb2ZJcgUDn6t8RYN/tvDp8Dn8u8oAuk4443y7GJMGIHM2KD2FYCxqF5fV7sSRvbK/Zmz3viSXGFKucZZVKw5KABnfqrpoyJkDRQA2X1AbVsRFKxDENQ+ETgDn0TMfyP1bRLQcDbKWbbaePYELAuFcThRPofoi3sLkJ35Q5pzlc/8zmcEZDPnL+8exsW3Vwmyq7YGWU1Q1a6IvDbP81XdZG7NcQH64t7ssQCgsPkuN04JsiqkvcciIYqNWkZOCuR0vmycw78A9ybZJ91pLQAAAABJRU5ErkJggg==>

[image24]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFYAAAAWCAYAAABaDmubAAAES0lEQVR4Xu2YTajPaRTHj4wi42UiMqTuhNJoKIymyGYmLFiwITayME1KzTTeFmJhaZKZZqFBFpoalGIaC4urqfG2YEFK1J1JJEmmRiTG+TjPub/ze+7zuy/duJf+3/rW/T3nPM9znvOcl+d/RVpooYUWWmih//gwH2ih/5inPJcPvk3MVP6svKD8J/Gs8kDgBuVon/AOAKfeVC7IBW8Q4/IBxzJlh3JyNg4+Vf6tXJQLBiG+FguOtlwwUNijPK78IBckbFKeUY7IBYMMN5Q/KYfkgoHASLH035oLAuYqH4qVjsGMF8ov88GBwifKe8qFuSAAxz6Xss5Q5QTl2FwQ4DpNGC7N84k+alhPXR69O8opuSAgX4c5Pa3bE1izmCGUgf+luQyAjcr/xBwMWAhH75aqPDC2P/3tYM5RqZrfk/SNLnyq3By+sSPu86NylXKU8k/lxDQO0Pld7FIAAXKkEtfAGn+kv+eL2cHejD8Q6yGTkrwnYCelMdq+vaYhdlvtYgdqAhMPK68rx6cxmsRvymGuJHYxu8I3KUmJGZO+2Yt99qbvFdJ1jUdS34e6z8XNSjJfC3DZsXzhaIIkB5mCU6elb3dsu1Q28SqKa3cHLoOSE23HvhqomdROoqQJvBQ6pGoKbWIp52WBiJku9jTzWyc9LimXpm/HV2KO4rDXpGs95JBcoqcWrxWAA+Plc4k4Pc7HsaU+MUO5Xqo114qt5ZewRPr2nMTul1Lf2+3shG9ClDRhtZgOzy7gc3AuT5vbYum9PMmBz/HIy9EkZ4z1I4gkIoqIdfhlx+fhF1J2bIRnX+6YvsD9FW2vZcpHystSPgzAiC1icqLRkUdPCdS67nRKcmok9mAXmeRR8K2Y7o70DUo2ELG/ZGOAc5BBNEeyjN4Qa/NnYpnUW7AvZcjhzb8TGEIJ+Fc5OwoSdovdLDfMk8zh0VbCNrEXQOngYI6YDk0pl6+TyjFEgBvva3lG4BAcg4MiKEOltzj9gPntUq0VL4mgWRm+d4plyOIwFhFtAdhdO8v3aeCqVD/JuN2PxQ71WLlGzFERXh9jsUcHXX5OAhrFXak3JnR4wKNDhNAAAHvSyEh1Ds76OI5aDvwikaH7XfrOyxeX7xEf4dlBj7iS/nbHst4hqdtJoKHT1NCw20sO87H7tWOJTp9cIhMvSj1Kc9AQbikPKk+KpcK+mobdOBdARKBzX6omgUHfKI+J/bOESKOzss55Med5s6HZcXieNzgOh2Ln4SSPKP2IIf3pByfEOjpr8ypgb9bLz/mrWKbSO0pPMOxmH7cdu/+qafQTRDkbE2F5VDuQoYOuOyoCWfxh0N0PDcZ5HvFWxrFEco5nUq9/DspHdBLr8N3044Co57JLjgW+ntvadP5BC6IGJ/IgB0Q/qfd5p0Yd/KMIeV+aUQ4C4AcpX9x7g1NiKTxVLMV53lFimoBTeMm0S7k+9gaUi9PSHM1FvAKZE+vMG0t9mAAAAABJRU5ErkJggg==>

[image25]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACMAAAAWCAYAAABKbiVHAAABC0lEQVR4XmNgGAWjYJgCDiB+BMSvgPg2EIujStMXsAJxJxD/B+I1QMyCKk1/MB+IfwOxDbrEQIDTQPwAiKXRxOkGQNEjAsTMQPwViLcyQNIPXYEEEK8C4tdAfI4BkmhB6aUcWRE9gBgQPwNiFSQxUYYBiiKQ7yehiRkzEI4iHiCWJBKDigZQEsALQOnjKhC7oIlHMxCOoiYGSFlEDAbZoQ/RhhuAQgCUUGXQxOcwYDqQ5gDk2k9oYrZA/JMBEkWg0ElHlaYd4ATiHUAsCOWDEjEoSEE5iR+IVwOxIlSOLkATiA8D8UYgPsUACa1ZQHwMiEuBmBGhlD4AlL1BGFTYgQDIAQII6VEwCsAAAAmGLpAfqu79AAAAAElFTkSuQmCC>

[image26]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFMAAAAWCAYAAAC8J6DfAAAEJklEQVR4Xu2YW8hMURTHl1wi90suUUq5EyVK4Yki8cADIon0SVIoXhSSB5cUCSlJQp888CDEg+KBFJFLkfpIPEgiFHJZv2+d9c2ePXNmzjDj6fzr38xZe+919l573WZEcuTIkSNHjtrRWdktFuaoHROVV5VD44G/QUflsYzcquxjy+qOV8o3yi/KqdFYo4ABHyhnxQMJpkupDUYmY+OVxwN5K7ZIqYF+K+8qeweypWVk9cRk5VfleWWHaKxR4PLGxcIIXZRXxGzCp6OdcrNyoAuYyOZDMImFByP5POUlsfzSCDSJvZfL/R/g7Gcl28UtFtvbh0C2UMy52sCtnA4FYp7HQjwxxAIpNXA9wT5+KKfFAw0CZ4/PmIYByqdidgEzlbckyrMrlGtCgWKS8r1ydCTfKOY9Djy4r9TuqcwfFAsVj5UtysHJc3sx/XymgUPG72d+P7FaAPjkOdbDWSZEskrAkTDmfOUz5ZTi4VJgoBNS3QMJEdx8iPK1sjkYYy0eFgK938VyDIfigL+Uc4I5HuLMXa4cpXykfCkF47Nun5j+VYlsuPKJmGEIxx1iF8I6CgP1gDO5VwHaoBvJZ1Z47syc07lBPKSa++PmKJwtZhQ3PimCPPIieXZg+CNS2ATe/00KVRs5eqiqa5WblCvFDHBb2TOZx2Ug2ylmdIAxH4pF0hkx3XwnuvorRyjfib3PgUezR9eRBezhuljerFa0WsFGaE3iEI+BR7kXYwSMC/wQYVHzfBNuAA/Dk/wwXOJH5UXlhkSOJ8wQC3UHRglTEK3LPTEjs2a9mLeR390TkfMujOrA0/HcrMCQ55QHxPRuLxpNgVfULO0PodQixe0SHh1XZJdhnDTQFjHnp1gDPbd4uA3MIV3Qk8L9yjFS6mFECpechlqMycUfFYssvrMHnAMnSYWHeJhbKmGX2FzPe92VN8VyKLmUVgqcTOalAUNQyb2Kex7Gw7gA8qfnNvRUS0EeHYRkGjwddY0HIrC3a1JIM8B7zoptlYc4G8kCjMR81gE/hPei6xK5Gz3GarHw80v0Ku560IFufmX4pssZkwO7LkC1ZR7vTQO62ScOkAb0LpLSHzRhz1k2d3Lz28QmUUGzgFAmlChC4JTYeoyMR/mLxorlujAUe4jlIG4cI3ySgsGGKd+Kzd8rlv8chBfrvO1Bz+FE5t6DEcM8ngZSAVEQA90UNcKa88QpxFtHxvaEA17VGIiJt+A1aWDzl8UKR7NYxSa3fBYLoXATpAJSAK3KHbEL876PdBB6LkbdLab7kBQMB/hT4rnyvpgu8uYSKejqpLwgxf1qGvDg2ODsM7YD/bUD/fE46aRausgEDEa19T7Qn8MK7KBNYV6vSI6xyl0aOmKvABjOdZUDUZalf8TYlVJBjhpBoSMH5qgDlon9BYen/xP+AI5+5MejmRmaAAAAAElFTkSuQmCC>

[image27]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAHIAAAAWCAYAAAAcuMgxAAAFLklEQVR4Xu2ZW8hlYxjH/zKKnA8xor4hNySHHKapcT5FccEFRdPcyDS5Mg13Ghdu5mKIiULJ1RCFkEPKdqiZcEGRIjXkUCSlKGfPb579fPtdz7xrr/XtvfsM7V897db7vt+71vuc1/qkOXPmzJkzZ86/zSFDmbOPc5zJAXmw4E2ThTxYYX+TY02OT+P7pev/KpeZnJAHZ82lJk+YPJLkoXJRAgVvNHnZ5GuTc5vTe2BsdR5MYMBXTf4cylcm75qcJr/HptHSZeNL+XP8YXJ1mpuUv03uyINL4EKT5+TPFrKrsaLgepNvTU7OE4kVJjtMfjL50ORHk/MbK6QN8pvVwEDr5Yb7vDm1yC3yw/+QJ5aBc0x+Nhlo+rLAWe+Xn4VgmZbb5HsdmCdKHjB5SR2L5Clit9qNQLr9xGR7nhhClPEwn6o97Z4oj4pBGl8OQln35okJuMDkfc3GkATQM/K9WjnS5D2Tu/JEhbUmv8uNXuM6ebRdnieGMPer/JBtHGrytty5lpvH5cqaNq0SzejoRvl+g+HYpBxj8rHJX3mi5Ex5qsRIXdysdo8llaAIoomoytDQ8LdE67hGBkPSKOEUNcgaNEY5e7BnVhYZIo9laNh4Nn5RVp8S0wXl5Sn5npwZx+RckxIBtDuNLxLK52aEbxs0JqeY7DT5xeQq+eEZDzg8SqilkcPlBXqgbsXW4O+flt83nGCVyWvy/W4yeVC+P3WbpikcYb38fKTNkrPkTQR7A81Zm5MuhYfVzG7sOY1zlGmVviQa0gaRVsfm3iFEwRfy+oinZ6JRqCniVHnzUpvrAq/mwXNawaCMXSM3Ml5LRJG+byjWXSs/X6ncBXmdxjmDg+T7tZWFvrxlcnRxjeOjF/QzCdGXEJGcBTvkV7VF5bOoi/PkD/W6ycFpDmKvWq1FOSiJ7nipRBf7ShrHkIzfanKnyRHyc7AOowQ4TxmRZTdZgnO2lYW+YMAr0hg6mcZBQnc4KbWySnRpLOoi6mNbE7JG3sjUDBlRwe84SNekEX4hUnItNZJN8p458ki7AzUj4iS5wXKEE9F9OvdxcG+eoSZdZ28j9kQv1fIXnVBNSTU4JBFJZNaIiHwsT2hkkNvzROIdk7OL69iTlJ7TCXvt0OhwkYLKryhb5OeL+7JfOBXnCaIOYUyMv07NqO6C9E9zQ5OTGWhvB1sK1Ndxel/shPrmb2pjW32EqKFtnsMhaULK+lGCscvaBmEc6jgRGCxo73dRzpPvjaNGo8H+p2uUqsqmjFr5jfx+7EPNJTLvljvgRaOlVXjNiMYrM5AbMjeBV8rfM8d95gT+dmxa3Spf9JHJyjRXA68Yl3qom9TPrPQgWvHn1axD1Kwz5C16dKTlHPWsfPc8Sv5pL3894jNYzizfa9QpU2sxMmmbMzMOqzRK34eZbJN3wcBrGePMR3dbEtFLMNynum5ekO/Bb/QWoSvGKUltsD9rnlTzDWFPMIRHsqCU/Kktw5qurnOLvDulS62x2eQ3+V4YHC/FIHgz31hrcGjqMo7E6wLK5Rqll7BXziy8s34nNzzKCHj1+EweeR+YXGJyj8kbJs9qZDRSN7oiE+XUDlmH5RcvMhfXeU0YE6dDF7Xa2WajUiamT+cVDU+OjBK89mK515Neap5eA+9EOW2pqJbWiGi8F8nRHv91KT09XwPZhZRdM+QsqBlypoRXkDaoAX2LNSmQl/L/Axi/TLWzhleVWj8xUzAkzdCj8pTaN3I4PO91fdfvy9B8vah6tE/LgrxLn4h/AJu6Q2gmFZfBAAAAAElFTkSuQmCC>

[image28]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACkAAAAVCAYAAADb2McgAAACT0lEQVR4Xu2WTahNURTH/0KRb08+oshAiTJAUqKMSCQRMTGjZEqMTZSRvIlIBiiGPmLCi5KvSBEDiiJJEUVG+P/uOvuefTb3IXpvcv/1656z9jp7r7P2XutcqauuuvqvOmBem+/mvfli9piRZqaZW7sOvAjioHlptptxlX2sOWWumOdmQmUfcE011xXZI9hSPeaOYnxQxBY+UgTAtnbSfg1ikCz8wcwvBwptMH2lsdIQRbaB61wjzNDCNvkXtlyM4dPSFEWQZ8ywZOygJWZ5abSOm0+KF3hq3qoOdJG5rdgpdmyFeaAoyI9mdeWXa5Rijr5k2KIIcl0y/KXWKIqK4kIEt08xH4V3QbFDrHHPnDYTFRm/bx6bSa0nQzPM3eq3JbbhorlhxiTjHyoV0rdywFqsWGiTIlPsEH6rMp/Z5o2aQe5UvAwxtTVakVLguj8xwa7sPu0Ai5TapuacBPHCTK/uEZnm+ROK7JP1W5VtR+bX0jH9PkgmuGwWZrbDqhfJxYLYjlTXaJkiO+xcEjWQZ3eB4lwD1w2RkSeKAuok2lKvmoV1UhHk3syGmIf5lmY2fEq/V6rXJQn4f9bPZ7Qt2g8OW9VsC1QZRUCjLzXPvDNnq3uyxhn8ag4lJ0UQfKXKhXnBtYqzfUnxATmv+lhQXOeSM5qj+mtCwEfNVUUb2J35laKdPFO0IFoPWVipZp/kiJCAsnfygtfMQ0WHQFT0TUW7Yt7Nlb0tJpll1puNij8R/TXbJHymmfHlQCXGyywizifP5ecUpY/C8MLe1T/pB3Eec5KmsTMPAAAAAElFTkSuQmCC>

[image29]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAF0AAAAWCAYAAACi7pBsAAAEZElEQVR4Xu2XS8iVVRSG36igzKy8VKZgiQiikigaZIJECII6iCAiBw4SGwSCkmIDrzgwxYFUgybSKEQhwTQU0QNBRYk1KARN+guxQaQgCIVYrqe1l2effb7vvxx/fzC+F17O2fe113V/UoMGDRo0aNCgwb2Ml42fGD8u+FE+aZiwRd3n9MeRwnbjb8ZLxqXF2ECIdTeNy4sx8JV8TiVeNf5unFoODCNOGcdm7ZeMN4zXjfOy/nHGs1l7JMD5yDG6HBgAsa6l6rX3GfeXnYF9xqPGh8qBYcJ4dSoWbDT+a/zO+ETWj/AnsvZIYI1clqHiTfk69FcF7v1T2Qm4MBdHCXcLrxgfKPowcpXAyHOs6LubCG/sRemxbkU5kBCR0IXnjdfk4d4fiIKJqg6jgbC77JDnQgQmteXgDAwS4FxSDsqpapdAvsHI+GBieCPptQRnkBKZV4VYR1pGrvs7h6sjKLdy6YmBJ40/qr0hxeZKe7hncGZL9Qp6zPi5cZa8SDH/HXkkfJHaAZSyx7gsa1OM+4yTUh+YIy9sh+X7vyD3RPbamc2bLI9+fsEU43m5rnJjs471eDr9Hxj/MM5M45XGjNTSZY0M5K2/0/9RxuPyan0nQNHlRUuQkj6VO8M6+XyUuVh+PpcLrE/juUKWqLtOobjLxmmp/bDcgP/IzwNRU+LOgQ/lnhtALta9nvVFnYpUzUMhj9r/EDmHwTrERiuNzxgflYf3nWCGfM/+nmiMQS53SH5BQMSRCkNxeBUG+DO1Axgqr1MYhDPzGvKU8aI81YVXvy2flyvrEeNJdT4GSEvli+89+Vqe4SA3wG1EzqmssAmL5FZnHuTtGQL2CsKxFLgOkXP7iv7AVnUrKQyV16nn1OnRIJ6tERGknG/k++VejZzIm7+yWFtGEu2IYGRg745aGZcpDwgQyqvll0IYsFDtd2mviJSGVwwGZcjmIBW0VK9MLv6iPHdTF0olYZhQDHsxl/uhF/QTQInIwH5vGCfI5Sk/iJCD+kcdRB72Z81t1H2cBAhtDuJlwwsH4OGEYvnMGwoipeVKqkN4bJfHJKBAFJnfgTSyQ20lURc4C0bYB8jvffJiy/4UWtJUS+0CTyr9Vq4HPJ58j0FIX/PTHICTUmvi+YhTMadD6e/LBcMyT+cDCSj9qvEt+UXIpZuM5+TVvBdwkXfl585W/bMvEDm39Lwc5GA8jMsi41rjX/IzyPfxUsH7Wmor89k0h74xxr3ywnpEbUPwXDwo3/9X+Vmb5cDIvKYA99iQ2nEnooNImEUDi7NJ5OjggjQ5gOXiCXRA/tT62jg9nzRIROGsYp0Xg4iK/ao3EHLuknvo9/IonGv8xXhGnd8BF4xfyhX5g3Gb/PzTxs/SHKKZuoUz/ix/naxK81g7Jc1DHs5kL85l71xGnAp9IcOQUfdRRJ58bRDEY3oFnouH132c5EC+XEbWlDKzHx4P47vj8aINUB5pJT+XvUo5Qjd1H2tEailDgwb/U9wCKHQN7upPUO8AAAAASUVORK5CYII=>

[image30]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADAAAAAUCAYAAADLP76nAAAAiElEQVR4XmNgGAWjYBSMglEwChgYxIA4H4i50SWGEqgB4pdA3A3EwmhyQw5wAvEzIF4HxOpockMGMAOxPxBfBeLjQMyIKj10AMgjTkB8HkqD+EMSmDNAYgIUI/ZocoMaDNkYQM4DuxiGWB4YsqUQqCIDVWig+kARTW5QA1BNDKrI+NAlRgGNAQAR1hDVIjW2ZQAAAABJRU5ErkJggg==>

[image31]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAUCAYAAAD/Rn+7AAAAhUlEQVR4XmNgGAWjYBSMglEAAmJAnA/E3OgSgwnUAPFLIO4GYmE0uUEHOIH4GRCvA2J1NLlBA5iB2B+IrwLxcSBmRJUePADkUCcgPg+lQfxBCcwZICEJClF7NLkBBYM2BJHT4C6GQZYGB20uBhXUoAIbVB4qoskNKADVJKCCmg9dYhQQAAAcNRDVddfI6wAAAABJRU5ErkJggg==>

[image32]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADEAAAAUCAYAAAAk/dWZAAAAi0lEQVR4XmNgGAWjYBSMglEwCqgH1IF4IRBPRJcYCoARiI8D8VUg9gdiZlTpwQsigPgBEO8CYnNUqcEPOIE4CYjXMUCSz5AC3ECcD8RvgXg+mtyQAKDQBzl+KhBLoskNKTDkYwIZDOk8gQ4CGCBFKqh00kOTG1IAVB84AfF5KD1k6gd8YEjX2IMaAADFJhJheoPQUQAAAABJRU5ErkJggg==>

[image33]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACgAAAAUCAYAAAD/Rn+7AAAAiElEQVR4XmNgGAWjYBSMglFAClAH4oVAPBFdYqABIxAfB+KrQOwPxMyo0gMDIoD4ARDvAmJzVKmBBZxAnATE6xggUTpoADcQ5wPxWyCejyY34AAUaiCHTQViSTS5QQMGdQgig0GbBtFBAAOkWAHlYj00uUEDQOWdExCfh9KDovzDBwZtTTJgAABKmBJh41caKgAAAABJRU5ErkJggg==>

[image34]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAADEAAAAUCAYAAAAk/dWZAAAAiElEQVR4XmNgGAWjYBSMglEwCggDMSDOB2JudImhBmqA+CUQdwOxMJrckAScQPwMiNcBsTqa3JACzEDsD8RXgfg4EDOiSg8tAPKMExCfh9Ig/pAF5gyQGAHFjD2a3KAHQzomkPPELoYhmCeGdOkEquxAlR6ovlBEkxv0AFRjgyo7PnSJUUAnAADwfRDVbhiRTwAAAABJRU5ErkJggg==>