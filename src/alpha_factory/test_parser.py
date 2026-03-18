import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

import numpy as np
from gplearn.genetic import SymbolicTransformer
from gplearn._program import _Program
from src.alpha_factory.operators import custom_operations
from src.alpha_factory.wq101_factors import WQ101_ALPHAS
import re

def create_program_from_string(formula_str, transformer, X_train):
    """
    Parses a string like 'add(X0, mul(X1, X2))' into a gplearn _Program.
    This requires mapping function names to transformer.function_set and variables to indices.
    """
    # 1. Tokenize
    # Replace feature names with X0, X1 etc based on feature_names if available, or just index
    # We'll just define a mock grammar parser
    tokens = re.findall(r'[a-zA-Z_0-9]+|\(|\)|,', formula_str)
    
    program_list = []
    
    # Flat representation for gplearn is prefix notation: [add, X0, mul, X1, X2]
    # We parse the tokens into this list by ignoring commas and parens, just preserving order
    # since formulas are already written in valid prefix if we strip parens.
    # WAIT, 'add(X0, X1)' -> tokens: ['add', '(', 'X0', ',', 'X1', ')']
    # Prefix list should be: [add_func, 0, 1]
    
    function_dict = {f.name: f for f in transformer._function_set}
    
    # Mock feature names for testing
    feature_names = ['close', 'open', 'high', 'low', 'volume', 'amount', 'vwap', 'returns']
    feature_dict = {name: i for i, name in enumerate(feature_names)}
    
    for token in tokens:
        if token in ['(', ')', ',']:
            continue
            
        if token in function_dict:
            program_list.append(function_dict[token])
        elif token in feature_dict:
            program_list.append(feature_dict[token])
        else:
            try:
                # It might be a constant float
                val = float(token)
                program_list.append(val)
            except ValueError:
                print(f"Unknown token: {token}")
                return None
                
    # Now create the _Program
    # We need to pass the proper arguments: function_set, arities, init_depth, etc.
    program = _Program(
        function_set=transformer._function_set,
        arities=transformer._arities,
        init_depth=transformer.init_depth,
        init_method=transformer.init_method,
        n_features=X_train.shape[1],
        const_range=transformer.const_range,
        metric=transformer.metric,
        p_point_replace=transformer.p_point_replace,
        parsimony_coefficient=transformer.parsimony_coefficient,
        random_state=transformer.random_state, # Use GP's random state
        program=program_list # inject our list!
    )
    
    return program

if __name__ == "__main__":
    function_set = ['add', 'sub', 'mul', 'neg', 'abs'] + custom_operations
    X = np.random.rand(10, 8)
    y = np.random.rand(10)
    
    transformer = SymbolicTransformer(
        generations=1,
        population_size=10,
        function_set=function_set,
        verbose=0
    )
    transformer.fit(X, y) # init internal structs
    
    formula = "mul(neg(volume), add(close, 0.001))"
    prog = create_program_from_string(formula, transformer, X)
    
    if prog:
        print(f"Successfully parsed!")
        print(f"Program string: {prog}")
        print(f"Program depth: {prog.depth_}")
        print(f"Program executed: {prog.execute(X)[:2]}")
    else:
        print("Parse failed")
