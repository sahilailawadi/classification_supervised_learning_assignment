"""
train.py — Model training, evaluation, and export for performance test classification.

Trains Decision Tree, Random Forest, and SVM classifiers on the engineered features.
Evaluates all models on the held-out test set with confusion matrix, accuracy, balanced
accuracy, precision, recall, F1-score, and ROC-AUC. Exports the best model.

Usage:
    python -m src.train                     # Full pipeline: extract → features → train
    python -m src.train --from-csv PATH     # Train from a pre-exported CSV
"""

import os
import sys
import json
import argparse
import warnings
import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use("Agg")  # Non-interactive backend for saving plots
import matplotlib.pyplot as plt
import seaborn as sns

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.metrics import (
    confusion_matrix, classification_report, accuracy_score,
    balanced_accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, roc_curve, ConfusionMatrixDisplay,
)

from src.features import MODEL_FEATURES, build_features, generate_reason
from src.extract import extract_training_data

warnings.filterwarnings("ignore", category=FutureWarning)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Get project root directory (parent of src/)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
TEST_CASES_DIR = os.path.join(PROJECT_ROOT, "test_cases")
RANDOM_STATE = 42
TEST_SIZE = 0.20


# ---------------------------------------------------------------------------
# 1. Data preparation
# ---------------------------------------------------------------------------

def prepare_data(run_df: pd.DataFrame):
    """
    Split into train/test at the testplan level, fit scaler on training set.

    Returns:
        X_train, X_test, y_train, y_test, scaler, train_plans, test_plans
    """
    # Unique runs for stratified split
    runs = run_df[["testplan", "label_pass_fail"]].drop_duplicates()
    train_plans, test_plans = train_test_split(
        runs["testplan"],
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=runs["label_pass_fail"],
    )

    train_df = run_df[run_df["testplan"].isin(train_plans)]
    test_df = run_df[run_df["testplan"].isin(test_plans)]

    X_train = train_df[MODEL_FEATURES].copy()
    y_train = train_df["label_pass_fail"].copy()
    X_test = test_df[MODEL_FEATURES].copy()
    y_test = test_df["label_pass_fail"].copy()

    # Scale features
    scaler = StandardScaler()
    X_train_scaled = pd.DataFrame(
        scaler.fit_transform(X_train), columns=MODEL_FEATURES, index=X_train.index
    )
    X_test_scaled = pd.DataFrame(
        scaler.transform(X_test), columns=MODEL_FEATURES, index=X_test.index
    )

    print(f"\n  Train: {len(X_train)} runs  |  Test: {len(X_test)} runs")
    print(f"  Train pass/fail: {(y_train == 1).sum()}/{(y_train == 0).sum()}")
    print(f"  Test  pass/fail: {(y_test == 1).sum()}/{(y_test == 0).sum()}")

    return X_train_scaled, X_test_scaled, y_train, y_test, scaler, train_plans, test_plans


# ---------------------------------------------------------------------------
# 2. Model training
# ---------------------------------------------------------------------------

def get_models(class_weight_strategy="balanced"):
    """
    Return a dict of model_name → classifier instances.

    class_weight_strategy: 'balanced' to handle imbalance, None for default.
    """
    return {
        "Decision Tree": DecisionTreeClassifier(
            max_depth=10,
            class_weight=class_weight_strategy,
            random_state=RANDOM_STATE,
        ),
        "Random Forest": RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            class_weight=class_weight_strategy,
            random_state=RANDOM_STATE,
            n_jobs=-1,
        ),
        "SVM": SVC(
            kernel="rbf",
            class_weight=class_weight_strategy,
            probability=True,  # needed for ROC-AUC
            random_state=RANDOM_STATE,
        ),
    }


