from typing import List

from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, status

from app.api.deps import get_current_user
from app.core.database import get_database
from app.core.time import utc_now, to_zulu
from app.models.survey import SurveyCreate, SurveyUpdateStatus, SurveySchemaUpdate, SurveyMetadataUpdate
from app.models.user import UserInDB
from app.services.question_service import build_question_snapshot, get_question_version_for_accessible_user


router = APIRouter(prefix="/surveys", tags=["surveys"])


def serialize_dt(value):
    return to_zulu(value)


def get_snapshot(question: dict) -> dict:
    return question["snapshot"]


def get_question_label(question: dict) -> str:
    return f"第{question['orderIndex']}题"


def serialize_schema_question(question: dict) -> dict:
    return {
        "questionId": question["questionId"],
        "version": question["version"],
        "versionId": str(question["versionId"]) if question.get("versionId") is not None else None,
        "orderIndex": question["orderIndex"],
        "snapshot": question.get("snapshot", {}),
    }


def normalize_choice_condition(raw_condition: str, question: dict) -> str:
    snapshot = get_snapshot(question)
    q_label = get_question_label(question)
    tokens = [token for token in str(raw_condition).split() if token]
    if not tokens:
        raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的跳转条件不能为空"})

    indexes: List[int] = []
    seen = set()
    max_index = len(snapshot.get("options", []))

    for token in tokens:
        if not token.isdigit():
            raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的跳转条件必须使用选项行号，多个行号以空格分隔"})
        index = int(token)
        if index < 1 or index > max_index:
            raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的跳转条件包含超出范围的行号"})
        if index in seen:
            raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的跳转条件包含重复行号"})
        seen.add(index)
        indexes.append(index)

    max_select = snapshot.get("maxSelect")
    if max_select == 1 and len(indexes) != 1:
        raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 为单选题，跳转条件只能填写一个行号"})
    if max_select is not None and len(indexes) > max_select:
        raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的跳转条件选择数量不能超过 {max_select} 项"})

    return " ".join(str(index) for index in sorted(indexes))


async def get_owned_survey_or_404(db, survey_id: str, current_user: UserInDB) -> dict:
    survey = await db.surveys.find_one({"_id": ObjectId(survey_id)})
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    if survey["userId"] != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": 40301, "message": "无权操作此问卷"})
    return survey


@router.post("", response_model=dict)
async def create_survey(
    survey_in: SurveyCreate,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database),
):
    survey_dict = survey_in.model_dump(by_alias=True)
    survey_dict["userId"] = current_user.id
    survey_dict["status"] = "DRAFT"
    survey_dict["questions"] = []
    survey_dict["logicRules"] = []
    survey_dict["createdAt"] = utc_now()
    survey_dict["updatedAt"] = utc_now()

    result = await db.surveys.insert_one(survey_dict)
    return {"code": 200, "data": {"survey_id": str(result.inserted_id), "status": "DRAFT"}}


@router.get("", response_model=dict)
async def list_surveys(
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database),
):
    cursor = db.surveys.find({"userId": current_user.id})
    surveys = await cursor.to_list(length=100)
    return {
        "code": 200,
        "data": [
            {
                "survey_id": str(survey["_id"]),
                "title": survey["title"],
                "description": survey.get("description", ""),
                "status": survey["status"],
                "is_anonymous": survey.get("is_anonymous", False),
                "end_time": serialize_dt(survey.get("end_time")),
                "created_at": serialize_dt(survey["createdAt"]),
            }
            for survey in surveys
        ],
    }


@router.get("/{survey_id}/schema", response_model=dict)
async def get_survey_schema(survey_id: str, db=Depends(get_database)):
    survey = await db.surveys.find_one({"_id": ObjectId(survey_id)})
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    return {
        "code": 200,
        "data": {
            "title": survey["title"],
            "description": survey.get("description", ""),
            "is_anonymous": survey.get("is_anonymous", False),
            "status": survey["status"],
            "end_time": serialize_dt(survey.get("end_time")),
            "questions": [serialize_schema_question(question) for question in survey.get("questions", [])],
            "logic_rules": survey.get("logicRules", []),
        },
    }


@router.patch("/{survey_id}", response_model=dict)
async def update_survey_metadata(
    survey_id: str,
    metadata_in: SurveyMetadataUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database),
):
    await get_owned_survey_or_404(db, survey_id, current_user)
    update_fields = metadata_in.model_dump(by_alias=True, exclude_unset=True)
    update_fields["updatedAt"] = utc_now()
    await db.surveys.update_one({"_id": ObjectId(survey_id)}, {"$set": update_fields})
    updated = await db.surveys.find_one({"_id": ObjectId(survey_id)})
    return {
        "code": 200,
        "data": {
            "survey_id": survey_id,
            "title": updated["title"],
            "description": updated.get("description", ""),
            "is_anonymous": updated.get("is_anonymous", False),
            "end_time": serialize_dt(updated.get("end_time")),
        },
    }


@router.patch("/{survey_id}/status", response_model=dict)
async def update_survey_status(
    survey_id: str,
    status_in: SurveyUpdateStatus,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database),
):
    await get_owned_survey_or_404(db, survey_id, current_user)
    await db.surveys.update_one(
        {"_id": ObjectId(survey_id)},
        {"$set": {"status": status_in.status, "updatedAt": utc_now()}},
    )
    return {
        "code": 200,
        "data": {
            "survey_id": survey_id,
            "status": status_in.status,
            "access_url": f"/survey/{survey_id}",
        },
    }


