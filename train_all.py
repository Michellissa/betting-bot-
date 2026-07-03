"""Compute features + train all models on StatsBomb data."""
import asyncio

import numpy as np
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


from betting_bot.database.session import get_async_session
from betting_bot.features.pipelines.advanced_features import AdvancedFeaturesPipeline
from betting_bot.features.pipelines.base_pipeline import FeatureEngineeringService
from betting_bot.features.pipelines.elo_features import EloFeaturesPipeline
from betting_bot.features.pipelines.form_features import FormFeaturesPipeline
from betting_bot.features.pipelines.goal_features import GoalFeaturesPipeline
from betting_bot.features.pipelines.h2h_features import H2HFeaturesPipeline
from betting_bot.features.pipelines.odds_features import OddsFeaturesPipeline
from betting_bot.features.pipelines.xg_features import XgFeaturesPipeline
from betting_bot.models.match import Match
from betting_bot.training.pipelines.base_trainer import BaseTrainer
from betting_bot.training.pipelines.training_pipeline import TrainingPipeline


async def compute_all_features(db: AsyncSession):
    """Compute features for all finished matches."""
    logger.info("Computing features for all finished matches...")
    svc = FeatureEngineeringService(db, "v1")
    svc.add_pipelines([
        FormFeaturesPipeline(db),
        GoalFeaturesPipeline(db),
        XgFeaturesPipeline(db),
        EloFeaturesPipeline(db),
        H2HFeaturesPipeline(db),
        AdvancedFeaturesPipeline(db),
    ])
    stmt = select(Match.id).where(Match.is_finished).where(Match.result.isnot(None))
    result = await db.execute(stmt)
    match_ids = [row[0] for row in result.all()]
    logger.info(f"Computing features for {len(match_ids)} matches...")
    count = 0
    for i, mid in enumerate(match_ids):
        try:
            features = await svc.compute_match_features(mid)
            if features:
                await svc.store_features(mid, features)
                count += 1
        except Exception as e:
            logger.error(f"Failed match {mid}: {e}")
        if (i + 1) % 200 == 0:
            await db.commit()
            logger.info(f"  Progress: {i+1}/{len(match_ids)} features computed")
    await db.commit()
    logger.info(f"Stored features for {count}/{len(match_ids)} matches")
    return count


async def train_models(db: AsyncSession, target: str):
    """Train models for a specific target."""
    logger.info(f"Training models for target='{target}'...")
    pipeline = TrainingPipeline(
        db=db,
        feature_version="v1",
        optimize=False,
        cv_folds=5,
    )
    results = await pipeline.run(target=target)
    # Sort by log loss (lower is better) to find best model
    results.sort(key=lambda r: r.test_log_loss if r.test_log_loss > 0 else 999)
    logger.info(f"Results for target='{target}':")
    logger.info(f"  {'Model':<25} {'Acc':>6} {'LogLoss':>8} {'Brier':>7} {'F1':>6}")
    logger.info(f"  {'-'*25} {'-'*6} {'-'*8} {'-'*7} {'-'*6}")
    for r in results:
        logger.info(
            f"  {r.model_name:<25} {r.test_accuracy:>6.3f} {r.test_log_loss:>8.4f} "
            f"{r.test_brier:>7.4f} {r.test_f1:>6.3f}"
        )
    best = results[0]
    logger.info(f"Best model for '{target}': {best.model_name} "
                f"(log_loss={best.test_log_loss:.4f}, "
                f"brier={best.test_brier:.4f})")
    return results


async def calibrate_and_evaluate(
    db: AsyncSession,
    target: str,
    results: list,
):
    """Fit probability calibration + re-evaluate on the best model per target.

    Uses the last 20% of the *training* set as a calibration set
    (time-respecting), wraps the model with CalibratedClassifierCV,
    and evaluates on the held-out test set.
    """
    pipeline = TrainingPipeline(
        db=db,
        feature_version="v1",
        optimize=False,
        cv_folds=5,
    )
    X, y, feature_names = await pipeline.load_training_data(target)
    if len(X) == 0:
        return
    X_train, X_test, y_train, y_test = pipeline.train_test_split(X, y)

    # Apply sparse column imputation (odds + player availability)
    X_train, X_test, feature_names, _ = pipeline.impute_sparse_columns(
        X_train, X_test, feature_names,
    )

    # Use last 20% of X_train as calibration set
    cal_split = int(len(X_train) * 0.8)
    X_fit, X_cal = X_train[:cal_split], X_train[cal_split:]
    y_fit, y_cal = y_train[:cal_split], y_train[cal_split:]

    best_result = results[0]
    logger.info(f"Calibrating best model '{best_result.model_name}' for '{target}'...")

    # Recreate the best model
    from betting_bot.models.ensemble.ensemble_manager import EnsembleManager
    model = EnsembleManager.create_classifier_from_name(best_result.model_name)
    model.fit(X_fit, y_fit)

    # Calibrate using isotonic regression on held-out calibration set
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

    # Evaluate calibrated model on test set manually
    y_proba_cal = calibrated_predict_proba(X_test)
    y_pred_cal = y_proba_cal.argmax(axis=1)

    cal_metrics = BaseTrainer.compute_metrics(y_test, y_pred_cal, y_proba_cal)

    logger.info(f"  {'Before/After':<25} {'Acc':>6} {'LogLoss':>8} {'Brier':>7}")
    logger.info(f"  {'Before (uncalibrated):':<25} {best_result.test_accuracy:>6.3f} "
                f"{best_result.test_log_loss:>8.4f} {best_result.test_brier:>7.4f}")
    logger.info(f"  {'After (isotonic):':<25} {cal_metrics['accuracy']:>6.3f} "
                f"{cal_metrics['log_loss']:>8.4f} {cal_metrics['brier']:>7.4f}")

    return {
        "target": target,
        "model": best_result.model_name,
        "before": {
            "accuracy": best_result.test_accuracy,
            "log_loss": best_result.test_log_loss,
            "brier": best_result.test_brier,
        },
        "after": {
            "accuracy": cal_metrics["accuracy"],
            "log_loss": cal_metrics["log_loss"],
            "brier": cal_metrics["brier"],
        },
    }


async def main():
    async for db in get_async_session():
        n = await compute_all_features(db)
        if n == 0:
            logger.error("No features computed. Cannot train.")
            return
        od = OddsFeaturesPipeline(db)
        await od.backfill_all()
        calibration_results = {}
        for target in ("result", "over_2_5", "btts"):
            results = await train_models(db, target)
            cal = await calibrate_and_evaluate(db, target, results)
            if cal:
                calibration_results[target] = cal

        # Final summary
        logger.info("=" * 60)
        logger.info("FINAL SUMMARY — Time-respecting CV + out-of-time holdout")
        logger.info("=" * 60)
        logger.info(f"  {'Target':<12} {'Model':<20} {'Acc':>6} {'LogLoss':>8} {'Brier':>7} {'CalibLogLoss':>13} {'CalibBrier':>12}")
        logger.info(f"  {'-'*12} {'-'*20} {'-'*6} {'-'*8} {'-'*7} {'-'*13} {'-'*12}")
        for target, cal in calibration_results.items():
            logger.info(
                f"  {target:<12} {cal['model']:<20} "
                f"{cal['before']['accuracy']:>6.3f} {cal['before']['log_loss']:>8.4f} {cal['before']['brier']:>7.4f} "
                f"{cal['after']['log_loss']:>13.4f} {cal['after']['brier']:>12.4f}"
            )
        logger.info("All training complete!")


if __name__ == "__main__":
    asyncio.run(main())
