from fastapi import APIRouter, Form, Query
from fastapi.responses import JSONResponse

from supabase_client import supabase 
from datetime import datetime, timedelta, time
from typing import List, Dict, Any, Optional

router = APIRouter()

# UUID del rol médico 
MEDICO_ROLE_ID = "5770e7d5-c449-4094-bbe1-fd52ee6fe75f"
DIAS_ES = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]


async def fetch_name_maps(supabase) -> Dict[str, Dict[str, str]]:

    maps = {"sucursales": {}, "usuarios": {}}
    

    try:
        suc_res = supabase.table("sucursales").select("id, nombre").execute()
        maps["sucursales"] = {str(s["id"]): s["nombre"] for s in suc_res.data}
    except Exception as e:
        print(f"Error al cargar sucursales: {e}")


    try:
        user_res = supabase.table("usuarios").select("id, nombre").execute()
        maps["usuarios"] = {str(u["id"]): u["nombre"] for u in user_res.data}
    except Exception as e:
        print(f"Error al cargar usuarios: {e}")
        
    return maps

def _get_disponibilidad_slots(horarios: List[Dict[str, Any]], citas: List[Dict[str, Any]], 
                              dias_a_ver: int, slot_duration_minutes: int) -> List[Dict[str, Any]]:

    disponibilidad: List[Dict[str, Any]] = []
    hoy = datetime.now().date()
    

    resultado_agrupado: Dict[str, Dict[str, List[str]]] = {} 

    for dia_offset in range(dias_a_ver):
        fecha_actual = hoy + timedelta(days=dia_offset)
        fecha_str = fecha_actual.strftime("%Y-%m-%d")
        dia_semana_str = DIAS_ES[fecha_actual.weekday()]


        horarios_dia = [h for h in horarios if h["dia_semana"] == dia_semana_str]
        
        sucursales_con_horario = set(h["sucursal_id"] for h in horarios_dia)

        for sucursal_id in sucursales_con_horario:
            horas_disponibles: List[str] = []
            
            horarios_sucursal = [h for h in horarios_dia if str(h["sucursal_id"]) == str(sucursal_id)]

            for h in horarios_sucursal:
                try:

                    hora_inicio = datetime.strptime(h["hora_inicio"], "%H:%M:%S")
                    hora_fin = datetime.strptime(h["hora_fin"], "%H:%M:%S")
                except ValueError:
                    continue 

                dt_actual = hora_inicio

                while dt_actual < hora_fin:
                    hora_str = dt_actual.strftime("%H:%M")

                    if fecha_actual == hoy and dt_actual.time() < datetime.now().time():
                        dt_actual += timedelta(minutes=slot_duration_minutes)
                        continue


                    ocupada = any(
                        c["fecha"] == fecha_str and
                        c["hora"] == hora_str and
                        c["estado"] == "pendiente" and
                        str(c["sucursal_id"]) == str(sucursal_id)
                        for c in citas
                    )

                    if not ocupada:
                        horas_disponibles.append(hora_str)
                    
                    dt_actual += timedelta(minutes=slot_duration_minutes)
            
            if horas_disponibles:

                key = f"{fecha_str}-{sucursal_id}"
                if key not in resultado_agrupado:
                    resultado_agrupado[key] = {
                        "fecha": fecha_str,
                        "dia_semana": dia_semana_str,
                        "sucursal_id": sucursal_id,
                        "horas_disponibles": []
                    }

                resultado_agrupado[key]["horas_disponibles"].extend(horas_disponibles)
    

    for key, data in resultado_agrupado.items():
        data["horas_disponibles"] = sorted(list(set(data["horas_disponibles"])))
        disponibilidad.append(data)
    
    return disponibilidad



@router.get("/medicos")
async def get_medicos():
    try:

        maps = await fetch_name_maps(supabase)
        sucursales_map = maps["sucursales"]
        

        res = supabase.table("usuarios").select("id,nombre,email,rol_id,sucursal_id").eq("rol_id", MEDICO_ROLE_ID).execute()
        medicos = res.data

        for medico in medicos:
            horarios_res = supabase.table("horarios").select("*").eq("medico_id", medico["id"]).execute()
            medico["horarios"] = horarios_res.data or []
            
            suc_id = str(medico["sucursal_id"])
            medico["sucursal_nombre"] = sucursales_map.get(suc_id, "Desconocida")

        return medicos

    except Exception as e:
        print(f"Error en get_medicos: {e}")
        return JSONResponse({"error": "Error interno del servidor", "detalle": str(e)}, status_code=500)


