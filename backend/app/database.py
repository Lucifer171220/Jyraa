import os
import urllib.parse
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Database configuration
SERVER = "localhost\\SQLEXPRESS02"
DATABASE = "JiraDB"
DRIVER = "ODBC+Driver+18+for+SQL+Server"
TRUSTED_CONNECTION = "yes"
TRUST_SERVER_CERT = "yes"

DATABASE_URL = (
    f"mssql+pyodbc://@{SERVER}/{DATABASE}"
    f"?driver={DRIVER}"
    f"&trusted_connection={TRUSTED_CONNECTION}"
    f"&TrustServerCertificate={TRUST_SERVER_CERT}"
)

# Master URL for admin operations (connects to master to create the database)
MASTER_URL = (
    f"mssql+pyodbc://@{SERVER}/master"
    f"?driver={DRIVER}"
    f"&trusted_connection={TRUSTED_CONNECTION}"
    f"&TrustServerCertificate={TRUST_SERVER_CERT}"
)


def create_database_if_not_exists():
    """Create the database if it doesn't exist."""
    # Create a temporary engine to connect to the 'master' database
    master_engine = create_engine(MASTER_URL, echo=False)
    
    try:
        with master_engine.connect() as conn:
            # Set autocommit for DDL operations
            conn = conn.execution_options(isolation_level="AUTOCOMMIT")
            
            # Check if database exists
            result = conn.execute(
                text("SELECT database_id FROM sys.databases WHERE name = :db_name"),
                {"db_name": DATABASE}
            )
            
            if result.fetchone() is None:
                print(f"Database '{DATABASE}' does not exist. Creating...")
                conn.execute(text(f"CREATE DATABASE [{DATABASE}]"))
                print(f"Database '{DATABASE}' created successfully.")
            else:
                print(f"Database '{DATABASE}' already exists.")
                
    except Exception as e:
        print(f"Error creating database: {e}")
        raise
    finally:
        master_engine.dispose()


engine = create_engine(
    DATABASE_URL,
    echo=True
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def seed_reference_data():
    """Ensure core lookup tables contain the values the API expects."""
    from app.models import IssuePriority, IssueStatus, IssueType, Resolution

    reference_sets = (
        (
            IssueType,
            "name",
            [
                {"name": "Epic", "description": "Large body of work", "icon_name": "epic", "is_subtask_enabled": False},
                {
                    "name": "Story",
                    "description": "User story representing a feature from user perspective",
                    "icon_name": "story",
                    "is_subtask_enabled": False,
                },
                {"name": "Task", "description": "General task", "icon_name": "task", "is_subtask_enabled": False},
                {"name": "Bug", "description": "Problem that needs fixing", "icon_name": "bug", "is_subtask_enabled": False},
                {"name": "Subtask", "description": "Child work item", "icon_name": "subtask", "is_subtask_enabled": True},
            ],
        ),
        (
            IssuePriority,
            "name",
            [
                {"name": "Highest", "description": "Critical priority", "color_hex": "#C0392B", "sort_order": 1},
                {"name": "High", "description": "High priority", "color_hex": "#E67E22", "sort_order": 2},
                {"name": "Medium", "description": "Normal priority", "color_hex": "#F1C40F", "sort_order": 3},
                {"name": "Low", "description": "Low priority", "color_hex": "#3498DB", "sort_order": 4},
                {"name": "Lowest", "description": "Lowest priority", "color_hex": "#95A5A6", "sort_order": 5},
            ],
        ),
        (
            IssueStatus,
            "name",
            [
                {"name": "To Do", "description": "Issue is ready to be worked on", "color_hex": "#6BA4FF", "sort_order": 1, "is_final_status": False},
                {"name": "In Progress", "description": "Issue is actively being worked on", "color_hex": "#F39C12", "sort_order": 2, "is_final_status": False},
                {"name": "In Review", "description": "Issue is awaiting review", "color_hex": "#9B59B6", "sort_order": 3, "is_final_status": False},
                {"name": "Done", "description": "Issue is completed", "color_hex": "#28B463", "sort_order": 4, "is_final_status": True},
                {"name": "Cancelled", "description": "Issue has been cancelled", "color_hex": "#7F8C8D", "sort_order": 5, "is_final_status": True},
            ],
        ),
        (
            Resolution,
            "name",
            [
                {"name": "Done", "description": "Issue completed successfully"},
                {"name": "Won't Do", "description": "Issue will not be worked on"},
                {"name": "Duplicate", "description": "Issue is tracked elsewhere"},
                {"name": "Cannot Reproduce", "description": "Problem could not be reproduced"},
            ],
        ),
    )

    db = SessionLocal()
    try:
        for model, key_field, rows in reference_sets:
            existing_values = {value for (value,) in db.query(getattr(model, key_field)).all()}
            for row in rows:
                if row[key_field] not in existing_values:
                    db.add(model(**row))
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize the database and all tables."""
    # First, ensure the database exists
    create_database_if_not_exists()
    
    # Now import models and create tables
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    seed_reference_data()
    print("Database tables created successfully!")


if __name__ == "__main__":
    init_db()
