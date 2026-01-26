from fastapi import APIRouter
from api.core.logger import APILogger


router = APIRouter()
logger = APILogger()

@router.get("/room_list")
async def get_room_list(user_no: str):
    return {"message": "Hello, World!"}


@router.get("/room_history")
async def get_room_history(user_no: str, room_id: str):
    return {"message": "Hello, World!"}