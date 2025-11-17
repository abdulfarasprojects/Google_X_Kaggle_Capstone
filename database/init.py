"""
Database initialization and migration utilities.

This module provides functions for initializing the SQLite database,
running migrations, and managing database schema updates. It handles
encryption setup, table creation, and data integrity checks.
"""

import os
import sqlite3
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager

from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from .models import Base, engine as default_engine
from config.settings import settings

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Database manager for SQLite operations with encryption support.

    Handles database initialization, migrations, and connection management
    with optional SQLCipher encryption for data at rest security.
    """

    def __init__(self, database_url: Optional[str] = None, encryption_key: Optional[str] = None):
        """
        Initialize database manager.

        Args:
            database_url: Database connection URL (defaults to settings)
            encryption_key: Encryption key for SQLCipher (optional)
        """
        self.database_url = database_url or settings.database_url
        self.encryption_key = encryption_key or settings.get_database_key()
        self.engine: Optional[Engine] = None

    def get_engine(self) -> Engine:
        """Get or create SQLAlchemy engine with encryption if enabled."""
        if self.engine is None:
            if self.encryption_key and settings.encryption_enabled:
                self.engine = self._create_encrypted_engine()
            else:
                self.engine = create_engine(
                    self.database_url,
                    connect_args={"check_same_thread": False},
                    poolclass=StaticPool,
                    echo=settings.debug
                )
        return self.engine

    def _create_encrypted_engine(self) -> Engine:
        """Create SQLAlchemy engine with SQLCipher encryption."""
        try:
            from sqlalchemy_sqlcipher import SQLCipherEngine  # type: ignore
        except ImportError:
            raise ImportError(
                "SQLCipher support required for encryption. "
                "Install with: pip install sqlalchemy-sqlcipher"
            )

        # Create connection with encryption
        connect_args = {
            "check_same_thread": False,
            "key": self.encryption_key,
            "cipher": "aes-256-cbc",  # AES-256 encryption
            "kdf_iter": 64000,       # PBKDF2 iterations for key derivation
        }

        return create_engine(
            self.database_url,
            module=SQLCipherEngine,
            connect_args=connect_args,
            poolclass=StaticPool,
            echo=settings.debug
        )

    def initialize_database(self) -> bool:
        """
        Initialize database schema and run migrations.

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            logger.info("Initializing database...")

            # Create database directory if needed
            db_path = self._get_database_path()
            if db_path:
                db_path.parent.mkdir(parents=True, exist_ok=True)

            # Create all tables
            engine = self.get_engine()
            Base.metadata.create_all(bind=engine)

            # Run any pending migrations
            self._run_migrations()

            # Validate schema
            if self._validate_schema():
                logger.info("Database initialization completed successfully")
                return True
            else:
                logger.error("Database schema validation failed")
                return False

        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return False

    def _get_database_path(self) -> Optional[Path]:
        """Get database file path from URL."""
        if self.database_url.startswith('sqlite:///'):
            db_path = self.database_url.replace('sqlite:///', '')
            return Path(db_path).resolve()
        return None

    def _run_migrations(self) -> None:
        """Run database migrations if any are pending."""
        # For MVP, we use SQLAlchemy's create_all which handles schema creation
        # In production, you would use Alembic for proper migrations
        logger.info("Running database migrations...")

        # Check for any migration scripts in migrations directory
        migrations_dir = Path(__file__).parent / "migrations"
        if migrations_dir.exists():
            self._apply_migration_scripts(migrations_dir)

    def _apply_migration_scripts(self, migrations_dir: Path) -> None:
        """Apply SQL migration scripts."""
        engine = self.get_engine()

        for sql_file in sorted(migrations_dir.glob("*.sql")):
            try:
                with open(sql_file, 'r') as f:
                    sql_content = f.read()

                with engine.connect() as conn:
                    conn.execute(text(sql_content))
                    logger.info(f"Applied migration: {sql_file.name}")

            except Exception as e:
                logger.error(f"Failed to apply migration {sql_file.name}: {e}")
                raise

    def _validate_schema(self) -> bool:
        """Validate that all required tables and indexes exist."""
        try:
            engine = self.get_engine()
            metadata = MetaData()
            metadata.reflect(bind=engine)

            required_tables = {
                'users', 'daily_logs_nutrition', 'daily_logs_fitness',
                'daily_logs_wellness', 'nudges', 'progress_summaries',
                'batch_states', 'api_usage'
            }

            existing_tables = set(metadata.tables.keys())

            missing_tables = required_tables - existing_tables
            if missing_tables:
                logger.error(f"Missing tables: {missing_tables}")
                return False

            # Validate critical indexes exist
            with engine.connect() as conn:
                result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='index'"))
                existing_indexes = {row[0] for row in result}

            required_indexes = {
                'idx_meal_logs_user_date', 'idx_workout_logs_user_date',
                'idx_wellness_logs_user_date', 'idx_nudges_scheduled',
                'idx_nudges_user_status', 'idx_progress_user_period',
                'idx_sessions_expires', 'idx_api_usage_provider_date'
            }

            missing_indexes = required_indexes - existing_indexes
            if missing_indexes:
                logger.warning(f"Missing indexes: {missing_indexes}")
                # Don't fail on missing indexes, just warn

            return True

        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return False

    def backup_database(self, backup_path: Optional[Path] = None) -> bool:
        """
        Create a backup of the database.

        Args:
            backup_path: Path for backup file (auto-generated if None)

        Returns:
            bool: True if backup successful
        """
        try:
            db_path = self._get_database_path()
            if not db_path or not db_path.exists():
                logger.error("Database file not found for backup")
                return False

            if backup_path is None:
                timestamp = os.path.getctime(db_path)
                backup_path = db_path.with_suffix(f".backup_{int(timestamp)}")

            # SQLite backup using VACUUM INTO (SQLite 3.27+)
            engine = self.get_engine()
            with engine.connect() as conn:
                conn.execute(text(f"VACUUM INTO '{backup_path}'"))

            logger.info(f"Database backup created: {backup_path}")
            return True

        except Exception as e:
            logger.error(f"Database backup failed: {e}")
            return False

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics and health information."""
        try:
            engine = self.get_engine()
            stats = {}

            with engine.connect() as conn:
                # Table counts
                for table_name in ['users', 'daily_logs_nutrition', 'daily_logs_fitness',
                                 'daily_logs_wellness', 'nudges', 'progress_summaries']:
                    result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    stats[f"{table_name}_count"] = result.scalar()

                # Database file size
                db_path = self._get_database_path()
                if db_path and db_path.exists():
                    stats['file_size_bytes'] = db_path.stat().st_size
                    stats['file_size_mb'] = round(db_path.stat().st_size / (1024 * 1024), 2)

                # SQLite version and settings
                result = conn.execute(text("SELECT sqlite_version()"))
                stats['sqlite_version'] = result.scalar()

                result = conn.execute(text("PRAGMA journal_mode"))
                stats['journal_mode'] = result.scalar()

                result = conn.execute(text("PRAGMA synchronous"))
                stats['synchronous_mode'] = result.scalar()

            return stats

        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}

    def optimize_database(self) -> bool:
        """Optimize database performance with VACUUM and ANALYZE."""
        try:
            logger.info("Optimizing database...")
            engine = self.get_engine()

            with engine.connect() as conn:
                # Run ANALYZE to update query planner statistics
                conn.execute(text("ANALYZE"))

                # Run VACUUM to reclaim space and defragment
                conn.execute(text("VACUUM"))

            logger.info("Database optimization completed")
            return True

        except Exception as e:
            logger.error(f"Database optimization failed: {e}")
            return False

    def reset_database(self) -> bool:
        """
        Reset database by dropping all tables and recreating schema.

        WARNING: This will delete all data. Use with caution.
        """
        try:
            logger.warning("Resetting database - all data will be lost!")

            engine = self.get_engine()
            metadata = MetaData()
            metadata.reflect(bind=engine)

            # Drop all tables
            with engine.connect() as conn:
                for table in reversed(metadata.sorted_tables):
                    conn.execute(text(f"DROP TABLE IF EXISTS {table.name}"))

            # Recreate schema
            Base.metadata.create_all(bind=engine)

            logger.info("Database reset completed")
            return True

        except Exception as e:
            logger.error(f"Database reset failed: {e}")
            return False


# Global database manager instance
db_manager = DatabaseManager()


def init_database() -> bool:
    """
    Initialize the database with default settings.

    Returns:
        bool: True if initialization successful
    """
    return db_manager.initialize_database()


def get_database_stats() -> Dict[str, Any]:
    """Get database statistics."""
    return db_manager.get_database_stats()


def backup_database(backup_path: Optional[Path] = None) -> bool:
    """Create database backup."""
    return db_manager.backup_database(backup_path)


def optimize_database() -> bool:
    """Optimize database performance."""
    return db_manager.optimize_database()


def reset_database() -> bool:
    """Reset database (WARNING: deletes all data)."""
    return db_manager.reset_database()


@contextmanager
def get_db_session():
    """
    Context manager for database sessions.

    Usage:
        with get_db_session() as session:
            # Use session for database operations
            pass
    """
    from sqlalchemy.orm import sessionmaker
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_manager.get_engine())

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


# Export key functions and classes
__all__ = [
    'DatabaseManager', 'db_manager',
    'init_database', 'get_database_stats', 'backup_database',
    'optimize_database', 'reset_database', 'get_db_session'
]