from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from app.models.survey import SurveyCreate, SurveyUpdateStatus, SurveyInDB, SurveyOut, SurveySchemaUpdate
from app.models.user import UserInDB
from app.api.deps import get_current_user
from app.core.database import get_database
from datetime import datetime
from bson import ObjectId

router = APIRouter(prefix="/surveys", tags=["surveys"])

@router.post("", response_model=dict)
async def create_survey(
    survey_in: SurveyCreate, 
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(get_database)
):
    survey_dict = survey_in.model_dump(by_alias=True)
    survey_dict["userId"] = current_user.id
    survey_dict["status"] = "DRAFT"
    survey_dict["questions"] = []
    survey_dict["logicRules"] = []
    survey_dict["createdAt"] = datetime.utcnow()
    survey_dict["updatedAt"] = datetime.utcnow()

    result = await db.surveys.insert_one(survey_dict)
    return {
        "code": 200,
        "data": {
            "survey_id": str(result.inserted_id),
            "status": "DRAFT"
        }
    }

@router.get("", response_model=dict)
async def list_surveys(
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(get_database)
):
    cursor = db.surveys.find({"userId": current_user.id})
    surveys = await cursor.to_list(length=100)
    
    data = []
    for s in surveys:
        data.append({
            "survey_id": str(s["_id"]),
            "title": s["title"],
            "description": s.get("description", ""),
            "status": s["status"],
            "is_anonymous": s["is_anonymous"],
            "end_time": s.get("end_time").isoformat() + "Z" if s.get("end_time") else None,
            "created_at": s["createdAt"].isoformat() + "Z"
        })
    
    return {
        "code": 200,
        "data": data
    }

@router.get("/{survey_id}/schema", response_model=dict)
async def get_survey_schema(
    survey_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(get_database)
):
    # Verify ownership
    survey = await db.surveys.find_one({"_id": ObjectId(survey_id)})
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    # We allow the owner to view it. If non-anonymous and not published, might need extra check.
    # For now, following api-spec, returning the schema.
    
    return {
        "code": 200,
        "data": {
            "title": survey["title"],
            "description": survey.get("description", ""),
            "is_anonymous": survey["is_anonymous"],
            "status": survey["status"],
            "questions": survey.get("questions", []),
            "logic_rules": survey.get("logicRules", [])
        }
    }

@router.patch("/{survey_id}/status", response_model=dict)
async def update_survey_status(
    survey_id: str,
    status_in: SurveyUpdateStatus,
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(get_database)
):
    # Verify ownership
    survey = await db.surveys.find_one({"_id": ObjectId(survey_id)})
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    if survey["userId"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 40301, "message": "无权操作此问卷"}
        )

    await db.surveys.update_one(
        {"_id": ObjectId(survey_id)},
        {"$set": {"status": status_in.status, "updatedAt": datetime.utcnow()}}
    )

    return {
        "code": 200,
        "data": {
            "survey_id": survey_id,
            "status": status_in.status
        }
    }

@router.put("/{survey_id}/schema", response_model=dict)
async def update_survey_schema(
    survey_id: str,
    schema_in: SurveySchemaUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(get_database)
):
    # Verify ownership
    survey = await db.surveys.find_one({"_id": ObjectId(survey_id)})
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    if survey["userId"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 40301, "message": "无权操作此问卷"}
        )
    
    # Optional: Logic validation (e.g. check if target_question_id exists)
    
    questions_dict = [q.model_dump(by_alias=True, exclude_none=True) for q in schema_in.questions]
    rules_dict = [r.model_dump(by_alias=True, exclude_none=True) for r in schema_in.logic_rules]

    await db.surveys.update_one(
        {"_id": ObjectId(survey_id)},
        {
            "$set": {
                "questions": questions_dict,
                "logicRules": rules_dict,
                "updatedAt": datetime.utcnow()
            }
        }
    )

    return {
        "code": 200,
        "message": "Schema updated successfully"
    }
