
"""
CyberSentinel V2
Normal-Only Network Anomaly Detection

Dataset: UNSW-NB15

Models compared:
1. Isolation Forest - all encoded features
2. Isolation Forest - numerical features only
3. PCA 95% + Isolation Forest
4. PCA 99% + Isolation Forest

Important:
- Detectors train on normal records only.
- Validation labels calibrate thresholds and select a model.
- Official testing records remain held out.
- The original CyberSentinel model is preserved.
"""

import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.ensemble import IsolationForest
from sklearn.impute import SimpleImputer

from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    fbeta_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
    roc_auc_score
)

from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from sklearn.preprocessing import (
    OneHotEncoder,
    StandardScaler
)


# -------------------------------------------------
# PROJECT CONFIGURATION
# -------------------------------------------------

ROOT = Path(__file__).resolve().parents[1]

RAW = ROOT / "datasets" / "raw"
OUT_MODELS = ROOT / "models"
OUT_DATA = ROOT / "datasets" / "processed"

TRAIN = RAW / "UNSW_NB15_training-set.csv"
TEST = RAW / "UNSW_NB15_testing-set.csv"

CATEGORICAL = [
    "proto",
    "service",
    "state"
]

EXCLUDE = {
    "id",
    "label",
    "attack_cat"
}

SEED = 42


# -------------------------------------------------
# DATASET LOADING
# -------------------------------------------------

def load_csv(path):

    if not path.is_file():
        raise FileNotFoundError(
            f"Missing dataset: {path}"
        )

    df = pd.read_csv(
        path,
        low_memory=False
    )

    required = {
        "label",
        *CATEGORICAL
    }

    missing = required.difference(
        df.columns
    )

    if missing:
        raise ValueError(
            f"Missing required columns: {sorted(missing)}"
        )

    df["label"] = pd.to_numeric(
        df["label"],
        errors="raise"
    ).astype(int)

    if not df["label"].isin([0, 1]).all():
        raise ValueError(
            "Labels must contain only 0 and 1."
        )

    return df


def balanced_sample(df, size, seed):

    if size <= 0 or size >= len(df):
        return df.reset_index(drop=True)

    selected, _ = train_test_split(
        df,
        train_size=size,
        random_state=seed,
        stratify=df["label"]
    )

    return selected.reset_index(drop=True)


# -------------------------------------------------
# FEATURE PREPARATION
# -------------------------------------------------

def prepare_frame(df, numeric_columns):

    X = df[
        numeric_columns + CATEGORICAL
    ].copy()

    for column in numeric_columns:

        X[column] = pd.to_numeric(
            X[column],
            errors="coerce"
        )

        X[column] = X[column].replace(
            [np.inf, -np.inf],
            np.nan
        )

    for column in CATEGORICAL:

        X[column] = (
            X[column]
            .fillna("unknown")
            .astype(str)
        )

    return X


def make_preprocessor(numeric_columns):

    numerical_pipeline = Pipeline([
        (
            "imputer",
            SimpleImputer(
                strategy="median",
                keep_empty_features=True
            )
        ),
        (
            "scaler",
            StandardScaler()
        )
    ])

    categorical_encoder = OneHotEncoder(
        handle_unknown="ignore",
        sparse_output=False,
        dtype=np.float32
    )

    return ColumnTransformer(
        transformers=[
            (
                "numerical",
                numerical_pipeline,
                numeric_columns
            ),
            (
                "categorical",
                categorical_encoder,
                CATEGORICAL
            )
        ],
        sparse_threshold=0
    )


# -------------------------------------------------
# MODEL EVALUATION
# -------------------------------------------------

def evaluate(y, predictions, scores):

    results = {
        "accuracy": float(
            accuracy_score(
                y,
                predictions
            )
        ),

        "balanced_accuracy": float(
            balanced_accuracy_score(
                y,
                predictions
            )
        ),

        "precision": float(
            precision_score(
                y,
                predictions,
                zero_division=0
            )
        ),

        "recall": float(
            recall_score(
                y,
                predictions,
                zero_division=0
            )
        ),

        "f1": float(
            f1_score(
                y,
                predictions,
                zero_division=0
            )
        ),

        "f2": float(
            fbeta_score(
                y,
                predictions,
                beta=2,
                zero_division=0
            )
        ),

        "mcc": float(
            matthews_corrcoef(
                y,
                predictions
            )
        ),

        "flagged": int(
            np.sum(predictions)
        ),

        "false_positive_rate": float(
            np.sum(
                (predictions == 1) &
                (y == 0)
            ) / max(1, np.sum(y == 0))
        ),

        "confusion_matrix": confusion_matrix(
            y,
            predictions,
            labels=[0, 1]
        ).tolist()
    }

    if len(np.unique(y)) == 2:

        results["roc_auc"] = float(
            roc_auc_score(
                y,
                scores
            )
        )

        results["pr_auc"] = float(
            average_precision_score(
                y,
                scores
            )
        )

    return results


