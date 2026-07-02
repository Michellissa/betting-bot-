"""Abstract base class for all ML regressor wrappers."""

from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np
import numpy.typing as npt


class BaseRegressor(ABC):
    """Abstract base for all regressor wrappers."""

    @abstractmethod
    def fit(
        self, X: npt.NDArray[np.float64] | np.ndarray, y: npt.NDArray[np.float64] | np.ndarray
    ) -> "BaseRegressor": ...

    @abstractmethod
    def predict(self, X: npt.NDArray[np.float64] | np.ndarray) -> npt.NDArray[np.float64]: ...

    @abstractmethod
    def save(self, path: str | Path) -> None: ...

    @classmethod
    @abstractmethod
    def load(cls, path: str | Path) -> "BaseRegressor": ...

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
