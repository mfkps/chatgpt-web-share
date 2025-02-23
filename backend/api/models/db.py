import uuid
from datetime import datetime
from typing import List, Optional

from fastapi_users_db_sqlalchemy import Integer
from sqlalchemy import String, Enum, Boolean, ForeignKey, func, Float
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column

from api.database.custom_types import GUID, Pydantic, UTCDateTime
from api.enums import RevChatStatus, RevChatModels, ApiChatModels, ChatSourceTypes
from api.models.json import CustomOpenaiApiSettings
from api.schema import UserSettingSchema, RevSourceSettingSchema, ApiSourceSettingSchema


# declarative base class
class Base(DeclarativeBase):
    type_annotation_map = {
        uuid.UUID: GUID,
    }


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, comment="用户id")
    username: Mapped[str] = mapped_column(String(32), unique=True, index=True, comment="用户名")
    nickname: Mapped[str] = mapped_column(String(64), comment="昵称")
    email: Mapped[str]
    rev_chat_status: Mapped[RevChatStatus] = mapped_column(Enum(RevChatStatus), default=RevChatStatus.idling,
                                                           comment="对话状态")
    last_active_time: Mapped[Optional[datetime]] = mapped_column(UTCDateTime(timezone=True), comment="最后活跃时间")
    create_time: Mapped[datetime] = mapped_column(UTCDateTime(timezone=True),
                                                  server_default=func.now(), comment="创建时间")
    avatar: Mapped[Optional[str]] = mapped_column(comment="头像")
    valid_until: Mapped[Optional[datetime]] = mapped_column(UTCDateTime(timezone=True), comment="用户有效期")
    remark: Mapped[Optional[str]] = mapped_column(String(256), comment="仅管理员可见的备注")
    is_superuser: Mapped[bool] = mapped_column(Boolean, comment="是否是管理员")
    is_active: Mapped[bool] = mapped_column(Boolean, comment="启用/禁用用户")
    is_verified: Mapped[bool] = mapped_column(Boolean, comment="是否已经验证")
    hashed_password: Mapped[str] = mapped_column(String(1024))

    setting: Mapped["UserSetting"] = relationship("UserSetting", back_populates="user", lazy="joined")
    conversations: Mapped[List["BaseConversation"]] = relationship("BaseConversation", back_populates="user")


class UserSetting(Base):
    __tablename__ = "user_setting"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), comment="用户id")
    user: Mapped[User] = relationship("User", back_populates="setting", lazy="joined")
    credits: Mapped[float] = mapped_column(Float, default=0, comment="积分")
    rev: Mapped[RevSourceSettingSchema] = mapped_column(Pydantic(RevSourceSettingSchema), comment="rev对话设置")
    api: Mapped[ApiSourceSettingSchema] = mapped_column(Pydantic(ApiSourceSettingSchema), comment="api对话设置")


class BaseConversation(Base):
    """
    https://docs.sqlalchemy.org/en/20/orm/inheritance.html#single-table-inheritance
    仅保留用户映射关系和基础信息，对话内容保存在mongodb中
    """

    __tablename__ = "conversation"
    __mapper_args__ = {
        "polymorphic_on": "type",
        "polymorphic_identity": "base",
    }

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[ChatSourceTypes] = mapped_column(Enum(ChatSourceTypes), comment="对话类型")
    conversation_id: Mapped[uuid.UUID] = mapped_column(GUID, index=True, unique=True, comment="uuid")
    current_model: Mapped[Optional[str]] = mapped_column(default=None, use_existing_column=True)
    title: Mapped[Optional[str]] = mapped_column(comment="对话标题")
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("user.id"), comment="发起用户id")
    user: Mapped["User"] = relationship(back_populates="conversations")
    is_valid: Mapped[bool] = mapped_column(Boolean, comment="是否有效")
    create_time: Mapped[Optional[datetime]] = mapped_column(UTCDateTime(timezone=True), comment="创建时间")
    update_time: Mapped[Optional[datetime]] = mapped_column(UTCDateTime(timezone=True), comment="最后更新时间")


class RevConversation(BaseConversation):
    __mapper_args__ = {
        "polymorphic_identity": "rev",
    }

    current_model: Mapped[Optional[Enum["RevChatModels"]]] = mapped_column(
        Enum(RevChatModels),
        default=None,
        use_existing_column=True)


class ApiConversation(BaseConversation):
    __mapper_args__ = {
        "polymorphic_identity": "api",
    }

    current_model: Mapped[Optional[Enum["ApiChatModels"]]] = mapped_column(
        Enum(ApiChatModels),
        default=None,
        use_existing_column=True)
