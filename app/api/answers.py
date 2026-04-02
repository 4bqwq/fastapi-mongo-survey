from fastapi import APIRouter, HTTPException, Depends, status
from app.models.answer import AnswerCreate, AnswerInDB
from app.models.user import UserInDB
from app.api.deps import get_current_user
from app.core.database import get_database
from datetime import datetime
from bson import ObjectId
from typing import Optional

router = APIRouter(prefix="/surveys", tags=["answers"])

@router.post("/{survey_id}/answers", response_model=dict)
async def submit_answer(
    survey_id: str,
    answer_in: AnswerCreate,
    current_user: Optional[UserInDB] = Depends(get_current_user), # Spec says filler must be logged in for non-anonymous
    db = Depends(get_database)
):
    survey = await db.surveys.find_one({"_id": ObjectId(survey_id)})
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    
    if survey["status"] != "PUBLISHED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 40302, "message": "该问卷已关闭或未发布"}
        )

    # Server-side validation
    payloads = answer_in.payloads
    questions = survey.get("questions", [])
    
    for q in questions:
        q_id = q["questionId"]
        ans = payloads.get(q_id)
        
        # 1. Required check
        if q.get("isRequired") and (ans is None or ans == "" or (isinstance(ans, list) and len(ans) == 0)):
            raise HTTPException(
                status_code=422,
                detail={"code": 42201, "message": f"题目 {q_id} 为必答题"}
            )
        
        if ans is not None:
            # 2. Type specific validation
            if q["type"] == "NumberQuestion":
                try:
                    val = float(ans)
                    if q.get("minValue") is not None and val < q["minValue"]:
                        raise HTTPException(422, detail={"code": 42205, "message": f"题目 {q_id} 值过小"})
                    if q.get("maxValue") is not None and val > q["maxValue"]:
                        raise HTTPException(422, detail={"code": 42205, "message": f"题目 {q_id} 值过大"})
                except ValueError:
                    raise HTTPException(422, detail={"code": 42205, "message": f"题目 {q_id} 必须为数字"})
            
            elif q["type"] == "ChoiceQuestion":
                if not isinstance(ans, list):
                    raise HTTPException(422, detail={"code": 42201, "message": f"题目 {q_id} 格式错误"})
                if q.get("minSelect") and len(ans) < q["minSelect"]:
                    raise HTTPException(422, detail={"code": 42201, "message": f"题目 {q_id} 选项过少"})
                if q.get("maxSelect") and len(ans) > q["maxSelect"]:
                    raise HTTPException(422, detail={"code": 42201, "message": f"题目 {q_id} 选项过多"})

    # Save to DB
    answer_doc = {
        "surveyId": ObjectId(survey_id),
        "respondentId": current_user.id if current_user and not survey["is_anonymous"] else None,
        "payloads": payloads,
        "submittedAt": datetime.utcnow(),
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow()
    }
    
    result = await db.answers.insert_one(answer_doc)
    
    return {
        "code": 200,
        "data": {
            "answer_id": str(result.inserted_id),
            "submitted_at": answer_doc["submittedAt"].isoformat() + "Z"
        }
    }