# Obtener disponibilidad de un médico 
@router.get("/medicos/{medico_id}/disponibilidad")
async def get_disponibilidad(medico_id: str, sucursal_id: Optional[str] = None, fecha: Optional[str] = None):
    try:

        maps = await fetch_name_maps(supabase)
        sucursales_map = maps["sucursales"]

        horarios_q = supabase.table("horarios").select("*").eq("medico_id", medico_id)
        if sucursal_id:
            horarios_q = horarios_q.eq("sucursal_id", sucursal_id)
        horarios = horarios_q.execute().data or []

        if not horarios:
            return JSONResponse({"error": "No hay horarios para este médico (o en esta sucursal)"}, status_code=400)

        citas = supabase.table("citas").select("fecha,hora,estado,sucursal_id").eq("medico_id", medico_id).execute().data or []
        

        dias_a_ver = 14
        if fecha:
            hoy = datetime.now().date()
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
            if fecha_obj < hoy:
                return JSONResponse({"error": "La fecha solicitada es anterior a hoy"}, status_code=400)

            dias_a_ver = (fecha_obj - hoy).days + 1
            if dias_a_ver < 0: dias_a_ver = 0

        disponibilidad_calculada = _get_disponibilidad_slots(
            horarios=horarios, 
            citas=citas, 
            dias_a_ver=dias_a_ver, 
            slot_duration_minutes=60
        )
        

        for slot in disponibilidad_calculada:
            slot["sucursal_nombre"] = sucursales_map.get(str(slot["sucursal_id"]), "Desconocida")

        if fecha:
            disponibilidad_calculada = [d for d in disponibilidad_calculada if d["fecha"] == fecha]
            if not disponibilidad_calculada and dias_a_ver > 0:
                return JSONResponse({"message": f"No hay disponibilidad para el médico en la fecha {fecha}"}, status_code=200)

        return disponibilidad_calculada

    except Exception as e:
        print(f"Error en get_disponibilidad: {e}")
        return JSONResponse({"error": "Error interno del servidor", "detalle": str(e)}, status_code=500)


# Obtener disponibilidad de un médico (Vista Admin - Slots de 1 hora)
@router.get("/admin/medicos/{medico_id}/disponibilidad")
async def admin_disponibilidad(medico_id: str, fecha: Optional[str] = None):
    try:

        maps = await fetch_name_maps(supabase)
        sucursales_map = maps["sucursales"]

        horarios = supabase.table("horarios").select("*").eq("medico_id", medico_id).execute().data or []

        if not horarios:
            return JSONResponse({"error": "No hay horarios para este médico"}, status_code=400)

        citas = supabase.table("citas").select("fecha,hora,estado,sucursal_id").eq("medico_id", medico_id).eq("estado", "pendiente").execute().data or []


        dias_a_ver = 14
        if fecha:
            hoy = datetime.now().date()
            fecha_obj = datetime.strptime(fecha, "%Y-%m-%d").date()
            if fecha_obj < hoy:
                return JSONResponse({"error": "La fecha solicitada es anterior a hoy"}, status_code=400)
            

            dias_a_ver = (fecha_obj - hoy).days + 1
            if dias_a_ver < 0: dias_a_ver = 0


        disponibilidad_calculada = _get_disponibilidad_slots(
            horarios=horarios, 
            citas=citas, 
            dias_a_ver=dias_a_ver, 
            slot_duration_minutes=60
        )
        

        for slot in disponibilidad_calculada:
            slot["sucursal_nombre"] = sucursales_map.get(str(slot["sucursal_id"]), "Desconocida")

        if fecha:
            disponibilidad_calculada = [d for d in disponibilidad_calculada if d["fecha"] == fecha]
            if not disponibilidad_calculada and dias_a_ver > 0:
                return JSONResponse({"message": f"No hay disponibilidad para el médico en la fecha {fecha}"}, status_code=200)

        return disponibilidad_calculada

    except Exception as e:
        print(f"Error en admin_disponibilidad: {e}")
        return JSONResponse({"error": "Error interno del servidor", "detalle": str(e)}, status_code=500)


