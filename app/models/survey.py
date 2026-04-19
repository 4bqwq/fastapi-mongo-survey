from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict

from app.models.user import PyObjectId


class SurveyQuestionRef(BaseModel):
    question_id: str = Field(alias="questionId")
    version: int
    order_index: int = Field(alias="orderIndex")

    model_config = ConfigDict(populate_by_name=True)


class LogicRuleModel(BaseModel):
    rule_id: str = Field(alias="ruleId")
    source_question_id: str = Field(alias="sourceQuestionId")
    target_question_id: str = Field(alias="targetQuestionId")
    trigger_condition: str = Field(alias="triggerCondition")

    model_config = ConfigDict(populate_by_name=True)


class SurveySchemaUpdate(BaseModel):
    questions: List[SurveyQuestionRef]
    logic_rules: List[LogicRuleModel] = Field(default_factory=list, alias="logic_rules")

    model_config = ConfigDict(populate_by_name=True)


class SurveyBase(BaseModel):
    title: str
    description: Optional[str] = ""
    is_anonymous: bool = Field(default=False, alias="is_anonymous")
    end_time: Optional[datetime] = Field(default=None, alias="end_time")


class SurveyCreate(SurveyBase):
    pass


class SurveyMetadataUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    is_anonymous: Optional[bool] = Field(default=None, alias="is_anonymous")
    end_time: Optional[datetime] = Field(default=None, alias="end_time")

    model_config = ConfigDict(populate_by_name=True)


class SurveyUpdateStatus(BaseModel):
    status: str


class SurveyInDB(SurveyBase):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    user_id: PyObjectId = Field(alias="userId")
    status: str = "DRAFT"
    questions: List[dict] = Field(default_factory=list)
    logic_rules: List[dict] = Field(default_factory=list, alias="logicRules")
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
