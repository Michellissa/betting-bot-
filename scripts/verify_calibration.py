"""Verify calibration correctness on the best model for each target."""
import asyncio
import sys
from pathlib import Path

import numpy as np
from loguru import logger


sys.path.insert(0, str(Path(__file__).parent.parent))

from betting_bot.database.session import get_async_session
from betting_bot.models.ensemble.ensemble_manager import EnsembleManager
from betting_bot.training.pipelines.base_trainer import BaseTrainer
from betting_bot.training.pipelines.training_pipeline import TrainingPipeline


def expected_calibration_error(y_true, y_proba, n_bins=10):
    """Compute Expected Calibration Error (ECE) and max calibration error."""
    bin_edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    mce = 0.0
    n_total = len(y_true)
    for i in range(n_bins):
        mask = (y_proba >= bin_edges[i]) & (y_proba < bin_edges[i + 1])
        bin_size = mask.sum()
        if bin_size == 0:
            continue
        bin_acc = y_true[mask].mean()
        bin_conf = y_proba[mask].mean()
        gap = abs(bin_acc - bin_conf)
        ece += gap * (bin_size / n_total)
        mce = max(mce, gap)
    return ece, mce


def compute_reliability(y_true, y_proba, n_bins=10):
    """Return bin centers, observed frequencies, and counts for reliability diagram."""
    bin_edges = np.linspace(0, 1, n_bins + 1)
    centers = []
    freqs = []
    counts = []
    for i in range(n_bins):
        mask = (y_proba >= bin_edges[i]) & (y_proba < bin_edges[i + 1])
        bin_size = mask.sum()
        if bin_size == 0:
            continue
        centers.append((bin_edges[i] + bin_edges[i + 1]) / 2)
        freqs.append(y_true[mask].mean())
        counts.append(bin_size)
    return np.array(centers), np.array(freqs), np.array(counts)


