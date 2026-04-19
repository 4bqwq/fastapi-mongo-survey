from datetime import datetime
from typing import Set

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, status

from app.api.deps import get_current_user
from app.core.database import get_database
from app.models.answer import AnswerCreate
from app.models.user import UserInDB


router = APIRouter(prefix="/surveys", tags=["answers"])


def get_question_label(question: dict) -> str:
    return f"第{question['orderIndex']}题"


def get_snapshot(question: dict) -> dict:
    return question["snapshot"]


def normalize_choice_indexes(indexes: list[int]) -> str:
    return " ".join(str(index) for index in sorted(indexes))


def get_choice_answer_condition(question: dict, answer: list) -> str | None:
    snapshot = get_snapshot(question)
    if not isinstance(answer, list) or not answer:
        return None

    option_to_index = {option: idx + 1 for idx, option in enumerate(snapshot.get("options", []))}
    indexes = []
    seen = set()
    for option in answer:
        if option not in option_to_index or option in seen:
            return None
        seen.add(option)
        indexes.append(option_to_index[option])
    return normalize_choice_indexes(indexes)


def get_effective_questions(questions: list, logic_rules: list, payloads: dict) -> Set[str]:
    effective_ids = set()
    sorted_qs = sorted(questions, key=lambda item: item["orderIndex"])
    question_index = {question["questionId"]: idx for idx, question in enumerate(sorted_qs)}

    i = 0
    while i < len(sorted_qs):
        question = sorted_qs[i]
        q_id = question["questionId"]
        effective_ids.add(q_id)

        answer = payloads.get(q_id)
        jumped = False
        if answer is not None:
            for rule in [rule for rule in logic_rules if rule["sourceQuestionId"] == q_id]:
                snapshot = get_snapshot(question)
                if snapshot["type"] == "ChoiceQuestion":
                    normalized_answer = get_choice_answer_condition(question, answer)
                    match = normalized_answer is not None and normalized_answer == rule["triggerCondition"]
                else:
                    match = str(answer) == str(rule["triggerCondition"])

                if match:
                    i = question_index.get(rule["targetQuestionId"], i + 1)
                    jumped = True
                    break
        if not jumped:
            i += 1
    return effective_ids


@router.post("/{survey_id}/answers", response_model=dict)
async def submit_answer(
    survey_id: str,
    answer_in: AnswerCreate,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database),
):
    survey = await db.surveys.find_one({"_id": ObjectId(survey_id)})
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    if survey["status"] != "PUBLISHED":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": 40302, "message": "该问卷已关闭或未发布"})

    end_time = survey.get("end_time")
    if end_time and end_time <= datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": 40302, "message": "该问卷已截止，无法继续提交"})

    payloads = answer_in.payloads
    submit_as_anonymous = answer_in.submit_as_anonymous
    questions = survey.get("questions", [])
    logic_rules = survey.get("logicRules", [])
    effective_ids = get_effective_questions(questions, logic_rules, payloads)

    for question in questions:
        q_id = question["questionId"]
        q_label = get_question_label(question)
        snapshot = get_snapshot(question)
        answer = payloads.get(q_id)

        if q_id not in effective_ids:
            continue

        if snapshot.get("isRequired") and (answer is None or answer == "" or (isinstance(answer, list) and len(answer) == 0)):
            raise HTTPException(status_code=422, detail={"code": 42201, "message": f"{q_label} 为必答题"})

        if answer is None:
            continue

        if snapshot["type"] == "NumberQuestion":
            try:
                value = float(answer)
            except (TypeError, ValueError):
                raise HTTPException(422, detail={"code": 42205, "message": f"{q_label} 必须为数字"})

            if snapshot.get("minValue") is not None and value < snapshot["minValue"]:
                raise HTTPException(422, detail={"code": 42205, "message": f"{q_label} 的数值不能小于 {snapshot['minValue']}"})
            if snapshot.get("maxValue") is not None and value > snapshot["maxValue"]:
                raise HTTPException(422, detail={"code": 42205, "message": f"{q_label} 的数值不能大于 {snapshot['maxValue']}"})
            if snapshot.get("mustBeInteger") and not value.is_integer():
                raise HTTPException(422, detail={"code": 42205, "message": f"{q_label} 必须填写整数"})
        elif snapshot["type"] == "ChoiceQuestion":
            if not isinstance(answer, list):
                raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的答案格式错误"})
            options = snapshot.get("options", [])
            if len(answer) != len(set(answer)):
                raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的选项不能重复"})
            if any(option not in options for option in answer):
                raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 包含不存在的选项"})
            if snapshot.get("minSelect") is not None and len(answer) < snapshot["minSelect"]:
                raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 至少需要选择 {snapshot['minSelect']} 项"})
            if snapshot.get("maxSelect") is not None and len(answer) > snapshot["maxSelect"]:
                raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 最多只能选择 {snapshot['maxSelect']} 项"})
        elif snapshot["type"] == "TextQuestion":
            if not isinstance(answer, str):
                raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的答案格式错误"})
            if snapshot.get("minLength") is not None and len(answer) < snapshot["minLength"]:
                raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 至少需要输入 {snapshot['minLength']} 个字"})
            if snapshot.get("maxLength") is not None and len(answer) > snapshot["maxLength"]:
                raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 最多只能输入 {snapshot['maxLength']} 个字"})

    if submit_as_anonymous and not survey.get("is_anonymous", False):
        raise HTTPException(status_code=422, detail={"code": 42201, "message": "当前问卷未开启匿名提交"})

    respondent_id = "-1" if submit_as_anonymous else current_user.id
    answer_doc = {
        "surveyId": ObjectId(survey_id),
        "respondentId": respondent_id,
        "isAnonymousSubmission": submit_as_anonymous,
        "payloads": payloads,
        "submittedAt": datetime.utcnow(),
        "createdAt": datetime.utcnow(),
        "updatedAt": datetime.utcnow(),
    }
    result = await db.answers.insert_one(answer_doc)
    return {
        "code": 200,
        "data": {"answer_id": str(result.inserted_id), "submitted_at": answer_doc["submittedAt"].isoformat() + "Z"},
    }
