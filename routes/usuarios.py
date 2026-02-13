from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Optional
from supabase_client import supabase
import uuid
from passlib.context import CryptContext

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password[:72])


@router.post("/")
async def crear_usuario(
    nombre: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    rol_id: str = Form(...),
    sucursal_id: str = Form(...),
    telefono: str = Form(""),
    foto: Optional[UploadFile] = File(None)
):
    foto_url = None
    try:
        if foto:
            file_data = await foto.read()
            unique_filename = f"{uuid.uuid4()}_{foto.filename}"
            supabase.storage.from_("usuarios").upload(unique_filename, file_data)
            foto_url = supabase.storage.from_("usuarios").get_public_url(unique_filename)

        hashed_password = hash_password(password)
        data = {
            "nombre": nombre,
            "email": email,
            "password": hashed_password,
            "rol_id": rol_id,
            "sucursal_id": sucursal_id,
            "telefono": telefono,
            "foto_url": foto_url
        }

        res = supabase.table("usuarios").insert(data).execute()
        if not res.data:
            return JSONResponse({"error": "No se pudo crear el usuario"}, status_code=400)

        user_data = {k: v for k, v in res.data[0].items() if k != "password"}
        return {"message": "Usuario creado correctamente", "user": user_data}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
