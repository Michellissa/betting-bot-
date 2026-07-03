"""Prediction generation service."""

from datetime import datetime
from pathlib import Path

import numpy as np
import numpy.typing as npt
from loguru import logger
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from betting_bot.core.config import get_settings
from betting_bot.core.constants import ConfidenceLevel, RiskLevel
from betting_bot.database.repositories.base import BaseRepository
from betting_bot.features.pipelines.base_pipeline import FeatureEngineeringService
from betting_bot.models.classifiers.base_classifier import BaseClassifier
from betting_bot.models.feature import FeatureStore
from betting_bot.models.match import Match
from betting_bot.models.model_registry import ModelRegistry
from betting_bot.models.prediction import ModelPrediction, Prediction


class PredictionGenerator:
    """Generates predictions for matches using trained models."""

    def __init__(
        self,
        db: AsyncSession,
        model_name: str | None = None,
        feature_version: str | None = None,
    ) -> None:
        self.db = db
        settings = get_settings()
        self.feature_version = feature_version or settings.TRAINING_FEATURE_VERSION
        self.model_name = model_name

    async def load_model_from_registry(
        self, model_name: str | None = None, target_variable: str | None = None
    ) -> tuple[BaseClassifier, dict]:
        """Load the best active model from registry."""
        name = model_name or self.model_name

        stmt = (
            select(ModelRegistry)
            .where(ModelRegistry.is_active)
            .order_by(desc(ModelRegistry.training_date))
        )
        if name:
            stmt = stmt.where(ModelRegistry.model_name == name)
        if target_variable:
            stmt = stmt.where(ModelRegistry.target_variable == target_variable)

        result = await self.db.execute(stmt)
        registry_entry = result.scalar_one_or_none()

        if registry_entry is None:
            msg = "No active model found"
            if name:
                msg += f" for '{name}'"
            raise ValueError(msg)

        model_path = Path(registry_entry.model_path)
        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        classifier = self._load_classifier(
            str(model_path),
            registry_entry.model_class,
        )

        return classifier, {
            "id": registry_entry.id,
            "model_name": registry_entry.model_name,
            "model_version": registry_entry.model_version,
            "feature_version": registry_entry.feature_version,
        }

    async def _load_model_by_target(self, target: str) -> tuple[BaseClassifier, dict] | None:
        """Load the best active model for a specific target type."""
        stmt = (
            select(ModelRegistry)
            .where(ModelRegistry.is_active)
            .where(ModelRegistry.target_variable == target)
            .order_by(desc(ModelRegistry.training_date))
        )
        result = await self.db.execute(stmt)
        entry = result.scalar_one_or_none()
        if entry is None:
            return None
        model_path = Path(entry.model_path)
        if not model_path.exists():
            return None
        classifier = self._load_classifier(str(model_path), entry.model_class)
        info = {
            "model_name": entry.model_name,
            "model_version": entry.model_version,
            "feature_version": entry.feature_version,
        }
        return classifier, info

    @staticmethod
    def _load_classifier(path: str, model_class: str) -> BaseClassifier:
        """Load a classifier from disk by class name."""
        from betting_bot.models.classifiers.catboost_classifier import CatBoostClassifier
        from betting_bot.models.classifiers.lightgbm_classifier import LightGBMClassifier
        from betting_bot.models.classifiers.logistic_regression import (
            LogisticRegressionClassifier,
        )
        from betting_bot.models.classifiers.random_forest import RandomForestClassifier
        from betting_bot.models.classifiers.xgboost_classifier import XGBoostClassifier
        from betting_bot.models.ensemble.voting_ensemble import VotingEnsemble

        registry = {
            "LogisticRegression": LogisticRegressionClassifier,
            "RandomForestClassifier": RandomForestClassifier,
            "XGBClassifier": XGBoostClassifier,
            "LGBMClassifier": LightGBMClassifier,
            "CatBoostClassifier": CatBoostClassifier,
            "VotingEnsemble": VotingEnsemble,
        }
        cls_type = registry.get(model_class)
        if cls_type is None:
            raise ValueError(f"Unknown model class: {model_class}")
        return cls_type.load(path)

    @staticmethod
    def _load_regressor(path: str, model_class: str):
        """Load a regressor from disk by class name."""
        from betting_bot.models.classifiers.xgboost_regressor import XGBoostRegressor
        registry = {
            "XGBRegressor": XGBoostRegressor,
        }
        cls_type = registry.get(model_class)
        if cls_type is None:
            raise ValueError(f"Unknown regressor class: {model_class}")
        return cls_type.load(path)

    async def _load_regressor_by_target(self, target: str):
        """Load the best active regressor for a target."""
        stmt = (
            select(ModelRegistry)
            .where(ModelRegistry.is_active)
            .where(ModelRegistry.target_variable == target)
            .where(ModelRegistry.is_classifier.is_(False))
            .order_by(desc(ModelRegistry.training_date))
        )
        result = await self.db.execute(stmt)
        entry = result.scalar_one_or_none()
        if entry is None:
            return None, None
        path = Path(entry.model_path)
        if not path.exists():
            return None, None
        reg = self._load_regressor(str(path), entry.model_class)
        info = {
            "model_name": entry.model_name,
            "model_version": entry.model_version,
            "feature_version": entry.feature_version,
        }
        return reg, info

    async def get_features_for_match(
        self, match_id: int
    ) -> tuple[npt.NDArray[np.float64], list[str]]:
        """Get feature vector for a match from FeatureStore."""
        repo = BaseRepository(FeatureStore, self.db)
        fs = await repo.get_by(match_id=match_id, feature_version=self.feature_version)

        if fs is None:
            logger.info(f"No features found for match {match_id}, computing...")
            svc = FeatureEngineeringService(self.db, self.feature_version)
            from betting_bot.features.pipelines.advanced_features import AdvancedFeaturesPipeline
            from betting_bot.features.pipelines.elo_features import EloFeaturesPipeline
            from betting_bot.features.pipelines.form_features import FormFeaturesPipeline
            from betting_bot.features.pipelines.goal_features import GoalFeaturesPipeline
            from betting_bot.features.pipelines.h2h_features import H2HFeaturesPipeline
            from betting_bot.features.pipelines.xg_features import XgFeaturesPipeline

            svc.add_pipelines([
                FormFeaturesPipeline(self.db),
                GoalFeaturesPipeline(self.db),
                XgFeaturesPipeline(self.db),
                EloFeaturesPipeline(self.db),
                H2HFeaturesPipeline(self.db),
                AdvancedFeaturesPipeline(self.db),
            ])
            features = await svc.compute_match_features(match_id)
            if features:
                await svc.store_features(match_id, features)
                await self.db.commit()
            fs = await repo.get_by(match_id=match_id, feature_version=self.feature_version)

        if fs is None:
            raise ValueError(f"Could not compute features for match {match_id}")

        # Build feature vector matching training columns
        feature_columns = [
            col.name for col in FeatureStore.__table__.columns
            if col.name not in (
                "id", "match_id", "feature_version",
                "created_at", "updated_at",
                "temperature", "humidity", "wind_speed", "weather_condition",
                "referee_id", "referee_home_win_rate",
                "odds_source", "player_data_available",
            )
        ]
        sparse_cols = [
            "odds_home_prob", "odds_draw_prob", "odds_away_prob",
            "odds_overround", "odds_home_odds_raw", "odds_draw_odds_raw",
            "odds_away_odds_raw",
            "home_missing_players_count", "away_missing_players_count",
        ]
        values = []
        active_columns = []
        for col in feature_columns:
            val = getattr(fs, col, None)
            if col in sparse_cols:
                values.append(float(val) if val is not None else np.nan)
            else:
                values.append(float(val) if val is not None else 0.0)
            active_columns.append(col)

        # Add odds_missing indicator
        odds_cols_subset = sparse_cols[:7]
        odds_none = any(getattr(fs, c, None) is None for c in odds_cols_subset if c in feature_columns)
        values.append(1.0 if odds_none else 0.0)
        active_columns.append("odds_missing")

        # Add player_data_missing indicator
        player_cols_subset = ["home_missing_players_count", "away_missing_players_count"]
        player_none = any(getattr(fs, c, None) is None for c in player_cols_subset if c in feature_columns)
        values.append(1.0 if player_none else 0.0)
        active_columns.append("player_data_missing")

        return np.array([values], dtype=np.float64), active_columns

    @staticmethod
    def _apply_odds_imputation(
        X: npt.NDArray[np.float64],
        clf: BaseClassifier,
    ) -> npt.NDArray[np.float64]:
        """Apply training-time odds imputation to inference features.

        Uses stored medians from the classifier's ``_odds_imputer``.
        Models with native NaN support (RF, XGBoost, etc.) skip imputation.
        """
        imputer = getattr(clf, "_odds_imputer", None)
        if imputer is None or not imputer.get("odds_medians"):
            return X

        indices = imputer.get("odds_column_indices", [])
        medians = imputer["odds_medians"]
        for col_idx, median in zip(indices, medians):
            if np.isnan(X[0, col_idx]):
                X[0, col_idx] = median

        return X

    async def predict_match(
        self,
        match_id: int,
        model_name: str | None = None,
    ) -> Prediction | None:
        """Generate a prediction for a single match.

        Predicts match result (H/D/A), over/under 2.5 goals,
        and both teams to score (BTTS) using separate trained models.
        Falls back gracefully if a specific target model is unavailable.
        """
        # --- Load result model ---
        try:
            result_clf, result_info = await self.load_model_from_registry(model_name, target_variable="result")
        except (ValueError, FileNotFoundError) as e:
            logger.error(f"Cannot load result model: {e}")
            return None

        match_repo = BaseRepository(Match, self.db)
        match = await match_repo.get(match_id)
        if match is None:
            logger.error(f"Match {match_id} not found")
            return None

        try:
            X, _feature_names = await self.get_features_for_match(match_id)
        except ValueError as e:
            logger.error(f"Cannot get features: {e}")
            return None

        # Apply odds imputation using stored model medians
        X = self._apply_odds_imputation(X, result_clf)

        # Load FeatureStore for expected goals computation
        fs_repo = BaseRepository(FeatureStore, self.db)
        fs = await fs_repo.get_by(match_id=match_id, feature_version=self.feature_version)

        # --- Predict match result (H/D/A) ---
        proba = result_clf.predict_proba(X)[0]
        n_classes = len(proba)
        home_win_prob = float(proba[0]) if n_classes > 0 else 0.33
        draw_prob = float(proba[1]) if n_classes > 1 else 0.33
        away_win_prob = float(proba[2]) if n_classes > 2 else 0.34

        # --- Predict Over/Under 2.5 ---
        over_2_5_prob = None
        under_2_5_prob = None
        try:
            o25_clf, _ = await self._load_model_by_target("over_2_5")
            if o25_clf is not None:
                o25_proba = o25_clf.predict_proba(X)[0]
                under_2_5_prob = float(o25_proba[0])
                over_2_5_prob = float(o25_proba[1])
        except Exception as e:
            logger.debug(f"Over/Under 2.5 model unavailable: {e}")

        # --- Predict BTTS ---
        btts_yes_prob = None
        btts_no_prob = None
        try:
            btts_clf, _ = await self._load_model_by_target("btts")
            if btts_clf is not None:
                btts_proba = btts_clf.predict_proba(X)[0]
                btts_no_prob = float(btts_proba[0])
                btts_yes_prob = float(btts_proba[1])
        except Exception as e:
            logger.debug(f"BTTS model unavailable: {e}")

        # --- Predict expected goals (use regression models if available) ---
        home_expected_goals, away_expected_goals = await self._predict_goals(X, fs)

        # --- Generate explanation (use string refs to avoid lazy-load in sync method) ---
        is_knockout = bool(match.league and match.league.name and "World Cup" in match.league.name and match.round and match.round >= 4)
        explanation = self._generate_explanation(
            result_clf, fs, _feature_names,
            home_win_prob, draw_prob, away_win_prob,
            over_2_5_prob, btts_yes_prob,
            home_expected_goals, away_expected_goals,
            home_name=match.home_team.name if match.home_team else None,
            away_name=match.away_team.name if match.away_team else None,
            competition=match.league.name if match.league else None,
            stage=str(match.round) if match.round else None,
            is_knockout=is_knockout,
        )

        # --- Confidence & Risk ---
        sorted_probs = sorted([home_win_prob, draw_prob, away_win_prob], reverse=True)
        confidence_score = sorted_probs[0] - sorted_probs[1]
        confidence_level = ConfidenceLevel.from_score(confidence_score).value

        risk_score = 1.0 - confidence_score
        risk_level = RiskLevel.from_value(risk_score).value

        # --- Store prediction ---
        prediction_data = {
            "match_id": match_id,
            "model_name": result_info["model_name"],
            "feature_version": result_info["feature_version"],
            "model_version": result_info["model_version"],
            "home_win_probability": home_win_prob,
            "draw_probability": draw_prob,
            "away_win_probability": away_win_prob,
            "over_2_5_probability": over_2_5_prob,
            "under_2_5_probability": under_2_5_prob,
            "btts_yes_probability": btts_yes_prob,
            "btts_no_probability": btts_no_prob,
            "home_expected_goals": home_expected_goals,
            "away_expected_goals": away_expected_goals,
            "confidence_score": confidence_score,
            "confidence_level": confidence_level,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "prediction_date": datetime.utcnow(),
            "explanation": explanation,
        }

        repo = BaseRepository(Prediction, self.db)
        prediction = await repo.create(**prediction_data)

        # Store model-specific prediction
        model_pred_repo = BaseRepository(ModelPrediction, self.db)
        await model_pred_repo.create(
            match_id=match_id,
            prediction_id=prediction.id,
            model_name=result_info["model_name"],
            home_win_probability=home_win_prob,
            draw_probability=draw_prob,
            away_win_probability=away_win_prob,
        )

        await self.db.commit()
        logger.info(
            f"Prediction for match {match_id}: "
            f"H={home_win_prob:.3f} D={draw_prob:.3f} A={away_win_prob:.3f} | "
            f"O2.5={over_2_5_prob:.3f} BTTS={btts_yes_prob:.3f} "
            f"(confidence={confidence_score:.3f})"
        )
        return prediction

    @staticmethod
    def _generate_explanation(
        model: BaseClassifier,
        fs: FeatureStore | None,
        feature_names: list[str],
        home_win_prob: float,
        draw_prob: float,
        away_win_prob: float,
        over_2_5_prob: float | None = None,
        btts_yes_prob: float | None = None,
        home_expected_goals: float | None = None,
        away_expected_goals: float | None = None,
        home_name: str | None = None,
        away_name: str | None = None,
        competition: str | None = None,
        stage: str | None = None,
        is_knockout: bool = False,
    ) -> str | None:
        """Generate human-readable explanation for the prediction."""
        if fs is None:
            return None

        try:
            importances = model.feature_importance
        except Exception:
            return None

        if not importances:
            return None

        # Determine predicted outcome
        max_prob = max(home_win_prob, draw_prob, away_win_prob)
        if max_prob == home_win_prob:
            outcome_label = "Home win"
        elif max_prob == draw_prob:
            outcome_label = "Draw"
        else:
            outcome_label = "Away win"

        # Match context
        home_name = home_name or "Home"
        away_name = away_name or "Away"
        competition = competition or ""
        stage = stage or ""

        # Feature name to human-readable template (uses team names)
        desc_map: dict[str, str] = {
            "home_goals_scored_avg_5": f"{home_name} scores {{v}} goals/game (last 5)",
            "home_goals_conceded_avg_5": f"{home_name} concedes {{v}} goals/game (last 5)",
            "away_goals_scored_avg_5": f"{away_name} scores {{v}} goals/game (last 5)",
            "away_goals_conceded_avg_5": f"{away_name} concedes {{v}} goals/game (last 5)",
            "home_goals_scored_avg_10": f"{home_name} scores {{v}} goals/game (last 10)",
            "away_goals_scored_avg_10": f"{away_name} scores {{v}} goals/game (last 10)",
            "home_goals_conceded_avg_10": f"{home_name} concedes {{v}} goals/game (last 10)",
            "away_goals_conceded_avg_10": f"{away_name} concedes {{v}} goals/game (last 10)",
            "home_form_last_5": f"{home_name} form: {{v}} pts/game (last 5)",
            "away_form_last_5": f"{away_name} form: {{v}} pts/game (last 5)",
            "home_points_last_5": f"{home_name} earned {{v}} pts (last 5)",
            "away_points_last_5": f"{away_name} earned {{v}} pts (last 5)",
            "home_points_last_10": f"{home_name} earned {{v}} pts (last 10)",
            "away_points_last_10": f"{away_name} earned {{v}} pts (last 10)",
            "elo_diff": f"Elo difference: {{v}} (positive favors home)",
            "home_elo": f"{home_name} Elo: {{v:.0f}}",
            "away_elo": f"{away_name} Elo: {{v:.0f}}",
            "home_attack_strength": f"{home_name} attack strength: {{v}}",
            "away_attack_strength": f"{away_name} attack strength: {{v}}",
            "home_defense_strength": f"{home_name} defense strength: {{v}}",
            "away_defense_strength": f"{away_name} defense strength: {{v}}",
            "h2h_home_goals_avg": f"{home_name} avg {{v}} goals vs this opponent",
            "h2h_away_goals_avg": f"{away_name} avg {{v}} goals vs this opponent",
            "h2h_home_win_rate": f"{home_name} won {{v:.0%}} of H2H matches",
            "h2h_away_win_rate": f"{away_name} won {{v:.0%}} of H2H matches",
            "h2h_matches_played": f"H2H matches played: {{v}}",
            "h2h_over_2_5_rate": f"H2H over 2.5 rate: {{v:.0%}}",
            "h2h_btts_rate": f"H2H BTTS rate: {{v:.0%}}",
            "home_clean_sheet_rate_5": f"{home_name} clean sheet: {{v:.0%}} (last 5)",
            "away_clean_sheet_rate_5": f"{away_name} clean sheet: {{v:.0%}} (last 5)",
            "home_scoring_streak": f"{home_name} scoring streak: {{v}} games",
            "away_scoring_streak": f"{away_name} scoring streak: {{v}} games",
            "home_rest_days": f"{home_name} rest: {{v}} days",
            "away_rest_days": f"{away_name} rest: {{v}} days",
            "home_possession_avg_5": f"{home_name} possession: {{v:.0%}}",
            "away_possession_avg_5": f"{away_name} possession: {{v:.0%}}",
            "home_shots_on_target_avg_5": f"{home_name} SoT: {{v}}/game (last 5)",
            "away_shots_on_target_avg_5": f"{away_name} SoT: {{v}}/game (last 5)",
            "home_xg_avg_5": f"{home_name} xG: {{v}}/game (last 5)",
            "away_xg_avg_5": f"{away_name} xG: {{v}}/game (last 5)",
            "home_xg_diff": f"{home_name} xG diff: {{v}}",
            "away_xg_diff": f"{away_name} xG diff: {{v}}",
        }

        # Get top 5 features by importance that have a description
        sorted_feats = sorted(importances.items(), key=lambda x: x[1], reverse=True)
        bullets: list[str] = []
        for feat_name, _ in sorted_feats:
            if len(bullets) >= 4:
                break
            template = desc_map.get(feat_name)
            if template is None:
                continue
            val = getattr(fs, feat_name, None)
            if val is None:
                continue
            try:
                bullets.append(template.format(v=round(val, 2)))
            except (ValueError, KeyError):
                continue

        lines: list[str] = []

        # Header with match context and outcome
        if competition:
            header = f"{competition}"
            header += f" Stage {stage}" if stage else ""
            lines.append(header)

        # Outcome
        if is_knockout:
            lines.append(
                f"Model predicts {outcome_label} in regulation "
                f"({home_name} {home_win_prob*100:.0f}% / Draw->ET/Pens {draw_prob*100:.0f}% / {away_name} {away_win_prob*100:.0f}%)"
            )
            lines.append("Knockout match: a draw leads to extra time and penalties")
        else:
            lines.append(
                f"Model predicts {outcome_label} "
                f"({home_name} {home_win_prob*100:.0f}% / Draw {draw_prob*100:.0f}% / {away_name} {away_win_prob*100:.0f}%)"
            )

        # Predicted score
        if home_expected_goals is not None and away_expected_goals is not None:
            lines.append(
                f"Predicted score: {home_name} {round(home_expected_goals)}-{round(away_expected_goals)} {away_name}"
            )

        # Feature bullets
        if bullets:
            lines.append("Key factors:")
            lines.extend(f"  - {b}" for b in bullets)

        # Additional model outputs
        extra: list[str] = []
        if over_2_5_prob is not None:
            extra.append(f"Over 2.5 goals: {over_2_5_prob*100:.0f}%")
        if btts_yes_prob is not None:
            extra.append(f"Both teams to score: {btts_yes_prob*100:.0f}%")
        if extra:
            lines.append("Additional: " + " | ".join(extra))

        return "\n".join(lines)

    async def _predict_goals(
        self, X: npt.NDArray[np.float64], fs: FeatureStore | None
    ) -> tuple[float, float]:
        """Predict goals using trained regression models, fall back to heuristic."""
        try:
            home_reg, _ = await self._load_regressor_by_target("home_goals")
            away_reg, _ = await self._load_regressor_by_target("away_goals")
            if home_reg is not None and away_reg is not None:
                # Handle dimension mismatch: regressors may not have odds_missing
                n_expected = getattr(home_reg._model, "n_features_in_", X.shape[1])
                X_reg = X[:, :n_expected] if X.shape[1] > n_expected else X
                home_pred = float(home_reg.predict(X_reg)[0])
                away_pred = float(away_reg.predict(X_reg)[0])
                return max(0.0, home_pred), max(0.0, away_pred)
        except Exception as e:
            logger.debug(f"Goal regression unavailable: {e}")
        return self._compute_expected_goals_heuristic(fs)

    @staticmethod
    def _compute_expected_goals_heuristic(fs: FeatureStore | None) -> tuple[float, float]:
        """Fallback heuristic when regression models aren't available."""
        if fs is None:
            return 0.0, 0.0
        home_attack = getattr(fs, "home_xg_avg_5", None) or getattr(fs, "home_goals_scored_avg_5", None) or 0.0
        away_defense = getattr(fs, "away_xga_avg_5", None) or getattr(fs, "away_goals_conceded_avg_5", None) or 0.0
        away_attack = getattr(fs, "away_xg_avg_5", None) or getattr(fs, "away_goals_scored_avg_5", None) or 0.0
        home_defense = getattr(fs, "home_xga_avg_5", None) or getattr(fs, "home_goals_conceded_avg_5", None) or 0.0
        home_xg = max(0.0, (home_attack + away_defense) / 2.0)
        away_xg = max(0.0, (away_attack + home_defense) / 2.0)
        home_attack_10 = getattr(fs, "home_xg_avg_10", None) or getattr(fs, "home_goals_scored_avg_10", None) or home_attack
        away_defense_10 = getattr(fs, "away_xga_avg_10", None) or getattr(fs, "away_goals_conceded_avg_10", None) or away_defense
        away_attack_10 = getattr(fs, "away_xg_avg_10", None) or getattr(fs, "away_goals_scored_avg_10", None) or away_attack
        home_defense_10 = getattr(fs, "home_xga_avg_10", None) or getattr(fs, "home_goals_conceded_avg_10", None) or home_defense
        home_xg_10 = max(0.0, (home_attack_10 + away_defense_10) / 2.0)
        away_xg_10 = max(0.0, (away_attack_10 + home_defense_10) / 2.0)
        home_final = round(home_xg * 0.6 + home_xg_10 * 0.4, 2)
        away_final = round(away_xg * 0.6 + away_xg_10 * 0.4, 2)
        return home_final, away_final

    async def predict_upcoming_matches(
        self,
        league_id: int | None = None,
        limit: int = 50,
    ) -> list[Prediction]:
        """Generate predictions for upcoming unfinished matches."""
        stmt = (
            select(Match)
            .where(Match.is_finished.is_(False))
            .where(Match.is_postponed.is_(False))
            .order_by(Match.match_date)
            .limit(limit)
        )
        if league_id:
            stmt = stmt.where(Match.league_id == league_id)

        result = await self.db.execute(stmt)
        matches = result.scalars().all()

        predictions = []
        for match in matches:
            pred = await self.predict_match(match.id)
            if pred:
                predictions.append(pred)

        logger.info(f"Generated {len(predictions)} predictions for upcoming matches")
        return predictions
