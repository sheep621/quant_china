"""
Alpha 101 暖启动基因注入器 (Warm Start Seeder)
================================================
将 wq101_factors.py 中的经典 Alpha 公式字符串，解析并转换为
gplearn 的内部 _Program 对象，注入到遗传算法第0代种群中。

这让 GP 算法"站在巨人肩膀上"开始进化 —— 不再盲目随机搜索，
而是直接在经典的金融因子基础上进行交叉变异，极大提升寻优效率。
"""

import re
import os
import sys
import numpy as np
from typing import List, Optional

from gplearn._program import _Program
from gplearn.functions import _Function

from src.infrastructure.logger import get_system_logger

logger = get_system_logger()


def _build_function_lookup(function_set_objects: list) -> dict:
    """从 gplearn 的 _function_set 列表中建立名称到函数对象的快速索引。"""
    lookup = {}
    for fn in function_set_objects:
        if isinstance(fn, _Function):
            lookup[fn.name] = fn
    return lookup


def _tokenize(formula: str) -> List[str]:
    """
    将公式字符串切割为 token 列表。
    例: 'add(sub(close, 1.0), volume)' ->
        ['add', '(', 'sub', '(', 'close', ',', '1.0', ')', ',', 'volume', ')']
    """
    return re.findall(r'[a-zA-Z_][a-zA-Z_0-9]*|[-+]?\d+\.?\d*|\(|\)|,', formula)


def parse_formula_to_prefix(formula: str, function_lookup: dict, feature_dict: dict) -> Optional[list]:
    """
    将一个括号前缀表达式字符串解析为 gplearn _Program 内部表示的列表 (prefix list)。

    gplearn 内部用如下格式表示一个程序树:
    - 函数节点: _Function 对象
    - 变量节点: int (特征索引)
    - 常量节点: float

    '( )' 和 ',' 在前缀表达式中只是分隔符，解析时跳过即可。
    """
    tokens = _tokenize(formula)
    program_list = []

    for token in tokens:
        if token in ('(', ')', ','):
            continue

        if token in function_lookup:
            program_list.append(function_lookup[token])
        elif token in feature_dict:
            program_list.append(feature_dict[token])
        else:
            # 尝试解析为浮点数常量
            try:
                val = float(token)
                program_list.append(val)
            except ValueError:
                # 未识别的符号 — 可能是不支持的操作或特征名
                logger.debug(f"Seeder: Unknown token '{token}' in formula '{formula[:40]}...', skipping.")
                return None

    if not program_list:
        return None

    return program_list


def validate_prefix_list(program_list: list) -> bool:
    """
    校验生成的 prefix list 是否是合法的 gplearn 程序树 (栈深度检查)。
    合法性条件: 结合所有函数的 arity，最终栈剩余深度应恰好为 1。
    """
    if not program_list:
        return False
    depth = 0
    for node in reversed(program_list):
        if isinstance(node, _Function):
            depth = depth - node.arity + 1
        elif isinstance(node, (int, float)):
            depth += 1
        if depth < 0:
            return False
    return depth == 1


def build_seed_programs(
    transformer,
    feature_names: list,
    n_features: int,
    random_state: np.random.RandomState,
) -> List[_Program]:
    """
    从 `wq101_factors.WQ101_ALPHAS` 加载所有经典公式，
    批量转换为合法的 `_Program` 对象列表。

    参数:
        transformer       : 已初始化的 SymbolicTransformer 实例 (用于获取内部参数)
        feature_names     : 当前数据集的特征列名列表
        n_features        : 特征数量
        random_state      : numpy 随机状态

    返回:
        合法的 _Program 对象列表
    """
    from src.alpha_factory.wq101_factors import WQ101_ALPHAS

    function_lookup = _build_function_lookup(transformer._function_set)
    feature_dict = {name: idx for idx, name in enumerate(feature_names)}

    seeds = []
    fail_count = 0

    for alpha in WQ101_ALPHAS:
        formula = alpha.get('formula', '')
        name = alpha.get('name', '?')

        prefix_list = parse_formula_to_prefix(formula, function_lookup, feature_dict)
        if prefix_list is None:
            fail_count += 1
            continue

        if not validate_prefix_list(prefix_list):
            logger.debug(f"Seeder: Invalid tree structure for '{name}', skipping.")
            fail_count += 1
            continue

        try:
            program = _Program(
                function_set=transformer._function_set,
                arities=transformer._arities,
                init_depth=transformer.init_depth,
                init_method=transformer.init_method,
                n_features=n_features,
                const_range=transformer.const_range,
                metric=transformer.metric,
                p_point_replace=transformer.p_point_replace,
                parsimony_coefficient=transformer.parsimony_coefficient,
                random_state=random_state,
                transformer=getattr(transformer, 'transformer', None),
                feature_names=feature_names,
                program=prefix_list
            )
            seeds.append(program)
        except Exception as e:
            logger.debug(f"Seeder: Failed to build Program for '{name}': {e}")
            fail_count += 1

    logger.info(f"Seeder: Successfully built {len(seeds)} seed Programs from {len(WQ101_ALPHAS)} Alpha101 formulas ({fail_count} skipped).")
    return seeds


def inject_seeds_into_population(transformer, seeds: List[_Program], population_ratio: float = 0.3):
    """
    将种子 Program 注入到已初始化的种群的第 0 代中。
    
    gplearn 的 _programs[0] 是第 0 代的种群列表。
    我们按比例将种子替换掉其中一部分随机生成的个体。

    参数:
        transformer      : 已调用 fit() 的 SymbolicTransformer
        seeds            : 要注入的 _Program 对象列表
        population_ratio : 注入种子占总种群的比例 (最高不超过 0.5 防止多样性丧失)
    """
    if not hasattr(transformer, '_programs') or not transformer._programs:
        logger.warning("Seeder: Cannot inject - transformer not yet fitted (_programs not initialized).")
        return

    population = transformer._programs[0]  # 第 0 代列表
    pop_size = len(population)
    n_inject = min(len(seeds), int(pop_size * min(population_ratio, 0.5)))

    if n_inject == 0:
        logger.warning("Seeder: No seeds available to inject.")
        return
    
    # 随机选择种子 (打乱后取前 n_inject 个)
    rng = np.random.RandomState(42)
    rng.shuffle(seeds)
    chosen_seeds = seeds[:n_inject]

    # 替换种群头部个体
    for i, seed in enumerate(chosen_seeds):
        population[i] = seed

    logger.info(f"Seeder: Injected {n_inject} Alpha101 seeds into Generation 0 (pop_size={pop_size}, ratio={n_inject/pop_size:.1%}).")