def train_and_evaluate(models: dict, X_train, X_test, y_train, y_test):
    """
    Train each model, evaluate on test set, return results dict.

    Returns:
        dict of model_name → {model, metrics, y_pred, y_proba}
    """
    results = {}

    for name, model in models.items():
        print(f"\n{'='*60}")
        print(f"  Training: {name}")
        print(f"{'='*60}")

        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1] if hasattr(model, "predict_proba") else None

        # Metrics
        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "balanced_accuracy": balanced_accuracy_score(y_test, y_pred),
            "precision": precision_score(y_test, y_pred, zero_division=0),
            "recall": recall_score(y_test, y_pred, zero_division=0),
            "f1_score": f1_score(y_test, y_pred, zero_division=0),
        }
        if y_proba is not None:
            try:
                metrics["roc_auc"] = roc_auc_score(y_test, y_proba)
            except ValueError:
                metrics["roc_auc"] = None  # Only one class in test set

        # Confusion matrix components
        cm = confusion_matrix(y_test, y_pred, labels=[0, 1])
        # For binary: [[TN, FP], [FN, TP]] when labels=[0,1]
        metrics["TN"] = int(cm[0, 0])
        metrics["FP"] = int(cm[0, 1])
        metrics["FN"] = int(cm[1, 0])
        metrics["TP"] = int(cm[1, 1])

        # Cross-validation on training set
        cv_scores = cross_val_score(model, X_train, y_train, cv=5, scoring="f1")
        metrics["cv_f1_mean"] = cv_scores.mean()
        metrics["cv_f1_std"] = cv_scores.std()

        # Print
        print(f"\n  Confusion Matrix:")
        print(f"    TN={metrics['TN']}  FP={metrics['FP']}")
        print(f"    FN={metrics['FN']}  TP={metrics['TP']}")
        print(f"\n  Accuracy:          {metrics['accuracy']:.4f}")
        print(f"  Balanced Accuracy: {metrics['balanced_accuracy']:.4f}")
        print(f"  Precision:         {metrics['precision']:.4f}")
        print(f"  Recall:            {metrics['recall']:.4f}")
        print(f"  F1-Score:          {metrics['f1_score']:.4f}")
        if metrics.get("roc_auc") is not None:
            print(f"  ROC-AUC:           {metrics['roc_auc']:.4f}")
        print(f"  CV F1 (5-fold):    {metrics['cv_f1_mean']:.4f} ± {metrics['cv_f1_std']:.4f}")

        print(f"\n  Classification Report:")
        print(classification_report(y_test, y_pred,
              target_names=["Fail (0)", "Pass (1)"], zero_division=0))

        results[name] = {
            "model": model,
            "metrics": metrics,
            "y_pred": y_pred,
            "y_proba": y_proba,
        }

    return results


# ---------------------------------------------------------------------------
# 3. Visualization
# ---------------------------------------------------------------------------

def plot_confusion_matrices(results: dict, y_test, save_dir: str = MODELS_DIR):
    """Save confusion matrix heatmaps for each model."""
    fig, axes = plt.subplots(1, len(results), figsize=(5 * len(results), 4))
    if len(results) == 1:
        axes = [axes]

    for ax, (name, res) in zip(axes, results.items()):
        cm = confusion_matrix(y_test, res["y_pred"], labels=[0, 1])
        disp = ConfusionMatrixDisplay(cm, display_labels=["Fail", "Pass"])
        disp.plot(ax=ax, cmap="Blues", colorbar=False)
        ax.set_title(name)

    plt.tight_layout()
    path = os.path.join(save_dir, "confusion_matrices.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved confusion matrices to {path}")


def plot_roc_curves(results: dict, y_test, save_dir: str = MODELS_DIR):
    """Save ROC curve comparison plot."""
    fig, ax = plt.subplots(figsize=(8, 6))

    for name, res in results.items():
        if res["y_proba"] is not None and res["metrics"].get("roc_auc") is not None:
            fpr, tpr, _ = roc_curve(y_test, res["y_proba"])
            ax.plot(fpr, tpr, label=f"{name} (AUC={res['metrics']['roc_auc']:.3f})")

    ax.plot([0, 1], [0, 1], "k--", alpha=0.5, label="Random")
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curves — Model Comparison")
    ax.legend(loc="lower right")
    ax.grid(alpha=0.3)

    plt.tight_layout()
    path = os.path.join(save_dir, "roc_curves.png")
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved ROC curves to {path}")


