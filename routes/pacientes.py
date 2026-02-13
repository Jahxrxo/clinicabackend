from fastapi import APIRouter, HTTPException
from supabase_client import supabase  

router = APIRouter()

ROL_PACIENTE_ID = "abc856dd-ba5f-41ae-8dea-27aa29f8ab47"

@router.get("/pacientes")
def obtener_pacientes():
    try:
        response = supabase.table("usuarios").select(
            "nombre, email, telefono, foto_url"
        ).eq("rol_id", ROL_PACIENTE_ID).execute()

        if not response.data:
            raise HTTPException(status_code=404, detail="No se encontraron pacientes")

        return {"pacientes": response.data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
