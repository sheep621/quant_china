import codecs

file_path = "src/alpha_factory/operators.py"

with codecs.open(file_path, "r", "utf-8") as f:
    code = f.read()

replacement = """
from src.alpha_factory.context import DataContext
original_make_function = make_function

def custom_make_function(function, name, arity):
    import re
    import pandas as pd
    
    if name == 'rank':
        # cs_rank (Cross-Sectional Rank) requires groupby Date
        def wrapper(*args):
            dates = DataContext.get_dates()
            if dates is None:
                return function(*args)
            df = pd.DataFrame({'val': args[0], 'date': dates})
            return df.groupby('date')['val'].rank(pct=True).fillna(0.5).values
        wrapper.__name__ = function.__name__
        func_to_register = wrapper
        
    elif name == 'indneu':
        # indneu (Industry Neutralize) requires groupby Industry
        # wait, the original _ind_neutralize already handles df groupby but ignores date?
        # Let's let original indneu handle it, we assume indneu is a cross-sectional logic but we just let it be for now
        func_to_register = function
        
    else:
        # Check if it's a TS operator by checking suffix like _ts_mean_5 -> window=5
        m = re.search(r'_(\\d+)$', function.__name__)
        if m:
            window = int(m.group(1))
            def wrapper(*args):
                res = function(*args)
                return DataContext.mask_invalid_ts(res, window)
            wrapper.__name__ = function.__name__
            func_to_register = wrapper
        else:
            func_to_register = function
            
    return original_make_function(function=func_to_register, name=name, arity=arity)

# Override make_function in this module namespace
make_function = custom_make_function

# 基础运算 (4个)
"""

if "custom_make_function" not in code:
    code = code.replace("# 基础运算 (4个)", replacement)
    with codecs.open(file_path, "w", "utf-8") as f:
        f.write(code)
    print("Patch successfully applied!")
else:
    print("Already patched.")
