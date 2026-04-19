from bson import ObjectId
from fastapi import HTTPException, status
from app.core.time import utc_now, to_zulu


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


def get_question_access_filter(user_id: ObjectId) -> dict:
    return {"$or": [{"userId": user_id}, {"sharedWith.userId": user_id}]}


def get_owned_question_filter(user_id: ObjectId) -> dict:
    return {"userId": user_id}


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

        normalized.update({"options": options, "minSelect": min_select, "maxSelect": max_select})
    elif q_type == "TextQuestion":
        min_length = question.get("minLength")
        max_length = question.get("maxLength")
        if min_length is not None and min_length < 0:
            raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的最少字数不能小于 0"})
        if max_length is not None and max_length < 0:
            raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的最多字数不能小于 0"})
        if min_length is not None and max_length is not None and max_length < min_length:
            raise HTTPException(422, detail={"code": 42201, "message": f"{q_label} 的最多字数不能小于最少字数"})

        normalized.update({"minLength": min_length, "maxLength": max_length})
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


def serialize_shared_grants(question_docs: list[dict], users_by_id: dict[ObjectId, dict]) -> list[dict]:
    if not question_docs:
        return []

    first_doc = question_docs[0]
    grants = []
    for grant in first_doc.get("sharedWith", []):
        user = users_by_id.get(grant["userId"])
        grants.append(
            {
                "user_id": str(grant["userId"]),
                "username": user["username"] if user else None,
                "shared_at": to_zulu(grant.get("sharedAt")),
            }
        )
    return grants


def serialize_library_state(question_doc: dict, user_id: ObjectId) -> bool:
    return any(grant["userId"] == user_id for grant in question_doc.get("libraryMembers", []))


def serialize_question_doc(question_doc: dict) -> dict:
    data = extract_question_content(question_doc)
    data.update(
        {
            "question_id": question_doc["questionId"],
            "owner_user_id": str(question_doc["userId"]),
            "version": question_doc["version"],
            "version_id": str(question_doc["_id"]),
            "previous_version_id": str(question_doc["previousVersionId"]) if question_doc.get("previousVersionId") else None,
            "shared_user_ids": [str(grant["userId"]) for grant in question_doc.get("sharedWith", [])],
            "library_user_ids": [str(grant["userId"]) for grant in question_doc.get("libraryMembers", [])],
        }
    )
    return data


def ensure_question_owner(question_doc: dict | None, user_id: ObjectId) -> dict:
    if not question_doc:
        raise HTTPException(404, detail={"code": 40401, "message": "题目不存在"})
    if question_doc["userId"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": 40301, "message": "无权修改该题目"})
    return question_doc


async def get_question_version_for_accessible_user(db, user_id: ObjectId, question_id: str, version: int) -> dict | None:
    return await db.questions.find_one(
        {
            "questionId": question_id,
            "version": version,
            **get_question_access_filter(user_id),
        }
    )


async def get_question_any_version_for_accessible_user(db, user_id: ObjectId, question_id: str) -> dict | None:
    return await db.questions.find_one({"questionId": question_id, **get_question_access_filter(user_id)})


async def create_question(db, user_id: ObjectId, payload: dict) -> dict:
    now = utc_now()
    question_id = f"q_{ObjectId()}"
    content = validate_question_content(payload)
    root_id = ObjectId()
    doc = {
        "_id": root_id,
        "questionId": question_id,
        "userId": user_id,
        "version": 1,
        "sharedWith": [],
        "libraryMembers": [],
        "previousVersionId": None,
        "versionChainRootId": root_id,
        **content,
        "createdAt": now,
        "updatedAt": now,
    }
    await db.questions.insert_one(doc)
    return doc


async def create_question_version(db, user_id: ObjectId, question_id: str, base_version: int, payload: dict) -> dict:
    base_doc = await db.questions.find_one({"questionId": question_id, "version": base_version, "userId": user_id})
    if not base_doc:
        raise HTTPException(404, detail={"code": 40401, "message": "题目版本不存在"})

    latest_doc = await db.questions.find_one({"userId": user_id, "questionId": question_id}, sort=[("version", -1)])
    next_version = latest_doc["version"] + 1
    content = validate_question_content(payload)
    now = utc_now()
    doc = {
        "questionId": question_id,
        "userId": user_id,
        "version": next_version,
        "sharedWith": list(base_doc.get("sharedWith", [])),
        "libraryMembers": list(base_doc.get("libraryMembers", [])),
        "previousVersionId": base_doc["_id"],
        "versionChainRootId": base_doc["versionChainRootId"],
        **content,
        "createdAt": now,
        "updatedAt": now,
    }
    result = await db.questions.insert_one(doc)
    doc["_id"] = result.inserted_id
    return doc


async def list_accessible_question_versions(db, user_id: ObjectId, question_id: str) -> list[dict]:
    cursor = db.questions.find({"questionId": question_id, **get_question_access_filter(user_id)}, sort=[("version", 1)])
    return await cursor.to_list(length=100)


async def share_question_with_user(db, owner_id: ObjectId, question_id: str, target_user: dict) -> list[dict]:
    owner_doc = await db.questions.find_one({"questionId": question_id, "userId": owner_id})
    if not owner_doc:
        accessible_doc = await get_question_any_version_for_accessible_user(db, owner_id, question_id)
        if accessible_doc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": 40301, "message": "无权修改该题目"})
        raise HTTPException(404, detail={"code": 40401, "message": "题目不存在"})

    if target_user["_id"] == owner_id:
        raise HTTPException(422, detail={"code": 42201, "message": "不能共享给自己"})

    all_versions = await db.questions.find({"questionId": question_id, "userId": owner_id}).to_list(length=200)
    already_shared = any(grant["userId"] == target_user["_id"] for grant in all_versions[0].get("sharedWith", []))
    if already_shared:
        return all_versions

    grant = {"userId": target_user["_id"], "sharedAt": utc_now()}
    await db.questions.update_many(
        {"questionId": question_id, "userId": owner_id},
        {"$push": {"sharedWith": grant}, "$set": {"updatedAt": utc_now()}},
    )
    return await db.questions.find({"questionId": question_id, "userId": owner_id}, sort=[("version", 1)]).to_list(length=200)


async def list_question_shares(db, owner_id: ObjectId, question_id: str) -> list[dict]:
    owner_doc = await db.questions.find_one({"questionId": question_id, "userId": owner_id})
    if not owner_doc:
        accessible_doc = await get_question_any_version_for_accessible_user(db, owner_id, question_id)
        if accessible_doc:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail={"code": 40301, "message": "无权查看共享列表"})
        raise HTTPException(404, detail={"code": 40401, "message": "题目不存在"})
    return await db.questions.find({"questionId": question_id, "userId": owner_id}, sort=[("version", 1)]).to_list(length=200)


