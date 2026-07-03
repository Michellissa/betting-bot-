"""Compute trivial baselines (majority class, base-rate probability) for all targets."""
import asyncio
import sys
from pathlib import Path

import numpy as np
from loguru import logger
from sklearn.metrics import accuracy_score, log_loss, brier_score_loss

sys.path.insert(0, str(Path(__file__).parent.parent))

from betting_bot.database.session import get_async_session
from betting_bot.training.pipelines.training_pipeline import TrainingPipeline
from betting_bot.training.pipelines.base_trainer import BaseTrainer


async def main():
    logger.remove()
    logger.add(sys.stderr, level="INFO")

    async for db in get_async_session():
        logger.info(f"{'='*60}")
        logger.info(f"{'Target':<12} {'Baseline':<25} {'Acc':>6} {'LogLoss':>8} {'Brier':>7}")
        logger.info(f"{'='*60}")

        for target in ("result", "over_2_5", "btts"):
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

            n_classes = len(np.unique(y))
            test_counts = np.bincount(y_test, minlength=n_classes)

            # --- Majority class baseline ---
            majority_class = np.argmax(test_counts)
            y_pred_majority = np.full_like(y_test, majority_class)
            y_proba_majority = np.zeros((len(y_test), n_classes))
            y_proba_majority[:, majority_class] = 1.0

            maj_acc = accuracy_score(y_test, y_pred_majority)
            maj_ll = log_loss(y_test, y_proba_majority)
            if n_classes == 2:
                maj_brier = brier_score_loss(y_test, y_proba_majority[:, 1])
            else:
                maj_brier = np.mean([
                    (y_test == c).astype(float) - y_proba_majority[:, c]
                    for c in range(n_classes)
                ]) ** 2

            logger.info(
                f"  {target:<12} {'Majority class':<25} "
                f"{maj_acc:>6.3f} {maj_ll:>8.4f}"
            )

            # --- Base-rate probability baseline ---
            train_counts = np.bincount(y_train, minlength=n_classes)
            base_rates = train_counts / train_counts.sum()

            y_proba_base = np.tile(base_rates, (len(y_test), 1))
            y_pred_base = y_proba_base.argmax(axis=1)

            base_acc = accuracy_score(y_test, y_pred_base)
            base_ll = log_loss(y_test, y_proba_base)
            if n_classes == 2:
                base_brier = brier_score_loss(y_test, y_proba_base[:, 1])
            else:
                multi_brier = 0.0
                for c in range(n_classes):
                    y_bin = (y_test == c).astype(float)
                    multi_brier += np.mean((y_bin - y_proba_base[:, c]) ** 2)
                base_brier = multi_brier

            logger.info(
                f"  {target:<12} {'Base-rate probability':<25} "
                f"{base_acc:>6.3f} {base_ll:>8.4f} {base_brier:>7.4f}"
            )

            # Also report training/test class distribution
            train_dist = dict(zip(range(n_classes), train_counts))
            test_dist = dict(zip(range(n_classes), test_counts))
            logger.info(f"  {'':<12} {'Train dist:':<25} {train_dist}")
            logger.info(f"  {'':<12} {'Test dist:':<25} {test_dist}")
            logger.info("")


if __name__ == "__main__":
    asyncio.run(main())