# Crear cita con validación de disponibilidad real
@router.post("/citas")
async def create_cita(
    paciente_id: str = Form(...),
    medico_id: str = Form(...),
    sucursal_id: str = Form(...),
    fecha: str = Form(...),
    hora: str = Form(...),
    estado: str = Form("pendiente"),
    comentarios: str = Form("")
):
    try:

        now = datetime.now()
        

        if hora.count(':') == 2:
            hora = hora[:-3] 

        try:
            nueva_dt = datetime.strptime(f"{fecha} {hora}", "%Y-%m-%d %H:%M")
        except ValueError:
            return JSONResponse({"error": "Formato de fecha u hora inválido. Use YYYY-MM-DD y HH:MM"}, status_code=400)
            
        if nueva_dt < now:
            return JSONResponse({"error": "No se puede agendar una cita en el pasado"}, status_code=400)

        horarios_res = supabase.table("horarios").select("*").eq("medico_id", medico_id).eq("sucursal_id", sucursal_id).execute()
        horarios = horarios_res.data or []

        if not horarios:
            return JSONResponse({"error": "El médico no tiene horarios en esta sucursal"}, status_code=400)


        citas_res = supabase.table("citas").select("fecha, hora, estado").eq("medico_id", medico_id).eq("sucursal_id", sucursal_id).eq("fecha", fecha).execute()
        citas_pendientes = citas_res.data or []


        disponible = False
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
        dia_semana_str = DIAS_ES[fecha_dt.weekday()]
        hora_dt = datetime.strptime(hora, "%H:%M")

        for h in horarios:
            if h["dia_semana"] != dia_semana_str:
                continue
            
            try:
                hora_inicio = datetime.strptime(h["hora_inicio"], "%H:%M:%S")
                hora_fin = datetime.strptime(h["hora_fin"], "%H:%M:%S")
            except ValueError:
                continue

            if hora_inicio.time() <= hora_dt.time() < hora_fin.time():

                ocupada = any(
                    c["fecha"] == fecha and
                    c["hora"] == hora and
                    c["estado"] == "pendiente"
                    for c in citas_pendientes
                )
                if not ocupada:
                    disponible = True
                    break

        if not disponible:
            return JSONResponse({"error": "El médico no está disponible en la fecha y hora seleccionadas (fuera de horario o ya reservado)"}, status_code=400)


        data = {
            "paciente_id": paciente_id,
            "medico_id": medico_id,
            "sucursal_id": sucursal_id,
            "fecha": fecha,
            "hora": hora,
            "estado": estado,
            "comentarios": comentarios
        }

        insert_res = supabase.table("citas").insert(data).execute()
        if not insert_res.data:
            return JSONResponse({"error": "No se pudo crear la cita"}, status_code=400)

        return JSONResponse({"message": "Cita creada correctamente", "cita": insert_res.data[0]}, status_code=201)

    except Exception as e:
        print(f"Error en create_cita: {e}")
        return JSONResponse({"error": "Error interno del servidor", "detalle": str(e)}, status_code=500)


# Obtener todas las citas futuras de un paciente 
@router.get("/citas/futuras/{paciente_id}")
async def get_citas_futuras(paciente_id: str):
    try:

        maps = await fetch_name_maps(supabase)
        usuarios_map = maps["usuarios"]
        sucursales_map = maps["sucursales"]
        hoy = datetime.now().strftime("%Y-%m-%d")


        res = supabase.table("citas").select("*") \
            .eq("paciente_id", paciente_id) \
            .gte("fecha", hoy) \
            .order("fecha", desc=False) \
            .order("hora", desc=False) \
            .execute()

        citas = res.data or []


        citas_enriquecidas = []
        for cita in citas:
            fecha_dt = datetime.strptime(cita["fecha"], "%Y-%m-%d")
            dia_semana = DIAS_ES[fecha_dt.weekday()]
            
            cita_enrich = {
                "id": cita["id"],
                "fecha": cita["fecha"],
                "fecha_formateada": f"{dia_semana} {fecha_dt.strftime('%d/%m/%Y')}",
                "hora": cita["hora"],
                "estado": cita["estado"],
                "comentarios": cita.get("comentarios", ""),
                "medico": usuarios_map.get(cita["medico_id"], "Desconocido"),
                "sucursal": sucursales_map.get(cita["sucursal_id"], "Desconocida")
            }
            citas_enriquecidas.append(cita_enrich)

        return citas_enriquecidas

    except Exception as e:
        print(f"Error en get_citas_futuras: {e}")
        return JSONResponse({"error": "Error interno del servidor", "detalle": str(e)}, status_code=500)


# Cancelar Cita
@router.patch("/citas/{cita_id}/cancelar")
async def cancelar_cita(cita_id: str):
    try:
        update_res = supabase.table("citas").update({"estado": "cancelada"}).eq("id", cita_id).execute()
        if not update_res.data:
            return JSONResponse({"error": "No se encontró la cita"}, status_code=404)

        return JSONResponse({"message": "Cita cancelada correctamente"}, status_code=200)
    except Exception as e:
        print(f"Error en cancelar_cita: {e}")
        return JSONResponse({"error": "Error interno del servidor", "detalle": str(e)}, status_code=500)
    
