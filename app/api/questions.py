from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.core.database import get_database
from app.models.question import QuestionCreate, QuestionVersionCreate, QuestionShareCreate
from app.models.user import UserInDB
from app.services.question_service import (
    create_question,
    create_question_version,
    serialize_question_doc,
    get_question_version_for_accessible_user,
    list_accessible_question_versions,
    share_question_with_user,
    list_question_shares,
    serialize_shared_grants,
    get_question_any_version_for_accessible_user,
    list_question_usages,
)


router = APIRouter(prefix="/questions", tags=["questions"])


async def build_users_by_id(db, user_ids: list[ObjectId]) -> dict[ObjectId, dict]:
    if not user_ids:
        return {}
    users = await db.users.find({"_id": {"$in": list(set(user_ids))}}).to_list(length=len(set(user_ids)))
    return {user["_id"]: user for user in users}


@router.post("", response_model=dict)
async def create_question_endpoint(
    question_in: QuestionCreate,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database),
):
    question_doc = await create_question(db, current_user.id, question_in.model_dump(by_alias=True, exclude_none=True))
    return {
        "code": 200,
        "data": {
            "question_id": question_doc["questionId"],
            "version": question_doc["version"],
            "version_id": str(question_doc["_id"]),
            "version_chain_root_id": str(question_doc["versionChainRootId"]),
        },
    }


@router.post("/{question_id}/versions", response_model=dict)
async def create_question_version_endpoint(
    question_id: str,
    version_in: QuestionVersionCreate,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database),
):
    question_doc = await create_question_version(
        db,
        current_user.id,
        question_id,
        version_in.base_version,
        version_in.model_dump(by_alias=True, exclude={"base_version"}, exclude_none=True),
    )
    return {
        "code": 200,
        "data": {
            "question_id": question_doc["questionId"],
            "version": question_doc["version"],
            "version_id": str(question_doc["_id"]),
            "previous_version_id": str(question_doc["previousVersionId"]) if question_doc.get("previousVersionId") else None,
        },
    }


@router.get("/{question_id}", response_model=dict)
async def list_question_versions(
    question_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database),
):
    versions = await list_accessible_question_versions(db, current_user.id, question_id)
    if not versions:
        raise HTTPException(404, detail={"code": 40401, "message": "题目不存在"})

    return {
        "code": 200,
        "data": {
            "question_id": question_id,
            "versions": [
                {
                    "version": version["version"],
                    "version_id": str(version["_id"]),
                    "type": version["type"],
                    "title": version["title"],
                }
                for version in versions
            ],
        },
    }


@router.get("/{question_id}/versions/{version}", response_model=dict)
async def get_question_version_detail(
    question_id: str,
    version: int,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database),
):
    question_doc = await get_question_version_for_accessible_user(db, current_user.id, question_id, version)
    if not question_doc:
        raise HTTPException(404, detail={"code": 40401, "message": "题目版本不存在"})

    return {"code": 200, "data": serialize_question_doc(question_doc)}


@router.post("/{question_id}/shares", response_model=dict)
async def share_question(
    question_id: str,
    share_in: QuestionShareCreate,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database),
):
    target_user = await db.users.find_one({"username": share_in.username, "isDeleted": False})
    if not target_user:
        raise HTTPException(404, detail={"code": 40401, "message": "目标用户不存在"})

    question_docs = await share_question_with_user(db, current_user.id, question_id, target_user)
    users_by_id = await build_users_by_id(db, [grant["userId"] for grant in question_docs[0].get("sharedWith", [])])
    return {
        "code": 200,
        "data": {
            "question_id": question_id,
            "shared_with": serialize_shared_grants(question_docs, users_by_id),
        },
    }


@router.get("/{question_id}/shares", response_model=dict)
async def get_question_shares(
    question_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database),
):
    question_docs = await list_question_shares(db, current_user.id, question_id)
    users_by_id = await build_users_by_id(db, [grant["userId"] for grant in question_docs[0].get("sharedWith", [])])
    return {
        "code": 200,
        "data": {
            "question_id": question_id,
            "shared_with": serialize_shared_grants(question_docs, users_by_id),
        },
    }


@router.get("/{question_id}/usage", response_model=dict)
async def get_question_usage(
    question_id: str,
    current_user: UserInDB = Depends(get_current_user),
    db=Depends(get_database),
):
    accessible_question = await get_question_any_version_for_accessible_user(db, current_user.id, question_id)
    if not accessible_question:
        raise HTTPException(404, detail={"code": 40401, "message": "题目不存在"})

    usages = await list_question_usages(db, question_id)
    users_by_id = await build_users_by_id(db, [usage["survey_owner_id"] for usage in usages])
    return {
        "code": 200,
        "data": {
            "question_id": question_id,
            "usages": [
                {
                    "survey_id": usage["survey_id"],
                    "survey_title": usage["survey_title"],
                    "survey_owner_id": str(usage["survey_owner_id"]),
                    "survey_owner_username": users_by_id.get(usage["survey_owner_id"], {}).get("username"),
                    "status": usage["status"],
                    "question_version": usage["question_version"],
                    "order_index": usage["order_index"],
                }
                for usage in usages
            ],
        },
    }
