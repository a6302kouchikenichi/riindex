import numpy as np
import pandas as pd

class SmartphoneRDModel:
    """
    スマホ計測を用いた簡易 HDM-4 RD モデル
    - IRI（BumpRecorder）
    - Crack, Pothole（RoadManager）
    - Traffic（ESAL）
    - SNP（道路種別の代理値）
    """

    def __init__(self,
                 iri_init,
                 crack_init,
                 pothole_init,
                 esal,               # 年間 ESAL（交通量）
                 snp,                # 道路種別から割り当て
                 k_age=0.0008,       # Age deterioration
                 k_traffic=0.0004,   # Traffic deterioration
                 k_crack=0.015,      # Crack→IRI影響
                 k_pothole=0.10):    # Pothole→IRI影響

        self.iri = iri_init
        self.crack = crack_init
        self.pothole = pothole_init
        self.esal = esal
        self.snp = snp

        # モデル係数（後で推定可能）
        self.k_age = k_age
        self.k_traffic = k_traffic
        self.k_crack = k_crack
        self.k_pothole = k_pothole

        # 予測結果を保持する
        self.history = []

    def annual_update(self):
        """
        1年間の劣化を計算し、IRI・Crack・Pothole を更新する
        """

        # IRI 劣化（Age＋Traffic＋Crack＋Pothole）
        d_iri = (
            self.k_age * self.iri +
            self.k_traffic * (self.esal / self.snp) +
            self.k_crack * self.crack +
            self.k_pothole * self.pothole
        )

        self.iri += d_iri

        # Crack progression（簡易モデル）
        self.crack += 0.02 * (self.esal / self.snp)

        # Pothole progression （CrackとIRIに依存）
        self.pothole += 0.001 * self.crack + 0.005 * self.iri

        # 保存
        self.history.append({
            "IRI": self.iri,
            "Crack": self.crack,
            "Pothole": self.pothole
        })

        return self.iri, self.crack, self.pothole

    def simulate(self, years=20):
        for _ in range(years):
            self.annual_update()
        return pd.DataFrame(self.history)

    def update_with_latest_observation(self, iri_obs, crack_obs, pothole_obs):
        """
        最新実測値（スマホアプリ）で現在値を更新
        """
        self.iri = iri_obs
        self.crack = crack_obs
        self.pothole = pothole_obs

    def compare_with_prediction(self, pred_iri):
        """
        最新 IRI と予測値の差分を評価
        """
        delta = self.iri - pred_iri
        if delta > 0.5:
            status = "予測より悪化（補修要検討）"
        elif delta < -0.3:
            status = "予測より良好（補修延伸可能）"
        else:
            status = "予測通り"
        return delta, status

    def estimate_repair_cost(self, unit_costs):
        """
        劣化状態から概算補修費を試算
        unit_costs例：
        {
            "overlay_50mm": 2500,  # 千円/延長m
            "crack_sealing": 100,   # 千円/延長m
            "pothole_patch": 300    # 千円/箇所
        }
        """

        # IRI による工法選定
        if self.iri > 6:
            method = "overlay_50mm"
            cost = unit_costs["overlay_50mm"]
        elif self.iri > 4:
            method = "crack_sealing"
            cost = unit_costs["crack_sealing"]
        else:
            method = "routine"
            cost = 0

        # Pothole は別立て
        pothole_cost = self.pothole * unit_costs["pothole_patch"]

        return {
            "method": method,
            "main_cost": cost,
            "pothole_cost": pothole_cost,
            "total_cost": cost + pothole_cost
        }