# Historial de citas de un paciente 
@router.get("/citas/historial/{paciente_id}")
async def get_historial_citas(paciente_id: str):
    try:

        maps = await fetch_name_maps(supabase)
        usuarios_map = maps["usuarios"]
        sucursales_map = maps["sucursales"]


        res = supabase.table("citas").select("*").eq("paciente_id", paciente_id).order("fecha", desc=True).execute()
        citas = res.data or []


        citas_enriquecidas = []
        for c in citas:
            fecha_dt = datetime.strptime(c["fecha"], "%Y-%m-%d").date()
            
            citas_enriquecidas.append({
                "id": c["id"],
                "fecha": c["fecha"],
                "hora": c["hora"],
                "estado": c["estado"],
                "comentarios": c.get("comentarios", ""),
                "fecha_formateada": fecha_dt.strftime("%d/%m/%Y"),
                "dia": DIAS_ES[fecha_dt.weekday()],
                "medico": usuarios_map.get(c["medico_id"], "Desconocido"),
                "sucursal": sucursales_map.get(c["sucursal_id"], "Desconocido")
            })

        return citas_enriquecidas

    except Exception as e:
        print(f"Error en get_historial_citas: {e}")
        return JSONResponse({"error": "Error interno del servidor", "detalle": str(e)}, status_code=500)

@router.patch("/citas/{cita_id}/reagendar")
async def reagendar_cita(
    cita_id: str,
    fecha: str = Query(..., description="Nueva fecha (YYYY-MM-DD)"),
    hora: str = Query(..., description="Nueva hora (HH:MM)"),
    sucursal_id: str = Query(..., description="ID de la nueva sucursal"),
    medico_id_param: str = Query(None, description="ID del nuevo médico (opcional)")
):
    try:

        cita_res = supabase.table("citas").select("*").eq("id", cita_id).execute()
        if not cita_res.data:
            return JSONResponse({"error": "Cita no encontrada"}, status_code=404)

        cita_original = cita_res.data[0]
        medico_id = medico_id_param or cita_original["medico_id"] 
        paciente_id = cita_original["paciente_id"]
        estado_original = cita_original["estado"]

        if estado_original == "pendiente":
            supabase.table("citas").update({"estado": "cancelada"}).eq("id", cita_id).execute()

        # Crear nueva cita
        nueva_cita = {
            "paciente_id": paciente_id,
            "medico_id": medico_id,
            "sucursal_id": sucursal_id,
            "fecha": fecha,
            "hora": hora,
            "estado": "pendiente",
            "comentarios": "Reagendada desde cita anterior"
        }

        insert_res = supabase.table("citas").insert(nueva_cita).execute()
        if not insert_res.data:
            return JSONResponse({"error": "No se pudo crear la nueva cita"}, status_code=400)

        nueva_cita_creada = insert_res.data[0]

        # Enriquecer la respuesta
        maps = await fetch_name_maps(supabase)
        usuarios_map = maps["usuarios"]
        sucursales_map = maps["sucursales"]

        fecha_dt = datetime.strptime(nueva_cita_creada["fecha"], "%Y-%m-%d")
        dia_semana = DIAS_ES[fecha_dt.weekday()]

        cita_enrich = {
            "id": nueva_cita_creada["id"],
            "fecha": nueva_cita_creada["fecha"],
            "hora": nueva_cita_creada["hora"],
            "estado": nueva_cita_creada["estado"],
            "comentarios": nueva_cita_creada["comentarios"],
            "fecha_formateada": f"{dia_semana} {fecha_dt.strftime('%d/%m/%Y')}",
            "paciente": usuarios_map.get(paciente_id, "Desconocido"),
            "medico": usuarios_map.get(medico_id, "Desconocido"),
            "sucursal": sucursales_map.get(sucursal_id, "Desconocida"),
        }

        return JSONResponse(
            {"message": "Cita reagendada correctamente", "cita": cita_enrich},
            status_code=201
        )

    except Exception as e:
        print(f"Error en reagendar_cita: {e}")
        return JSONResponse({"error": "Error interno del servidor", "detalle": str(e)}, status_code=500)

# Endpoint para que el admin vea las citas del paciente y del medico
@router.get("/citas/todas")
async def get_all_citas():
    try:

        maps = await fetch_name_maps(supabase)
        usuarios_map = maps["usuarios"]
        sucursales_map = maps["sucursales"]

        citas_res = supabase.table("citas").select("*").execute()
        citas = citas_res.data or []

        citas_enriquecidas = []
        for c in citas:
            fecha_dt = datetime.strptime(c["fecha"], "%Y-%m-%d").date()
            dia_semana = DIAS_ES[fecha_dt.weekday()]

            citas_enriquecidas.append({
                "id": c["id"],
                "paciente": usuarios_map.get(c["paciente_id"], "Desconocido"),
                "medico": usuarios_map.get(c["medico_id"], "Desconocido"),
                "sucursal": sucursales_map.get(c["sucursal_id"], "Desconocida"),
                "fecha": c["fecha"],
                "hora": c["hora"],
                "fecha_formateada": f"{dia_semana} {fecha_dt.strftime('%d/%m/%Y')}",
                "estado": c["estado"]
            })

        return citas_enriquecidas
    except Exception as e:
        print(f"Error en get_all_citas: {e}")
        return JSONResponse({"error": "Error interno del servidor", "detalle": str(e)}, status_code=500)
