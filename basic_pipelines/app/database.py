from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from databases import Database
from .config import DATABASE_URL

# Création de l’engine SQLAlchemy
engine = create_engine(DATABASE_URL)

# Création de la base déclarative
Base = declarative_base()

# Création de la session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Configuration de la connexion asynchrone
database = Database(DATABASE_URL)