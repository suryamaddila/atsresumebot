import logging
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import json

logger = logging.getLogger(__name__)

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    total_resumes = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)

class ResumeSession(Base):
    __tablename__ = 'resume_sessions'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, nullable=False)
    session_id = Column(String(100), unique=True, nullable=False)
    step = Column(String(50), nullable=False)
    original_resume = Column(Text)
    job_description = Column(Text)
    optimized_resume = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    is_completed = Column(Boolean, default=False)

class Payment(Base):
    __tablename__ = 'payments'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, nullable=False)
    payment_id = Column(String(100), unique=True, nullable=False)
    utr = Column(String(20))
    amount = Column(Float, nullable=False)
    status = Column(String(20), default='pending')  # pending, verified, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime)
    session_id = Column(String(100))

class DatabaseManager:
    """Manage database operations"""
    
    def __init__(self, database_url: Optional[str] = None):
        if database_url:
            self.engine = create_engine(database_url)
            Base.metadata.create_all(self.engine)
            Session = sessionmaker(bind=self.engine)
            self.session = Session()
            logger.info("Database connected successfully")
        else:
            self.engine = None
            self.session = None
            logger.warning("No database URL provided, using in-memory storage")
    
    def create_user(self, telegram_id: int, username: str = None, 
                   first_name: str = None, last_name: str = None) -> bool:
        """Create or update user"""
        if not self.session:
            return False
        
        try:
            user = self.session.query(User).filter_by(telegram_id=telegram_id).first()
            
            if user:
                # Update existing user
                user.username = username or user.username
                user.first_name = first_name or user.first_name
                user.last_name = last_name or user.last_name
                user.last_active = datetime.utcnow()
            else:
                # Create new user
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name
                )
                self.session.add(user)
            
            self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            self.session.rollback()
            return False
    
    def create_session(self, telegram_id: int, session_id: str) -> bool:
        """Create resume session"""
        if not self.session:
            return False
        
        try:
            resume_session = ResumeSession(
                telegram_id=telegram_id,
                session_id=session_id,
                step='waiting_resume'
            )
            self.session.add(resume_session)
            self.session.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            self.session.rollback()
            return False