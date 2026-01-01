"""
ML Model Wrapper
================

Wrapper for LightGBM model to predict stock returns.
"""

import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
import pickle
from pathlib import Path
from typing import Optional


class MLScorer:
    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.features = [
            "price_vs_ma20",
            "price_vs_ma50",
            "price_vs_ma200",
            "mom_1m",
            "mom_3m",
            "mom_6m",
            "vol_annual",
            "atr_pct",
            "rsi",
        ]
        if model_path and Path(model_path).exists():
            self.load(model_path)

    def train(self, df: pd.DataFrame):
        """
        Train the model
        df: Dataset containing features and 'target' column
        """
        X = df[self.features]
        y = df["target"]

        # HistGradientBoostingClassifier is similar to LightGBM
        self.model = HistGradientBoostingClassifier(
            learning_rate=0.05,
            max_iter=100,
            max_leaf_nodes=31,
            early_stopping=False,
            random_state=42,
        )

        self.model.fit(X, y)

    def predict(self, df: pd.DataFrame) -> pd.Series:
        """
        Return probability scores
        """
        if self.model is None:
            raise ValueError("Model not trained or loaded")

        X = df[self.features]
        # predict_proba returns [prob_0, prob_1]
        preds = self.model.predict_proba(X)[:, 1]
        return pd.Series(preds, index=df.index)

    def save(self, path: str):
        with open(path, "wb") as f:
            pickle.dump(self.model, f)

    def load(self, path: str):
        with open(path, "rb") as f:
            self.model = pickle.load(f)
