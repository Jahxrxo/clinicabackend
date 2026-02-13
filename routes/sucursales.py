from fastapi import APIRouter
from supabase_client import supabase

router = APIRouter(prefix="/sucursales", tags=["Sucursales"])

@router.get("/")
async def get_sucursales():
    res = supabase.table("sucursales").select("*").execute()
    return res.data