# -------------------------------------------------
# VALIDATION THRESHOLD SELECTION
# -------------------------------------------------

def calibrate_threshold(
    labels,
    scores,
    max_fpr
):

    normal_scores = scores[
        labels == 0
    ]

    if (
        len(normal_scores) == 0
        or not np.any(labels == 1)
    ):
        raise ValueError(
            "Validation requires normal and attack records."
        )

    allowed_fpr_values = np.linspace(
        0.005,
        max_fpr,
        80
    )

    thresholds = np.unique(
        np.quantile(
            normal_scores,
            1 - allowed_fpr_values
        )
    )

    thresholds = np.append(
        thresholds,
        float(np.max(scores) + 1e-7)
    )

    candidates = []

    for threshold in thresholds:

        predictions = (
            scores >= threshold
        ).astype(int)

        result = evaluate(
            labels,
            predictions,
            scores
        )

        if (
            result["false_positive_rate"]
            <= max_fpr + 1e-9
        ):

            candidates.append((
                result["f1"],
                result["balanced_accuracy"],
                -result["false_positive_rate"],
                float(threshold),
                result
            ))

    if not candidates:
        raise RuntimeError(
            "No threshold satisfies the validation FPR limit."
        )

    best = max(
        candidates,
        key=lambda item: (
            item[0],
            item[1],
            item[2]
        )
    )

    return best[3], best[4]


# -------------------------------------------------
# FEATURE VIEW SELECTION
# -------------------------------------------------

def transform_view(
    name,
    X,
    pca95,
    pca99,
    numeric_count
):

    if name == "full_features":
        return X

    if name == "numeric_only":
        return X[:, :numeric_count]

    if name == "pca_95":

        return pca95.transform(
            X
        ).astype(np.float32)

    if name == "pca_99":

        return pca99.transform(
            X
        ).astype(np.float32)

    raise ValueError(
        f"Unknown feature view: {name}"
    )


# -------------------------------------------------
# MAIN TRAINING
# -------------------------------------------------

