from app.db.database import engine
from app.db.models import Base


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")


if __name__ == "__main__":
    initialize_database()