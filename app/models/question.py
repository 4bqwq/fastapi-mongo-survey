from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict

from app.core.time import utc_now
from app.models.user import PyObjectId


class SharedGrant(BaseModel):
    user_id: PyObjectId = Field(alias="userId")
    shared_at: datetime = Field(default_factory=utc_now, alias="sharedAt")

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class LibraryGrant(BaseModel):
    user_id: PyObjectId = Field(alias="userId")
    added_at: datetime = Field(default_factory=utc_now, alias="addedAt")

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)


class QuestionContent(BaseModel):
    type: str
    title: str
    is_required: bool = Field(default=True, alias="isRequired")
    options: Optional[List[str]] = None
    min_select: Optional[int] = Field(default=None, alias="minSelect")
    max_select: Optional[int] = Field(default=None, alias="maxSelect")
    min_length: Optional[int] = Field(default=None, alias="minLength")
    max_length: Optional[int] = Field(default=None, alias="maxLength")
    min_value: Optional[float] = Field(default=None, alias="minValue")
    max_value: Optional[float] = Field(default=None, alias="maxValue")
    must_be_integer: bool = Field(default=False, alias="mustBeInteger")

    model_config = ConfigDict(populate_by_name=True)


class QuestionCreate(QuestionContent):
    pass


class QuestionVersionCreate(QuestionContent):
    base_version: int = Field(alias="base_version")

    model_config = ConfigDict(populate_by_name=True)


class QuestionShareCreate(BaseModel):
    username: str


class QuestionInDB(QuestionContent):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    question_id: str = Field(alias="questionId")
    user_id: PyObjectId = Field(alias="userId")
    version: int
    shared_with: List[SharedGrant] = Field(default_factory=list, alias="sharedWith")
    library_members: List[LibraryGrant] = Field(default_factory=list, alias="libraryMembers")
    previous_version_id: Optional[PyObjectId] = Field(default=None, alias="previousVersionId")
    version_chain_root_id: PyObjectId = Field(alias="versionChainRootId")
    created_at: datetime = Field(default_factory=utc_now, alias="createdAt")
    updated_at: datetime = Field(default_factory=utc_now, alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
