import os
from sqlalchemy import create_engine, Column, Integer, String, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

db_url = os.getenv("DATABASE_URL")
if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

engine = create_engine(db_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class VPNUser(Base):
    __tablename__ = "vpn_users"
    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, unique=True, index=True) # Защита для длинных ID
    marzban_username = Column(String, unique=True)

def init_db():
    Base.metadata.create_all(bind=engine)
