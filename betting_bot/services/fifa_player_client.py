"""Client for FIFA player dataset from Kaggle."""
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

FIFA_DATASET_PATH = Path(
    "~/.cache/kagglehub/datasets/maso0dahmed/football-players-data/versions/1/fifa_players.csv"
).expanduser()


class FIFAPlayerClient:
    """Client for loading and querying FIFA player attributes."""

    def __init__(self, csv_path: str | Path | None = None) -> None:
        self.csv_path = Path(csv_path or FIFA_DATASET_PATH)
        self._df: pd.DataFrame | None = None

    def load(self) -> pd.DataFrame:
        """Load the dataset into memory."""
        if self._df is not None:
            return self._df
        path = self.csv_path
        if not path.exists():
            raise FileNotFoundError(
                f"FIFA dataset not found at {path}. "
                "Download first via: "
                "import kagglehub; kagglehub.dataset_download('maso0dahmed/football-players-data')"
            )
        logger.info(f"Loading FIFA players from {path}")
        self._df = pd.read_csv(path, encoding="latin1")
        logger.info(f"Loaded {len(self._df)} players, {len(self._df.columns)} columns")
        return self._df

    @property
    def df(self) -> pd.DataFrame:
        if self._df is None:
            return self.load()
        return self._df

    def search_player(self, name: str, top_n: int = 5) -> pd.DataFrame:
        """Search for a player by name (case-insensitive partial match)."""
        mask = self.df["name"].str.contains(name, case=False, na=False)
        return self.df[mask].head(top_n)

    def get_top_players(self, column: str = "overall_rating", top_n: int = 20) -> pd.DataFrame:
        """Get top N players by a given column."""
        return self.df.nlargest(top_n, column)[
            ["name", "full_name", column, "age", "positions", "nationality"]
        ]

    def get_players_by_position(self, position: str, top_n: int = 50) -> pd.DataFrame:
        """Get top N players by position."""
        mask = self.df["positions"].str.contains(position, case=False, na=False)
        return (
            self.df[mask]
            .nlargest(top_n, "overall_rating")[
                ["name", "full_name", "overall_rating", "age", "nationality"]
            ]
        )

    def get_team_squad(self, team_name: str) -> pd.DataFrame:
        """Get players matching a team name (approximate)."""
        mask = self.df.get("national_team", pd.Series(dtype=str)).str.contains(
            team_name, case=False, na=False
        )
        if mask.any():
            return self.df[mask].nlargest(30, "overall_rating")[
                ["name", "positions", "overall_rating", "age"]
            ]
        return pd.DataFrame()

    def to_storage_dict(self, row: pd.Series) -> dict[str, Any]:
        """Convert a player row into a dict for database storage."""
        return {
            "name": row.get("name", ""),
            "full_name": row.get("full_name", ""),
            "birth_date": row.get("birth_date"),
            "age": row.get("age"),
            "height_cm": row.get("height_cm"),
            "weight_kgs": row.get("weight_kgs"),
            "positions": row.get("positions", ""),
            "nationality": row.get("nationality", ""),
            "overall_rating": row.get("overall_rating"),
            "potential": row.get("potential"),
            "value_euro": row.get("value_euro"),
            "wage_euro": row.get("wage_euro"),
            "preferred_foot": row.get("preferred_foot"),
            "source": "fifa_kaggle",
        }
