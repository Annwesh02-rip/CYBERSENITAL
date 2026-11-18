from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score


def evaluate_predictions(true_labels, predicted_anomaly):
    """Use labels ONLY for post-training evaluation; 1 denotes an anomaly."""
    return {
        "accuracy": round(float(accuracy_score(true_labels, predicted_anomaly)), 4),
        "precision": round(float(precision_score(true_labels, predicted_anomaly, zero_division=0)), 4),
        "recall": round(float(recall_score(true_labels, predicted_anomaly, zero_division=0)), 4),
        "f1": round(float(f1_score(true_labels, predicted_anomaly, zero_division=0)), 4),
    }
