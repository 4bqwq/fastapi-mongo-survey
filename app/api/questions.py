from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_current_user
from app.core.database import get_database
from app.models.question import QuestionCreate, QuestionVersionCreate
from app.models.user import UserInDB
from app.services.question_service import (
    create_question,
    create_question_version,
    serialize_question_doc,
    get_question_version_for_user,
)


router = APIRouter(prefix="/questions", tags=["questions"])


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
    cursor = db.questions.find(
        {"userId": current_user.id, "questionId": question_id},
        sort=[("version", 1)],
    )
    versions = await cursor.to_list(length=100)
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
    question_doc = await get_question_version_for_user(db, current_user.id, question_id, version)
    if not question_doc:
        raise HTTPException(404, detail={"code": 40401, "message": "题目版本不存在"})

    return {
        "code": 200,
        "data": serialize_question_doc(question_doc),
    }
