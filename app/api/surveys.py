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
            "status": status_in.status,
            "access_url": f"/survey/{survey_id}"
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

@router.get("/{survey_id}/statistics", response_model=dict)
async def get_survey_statistics(
    survey_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db = Depends(get_database)
):
    # 1. Verify ownership
    survey = await db.surveys.find_one({"_id": ObjectId(survey_id)})
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    if survey["userId"] != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 40301, "message": "无权查看此问卷的统计数据"}
        )

    # 2. Macro stats
    total_respondents = await db.answers.count_documents({"surveyId": ObjectId(survey_id)})
    
    micro_stats = {}
    questions = survey.get("questions", [])
    
    for q in questions:
        q_id = q["questionId"]
        q_type = q["type"]
        
        if q_type == "ChoiceQuestion":
            # Count distribution
            pipeline = [
                {"$match": {"surveyId": ObjectId(survey_id), f"payloads.{q_id}": {"$exists": True}}},
                {"$unwind": f"$payloads.{q_id}"},
                {"$group": {"_id": f"$payloads.{q_id}", "count": {"$sum": 1}}}
            ]
            cursor = db.answers.aggregate(pipeline)
            results = await cursor.to_list(length=100)
            distribution = {r["_id"]: r["count"] for r in results}
            
            micro_stats[q_id] = {
                "type": q_type,
                "title": q.get("title", ""),
                "total_answers": total_respondents,
                "distribution": distribution
            }
            
        elif q_type == "NumberQuestion":
            # Calculate average
            pipeline = [
                {"$match": {"surveyId": ObjectId(survey_id), f"payloads.{q_id}": {"$ne": None}}},
                {"$group": {"_id": None, "average": {"$avg": f"$payloads.{q_id}"}, "count": {"$sum": 1}}}
            ]
            cursor = db.answers.aggregate(pipeline)
            results = await cursor.to_list(length=1)
            
            avg_val = results[0]["average"] if results else 0
            count = results[0]["count"] if results else 0
            
            micro_stats[q_id] = {
                "type": q_type,
                "title": q.get("title", ""),
                "valid_answers": count,
                "average_value": round(float(avg_val), 2)
            }
            
        elif q_type == "TextQuestion":
            # List some answers
            cursor = db.answers.find(
                {"surveyId": ObjectId(survey_id), f"payloads.{q_id}": {"$ne": ""}},
                {f"payloads.{q_id}": 1}
            ).limit(20)
            results = await cursor.to_list(length=20)
            text_list = [r["payloads"][q_id] for r in results if q_id in r["payloads"]]
            
            micro_stats[q_id] = {
                "type": q_type,
                "title": q.get("title", ""),
                "total_answers": len(text_list),
                "text_list": text_list
            }

    return {
        "code": 200,
        "data": {
            "macro_stats": {"total_respondents": total_respondents},
            "micro_stats": micro_stats
        }
    }