async def verify_calibration(target: str, model_name: str | None = None):
    """Train model, calibrate, and produce reliability metrics."""
    async for db in get_async_session():
        pipeline = TrainingPipeline(
            db=db,
            feature_version="v1",
            optimize=False,
            cv_folds=5,
        )
        X, y, feature_names = await pipeline.load_training_data(target)
        if len(X) == 0:
            logger.warning(f"No data for target '{target}'")
            return

        X_train, X_test, y_train, y_test = pipeline.train_test_split(X, y)

        # 80/20 split of training for fit/calibration
        cal_split = int(len(X_train) * 0.8)
        X_fit, X_cal = X_train[:cal_split], X_train[cal_split:]
        y_fit, y_cal = y_train[:cal_split], y_train[cal_split:]

        logger.info(f"Target '{target}': {len(X_fit)} fit, {len(X_cal)} cal, {len(X_test)} test samples")

        # Determine best model if not specified
        if model_name is None:
            from betting_bot.training.pipelines.training_pipeline import TrainingPipeline as TP
            tp = TP(db=db, feature_version="v1", optimize=False, cv_folds=5)
            results = await tp.run(target=target)
            results.sort(key=lambda r: r.test_log_loss if r.test_log_loss > 0 else 999)
            model_name = results[0].model_name
            logger.info(f"Best model for '{target}': {model_name}")

        # Train model
        model = EnsembleManager.create_classifier_from_name(model_name)
        model.fit(X_fit, y_fit)

        # ===== UNCalibrated predictions =====
        y_proba_raw = model.predict_proba(X_test)
        y_pred_raw = y_proba_raw.argmax(axis=1)

        # ===== Calibrated predictions (hand-rolled isotonic) =====
        from sklearn.isotonic import IsotonicRegression
        y_proba_fit = model.predict_proba(X_cal)

        calibrators = []
        for i in range(y_proba_fit.shape[1]):
            iso = IsotonicRegression(out_of_bounds="clip")
            iso.fit(y_proba_fit[:, i], (y_cal == i).astype(float))
            calibrators.append(iso)

        def calibrated_predict_proba(X):
            raw = model.predict_proba(X)
            calibrated = np.column_stack([
                cal.predict(raw[:, i])
                for i, cal in enumerate(calibrators)
            ])
            row_sums = calibrated.sum(axis=1, keepdims=True)
            return calibrated / row_sums

        y_proba_cal = calibrated_predict_proba(X_test)
        y_pred_cal = y_proba_cal.argmax(axis=1)

        raw_metrics = BaseTrainer.compute_metrics(y_test, y_pred_raw, y_proba_raw)
        cal_metrics = BaseTrainer.compute_metrics(y_test, y_pred_cal, y_proba_cal)

        # ===== Monotonicity verification =====
        monotonic = True
        for class_idx in range(y_proba_raw.shape[1]):
            raw_probs = y_proba_raw[:, class_idx]
            cal_probs = y_proba_cal[:, class_idx]
            sort_idx = np.argsort(raw_probs)
            sorted_cal = cal_probs[sort_idx]
            diffs = np.diff(sorted_cal)
            if np.any(diffs < -1e-10):
                n_decreasing = int((diffs < -1e-10).sum())
                logger.warning(f"  Class {class_idx}: {n_decreasing}/{len(diffs)} decreasing steps detected")
                monotonic = False
            else:
                logger.info(f"  Class {class_idx}: monotonicity OK")

        # ===== Reliability (for class 0 = home win in result, or positive for binary) =====
        n_classes = y_proba_raw.shape[1]
        logger.info(f"\n  {'Target':<10} {target}")
        logger.info(f"  {'Classes':<10} {n_classes}")
        logger.info(f"  {'Model':<10} {model_name}")
        logger.info(f"  {'':<10} {'Acc':>6} {'LogLoss':>8} {'Brier':>7} {'ECE':>8} {'MCE':>8}")
        logger.info(f"  {'Raw:':<10} {raw_metrics['accuracy']:>6.3f} {raw_metrics['log_loss']:>8.4f} {raw_metrics['brier']:>7.4f}")
        logger.info(f"  {'Cal:':<10} {cal_metrics['accuracy']:>6.3f} {cal_metrics['log_loss']:>8.4f} {cal_metrics['brier']:>7.4f}")

        # Per-class calibration
        logger.info(f"\n  Per-class calibration (Test set):")
        logger.info(f"  {'Class':<8} {'Raw ECE':>8} {'Cal ECE':>8} {'Raw MCE':>8} {'Cal MCE':>8}")
        for c in range(n_classes):
            y_bin = (y_test == c).astype(float)
            raw_ece, raw_mce = expected_calibration_error(y_bin, y_proba_raw[:, c])
            cal_ece, cal_mce = expected_calibration_error(y_bin, y_proba_cal[:, c])
            logger.info(f"  {c:<8} {raw_ece:>8.4f} {cal_ece:>8.4f} {raw_mce:>8.4f} {cal_mce:>8.4f}")

        # Reliability data for plotting
        logger.info(f"\n  Reliability bins for each class:")
        for c in range(n_classes):
            y_bin = (y_test == c).astype(float)
            _, raw_freqs, raw_counts = compute_reliability(y_bin, y_proba_raw[:, c])
            _, cal_freqs, cal_counts = compute_reliability(y_bin, y_proba_cal[:, c])
            logger.info(f"  Class {c} (before calibration):")
            for bin_conf, bin_freq, count in zip(
                np.linspace(0.05, 0.95, 10), raw_freqs, raw_counts
            ):
                logger.info(f"    [{bin_conf-0.05:.1f}-{bin_conf+0.05:.1f}] n={count:4d}  freq={bin_freq:.3f}")
            logger.info(f"  Class {c} (after calibration):")
            for bin_conf, bin_freq, count in zip(
                np.linspace(0.05, 0.95, 10), cal_freqs, cal_counts
            ):
                logger.info(f"    [{bin_conf-0.05:.1f}-{bin_conf+0.05:.1f}] n={count:4d}  freq={bin_freq:.3f}")

        logger.info(f"  Monotonicity: {'PASS' if monotonic else 'FAIL'}")
        logger.info(f"  Calibration improvement: "
                    f"LL {raw_metrics['log_loss']:.4f} -> {cal_metrics['log_loss']:.4f}, "
                    f"Brier {raw_metrics['brier']:.4f} -> {cal_metrics['brier']:.4f}")

        return {
            "target": target,
            "model": model_name,
            "monotonic": monotonic,
            "raw": raw_metrics,
            "cal": cal_metrics,
        }


async def main():
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    for target in ("result", "over_2_5", "btts"):
        logger.info("=" * 60)
        await verify_calibration(target)
        logger.info("")


if __name__ == "__main__":
    asyncio.run(main())