async def list_question_usages(db, question_id: str) -> list[dict]:
    cursor = db.surveys.find({"questions.questionId": question_id})
    surveys = await cursor.to_list(length=500)
    usages = []
    for survey in surveys:
        for question in survey.get("questions", []):
            if question["questionId"] == question_id:
                usages.append(
                    {
                        "survey_id": str(survey["_id"]),
                        "survey_title": survey["title"],
                        "survey_owner_id": survey["userId"],
                        "status": survey["status"],
                        "question_version": question["version"],
                        "order_index": question["orderIndex"],
                    }
                )
    usages.sort(key=lambda item: (item["survey_title"], item["order_index"], item["question_version"]))
    return usages


async def list_question_snapshot_usages(db, question_id: str) -> list[dict]:
    cursor = db.surveys.find({"questions.questionId": question_id})
    surveys = await cursor.to_list(length=500)
    snapshot_usages = []
    for survey in surveys:
        for question in survey.get("questions", []):
            if question["questionId"] == question_id:
                snapshot_usages.append(
                    {
                        "surveyId": survey["_id"],
                        "surveyTitle": survey["title"],
                        "status": survey["status"],
                        "version": question["version"],
                        "snapshot": question["snapshot"],
                    }
                )
    return snapshot_usages


def ensure_consistent_cross_survey_type(snapshot_usages: list[dict]) -> tuple[str, str]:
    if not snapshot_usages:
        raise HTTPException(404, detail={"code": 40401, "message": "题目暂无跨问卷统计数据"})

    snapshot_types = {usage["snapshot"]["type"] for usage in snapshot_usages}
    if len(snapshot_types) > 1:
        raise HTTPException(422, detail={"code": 42201, "message": "该题存在多种题型版本，无法直接合并统计"})

    first_snapshot = snapshot_usages[0]["snapshot"]
    return first_snapshot["type"], first_snapshot.get("title", "")


