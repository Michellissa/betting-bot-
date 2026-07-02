"""Abstract base class for all ML classifier wrappers."""

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
import numpy.typing as npt


class BaseClassifier(ABC):
    """Abstract base for all classifier wrappers.

    Provides a uniform interface across sklearn, XGBoost, LightGBM, CatBoost.
    """

    @abstractmethod
    def fit(
        self, X: npt.NDArray[np.float64] | np.ndarray, y: npt.NDArray[np.int64] | np.ndarray
    ) -> "BaseClassifier": ...

    @abstractmethod
    def predict(self, X: npt.NDArray[np.float64] | np.ndarray) -> npt.NDArray[np.int64]: ...

    @abstractmethod
    def predict_proba(
        self, X: npt.NDArray[np.float64] | np.ndarray
    ) -> npt.NDArray[np.float64]: ...

    @abstractmethod
    def save(self, path: str | Path) -> None: ...

    @classmethod
    @abstractmethod
    def load(cls, path: str | Path) -> "BaseClassifier": ...

    @property
    @abstractmethod
    def feature_importance(self) -> dict[str, float]: ...

    @property
    @abstractmethod
    def model_type(self) -> str: ...

    @property
    @abstractmethod
    def model_class(self) -> str: ...

    @abstractmethod
    def get_params(self) -> dict: ...

    @abstractmethod
    def set_params(self, **params) -> None: ...

    @property
    def classes_(self) -> list[int]:
        """Return the class labels."""
        return [0, 1, 2]
