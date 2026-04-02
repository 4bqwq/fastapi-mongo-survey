from fastapi import APIRouter, HTTPException, Depends, status
from typing import List
from app.models.survey import SurveyCreate, SurveyUpdateStatus, SurveyInDB, SurveyOut
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
