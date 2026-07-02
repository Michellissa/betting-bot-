"""Hyperparameter search space definitions for each model type."""

import optuna


def logistic_regression_space(trial: optuna.Trial) -> dict:
    """Search space for LogisticRegression."""
    return {
        "C": trial.suggest_float("C", 1e-4, 10, log=True),
        "penalty": trial.suggest_categorical("penalty", ["l1", "l2", "elasticnet"]),
        "solver": trial.suggest_categorical("solver", ["lbfgs", "liblinear", "saga"]),
        "max_iter": trial.suggest_int("max_iter", 500, 3000, step=500),
        "class_weight": trial.suggest_categorical("class_weight", [None, "balanced"]),
    }


def random_forest_space(trial: optuna.Trial) -> dict:
    """Search space for RandomForestClassifier."""
    return {
        "n_estimators": trial.suggest_int("n_estimators", 100, 1000, step=100),
        "max_depth": trial.suggest_int("max_depth", 5, 30, step=5),
        "min_samples_split": trial.suggest_int("min_samples_split", 2, 20),
        "min_samples_leaf": trial.suggest_int("min_samples_leaf", 1, 10),
        "max_features": trial.suggest_categorical("max_features", ["sqrt", "log2", None]),
        "class_weight": trial.suggest_categorical(
            "class_weight", [None, "balanced", "balanced_subsample"]
        ),
    }


def xgboost_space(trial: optuna.Trial) -> dict:
    """Search space for XGBoost."""
    return {
        "n_estimators": trial.suggest_int("n_estimators", 100, 1000, step=100),
        "max_depth": trial.suggest_int("max_depth", 3, 12),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
        "gamma": trial.suggest_float("gamma", 0, 5),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-4, 10, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-4, 10, log=True),
    }


def lightgbm_space(trial: optuna.Trial) -> dict:
    """Search space for LightGBM."""
    return {
        "n_estimators": trial.suggest_int("n_estimators", 100, 1000, step=100),
        "num_leaves": trial.suggest_int("num_leaves", 15, 127),
        "max_depth": trial.suggest_int("max_depth", 3, 15),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "min_child_samples": trial.suggest_int("min_child_samples", 5, 50),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-4, 10, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-4, 10, log=True),
    }


def catboost_space(trial: optuna.Trial) -> dict:
    """Search space for CatBoost."""
    return {
        "iterations": trial.suggest_int("iterations", 200, 1000, step=100),
        "depth": trial.suggest_int("depth", 4, 10),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
        "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1, 10),
        "border_count": trial.suggest_int("border_count", 32, 255),
    }


SEARCH_SPACES: dict[str, callable] = {
    "logistic_regression": logistic_regression_space,
    "random_forest": random_forest_space,
    "xgboost": xgboost_space,
    "lightgbm": lightgbm_space,
    "catboost": catboost_space,
}


def get_search_space(model_name: str) -> callable:
    """Get the search space function for a given model name."""
    space_fn = SEARCH_SPACES.get(model_name)
    if space_fn is None:
        raise ValueError(f"No search space defined for model: {model_name}")
    return space_fn
