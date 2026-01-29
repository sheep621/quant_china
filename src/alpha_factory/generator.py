from gplearn.genetic import SymbolicTransformer
import pandas as pd
import numpy as np
from src.infrastructure.logger import get_system_logger
from src.alpha_factory.operators import custom_operations

logger = get_system_logger()

class AlphaGenerator:
    def __init__(self, population_size=2000, generations=20, n_jobs=1):
        """
        Expanded Alpha Generator
        population_size: Increased to 2000 for better diversity
        generations: Increased to 20
        """
        # Standard algebraic set + Our Custom Quant Ops
        function_set = ['add', 'sub', 'mul', 'div', 'neg', 'abs', 'inv'] + custom_operations
        
        self.gp = SymbolicTransformer(
            generations=generations,
            population_size=population_size,
            hall_of_fame=100,
            n_components=20, # Generate 20 best alphas
            function_set=function_set,
            metric='spearman', # Rank IC
            parsimony_coefficient=0.001, # Penalty for complexity
            max_samples=0.9,
            verbose=1,
            random_state=42,
            n_jobs=n_jobs
        )
        
    def fit(self, X, y):
        """
        Minings alphas.
        X: Feature Matrix
        y: Target (Label)
        """
        logger.info(f"Starting GP Alpha Mining with {X.shape[1]} base features...")
        logger.info(f"Population: {self.gp.population_size}, Gens: {self.gp.generations}")
        
        try:
            # Handle NaNs in X before GP (gplearn doesn't like NaNs)
            if isinstance(X, pd.DataFrame):
                X = X.fillna(0)
            else:
                X = np.nan_to_num(X)
                
            self.gp.fit(X, y)
            logger.info("GP Mining Completed Successfully.")
            
            # Log best programs
            logger.info("Top 5 Discovered Alphas:")
            for i, prog in enumerate(self.gp._best_programs[:5]):
                logger.info(f"Alpha #{i+1}: {prog}")
                
        except Exception as e:
            logger.error(f"GP Mining failed: {e}")
            raise e
            
    def transform(self, X):
        if isinstance(X, pd.DataFrame):
            X = X.fillna(0)
        else:
            X = np.nan_to_num(X)
        return self.gp.transform(X)
