from fastapi import APIRouter, HTTPException, Depends, status
from app.models.answer import AnswerCreate
from app.models.user import UserInDB
from app.api.deps import get_current_user
from app.core.database import get_database
from datetime import datetime
from bson import ObjectId
from typing import Set

router = APIRouter(prefix="/surveys", tags=["answers"])

def get_question_label(question: dict) -> str:
    return f"第{question['orderIndex']}题"

def get_effective_questions(questions: list, logic_rules: list, payloads: dict) -> Set[str]:
    """Calculate which questions are actually seen by the user based on logic jumps."""
    effective_ids = set()
    sorted_qs = sorted(questions, key=lambda x: x["orderIndex"])
    
    i = 0
    while i < len(sorted_qs):
        q = sorted_qs[i]
        effective_ids.add(q["questionId"])
        
        # Check if there's a matching rule for this question
        ans = payloads.get(q["questionId"])
        jumped = False
        if ans:
            # Find rules for this question
            rules = [r for r in logic_rules if r["sourceQuestionId"] == q["questionId"]]
            for rule in rules:
                match = False
                if isinstance(ans, list):
                    match = rule["triggerCondition"] in ans
                else:
                    match = str(ans) == str(rule["triggerCondition"])
                
                if match:
                    # Find target question index
                    target_id = rule["targetQuestionId"]
                    target_q = next((t for t in sorted_qs if t["questionId"] == target_id), None)
                    if target_q:
                        # Jump to target
                        i = sorted_qs.index(target_q)
                        jumped = True
                        break
            if jumped:
                continue
        i += 1
    return effective_ids

@router.post("/{survey_id}/answers", response_model=dict)
async def submit_answer(
    survey_id: str,
    answer_in: AnswerCreate,
    current_user: UserInDB = Depends(get_current_user), # Mandatory login for all
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

    end_time = survey.get("end_time")
    if end_time and end_time <= datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": 40302, "message": "该问卷已截止，无法继续提交"}
        )

    payloads = answer_in.payloads
    submit_as_anonymous = answer_in.submit_as_anonymous
    questions = survey.get("questions", [])
    logic_rules = survey.get("logicRules", [])
    
    # Calculate effective path
    effective_ids = get_effective_questions(questions, logic_rules, payloads)
    
    for q in questions:
        q_id = q["questionId"]
        q_label = get_question_label(q)
        
        # Skip validation for questions NOT in the effective path
        if q_id not in effective_ids:
            continue
            
        ans = payloads.get(q_id)
        
        # 1. Required check (only for effective questions)
        if q.get("isRequired") and (ans is None or ans == "" or (isinstance(ans, list) and len(ans) == 0)):
            raise HTTPException(
                status_code=422,
                detail={"code": 42201, "message": f"{q_label} 为必答题"}
            )
        
        if ans is not None:
            # 2. Type specific validation
            if q["type"] == "NumberQuestion":
                try:
                    val = float(ans)
                    if q.get("minValue") is not None and val < q["minValue"]:
                        raise HTTPException(422, detail={"code": 42205, "message": f"{q_label} 的数值不能小于 {q['minValue']}"})
                    if q.get("maxValue") is not None and val > q["maxValue"]:
                        raise HTTPException(422, detail={"code": 42205, "message": f"{q_label} 的数值不能大于 {q['maxValue']}"})
                    if q.get("mustBeInteger") and not val.is_integer():
                        raise HTTPException(422, detail={"code": 42205, "message": f"{q_label} 必须填写整数"})
                except (ValueError, TypeError):
                    raise HTTPException(422, detail={"code": 42205, "message": f"{q_label} 必须为数字"})
            
            elif q["type"] == "ChoiceQuestion":
                if not isinstance(ans, list):
                    raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的答案格式错误"})
                if q.get("minSelect") and len(ans) < q["minSelect"]:
                    raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 至少需要选择 {q['minSelect']} 项"})
                if q.get("maxSelect") and len(ans) > q["maxSelect"]:
                    raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 最多只能选择 {q['maxSelect']} 项"})

            elif q["type"] == "TextQuestion":
                if not isinstance(ans, str):
                    raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的答案格式错误"})
                if q.get("minLength") is not None and len(ans) < q["minLength"]:
                    raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 至少需要输入 {q['minLength']} 个字"})
                if q.get("maxLength") is not None and len(ans) > q["maxLength"]:
                    raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 最多只能输入 {q['maxLength']} 个字"})

    if submit_as_anonymous and not survey.get("is_anonymous", False):
        raise HTTPException(
            status_code=422,
            detail={"code": 42201, "message": "当前问卷未开启匿名提交"}
        )

    # Save to DB
    # If anonymous, respondentId = "-1", else current_user.id
    respondent_id = "-1" if submit_as_anonymous else current_user.id

    answer_doc = {
        "surveyId": ObjectId(survey_id),
        "respondentId": respondent_id,
        "isAnonymousSubmission": submit_as_anonymous,
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