def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--normal-rows",
        type=int,
        default=12000
    )

    parser.add_argument(
        "--validation-rows",
        type=int,
        default=6000
    )

    parser.add_argument(
        "--test-rows",
        type=int,
        default=5000
    )

    parser.add_argument(
        "--max-fpr",
        type=float,
        default=0.15
    )

    args = parser.parse_args()

    if not 0.005 <= args.max_fpr <= 0.50:
        parser.error(
            "--max-fpr must be between 0.005 and 0.50."
        )

    if min(
        args.normal_rows,
        args.validation_rows,
        args.test_rows
    ) < 100:
        parser.error(
            "Row limits must be at least 100."
        )

    print("\n" + "=" * 60)
    print("CYBERSENTINEL V2 - NORMAL-ONLY TRAINING")
    print("=" * 60)

    # ---------------------------------------------
    # 1. LOAD DATA
    # ---------------------------------------------

    full_train = load_csv(TRAIN)
    full_test = load_csv(TEST)

    # Split only the official training CSV.
    # The testing CSV remains independent.

    fit_pool, validation_pool = train_test_split(
        full_train,
        test_size=0.20,
        random_state=SEED,
        stratify=full_train["label"]
    )

    # Train only on legitimate network traffic.

    normal_pool = fit_pool[
        fit_pool["label"] == 0
    ]

    if len(normal_pool) < 100:
        raise ValueError(
            "Not enough normal training records."
        )

    fit = normal_pool.sample(
        n=min(
            args.normal_rows,
            len(normal_pool)
        ),
        random_state=SEED
    ).reset_index(drop=True)

    validation = balanced_sample(
        validation_pool,
        args.validation_rows,
        SEED + 1
    )

    # Same test sampling method as your original
    # CyberSentinel experiment.

    test = full_test.sample(
        n=min(
            args.test_rows,
            len(full_test)
        ),
        random_state=43
    ).reset_index(drop=True)

    print(
        f"\nNormal-only training: {len(fit):,}"
    )

    print(
        f"Validation records: {len(validation):,}"
    )

    print(
        f"Official testing records: {len(test):,}"
    )

    # ---------------------------------------------
    # 2. PREPROCESSING
    # ---------------------------------------------

    numeric_columns = [
        name
        for name in full_train.columns
        if (
            name not in EXCLUDE
            and name not in CATEGORICAL
        )
    ]

    transformer = make_preprocessor(
        numeric_columns
    )

    X_train = transformer.fit_transform(
        prepare_frame(
            fit,
            numeric_columns
        )
    ).astype(np.float32)

    X_val = transformer.transform(
        prepare_frame(
            validation,
            numeric_columns
        )
    ).astype(np.float32)

    numeric_count = len(
        numeric_columns
    )

    print(
        "\nEncoded features:",
        X_train.shape[1]
    )

    # ---------------------------------------------
    # 3. PCA
    # ---------------------------------------------

    pca95 = PCA(
        n_components=0.95,
        svd_solver="full"
    )

    pca99 = PCA(
        n_components=0.99,
        svd_solver="full"
    )

    pca95.fit(X_train)
    pca99.fit(X_train)

    print(
        "PCA 95% dimensions:",
        pca95.n_components_
    )

    print(
        "PCA 99% dimensions:",
        pca99.n_components_
    )

    # ---------------------------------------------
    # 4. COMPARE FOUR MODELS
    # ---------------------------------------------

    y_val = validation[
        "label"
    ].to_numpy(dtype=int)

    trained_models = {}
    tuning_results = {}

    candidates = [
        "full_features",
        "numeric_only",
        "pca_95",
        "pca_99"
    ]

    for name in candidates:

        print(
            f"\nTraining candidate: {name}"
        )

        model = IsolationForest(
            n_estimators=160,
            max_samples=min(
                256,
                len(fit)
            ),
            contamination="auto",
            random_state=SEED,
            n_jobs=-1
        )

        X_train_view = transform_view(
            name,
            X_train,
            pca95,
            pca99,
            numeric_count
        )

        X_val_view = transform_view(
            name,
            X_val,
            pca95,
            pca99,
            numeric_count
        )

        # Train without attack labels.

        model.fit(
            X_train_view
        )

        # Higher score = more unusual.

        validation_scores = -model.score_samples(
            X_val_view
        )

        threshold, val_metrics = calibrate_threshold(
            y_val,
            validation_scores,
            args.max_fpr
        )

        trained_models[name] = model

        tuning_results[name] = {
            "threshold": threshold,
            "validation_metrics": val_metrics
        }

        print(
            "Validation F1:",
            round(
                val_metrics["f1"],
                4
            )
        )

        print(
            "Validation Recall:",
            round(
                val_metrics["recall"],
                4
            )
        )

        print(
            "Validation FPR:",
            round(
                val_metrics["false_positive_rate"],
                4
            )
        )

        print(
            "Validation PR-AUC:",
            round(
                val_metrics["pr_auc"],
                4
            )
        )

    # ---------------------------------------------
    # 5. SELECT MODEL USING VALIDATION ONLY
    # ---------------------------------------------

    winner = max(
        tuning_results,
        key=lambda name: (
            tuning_results[name][
                "validation_metrics"
            ]["f1"],

            tuning_results[name][
                "validation_metrics"
            ]["pr_auc"]
        )
    )

    decision_threshold = tuning_results[
        winner
    ]["threshold"]

    print(
        "\nSelected model:",
        winner
    )

    # ---------------------------------------------
    # 6. FINAL TEST EVALUATION
    # ---------------------------------------------

    X_test = transformer.transform(
        prepare_frame(
            test,
            numeric_columns
        )
    ).astype(np.float32)

    X_winner = transform_view(
        winner,
        X_test,
        pca95,
        pca99,
        numeric_count
    )

    scores_test = -trained_models[
        winner
    ].score_samples(X_winner)

    predictions = (
        scores_test >= decision_threshold
    ).astype(int)

    y_test = test[
        "label"
    ].to_numpy(dtype=int)

    test_metrics = evaluate(
        y_test,
        predictions,
        scores_test
    )

    print("\n" + "=" * 60)
    print("V2 OFFICIAL TEST RESULTS")
    print("=" * 60)

    print(
        json.dumps(
            test_metrics,
            indent=2
        )
    )

    # ---------------------------------------------
    # 7. COMPARE ORIGINAL V1 ON SAME TEST ROWS
    # ---------------------------------------------

    baseline_metrics = None

    baseline_path = (
        OUT_MODELS / "unsw_nb15_pipeline.joblib"
    )

    if baseline_path.is_file():

        try:

            # Only load your locally trained model.

            old = joblib.load(
                baseline_path
            )

            old_numeric = list(
                old["numeric_columns"]
            )

            X_old = old[
                "transformer"
            ].transform(
                prepare_frame(
                    test,
                    old_numeric
                )
            )

            old_model = old[
                "raw_isolation_forest"
            ]

            old_scores = -old_model.score_samples(
                X_old
            )

            old_predictions = (
                old_model.predict(X_old) == -1
            ).astype(int)

            baseline_metrics = evaluate(
                y_test,
                old_predictions,
                old_scores
            )

            print(
                "\nORIGINAL V1 RESULTS - SAME TEST RECORDS"
            )

            print(
                json.dumps(
                    baseline_metrics,
                    indent=2
                )
            )

            print(
                "\nV2 minus V1:"
            )

            print(
                "Accuracy difference:",
                round(
                    test_metrics["accuracy"]
                    - baseline_metrics["accuracy"],
                    4
                )
            )

            print(
                "Recall difference:",
                round(
                    test_metrics["recall"]
                    - baseline_metrics["recall"],
                    4
                )
            )

            print(
                "F1 difference:",
                round(
                    test_metrics["f1"]
                    - baseline_metrics["f1"],
                    4
                )
            )

        except Exception as exc:

            print(
                "Original model comparison skipped:",
                exc
            )

    # ---------------------------------------------
    # 8. SAVE MODEL AND REPORT
    # ---------------------------------------------

    OUT_MODELS.mkdir(
        parents=True,
        exist_ok=True
    )

    OUT_DATA.mkdir(
        parents=True,
        exist_ok=True
    )

    model_path = (
        OUT_MODELS
        / "unsw_nb15_v2_pipeline.joblib"
    )

    report_path = (
        OUT_MODELS
        / "unsw_nb15_v2_report.json"
    )

    prediction_path = (
        OUT_DATA
        / "unsw_nb15_v2_predictions.csv"
    )

    report = {
        "experiment": (
            "Normal-only Isolation Forest "
            "with validation-based calibration"
        ),

        "training_rows_normal_only": len(fit),
        "validation_rows": len(validation),
        "test_rows": len(test),

        "test_normal": int(
            np.sum(y_test == 0)
        ),

        "test_attack": int(
            np.sum(y_test == 1)
        ),

        "max_validation_false_positive_rate": (
            args.max_fpr
        ),

        "encoded_features": int(
            X_train.shape[1]
        ),

        "pca_95_dimensions": int(
            pca95.n_components_
        ),

        "pca_99_dimensions": int(
            pca99.n_components_
        ),

        "selected_model": winner,

        "selected_threshold": (
            decision_threshold
        ),

        "validation_comparison": (
            tuning_results
        ),

        "final_test_metrics": (
            test_metrics
        ),

        "original_v1_same_test_metrics": (
            baseline_metrics
        ),

        "note": (
            "Detectors train on normal traffic only. "
            "Validation labels select the model and "
            "threshold. The official testing labels "
            "are used only for final evaluation. "
            "Improved performance is not guaranteed."
        )
    }

    with open(
        report_path,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            report,
            file,
            indent=4
        )

    # Save selected V2 model separately.

    joblib.dump(
        {
            "transformer": transformer,

            "numeric_columns": (
                numeric_columns
            ),

            "categorical_columns": (
                CATEGORICAL
            ),

            "pca95": pca95,
            "pca99": pca99,

            "selected_model_name": winner,

            "detector": trained_models[
                winner
            ],

            "threshold": decision_threshold,

            "number_of_numeric_columns": (
                numeric_count
            ),

            "experiment": "v2"
        },
        model_path
    )

    # ---------------------------------------------
    # 9. SAVE TEST PREDICTIONS
    # ---------------------------------------------

    prediction_df = pd.DataFrame({
        "actual_attack": y_test,

        "predicted_anomaly": (
            predictions
        ),

        "anomaly_score": (
            scores_test
        ),

        "proto": test[
            "proto"
        ].astype(str),

        "service": test[
            "service"
        ].astype(str),

        "state": test[
            "state"
        ].astype(str),

        "attack_cat": (
            test["attack_cat"].astype(str)
            if "attack_cat" in test.columns
            else "unavailable"
        )
    })

    prediction_df.to_csv(
        prediction_path,
        index=False
    )

    print("\n" + "=" * 60)
    print("CYBERSENTINEL V2 COMPLETED")
    print("=" * 60)

    print(
        "\nSaved model:",
        model_path
    )

    print(
        "Saved report:",
        report_path
    )

    print(
        "Saved predictions:",
        prediction_path
    )

    print(
        "\nOriginal CyberSentinel V1 remains unchanged."
    )


if __name__ == "__main__":
    main()