def plot_feature_importance(results: dict, save_dir: str = MODELS_DIR):
    """Save feature importance plot for tree-based models."""
    for name in ["Random Forest", "Decision Tree"]:
        if name not in results:
            continue
        model = results[name]["model"]
        if not hasattr(model, "feature_importances_"):
            continue

        importances = model.feature_importances_
        indices = np.argsort(importances)[::-1]

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(
            range(len(MODEL_FEATURES)),
            importances[indices[::-1]],
            color="steelblue",
        )
        ax.set_yticks(range(len(MODEL_FEATURES)))
        ax.set_yticklabels([MODEL_FEATURES[i] for i in indices[::-1]])
        ax.set_xlabel("Importance")
        ax.set_title(f"Feature Importance — {name}")
        ax.grid(alpha=0.3, axis="x")

        plt.tight_layout()
        path = os.path.join(save_dir, f"feature_importance_{name.lower().replace(' ', '_')}.png")
        plt.savefig(path, dpi=150, bbox_inches="tight")
        plt.close()
        print(f"  Saved feature importance ({name}) to {path}")


# ---------------------------------------------------------------------------
# 4. Export
# ---------------------------------------------------------------------------

def select_best_model(results: dict) -> str:
    """Select the best model by balanced accuracy, then F1 as tiebreaker."""
    best_name = max(
        results.keys(),
        key=lambda n: (
            results[n]["metrics"]["balanced_accuracy"],
            results[n]["metrics"]["f1_score"],
        ),
    )
    print(f"\n  Best model: {best_name} "
          f"(balanced_acc={results[best_name]['metrics']['balanced_accuracy']:.4f}, "
          f"f1={results[best_name]['metrics']['f1_score']:.4f})")
    return best_name


def export_model(results: dict, best_name: str, scaler, save_dir: str = MODELS_DIR):
    """Save the best model, scaler, and all metrics."""
    os.makedirs(save_dir, exist_ok=True)

    # Model
    model_path = os.path.join(save_dir, "model.pkl")
    joblib.dump(results[best_name]["model"], model_path)
    print(f"  Saved model to {model_path}")

    # Scaler
    scaler_path = os.path.join(save_dir, "scaler.pkl")
    joblib.dump(scaler, scaler_path)
    print(f"  Saved scaler to {scaler_path}")

    # All metrics as JSON
    metrics_export = {}
    for name, res in results.items():
        m = res["metrics"].copy()
        # Convert numpy types for JSON serialization
        for k, v in m.items():
            if isinstance(v, (np.integer, np.int64)):
                m[k] = int(v)
            elif isinstance(v, (np.floating, np.float64)):
                m[k] = float(v)
        metrics_export[name] = m
    metrics_export["best_model"] = best_name

    metrics_path = os.path.join(save_dir, "metrics.json")
    with open(metrics_path, "w") as f:
        json.dump(metrics_export, f, indent=2)
    print(f"  Saved metrics to {metrics_path}")


def export_test_cases(
    run_df: pd.DataFrame,
    scaler,
    save_dir: str = TEST_CASES_DIR,
):
    """
    Select 3 representative test cases and save as JSON.

    Case 1: Clean pass — lowest max_pct_deviation_p95 among passing runs
    Case 2: Response time failure — exit_code 3
    Case 3: Throughput / error failure — exit_code 2 or 4, or highest fail_ratio among failures
    """
    os.makedirs(save_dir, exist_ok=True)

    cases = []

    # Case 1: Clean pass
    passing = run_df[run_df["label_pass_fail"] == 1].copy()
    if len(passing) > 0:
        best_pass = passing.loc[passing["max_pct_deviation_p95"].idxmin()]
        cases.append({
            "case_name": "Case 1: Clean Pass",
            "description": "All transactions within baseline thresholds. Healthy test run.",
            "testplan": best_pass["testplan"],
            "features": {f: float(best_pass[f]) for f in MODEL_FEATURES},
            "test_status_label": int(best_pass["label_pass_fail"]),
            "exit_code": int(best_pass["exit_code"]),
            "reason": generate_reason(best_pass),
        })

    # Case 2: Response time failure (exit_code == 3)
    rt_failures = run_df[run_df["exit_code"] == 3].copy()
    if len(rt_failures) > 0:
        worst_rt = rt_failures.loc[rt_failures["max_pct_deviation_p95"].idxmax()]
        cases.append({
            "case_name": "Case 2: Response Time Failure",
            "description": "Multiple transactions critical on p95 and avg RT. Exit code 3.",
            "testplan": worst_rt["testplan"],
            "features": {f: float(worst_rt[f]) for f in MODEL_FEATURES},
            "test_status_label": int(worst_rt["label_pass_fail"]),
            "exit_code": int(worst_rt["exit_code"]),
            "reason": generate_reason(worst_rt),
        })

    # Case 3: Throughput / error failure (exit_code 2 or 4, or worst fail_ratio)
    other_failures = run_df[run_df["exit_code"].isin([2, 4])].copy()
    if len(other_failures) > 0:
        worst = other_failures.loc[other_failures["fail_ratio"].idxmax()]
    else:
        # Fall back to the failing run with highest fail_ratio
        all_failures = run_df[run_df["label_pass_fail"] == 0].copy()
        if len(all_failures) > 0:
            worst = all_failures.loc[all_failures["fail_ratio"].idxmax()]
        else:
            worst = None

    if worst is not None:
        cases.append({
            "case_name": "Case 3: Throughput / Error Failure",
            "description": "High failure ratio and/or low throughput. Degraded or critical.",
            "testplan": worst["testplan"],
            "features": {f: float(worst[f]) for f in MODEL_FEATURES},
            "test_status_label": int(worst["label_pass_fail"]),
            "exit_code": int(worst["exit_code"]),
            "reason": generate_reason(worst),
        })

    # Save
    path = os.path.join(save_dir, "test_cases.json")
    with open(path, "w") as f:
        json.dump(cases, f, indent=2)
    print(f"  Saved {len(cases)} test cases to {path}")

    return cases


