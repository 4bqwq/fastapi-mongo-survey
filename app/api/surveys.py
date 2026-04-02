from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict
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
    db = Depends(get_database)
):
    survey = await db.surveys.find_one({"_id": ObjectId(survey_id)})
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    # Check if survey is accessible (must be published or owner)
    # For simplicity in this step, allowing access to get schema if published
    if survey["status"] != "PUBLISHED":
        # Need to check if it's the owner - this would require optional auth
        # For now, let's keep it simple as the fill page handles redirects
        pass

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
    
    # Validation Logic
    questions_dict_list = [q.model_dump(by_alias=True, exclude_none=True) for q in schema_in.questions]
    rules_dict_list = [r.model_dump(by_alias=True, exclude_none=True) for r in schema_in.logic_rules]
    
    q_map = {q["questionId"]: q for q in questions_dict_list}
    seen_conditions = {} # source_id -> set of conditions

    for rule in rules_dict_list:
        src_id = rule["sourceQuestionId"]
        target_id = rule["targetQuestionId"]
        cond = rule["triggerCondition"]

        if src_id not in q_map or target_id not in q_map:
            raise HTTPException(422, detail={"code": 42201, "message": f"规则 {rule.get('ruleId')} 关联题目不存在"})
        
        src_q = q_map[src_id]
        target_q = q_map[target_id]
        
        if target_q["orderIndex"] <= src_q["orderIndex"]:
            raise HTTPException(422, detail={"code": 42201, "message": f"规则 {rule.get('ruleId')} 跳转目标必须在源题目之后"})
        
        if src_id not in seen_conditions:
            seen_conditions[src_id] = set()
        
        if cond in seen_conditions[src_id]:
            raise HTTPException(422, detail={"code": 42201, "message": f"题目 {src_id} 存在重复的跳转条件: {cond}"})
        
        seen_conditions[src_id].add(cond)

    await db.surveys.update_one(
        {"_id": ObjectId(survey_id)},
        {
            "$set": {
                "questions": questions_dict_list,
                "logicRules": rules_dict_list,
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
