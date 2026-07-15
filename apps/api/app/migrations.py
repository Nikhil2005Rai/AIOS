from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import settings, sqlalchemy_database_url


def run_migrations() -> None:
    if settings.environment == "test":
        return

    base_dir = Path(__file__).resolve().parents[1]
    config = Config(str(base_dir / "alembic.ini"))
    config.set_main_option("script_location", str(base_dir / "migrations"))
    _stamp_existing_phase_1_schema(config)
    command.upgrade(config, "head")


def _stamp_existing_phase_1_schema(config: Config) -> None:
    engine = create_engine(sqlalchemy_database_url(), pool_pre_ping=True)
    with engine.connect() as connection:
        inspector = inspect(connection)
        tables = set(inspector.get_table_names())
        has_version_table = "alembic_version" in tables
        has_phase_1_schema = {"users", "conversations", "messages"}.issubset(tables)
        has_tool_calls = "tool_calls" in tables

        if has_version_table or not has_phase_1_schema:
            return

        if has_tool_calls:
            stamp_revision = "head"
        else:
            stamp_revision = "0001_initial"

    command.stamp(config, stamp_revision)
