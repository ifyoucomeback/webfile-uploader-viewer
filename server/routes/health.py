"""health HTTP 接口。"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/api/health")
async def health():
    return {"success": True}
