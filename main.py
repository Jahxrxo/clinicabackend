from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth, usuarios, roles, sucursales, medicos, citas, pacientes

app = FastAPI()

# CORS
origins = ["http://localhost:5173"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
@app.get("/")
def read_root():
    return {"message": "Servidor desplegado"}
# Registrar rutas
app.include_router(auth.router)
app.include_router(usuarios.router)
app.include_router(roles.router)
app.include_router(sucursales.router)
app.include_router(medicos.router)
app.include_router(citas.router)
app.include_router(pacientes.router)