async def get_cross_survey_question_statistics(db, question_id: str) -> dict:
    snapshot_usages = await list_question_snapshot_usages(db, question_id)
    question_type, title = ensure_consistent_cross_survey_type(snapshot_usages)
    survey_ids = list({usage["surveyId"] for usage in snapshot_usages})
    survey_count = len(survey_ids)

    if question_type == "ChoiceQuestion":
        total_answers = await db.answers.count_documents({"surveyId": {"$in": survey_ids}, f"payloads.{question_id}": {"$exists": True}})
        pipeline = [
            {"$match": {"surveyId": {"$in": survey_ids}, f"payloads.{question_id}": {"$exists": True}}},
            {"$unwind": f"$payloads.{question_id}"},
            {"$group": {"_id": f"$payloads.{question_id}", "count": {"$sum": 1}}},
        ]
        results = await db.answers.aggregate(pipeline).to_list(length=200)
        return {
            "question_id": question_id,
            "type": question_type,
            "title": title,
            "survey_count": survey_count,
            "total_answers": total_answers,
            "distribution": {result["_id"]: result["count"] for result in results},
        }

    if question_type == "NumberQuestion":
        pipeline = [
            {"$match": {"surveyId": {"$in": survey_ids}, f"payloads.{question_id}": {"$ne": None}}},
            {"$group": {"_id": None, "average": {"$avg": f"$payloads.{question_id}"}, "count": {"$sum": 1}}},
        ]
        results = await db.answers.aggregate(pipeline).to_list(length=1)
        avg_val = results[0]["average"] if results else 0
        count = results[0]["count"] if results else 0

        distribution_pipeline = [
            {"$match": {"surveyId": {"$in": survey_ids}, f"payloads.{question_id}": {"$ne": None}}},
            {"$group": {"_id": f"$payloads.{question_id}", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]
        distribution_results = await db.answers.aggregate(distribution_pipeline).to_list(length=500)
        detail_results = await db.answers.find(
            {"surveyId": {"$in": survey_ids}, f"payloads.{question_id}": {"$ne": None}},
            {f"payloads.{question_id}": 1},
        ).limit(50).to_list(length=50)

        return {
            "question_id": question_id,
            "type": question_type,
            "title": title,
            "survey_count": survey_count,
            "valid_answers": count,
            "average_value": round(float(avg_val), 2) if count else 0.0,
            "distribution": {str(result["_id"]): result["count"] for result in distribution_results},
            "text_list": [str(item["payloads"][question_id]) for item in detail_results if question_id in item.get("payloads", {})],
        }

    if question_type == "TextQuestion":
        total_answers = await db.answers.count_documents({"surveyId": {"$in": survey_ids}, f"payloads.{question_id}": {"$ne": ""}})
        results = await db.answers.find(
            {"surveyId": {"$in": survey_ids}, f"payloads.{question_id}": {"$ne": ""}},
            {f"payloads.{question_id}": 1},
        ).limit(50).to_list(length=50)
        text_list = [item["payloads"][question_id] for item in results if question_id in item.get("payloads", {})]
        return {
            "question_id": question_id,
            "type": question_type,
            "title": title,
            "survey_count": survey_count,
            "total_answers": total_answers,
            "text_list": text_list,
        }

    raise HTTPException(422, detail={"code": 42201, "message": "该题型暂不支持跨问卷统计"})


async def add_question_to_library(db, user_id: ObjectId, question_id: str) -> dict:
    accessible_doc = await get_question_any_version_for_accessible_user(db, user_id, question_id)
    if not accessible_doc:
        raise HTTPException(404, detail={"code": 40401, "message": "题目不存在"})

    if serialize_library_state(accessible_doc, user_id):
        return accessible_doc

    grant = {"userId": user_id, "addedAt": utc_now()}
    await db.questions.update_many(
        {"questionId": question_id},
        {"$push": {"libraryMembers": grant}, "$set": {"updatedAt": utc_now()}},
    )
    return await db.questions.find_one({"questionId": question_id, **get_question_access_filter(user_id)}, sort=[("version", -1)])


async def remove_question_from_library(db, user_id: ObjectId, question_id: str) -> dict:
    accessible_doc = await get_question_any_version_for_accessible_user(db, user_id, question_id)
    if not accessible_doc:
        raise HTTPException(404, detail={"code": 40401, "message": "题目不存在"})

    await db.questions.update_many(
        {"questionId": question_id},
        {"$pull": {"libraryMembers": {"userId": user_id}}, "$set": {"updatedAt": utc_now()}},
    )
    return await db.questions.find_one({"questionId": question_id, **get_question_access_filter(user_id)}, sort=[("version", -1)])


async def list_library_questions(db, user_id: ObjectId) -> list[dict]:
    cursor = db.questions.find(
        {
            "libraryMembers.userId": user_id,
            **get_question_access_filter(user_id),
        },
        sort=[("questionId", 1), ("version", -1)],
    )
    docs = await cursor.to_list(length=500)
    latest_by_question_id = {}
    for doc in docs:
        latest_by_question_id.setdefault(doc["questionId"], doc)
    return list(latest_by_question_id.values())
