import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.ensemble import IsolationForest


def fit_isolation_forest(features, contamination: float = 0.10):
    detector = IsolationForest(
        n_estimators=150, contamination=contamination, random_state=42
    )
    detector.fit(features)
    return detector


def dbscan_summary(projected_features, eps: float = 0.85, min_samples: int = 6):
    labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(projected_features)
    return {
        "clusters": int(len(set(labels) - {-1})),
        "noise_points": int(np.sum(labels == -1)),
    }
