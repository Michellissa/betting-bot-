"""Split holdout into odds-present vs odds-absent groups and report metrics."""
import asyncio
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


sys.path.insert(0, str(Path(__file__).parent.parent))

from betting_bot.database.session import get_async_session
from betting_bot.models.feature import FeatureStore
from betting_bot.models.match import Match
from betting_bot.models.ensemble.ensemble_manager import EnsembleManager
from betting_bot.training.pipelines.base_trainer import BaseTrainer
from betting_bot.training.pipelines.training_pipeline import TrainingPipeline


def split_by_odds_presence(
    X_test: np.ndarray, y_test: np.ndarray, feature_names: list[str], match_test_ids: list[int], db
):
    """Split test set into rows where odds features are present vs absent."""
    if "odds_missing" in feature_names:
        odds_missing_idx = feature_names.index("odds_missing")
        odds_idx = np.where(X_test[:, odds_missing_idx] == 0)[0]
        no_odds_idx = np.where(X_test[:, odds_missing_idx] == 1)[0]
    else:
        # Fall back to old method
        odds_idx = np.where(X_test[:, feature_names.index("odds_home_prob")] > 0)[0]
        no_odds_idx = np.where(X_test[:, feature_names.index("odds_home_prob")] == 0)[0]

    return odds_idx, no_odds_idx


def compute_metrics_binary(y_true, y_proba, target):
    """Compute acc/log_loss/brier for binary or multi-class."""
    if target == "result":
        y_pred = y_proba.argmax(axis=1)
        return BaseTrainer.compute_metrics(y_true, y_pred, y_proba)
    else:
        # Binary: y_proba is (n, 2) or (n,) - handle both
        if y_proba.ndim == 2:
            y_prob_pos = y_proba[:, 1]
        else:
            y_prob_pos = y_proba
        y_pred = (y_prob_pos >= 0.5).astype(int)
        return BaseTrainer.compute_metrics(y_true, y_pred, y_proba)


async def run():
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    async for db in get_async_session():
        for target in ("result", "over_2_5", "btts"):
            logger.info(f"\n{'='*60}")
            logger.info(f"TARGET: {target}")

            pipeline = TrainingPipeline(
                db=db,
                feature_version="v1",
                optimize=False,
                cv_folds=5,
            )
            X, y, feature_names = await pipeline.load_training_data(target)
            if len(X) == 0:
                continue

            X_train, X_test, y_train, y_test = pipeline.train_test_split(X, y)

            # Find best model
            results = await pipeline.run(target=target)
            results.sort(key=lambda r: r.test_log_loss if r.test_log_loss > 0 else 999)
            best = results[0]
            model_name = best.model_name

            # Train model
            cal_split = int(len(X_train) * 0.8)
            X_fit, X_cal = X_train[:cal_split], X_train[cal_split:]
            y_fit, y_cal = y_train[:cal_split], y_train[cal_split:]

            model = EnsembleManager.create_classifier_from_name(model_name)
            model.fit(X_fit, y_fit)

            # Hand-rolled isotonic calibration
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
                    cal.predict(raw[:, i]) for i, cal in enumerate(calibrators)
                ])
                return calibrated / calibrated.sum(axis=1, keepdims=True)

            y_proba_raw = model.predict_proba(X_test)
            y_proba_cal = calibrated_predict_proba(X_test)

            # Split test by odds presence using odds_missing indicator
            if "odds_missing" in feature_names:
                odds_missing_idx = feature_names.index("odds_missing")
                odds_mask = X_test[:, odds_missing_idx] == 0  # 0 = odds present
            else:
                odds_home_idx = feature_names.index("odds_home_prob")
                odds_mask = X_test[:, odds_home_idx] > 0
            n_present = int(odds_mask.sum())
            n_absent = int((~odds_mask).sum())
            logger.info(f"  Odds present: {n_present}, Odds absent: {n_absent}")

            def report_group(name, idx, y_true, y_proba_raw, y_proba_cal):
                if len(idx) == 0:
                    logger.info(f"  {name}: no samples")
                    return
                yg = y_true[idx]
                r_raw = compute_metrics_binary(yg, y_proba_raw[idx], target)
                r_cal = compute_metrics_binary(yg, y_proba_cal[idx], target)
                logger.info(f"  {name} (n={len(idx)}):")
                logger.info(f"    {'':<12} {'Acc':>6} {'LogLoss':>8} {'Brier':>7}")
                logger.info(f"    {'Raw:':<12} {r_raw['accuracy']:>6.3f} {r_raw['log_loss']:>8.4f} {r_raw['brier']:>7.4f}")
                logger.info(f"    {'Cal:':<12} {r_cal['accuracy']:>6.3f} {r_cal['log_loss']:>8.4f} {r_cal['brier']:>7.4f}")

            report_group("With odds", np.where(odds_mask)[0], y_test, y_proba_raw, y_proba_cal)
            report_group("Without odds", np.where(~odds_mask)[0], y_test, y_proba_raw, y_proba_cal)
            report_group("All test", np.arange(len(y_test)), y_test, y_proba_raw, y_proba_cal)


if __name__ == "__main__":
    asyncio.run(run())
