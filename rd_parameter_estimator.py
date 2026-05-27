import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

class RDParameterEstimator:
    """
    スマホRDモデルのパラメータ推定クラス
    入力：IRI, Crack, Pothole, ESAL, SNP の時系列データ
    出力：k_age, k_traffic, k_crack, k_pothole
    """

    def __init__(self, df):
        """
        df は次の列を含む pandas.DataFrame（時系列）
        - IRI
        - Crack
        - Pothole
        - ESAL
        - SNP
        - Year（任意）
        """
        self.df = df.copy()
        self._prepare_data()

    def _prepare_data(self):
        # ΔIRI を計算
        self.df["IRI_prev"] = self.df["IRI"].shift(1)
        self.df["dIRI"] = self.df["IRI"] - self.df["IRI_prev"]

        # 1年目（差分が取れない）は除去
        self.df = self.df.dropna()

    def estimate_parameters(self):
        """
        ΔIRI = k_age * IRI_prev
             + k_traffic * (ESAL/SNP)
             + k_crack * Crack
             + k_pothole * Pothole
        の線形回帰で係数を推定
        """

        # 説明変数 X
        X = pd.DataFrame({
            "age_term": self.df["IRI_prev"],
            "traffic_term": self.df["ESAL"] / self.df["SNP"],
            "crack_term": self.df["Crack"],
            "pothole_term": self.df["Pothole"]
        })

        # 目的変数
        y = self.df["dIRI"]

        # 回帰分析
        model = LinearRegression()
        model.fit(X, y)

        k_age = model.coef_[0]
        k_traffic = model.coef_[1]
        k_crack = model.coef_[2]
        k_pothole = model.coef_[3]

        return {
            "k_age": k_age,
            "k_traffic": k_traffic,
            "k_crack": k_crack,
            "k_pothole": k_pothole,
            "intercept": model.intercept_,
            "r2": model.score(X, y)
        }

    def print_summary(self):
        params = self.estimate_parameters()

        print("=== RD モデル パラメータ推定結果 ===")
        print(f"k_age        : {params['k_age']:.5f}")
        print(f"k_traffic    : {params['k_traffic']:.5f}")
        print(f"k_crack      : {params['k_crack']:.5f}")
        print(f"k_pothole    : {params['k_pothole']:.5f}")
        print("----------------------------------")
        print(f"切片（バイアス）: {params['intercept']:.5f}")
        print(f"決定係数 R2     : {params['r2']:.3f}")
        return params