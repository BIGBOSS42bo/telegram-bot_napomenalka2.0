from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Reminder(Base):
    __tablename__ = 'reminders'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    message = Column(String)
    first_delay = Column(Integer)  # в секундах
    interval = Column(Integer)     # в секундах
    count = Column(Integer)        # количество повторений
    created_at = Column(DateTime)

engine = create_engine('sqlite:///reminders.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
