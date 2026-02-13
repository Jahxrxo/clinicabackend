from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse
from supabase_client import supabase
from datetime import datetime

router = APIRouter()

MEDICO_ROLE_ID = "5770e7d5-c449-4094-bbe1-fd52ee6fe75f"

@router.get("/medicos")
async def get_medicos():
    
    try:
        res = supabase.table("usuarios").select(
            "id, nombre, email, telefono, foto_url"
        ).eq("rol_id", MEDICO_ROLE_ID).execute()
        
        if not res.data:
            return JSONResponse({"error": "No se encontraron médicos"}, status_code=404)

        return res.data
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)



@router.get("/citas/medico/{medico_id}")
async def get_citas_medico(medico_id: str):
    try:
        res = supabase.table("citas").select("*").eq("medico_id", medico_id).order("fecha", desc=False).order("hora", desc=False).execute()
        citas = res.data or []

        dias_es = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]

        citas_enriquecidas = []
        for c in citas:

            paciente_res = supabase.table("usuarios").select("nombre").eq("id", c["paciente_id"]).execute()
            paciente_nombre = paciente_res.data[0]["nombre"] if paciente_res.data else "Desconocido"

            sucursal_res = supabase.table("sucursales").select("nombre").eq("id", c["sucursal_id"]).execute()
            sucursal_nombre = sucursal_res.data[0]["nombre"] if sucursal_res.data else "Desconocida"

            fecha_dt = datetime.strptime(c["fecha"], "%Y-%m-%d")
            dia_semana = dias_es[fecha_dt.weekday()]
            fecha_formateada = fecha_dt.strftime("%d/%m/%Y")

            citas_enriquecidas.append({
                "id": c["id"],
                "fecha": c["fecha"],
                "fecha_formateada": fecha_formateada,
                "dia": dia_semana,
                "hora": c["hora"],
                "estado": c["estado"],
                "comentarios": c.get("comentarios", ""),
                "paciente_nombre": paciente_nombre,
                "sucursal": sucursal_nombre
            })

        return citas_enriquecidas

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)



@router.patch("/citas/{cita_id}/completar")
async def completar_cita(cita_id: str):

    try:
        res = supabase.table("citas").update({"estado": "completada"}).eq("id", cita_id).execute()
        if not res.data:
            return JSONResponse({"error": "Cita no encontrada"}, status_code=404)
        return {"message": "Cita completada", "cita": res.data[0]}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)