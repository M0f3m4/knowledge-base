import os
import bcrypt
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

mongo = MongoClient(os.getenv("MONGO_URI"))
db = mongo[os.getenv("DB_NAME")]
usuarios = db["usuarios"]

# Usuarios iniciales
USUARIOS_INICIALES = [
    {"usuario": "JorgeM",  "password": "Morfin2003$", "rol": "admin"},
    {"usuario": "prueba",  "password": "prueba",       "rol": "usuario"},
]

def crear_usuario(usuario, password, rol):
    # Verificar si ya existe
    if usuarios.find_one({"usuario": usuario}):
        print(f"⚠️  Usuario '{usuario}' ya existe — saltando")
        return

    # Hashear contraseña
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    usuarios.insert_one({
        "usuario": usuario,
        "password": hashed,
        "rol": rol,
        "activo": True
    })
    print(f"✅ Usuario '{usuario}' creado con rol '{rol}'")

if __name__ == "__main__":
    print("🔐 Creando usuarios en MongoDB Atlas...")
    print("=" * 40)
    for u in USUARIOS_INICIALES:
        crear_usuario(u["usuario"], u["password"], u["rol"])
    print("=" * 40)
    print("✨ Listo")