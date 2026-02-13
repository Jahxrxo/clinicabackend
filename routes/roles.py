from fastapi import APIRouter
from supabase_client import supabase

router = APIRouter(prefix="/roles", tags=["Roles"])

@router.get("/")
async def get_roles():
    res = supabase.table("roles").select("*").execute()
    return res.data
