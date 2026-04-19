from datetime import datetime

from bson import ObjectId
from fastapi import HTTPException


QUESTION_CONTENT_FIELDS = [
    "type",
    "title",
    "isRequired",
    "options",
    "minSelect",
    "maxSelect",
    "minLength",
    "maxLength",
    "minValue",
    "maxValue",
    "mustBeInteger",
]


def get_question_label(question: dict) -> str:
    return question.get("title", "题目")


def validate_question_content(question: dict, label: str | None = None) -> dict:
    q_type = question["type"]
    q_label = label or get_question_label(question)

    normalized = {
        "type": q_type,
        "title": question["title"],
        "isRequired": question.get("isRequired", True),
    }

    if q_type == "ChoiceQuestion":
        options = question.get("options") or []
        if len(options) < 2:
            raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 至少需要 2 个选项"})
        if len(set(options)) != len(options):
            raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的选项内容不能重复"})

        min_select = question.get("minSelect")
        max_select = question.get("maxSelect")
        if min_select is not None and min_select < 1:
            raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的最少选择数不能小于 1"})
        if max_select is not None and max_select < 1:
            raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的最多选择数不能小于 1"})
        if min_select is not None and max_select is not None and max_select < min_select:
            raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的最大选择数不能小于最小选择数"})
        if max_select is not None and max_select > len(options):
            raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的最多选择数不能超过选项数"})

        normalized.update({
            "options": options,
            "minSelect": min_select,
            "maxSelect": max_select,
        })
    elif q_type == "TextQuestion":
        min_length = question.get("minLength")
        max_length = question.get("maxLength")
        if min_length is not None and min_length < 0:
            raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的最少字数不能小于 0"})
        if max_length is not None and max_length < 0:
            raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的最多字数不能小于 0"})
        if min_length is not None and max_length is not None and max_length < min_length:
            raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的最多字数不能小于最少字数"})

        normalized.update({
            "minLength": min_length,
            "maxLength": max_length,
        })
    elif q_type == "NumberQuestion":
        min_value = question.get("minValue")
        max_value = question.get("maxValue")
        if min_value is not None and max_value is not None and max_value < min_value:
            raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的最大值不能小于最小值"})

        normalized.update({
            "minValue": min_value,
            "maxValue": max_value,
            "mustBeInteger": question.get("mustBeInteger", False),
        })
    else:
        raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的题型不支持"})

    return normalized


def extract_question_content(question_doc: dict) -> dict:
    return {field: question_doc[field] for field in QUESTION_CONTENT_FIELDS if field in question_doc}


def build_question_snapshot(question_doc: dict) -> dict:
    return extract_question_content(question_doc)


def serialize_question_doc(question_doc: dict) -> dict:
    data = extract_question_content(question_doc)
    data.update(
        {
            "question_id": question_doc["questionId"],
            "version": question_doc["version"],
            "version_id": str(question_doc["_id"]),
            "previous_version_id": str(question_doc["previousVersionId"]) if question_doc.get("previousVersionId") else None,
        }
    )
    return data


async def create_question(db, user_id: ObjectId, payload: dict) -> dict:
    now = datetime.utcnow()
    question_id = f"q_{ObjectId()}"
    content = validate_question_content(payload)
    root_id = ObjectId()
    doc = {
        "_id": root_id,
        "questionId": question_id,
        "userId": user_id,
        "version": 1,
        "previousVersionId": None,
        "versionChainRootId": root_id,
        **content,
        "createdAt": now,
        "updatedAt": now,
    }
    await db.questions.insert_one(doc)
    return doc


async def get_question_version_for_user(db, user_id: ObjectId, question_id: str, version: int) -> dict | None:
    return await db.questions.find_one({"userId": user_id, "questionId": question_id, "version": version})


async def create_question_version(db, user_id: ObjectId, question_id: str, base_version: int, payload: dict) -> dict:
    base_doc = await get_question_version_for_user(db, user_id, question_id, base_version)
    if not base_doc:
        raise HTTPException(404, detail={"code": 40401, "message": "题目版本不存在"})

    latest_doc = await db.questions.find_one(
        {"userId": user_id, "questionId": question_id},
        sort=[("version", -1)],
    )
    next_version = latest_doc["version"] + 1
    content = validate_question_content(payload)
    now = datetime.utcnow()
    doc = {
        "questionId": question_id,
        "userId": user_id,
        "version": next_version,
        "previousVersionId": base_doc["_id"],
        "versionChainRootId": base_doc["versionChainRootId"],
        **content,
        "createdAt": now,
        "updatedAt": now,
    }
    result = await db.questions.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc
