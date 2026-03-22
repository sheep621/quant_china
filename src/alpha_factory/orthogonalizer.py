import numpy as np

class GramSchmidtOrthogonalizer:
    def __init__(self, corr_threshold=0.8):
        self.corr_threshold = corr_threshold
        
    def check_and_orthogonalize(self, new_feature_array, existing_features_matrix):
        """
        检查新因子与已有因子的共线性。
        如果皮尔逊相关系数 > corr_threshold，判定为严重同质化，返回 None。
        """
        if existing_features_matrix is None or existing_features_matrix.shape[1] == 0:
            return new_feature_array

        new_var = np.var(new_feature_array)
        if new_var == 0: return None

        # 检查是否与任何已入库因子高度相关
        for i in range(existing_features_matrix.shape[1]):
            existing_col = existing_features_matrix[:, i]
            corr = np.corrcoef(new_feature_array, existing_col)[0, 1]
            if abs(corr) > self.corr_threshold:
                return None  # 基因高度重合，直接流产该因子
                
        return new_feature_array