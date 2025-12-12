import uuid

from sqlalchemy import Column, Enum, String, Text, DateTime, Date, Integer, PrimaryKeyConstraint, UniqueConstraint, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    title = Column(String, nullable=True)
    slack_user_id = Column(String, unique=True, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    workspace = relationship("Workspace", back_populates="users")
    messages = relationship("Message", back_populates="user")

class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, unique=True, nullable=False)

    channels = relationship("Channel", back_populates="workspace")
    messages = relationship("Message", back_populates="workspace")

class Channel(Base):
    __tablename__ = "channels"
    __table_args__ = (UniqueConstraint("workspace_id", "name", name="uq_channel_workspace_name"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    workspace = relationship("Workspace", back_populates="channels")
    messages = relationship("Message", back_populates="channel")

class Message(Base):
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ts = Column(String, nullable=False)  # raw Slack ts
    message_ts = Column(DateTime(timezone=True))
    thread_ts = Column(String, nullable=True)  # null for root / non-thread messages
    text = Column(Text, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

    user = relationship("User", back_populates="messages")
    channel = relationship("Channel", back_populates="messages")
    workspace = relationship("Workspace", back_populates="messages")

class TopicCounts(Base):
    __tablename__ = "topic_counts"
    __table_args__ = (PrimaryKeyConstraint("date", "topic", "channel_id", name="pk_topic_counts"),)

    date = Column(Date, nullable=False)
    topic = Column(Enum("PCB", "impedance", "power", "firmware", "mechanical", name="topic_enum"), nullable=False)
    topic_count = Column(Integer, nullable=False)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)

class UserMessageCounts(Base):
    __tablename__ = "user_message_counts"
    __table_args__ = (PrimaryKeyConstraint("date", "user_id", "channel_id", name="pk_user_message_counts"),)

    date = Column(Date, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    message_count = Column(Integer, nullable=False)
    channel_id = Column(UUID(as_uuid=True), ForeignKey("channels.id"), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=False)
