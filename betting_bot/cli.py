"""Command-line interface for the Betting Bot application."""

import sys

import uvicorn
from loguru import logger

from betting_bot.core.config import get_settings


def setup_logging() -> None:
    """Configure structured logging."""
    settings = get_settings()
    log_level = settings.LOG_LEVEL
    log_format = settings.LOG_FORMAT

    logger.remove()

    if log_format == "json":
        logger.add(
            sys.stderr,
            level=log_level,
            format="{time} | {level} | {name}:{function}:{line} | {message}",
            serialize=True,
        )
    else:
        logger.add(
            sys.stderr,
            level=log_level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        )

    logger.add(
        "logs/betting_bot_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="1 day",
        retention="30 days",
        compression="gz",
        format="{time} | {level} | {name}:{function}:{line} | {message}",
    )

    logger.info(f"Logging configured at {log_level} level")


def main() -> None:
    """Main entry point for the Betting Bot CLI."""
    setup_logging()
    settings = get_settings()

    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "serve":
            _run_api_server(settings)
        elif command == "train":
            _run_training()
        elif command == "predict":
            _run_prediction()
        elif command == "fetch":
            _run_data_fetch()
        elif command == "init-db":
            _init_database()
        elif command == "seed":
            _seed_database()
        else:
            logger.error(f"Unknown command: {command}")
            _print_help()
    else:
        _print_help()


def _run_api_server(settings) -> None:
    """Start the FastAPI web server."""
    host = "0.0.0.0"
    port = 8000
    logger.info(f"Starting API server on {host}:{port}")
    uvicorn.run(
        "betting_bot.api.app:create_app",
        host=host,
        port=port,
        reload=settings.DEBUG,
        factory=True,
        log_level=settings.LOG_LEVEL.lower(),
    )


def _run_training() -> None:
    """Run the model training pipeline."""
    import asyncio

    from betting_bot.database.session import get_async_session
    from betting_bot.training.pipelines.training_pipeline import TrainingPipeline

    async def run():
        async for session in get_async_session():
            pipeline = TrainingPipeline(db=session, optimize=True, n_trials=30)
            results = await pipeline.run()
            logger.info(f"Training completed: {len(results)} models trained")
            for r in results:
                logger.info(
                    f"  {r.model_name}: acc={r.test_accuracy:.4f}, "
                    f"f1={r.test_f1:.4f}, log_loss={r.test_log_loss:.4f}"
                )

    logger.info("Starting model training pipeline")
    asyncio.run(run())
    logger.info("Training pipeline completed")


def _run_prediction() -> None:
    """Generate predictions from the CLI."""
    import asyncio

    from betting_bot.database.session import get_async_session
    from betting_bot.prediction.predictor import PredictionGenerator

    async def run():
        async for session in get_async_session():
            generator = PredictionGenerator(db=session)

            if len(sys.argv) >= 4 and sys.argv[2] == "--match":
                match_id = int(sys.argv[3])
                prediction = await generator.predict_match(match_id)
                if prediction:
                    logger.info(
                        f"Prediction for match {match_id}: "
                        f"H={prediction.home_win_probability:.3f} "
                        f"D={prediction.draw_probability:.3f} "
                        f"A={prediction.away_win_probability:.3f} "
                        f"(confidence={prediction.confidence_score:.3f})"
                    )
            elif len(sys.argv) >= 4 and sys.argv[2] == "--upcoming":
                limit = int(sys.argv[3]) if len(sys.argv) > 3 else 10
                predictions = await generator.predict_upcoming_matches(limit=limit)
                logger.info(f"Generated {len(predictions)} predictions")
            else:
                logger.error("Usage: betting-bot predict --match <id> | --upcoming [limit]")

    asyncio.run(run())


def _run_data_fetch() -> None:
    """Fetch data from external sources."""
    import asyncio

    from betting_bot.database.session import get_async_session
    from betting_bot.services.data_orchestrator import DataOrchestrator

    async def run():
        source = sys.argv[2] if len(sys.argv) > 2 else "all"
        league = sys.argv[3] if len(sys.argv) > 3 else None

        orchestrator = DataOrchestrator()
        try:
            async for session in get_async_session():
                results = await orchestrator.fetch_and_store_all(
                    db=session,
                    source=source,
                    league_code=league,
                )
                logger.info(f"Fetch results: {results}")
        finally:
            await orchestrator.close_all()

    logger.info("Starting data fetch from external APIs")
    asyncio.run(run())
    logger.info("Data fetch completed")


def _init_database() -> None:
    """Initialize database tables."""
    import asyncio

    from betting_bot.database.session import init_db

    logger.info("Initializing database")
    asyncio.run(init_db())
    logger.info("Database initialized")


def _seed_database() -> None:
    """Seed the database with initial data."""
    import asyncio

    from betting_bot.database.seeds.seed_all import seed_database
    from betting_bot.database.session import get_async_session

    async def run_seed():
        async for session in get_async_session():
            await seed_database(session)

    logger.info("Seeding database")
    asyncio.run(run_seed())
    logger.info("Database seeded")


def _print_help() -> None:
    """Print CLI usage information."""
    print(
        """
Betting Bot - Football Betting Analysis Platform

Usage:
    betting-bot serve                  Start the API server
    betting-bot train                  Run model training pipeline
    betting-bot predict --match <id>   Generate prediction for a match
    betting-bot predict --upcoming [n] Generate predictions for n upcoming matches
    betting-bot fetch [source] [league]  Fetch data from external APIs
                                    source: all, football_data, statsbomb, odds, fifa
    betting-bot init-db                Initialize database tables
    betting-bot seed                   Seed database with initial data
    betting-bot help                   Show this help message

Examples:
    betting-bot serve
    betting-bot predict --match 42
    betting-bot predict --upcoming 10
    betting-bot init-db
        """
    )


if __name__ == "__main__":
    main()
