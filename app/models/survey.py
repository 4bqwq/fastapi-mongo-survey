from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models.user import PyObjectId

class SurveyBase(BaseModel):
    title: str
    description: Optional[str] = ""
    is_anonymous: bool = Field(default=False, alias="is_anonymous")
    end_time: Optional[datetime] = Field(default=None, alias="end_time")

class SurveyCreate(SurveyBase):
    pass

class SurveyUpdateStatus(BaseModel):
    status: str # DRAFT, PUBLISHED, CLOSED

class SurveyInDB(SurveyBase):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: PyObjectId = Field(alias="userId")
    status: str = "DRAFT"
    questions: List[dict] = []
    logic_rules: List[dict] = []
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

class SurveyOut(BaseModel):
    survey_id: str
    title: str
    description: Optional[str]
    is_anonymous: bool
    status: str
    end_time: Optional[datetime]
    created_at: datetime

    model_config = ConfigDict(
        populate_by_name=True
    )
