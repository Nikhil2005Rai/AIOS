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

        if has_version_table or not has_phase_1_schema:
            return

        if "tool_calls" not in tables:
            stamp_revision = "0001_initial"
        else:
            tool_calls_cols = {c["name"] for c in inspector.get_columns("tool_calls")}
            if "agent_name" not in tool_calls_cols:
                stamp_revision = "0002_tool_calls"
            elif "user_api_keys" not in tables:
                stamp_revision = "0003_tool_calls_agent_name"
            else:
                users_cols = {c["name"] for c in inspector.get_columns("users")}
                if "preferred_provider" not in users_cols:
                    stamp_revision = "0004_user_api_keys"
                elif "documents" not in tables:
                    stamp_revision = "0005_users_preferred_provider"
                else:
                    stamp_revision = "head"

    command.stamp(config, stamp_revision)
