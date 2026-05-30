from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from .database.db import Base


class Person(Base):
    __tablename__ = "person"

    createdAt = Column(DateTime, nullable=False, default=datetime.now)
    updatedAt = Column(
        DateTime, nullable=False, default=datetime.now, onupdate=datetime.now
    )
    deletedAt = Column(DateTime, nullable=True)

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    accountId = Column(Integer, ForeignKey("account.id"), nullable=True)

    account = relationship("Account")
    splits = relationship("Split", back_populates="person")
