from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict
from app.core.time import utc_now
from app.models.user import PyObjectId

class AnswerCreate(BaseModel):
    submit_as_anonymous: bool = Field(default=False, alias="submit_as_anonymous")
    payloads: Dict[str, Any] # questionId -> answer

    model_config = ConfigDict(populate_by_name=True)

class AnswerInDB(BaseModel):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    survey_id: PyObjectId = Field(alias="surveyId")
    respondent_id: Optional[PyObjectId] = Field(default=None, alias="respondentId")
    payloads: Dict[str, Any]
    submitted_at: datetime = Field(default_factory=utc_now, alias="submittedAt")
    created_at: datetime = Field(default_factory=utc_now, alias="createdAt")
    updated_at: datetime = Field(default_factory=utc_now, alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )
