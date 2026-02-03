from sqlalchemy import Column, Integer, Text, Boolean, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class GenerationLog(Base):
    __tablename__ = "generation_logs"

    id = Column(Integer, primary_key=True)
    prompt = Column(Text, nullable=False)
    output = Column(Text)
    valid_mermaid = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())