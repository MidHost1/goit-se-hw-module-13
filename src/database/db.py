from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Якщо використовуєш PostgreSQL, рядок буде типу: "postgresql+psycopg2://user:password@localhost/dbname"
SQLALCHEMY_DATABASE_URL = "sqlite:///./sql_app.db"

# Для SQLite потрібен check_same_thread=False
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency для FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()