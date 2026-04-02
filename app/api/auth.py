from fastapi import APIRouter, HTTPException, Depends, status
from app.models.user import UserCreate, UserOut, UserInDB
from app.services.auth import get_password_hash, verify_password, create_access_token
from app.core.database import get_database
from datetime import datetime
from bson import ObjectId

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=dict)
async def register(user_in: UserCreate, db=Depends(get_database)):
    # Check if user already exists
    existing_user = await db.users.find_one({"username": user_in.username})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": 40001, "message": "用户名已存在"}
        )
    
    # Hash password and create user
    user_dict = user_in.model_dump(by_alias=True)
    password = user_dict.pop("password")
    user_dict["passwordHash"] = get_password_hash(password)
    user_dict["createdAt"] = datetime.utcnow()
    user_dict["updatedAt"] = datetime.utcnow()
    user_dict["isDeleted"] = False

    result = await db.users.insert_one(user_dict)
    
    return {
        "code": 200,
        "message": "success",
        "data": {
            "user_id": str(result.inserted_id),
            "username": user_in.username,
            "created_at": user_dict["createdAt"].isoformat() + "Z"
        }
    }

@router.post("/login", response_model=dict)
async def login(user_in: UserCreate, db=Depends(get_database)):
    user = await db.users.find_one({"username": user_in.username, "isDeleted": False})
    if not user or not verify_password(user_in.password, user["passwordHash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 40101, "message": "用户名或密码错误"}
        )
    
    access_token = create_access_token(data={"sub": str(user["_id"])})
    return {
        "code": 200,
        "message": "success",
        "data": {
            "access_token": access_token,
            "token_type": "Bearer"
        }
    }
