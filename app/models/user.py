from datetime import datetime
from typing import Optional, Any
from pydantic import BaseModel, Field, ConfigDict, GetCoreSchemaHandler
from pydantic_core import core_schema
from bson import ObjectId

class PyObjectId(ObjectId):
    @classmethod
    def __get_pydantic_core_schema__(
        cls, _source_type: Any, _handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        def validate(v: Any) -> ObjectId:
            if not ObjectId.is_valid(v):
                raise ValueError("Invalid ObjectId")
            return ObjectId(v)

        return core_schema.json_or_python_schema(
            json_schema=core_schema.str_schema(),
            python_schema=core_schema.union_schema([
                core_schema.is_instance_schema(ObjectId),
                core_schema.chain_schema([
                    core_schema.str_schema(),
                    core_schema.no_info_plain_validator_function(validate),
                ])
            ]),
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda x: str(x), 
                when_used='always'
            )
        )

class UserBase(BaseModel):
    username: str
    is_deleted: bool = Field(default=False, alias="isDeleted")

class UserCreate(UserBase):
    password: str

class UserInDB(UserBase):
    id: Optional[PyObjectId] = Field(default=None, alias="_id")
    password_hash: str = Field(alias="passwordHash")
    created_at: datetime = Field(default_factory=datetime.utcnow, alias="createdAt")
    updated_at: datetime = Field(default_factory=datetime.utcnow, alias="updatedAt")

    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True
    )

class UserOut(BaseModel):
    user_id: str
    username: str
    created_at: datetime

    model_config = ConfigDict(
        populate_by_name=True
    )
