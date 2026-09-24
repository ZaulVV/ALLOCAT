import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base, get_db
from backend.app.main import app
from backend.app.models import Role

os.environ["DATABASE_URL"] = "sqlite:///./test_allocat.db"
engine = create_engine("sqlite:///./test_allocat.db", connect_args={"check_same_thread": False})
TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = TestingSession()
    db.add_all([Role(name="ADMIN"), Role(name="REQUESTER"), Role(name="AUDITOR")])
    db.commit()
    db.close()
    def override():
        db = TestingSession()
        try: yield db
        finally: db.close()
    app.dependency_overrides[get_db] = override
    with TestClient(app) as value:
        yield value
    app.dependency_overrides.clear()
