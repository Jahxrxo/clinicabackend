from fastapi import APIRouter
from fastapi.responses import JSONResponse
from supabase_client import supabase

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("/")
async def get_roles():
    """Lista todos los roles disponibles."""
    try:
        res = supabase.table("roles").select("*").execute()
        return res.data or []
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/usuarios")
async def get_usuarios_con_rol():
    """Lista todos los usuarios con su rol actual."""
    try:
        res = supabase.table("usuarios").select(
            "id, nombre, email, rol_id, roles(id, nombre)"
        ).execute()
        return res.data or []
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/usuarios/{usuario_id}")
async def cambiar_rol_usuario(usuario_id: str, body: dict):
    """
    Asigna un nuevo rol a un usuario directamente.
    Body: { "rol_id": "<uuid>" }
    """
    try:
        rol_id = body.get("rol_id")
        if not rol_id:
            return JSONResponse({"error": "rol_id es requerido"}, status_code=422)

        # Verificar que el rol existe
        rol_res = supabase.table("roles").select("id, nombre").eq("id", rol_id).execute()
        if not rol_res.data:
            return JSONResponse({"error": "El rol especificado no existe"}, status_code=404)

        # Actualizar el rol del usuario
        res = supabase.table("usuarios").update({"rol_id": rol_id}).eq("id", usuario_id).execute()
        if not res.data:
            return JSONResponse({"error": "Usuario no encontrado o no se pudo actualizar"}, status_code=404)

        usuario = {k: v for k, v in res.data[0].items() if k != "password"}
        return {
            "message": "Rol actualizado correctamente",
            "usuario": usuario,
            "nuevo_rol": rol_res.data[0]
        }

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
