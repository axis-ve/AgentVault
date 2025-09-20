from __future__ import annotations

import argparse
import os
from pathlib import Path

from alembic import command
from alembic.config import Config


def _resolve_alembic_config(database_url: str | None = None) -> Config:
    project_root = Path(__file__).resolve().parents[3]
    ini_path = project_root / "alembic.ini"
    if not ini_path.exists():
        raise FileNotFoundError(f"alembic.ini not found at {ini_path}")
    cfg = Config(str(ini_path))
    if database_url:
        cfg.set_main_option("sqlalchemy.url", database_url)
    elif os.getenv("VAULTPILOT_DATABASE_URL"):
        cfg.set_main_option("sqlalchemy.url", os.environ["VAULTPILOT_DATABASE_URL"])
    return cfg


def upgrade(database_url: str | None = None, revision: str = "head") -> None:
    cfg = _resolve_alembic_config(database_url)
    command.upgrade(cfg, revision)


def downgrade(database_url: str | None = None, revision: str = "-1") -> None:
    cfg = _resolve_alembic_config(database_url)
    command.downgrade(cfg, revision)


def stamp(database_url: str | None = None, revision: str = "head") -> None:
    cfg = _resolve_alembic_config(database_url)
    command.stamp(cfg, revision)


def main() -> None:
    parser = argparse.ArgumentParser(description="VaultPilot database migration utility")
    parser.add_argument("action", choices=["upgrade", "downgrade", "stamp"], help="Migration command")
    parser.add_argument("revision", nargs="?", default="head", help="Target revision")
    parser.add_argument("--database-url", dest="database_url")
    args = parser.parse_args()

    if args.action == "upgrade":
        upgrade(args.database_url, args.revision)
    elif args.action == "downgrade":
        downgrade(args.database_url, args.revision)
    else:
        stamp(args.database_url, args.revision)


if __name__ == "__main__":
    main()
