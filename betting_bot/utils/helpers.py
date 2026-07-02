"""General-purpose helper functions for calculations and data processing."""

import asyncio
import hashlib
import json
import time
from collections.abc import AsyncGenerator, Generator, Sequence
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from loguru import logger


def safe_division(a: float, b: float, default: float = 0.0) -> float:
    """Safe division returning default when dividing by zero."""
    if b == 0 or abs(b) < 1e-10:
        return default
    return a / b


def calculate_implied_probability(odds: float) -> float:
    """Convert decimal odds to implied probability."""
    if odds <= 1.0:
        raise ValueError(f"Odds must be > 1.0, got {odds}")
    return 1.0 / odds


def calculate_kelly_criterion(
    probability: float,
    odds: float,
    fraction: float = 0.25,
) -> float:
    """Calculate Kelly Criterion bet size as fraction of bankroll.

    Args:
        probability: Estimated probability of the outcome.
        odds: Decimal odds from bookmaker.
        fraction: Kelly fraction for conservative betting.

    Returns:
        Fraction of bankroll to stake (0 to 1).
    """
    implied_prob = 1.0 / odds
    b = odds - 1  # Net odds
    p = probability
    q = 1.0 - probability

    kelly = (b * p - q) / b
    kelly = max(0.0, min(kelly, 1.0))  # Clamp to [0, 1]
    return kelly * fraction


def calculate_expected_value(probability: float, odds: float) -> float:
    """Calculate Expected Value for a bet.

    EV = (probability * (odds - 1)) - (1 - probability)
    """
    return (probability * (odds - 1)) - (1 - probability)


def convert_odds_to_probability(odds: float) -> float:
    """Convert decimal odds to fair probability (no margin)."""
    if odds <= 1.0:
        raise ValueError(f"Odds must be > 1.0, got {odds}")
    return 1.0 / odds


def validate_probability_sum(probabilities: dict[str, float], tolerance: float = 0.01) -> bool:
    """Check that probabilities sum to approximately 1.0."""
    total = sum(probabilities.values())
    return abs(1.0 - total) <= tolerance


def date_range(start: date, end: date) -> list[date]:
    """Generate a list of dates between start and end inclusive."""
    delta = end - start
    return [start + timedelta(days=i) for i in range(delta.days + 1)]


def chunks(sequence: Sequence[Any], chunk_size: int) -> Generator[list[Any], None, None]:
    """Split a sequence into chunks of a given size."""
    for i in range(0, len(sequence), chunk_size):
        yield sequence[i : i + chunk_size]


def timing(func: Any) -> Any:
    """Decorator that prints execution time (synchronous version)."""
    import functools

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        logger.info(f"{func.__name__} took {elapsed:.4f}s")
        return result

    return wrapper


def generate_run_id() -> str:
    """Generate a unique run identifier."""
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    hash_suffix = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
    return f"{timestamp}_{hash_suffix}"


def normalize_team_name(name: str) -> str:
    """Normalize team name for matching across data sources."""
    replacements = {
        "FC": "",
        "United": "Utd",
        "F.C.": "",
        "AC ": "",
        "AFC ": "",
        "&": "and",
    }
    name = name.strip()
    for old, new in replacements.items():
        name = name.replace(old, new)
    return name.strip()


def json_serialize(obj: Any) -> Any:
    """JSON serializer that handles special types like datetime."""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")


def ensure_directory(path: Path) -> Path:
    """Ensure a directory exists and return its path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


async def retry_async(
    func: Any,
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
) -> Any:
    """Retry an async function with exponential backoff."""
    import asyncio

    for attempt in range(max_retries):
        try:
            return await func()
        except exceptions as e:
            if attempt == max_retries - 1:
                raise
            wait = delay * (backoff**attempt)
            logger.warning(f"Attempt {attempt + 1}/{max_retries} failed: {e}. Retrying in {wait:.1f}s")
            await asyncio.sleep(wait)