@router.put("/{survey_id}/schema", response_model=dict)
async def update_survey_schema(
    survey_id: str,
    schema_in: SurveySchemaUpdate,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database),
):
    await get_owned_survey_or_404(db, survey_id, current_user)

    question_refs = [question.model_dump(by_alias=True) for question in schema_in.questions]
    rules_dict_list = [rule.model_dump(by_alias=True, exclude_none=True) for rule in schema_in.logic_rules]

    seen_order_indexes = set()
    seen_question_ids = set()
    questions_dict_list = []

    for ref in question_refs:
        order_index = ref["orderIndex"]
        if order_index < 1:
            raise HTTPException(422, detail={"code": 42201, "message": "题目顺序必须从 1 开始"})
        if order_index in seen_order_indexes:
            raise HTTPException(422, detail={"code": 42201, "message": f"第{order_index}题 的顺序编号重复"})
        seen_order_indexes.add(order_index)

        question_doc = await get_question_version_for_accessible_user(db, current_user.id, ref["questionId"], ref["version"])
        if not question_doc:
            raise HTTPException(422, detail={"code": 42201, "message": f"题目 {ref['questionId']} 的版本 {ref['version']} 不存在"})
        if ref["questionId"] in seen_question_ids:
            raise HTTPException(422, detail={"code": 42201, "message": f"题目 {ref['questionId']} 在同一问卷中重复出现"})
        seen_question_ids.add(ref["questionId"])

        questions_dict_list.append(
            {
                "questionId": ref["questionId"],
                "version": ref["version"],
                "versionId": question_doc["_id"],
                "orderIndex": order_index,
                "snapshot": build_question_snapshot(question_doc),
            }
        )

    questions_dict_list.sort(key=lambda item: item["orderIndex"])
    q_map = {question["questionId"]: question for question in questions_dict_list}
    seen_conditions = {}

    for rule in rules_dict_list:
        src_id = rule["sourceQuestionId"]
        target_id = rule["targetQuestionId"]
        if src_id not in q_map or target_id not in q_map:
            raise HTTPException(422, detail={"code": 42201, "message": f"规则 {rule.get('ruleId')} 关联题目不存在"})

        src_q = q_map[src_id]
        target_q = q_map[target_id]
        src_label = get_question_label(src_q)
        cond = rule["triggerCondition"]

        if get_snapshot(src_q)["type"] == "ChoiceQuestion":
            cond = normalize_choice_condition(cond, src_q)
            rule["triggerCondition"] = cond

        if target_q["orderIndex"] <= src_q["orderIndex"]:
            raise HTTPException(422, detail={"code": 42201, "message": f"{src_label} 的跳转目标必须在当前题目之后"})

        if src_id not in seen_conditions:
            seen_conditions[src_id] = set()
        if cond in seen_conditions[src_id]:
            raise HTTPException(422, detail={"code": 42201, "message": f"{src_label} 存在重复的跳转条件: {cond}"})
        seen_conditions[src_id].add(cond)

    await db.surveys.update_one(
        {"_id": ObjectId(survey_id)},
        {"$set": {"questions": questions_dict_list, "logicRules": rules_dict_list, "updatedAt": utc_now()}},
    )
    return {"code": 200, "message": "Schema updated successfully"}


@router.get("/{survey_id}/statistics", response_model=dict)
async def get_survey_statistics(
    survey_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database),
):
    survey = await get_owned_survey_or_404(db, survey_id, current_user)
    survey_object_id = ObjectId(survey_id)
    total_respondents = await db.answers.count_documents({"surveyId": survey_object_id})

    micro_stats = {}
    for question in survey.get("questions", []):
        snapshot = get_snapshot(question)
        q_id = question["questionId"]
        q_type = snapshot["type"]
        q_title = snapshot.get("title", "")

        if q_type == "ChoiceQuestion":
            pipeline = [
                {"$match": {"surveyId": survey_object_id, f"payloads.{q_id}": {"$exists": True}}},
                {"$unwind": f"$payloads.{q_id}"},
                {"$group": {"_id": f"$payloads.{q_id}", "count": {"$sum": 1}}},
            ]
            results = await db.answers.aggregate(pipeline).to_list(length=100)
            micro_stats[q_id] = {
                "type": q_type,
                "title": q_title,
                "total_answers": total_respondents,
                "distribution": {result["_id"]: result["count"] for result in results},
            }
        elif q_type == "NumberQuestion":
            pipeline = [
                {"$match": {"surveyId": survey_object_id, f"payloads.{q_id}": {"$ne": None}}},
                {"$group": {"_id": None, "average": {"$avg": f"$payloads.{q_id}"}, "count": {"$sum": 1}}},
            ]
            results = await db.answers.aggregate(pipeline).to_list(length=1)
            avg_val = results[0]["average"] if results else 0
            count = results[0]["count"] if results else 0
            detail_results = await db.answers.find(
                {"surveyId": survey_object_id, f"payloads.{q_id}": {"$ne": None}},
                {f"payloads.{q_id}": 1},
            ).limit(50).to_list(length=50)
            micro_stats[q_id] = {
                "type": q_type,
                "title": q_title,
                "valid_answers": count,
                "average_value": round(float(avg_val), 2) if count else 0.0,
                "text_list": [str(item["payloads"][q_id]) for item in detail_results if q_id in item.get("payloads", {})],
            }
        elif q_type == "TextQuestion":
            results = await db.answers.find(
                {"surveyId": survey_object_id, f"payloads.{q_id}": {"$ne": ""}},
                {f"payloads.{q_id}": 1},
            ).limit(20).to_list(length=20)
            text_list = [item["payloads"][q_id] for item in results if q_id in item.get("payloads", {})]
            micro_stats[q_id] = {
                "type": q_type,
                "title": q_title,
                "total_answers": len(text_list),
                "text_list": text_list,
            }

    return {
        "code": 200,
        "data": {"macro_stats": {"total_respondents": total_respondents}, "micro_stats": micro_stats},
    }
