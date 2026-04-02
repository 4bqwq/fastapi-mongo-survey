from datetime import datetime
from typing import Optional, List, Any, Union
from pydantic import BaseModel, Field, ConfigDict
from app.models.user import PyObjectId

class QuestionModel(BaseModel):
    question_id: str = Field(alias="questionId")
    type: str # ChoiceQuestion, TextQuestion, NumberQuestion
    is_required: bool = Field(default=True, alias="isRequired")
    order_index: int = Field(alias="orderIndex")
    
    # Choice specific
    options: Optional[List[str]] = None
    min_select: Optional[int] = Field(default=None, alias="minSelect")
    max_select: Optional[int] = Field(default=None, alias="maxSelect")
    
    # Text specific
    min_length: Optional[int] = Field(default=None, alias="minLength")
    max_length: Optional[int] = Field(default=None, alias="maxLength")
    
    # Number specific
    min_value: Optional[float] = Field(default=None, alias="minValue")
    max_value: Optional[float] = Field(default=None, alias="maxValue")
    must_be_integer: Optional[bool] = Field(default=False, alias="mustBeInteger")

    model_config = ConfigDict(populate_by_name=True)

class LogicRuleModel(BaseModel):
    rule_id: str = Field(alias="ruleId")
    source_question_id: str = Field(alias="sourceQuestionId")
    target_question_id: str = Field(alias="targetQuestionId")
    trigger_condition: str = Field(alias="triggerCondition")

    model_config = ConfigDict(populate_by_name=True)

class SurveySchemaUpdate(BaseModel):
    questions: List[QuestionModel]
    logic_rules: List[LogicRuleModel] = Field(default=[], alias="logic_rules")

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
    questions: List[dict] = []
    logic_rules: List[dict] = []

    model_config = ConfigDict(
        populate_by_name=True
    )