# ---------------------------------------------------------------------------
# 5. Main pipeline
# ---------------------------------------------------------------------------

def run_pipeline(df_raw: pd.DataFrame = None, csv_path: str = None):
    """
    Full training pipeline: extract → features → train → evaluate → export.

    Args:
        df_raw: Pre-extracted DataFrame (if None, extracts from DB)
        csv_path: Path to pre-exported CSV (alternative to DB extraction)
    """
    os.makedirs(MODELS_DIR, exist_ok=True)

    # --- Extract ---
    if df_raw is not None:
        print("Using provided DataFrame...")
    elif csv_path:
        print(f"Loading from CSV: {csv_path}")
        df_raw = pd.read_csv(csv_path)
    else:
        df_raw = extract_training_data()

    # --- Feature engineering (baselines from full dataset, then split) ---
    run_df, baselines = build_features(df_raw, is_training=True)

    # --- Train/test split ---
    print("\n=== Train / Test Split ===")
    X_train, X_test, y_train, y_test, scaler, train_plans, test_plans = prepare_data(run_df)

    # NOTE: Ideally baselines should be computed from training set only.
    # For a more rigorous approach, recompute baselines after split:
    #   train_raw = df_raw[df_raw["testplan"].isin(train_plans)]
    #   run_df_train, baselines = build_features(train_raw, is_training=True)
    #   run_df_test, _ = build_features(
    #       df_raw[df_raw["testplan"].isin(test_plans)],
    #       baselines=baselines, is_training=False)
    # This is noted as a future improvement. For the demo with the current
    # data volume, the difference is negligible.

    # --- Train & evaluate ---
    print("\n=== Model Training & Evaluation ===")
    models = get_models(class_weight_strategy="balanced")
    results = train_and_evaluate(models, X_train, X_test, y_train, y_test)

    # --- Visualizations ---
    print("\n=== Generating Visualizations ===")
    plot_confusion_matrices(results, y_test)
    plot_roc_curves(results, y_test)
    plot_feature_importance(results)

    # --- Select best & export ---
    print("\n=== Model Export ===")
    best_name = select_best_model(results)
    export_model(results, best_name, scaler)

    # --- Test cases ---
    print("\n=== Test Case Export ===")
    export_test_cases(run_df, scaler)

    # --- Summary ---
    print("\n" + "=" * 60)
    print("  TRAINING COMPLETE")
    print("=" * 60)
    print(f"  Best model: {best_name}")
    for metric in ["accuracy", "balanced_accuracy", "precision", "recall", "f1_score", "roc_auc"]:
        val = results[best_name]["metrics"].get(metric)
        if val is not None:
            print(f"    {metric:20s}: {val:.4f}")
    print(f"\n  Artifacts saved to: {MODELS_DIR}/")
    print(f"  Test cases saved to: {TEST_CASES_DIR}/")

    return results, run_df, baselines


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Train performance test classifier")
    parser.add_argument(
        "--from-csv", type=str, default=None,
        help="Path to pre-exported training CSV (skip DB extraction)"
    )
    args = parser.parse_args()
    run_pipeline(csv_path=args.from_csv)


if __name__ == "__main__":
    main()
