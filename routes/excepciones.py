from fastapi import APIRouter, Form
from fastapi.responses import JSONResponse
from supabase_client import supabase
from datetime import datetime, date
from typing import Optional

router = APIRouter(prefix="/medicos", tags=["Excepciones de Disponibilidad"])


def _parse_date(fecha_str: str, campo: str):
    try:
        return datetime.strptime(fecha_str, "%Y-%m-%d").date()
    except ValueError:
        return None



# GET  /medicos/{medico_id}/excepciones
# Lista todas las excepciones de un médico
# 
@router.get("/{medico_id}/excepciones")
async def get_excepciones(medico_id: str):
    try:
        res = (
            supabase.table("disponibilidad_excepciones")
            .select("*")
            .eq("medico_id", medico_id)
            .order("fecha_inicio", desc=False)
            .execute()
        )
        return res.data or []
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)



# POST  /medicos/{medico_id}/excepciones
# Crea un rango de no disponibilidad

@router.post("/{medico_id}/excepciones")
async def crear_excepcion(
    medico_id: str,
    fecha_inicio: str = Form(..., description="YYYY-MM-DD"),
    fecha_fin: str = Form(..., description="YYYY-MM-DD"),
    motivo: Optional[str] = Form(""),
):
    try:
        fi = _parse_date(fecha_inicio, "fecha_inicio")
        ff = _parse_date(fecha_fin, "fecha_fin")

        if fi is None or ff is None:
            return JSONResponse(
                {"error": "Formato de fecha inválido. Use YYYY-MM-DD"},
                status_code=400,
            )

        if ff < fi:
            return JSONResponse(
                {"error": "fecha_fin no puede ser anterior a fecha_inicio"},
                status_code=400,
            )

        if ff < date.today():
            return JSONResponse(
                {"error": "El rango de fechas ya está en el pasado"},
                status_code=400,
            )

        # Verificar que el médico exista
        medico_res = supabase.table("usuarios").select("id").eq("id", medico_id).execute()
        if not medico_res.data:
            return JSONResponse({"error": "Médico no encontrado"}, status_code=404)

        # Detectar solapamiento con excepciones existentes
        overlap_res = (
            supabase.table("disponibilidad_excepciones")
            .select("id, fecha_inicio, fecha_fin, motivo")
            .eq("medico_id", medico_id)
            .lte("fecha_inicio", fecha_fin)   # existente.inicio <= nueva.fin
            .gte("fecha_fin",   fecha_inicio)  # existente.fin   >= nueva.inicio
            .execute()
        )
        if overlap_res.data:
            conflictos = [
                f"{e['fecha_inicio']} → {e['fecha_fin']}" for e in overlap_res.data
            ]
            return JSONResponse(
                {
                    "error": "Ya existe una excepción que se solapa con ese rango",
                    "conflictos": conflictos,
                },
                status_code=409,
            )

        data = {
            "medico_id": medico_id,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "motivo": motivo or "",
        }
        insert_res = supabase.table("disponibilidad_excepciones").insert(data).execute()

        if not insert_res.data:
            return JSONResponse(
                {"error": "No se pudo crear la excepción"}, status_code=400
            )

        return JSONResponse(
            {
                "message": "Excepción de disponibilidad creada correctamente",
                "excepcion": insert_res.data[0],
            },
            status_code=201,
        )

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)



# DELETE  /medicos/excepciones/{excepcion_id}
# Elimina una excepción específica

@router.delete("/excepciones/{excepcion_id}")
async def eliminar_excepcion(excepcion_id: str):
    try:
        res = (
            supabase.table("disponibilidad_excepciones")
            .delete()
            .eq("id", excepcion_id)
            .execute()
        )
        if not res.data:
            return JSONResponse({"error": "Excepción no encontrada"}, status_code=404)

        return JSONResponse(
            {"message": "Excepción eliminada correctamente"}, status_code=200
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)