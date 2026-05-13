# install.py
import os
import sys
import subprocess


def crear_estructura():
    """Crea las carpetas necesarias para la arquitectura del proyecto."""
    carpetas = [
        "app",
        "database",
        "reports/excel",
        "reports/modules",
        "reports/evidences/ARCHIVOS/IMAGENES",
        "reports/evidences/ARCHIVOS/PDF",
        "DICCIONARIO"
    ]

    print("📁 Creando estructura de directorios...")
    for carpeta in carpetas:
        os.makedirs(carpeta, exist_ok=True)
        print(f"  ✔ Carpeta lista: {carpeta}")


def crear_env_plantilla():
    """Genera un archivo .env de ejemplo con todas las variables requeridas."""
    if not os.path.exists(".env"):
        print("\n⚙️ Creando archivo de configuración (.env)...")
        with open(".env", "w", encoding="utf-8") as f:
            f.write("# ==========================================\n")
            f.write("# CONFIGURACIÓN DE BASE DE DATOS (POSTGRESQL)\n")
            f.write("# ==========================================\n")
            f.write("DB_USER=postgres\n")
            f.write("DB_PASSWORD=tu_contraseña\n")
            f.write("DB_HOST=localhost\n")
            f.write("DB_PORT=5432\n")
            f.write("DB_NAME=aps_2026\n\n")
            f.write("# ==========================================\n")
            f.write("# CREDENCIALES GLOBALES DE EPICOLLECT5\n")
            f.write("# ==========================================\n")
            f.write("CLIENT_ID=tu_client_id_global\n")
            f.write("CLIENT_SECRET=tu_client_secret_global\n\n")
            f.write("# ==========================================\n")
            f.write("# CREDENCIALES ESPECÍFICAS (Opcional, si difieren)\n")
            f.write("# ==========================================\n")
            f.write("TRAMITES_2026_CLIENT_ID=\n")
            f.write("TRAMITES_2026_CLIENT_SECRET=\n")
            f.write("API_PROJECT_SLUG_TRAMITES_2026=formulario-tramites\n\n")
            f.write("# ==========================================\n")
            f.write("# CONFIGURACIÓN DE CORREO (Reportes)\n")
            f.write("# ==========================================\n")
            f.write("GMAIL_SENDER=tu_correo@gmail.com\n")
            f.write("GMAIL_APP_PASSWORD=tu_contraseña_de_aplicacion\n")
        print("  ✔ Archivo .env creado. ¡RECUERDA CONFIGURAR TUS CREDENCIALES!")
    else:
        print("\n⚙️ El archivo .env ya existe. Omitiendo...")


def crear_requirements():
    """Crea el archivo requirements.txt."""
    if not os.path.exists("requirements.txt"):
        print("\n📦 Creando requirements.txt...")
        with open("requirements.txt", "w", encoding="utf-8") as f:
            f.write("pandas\n")
            f.write("requests\n")
            f.write("sqlalchemy\n")
            f.write("psycopg2-binary\n")
            f.write("python-dotenv\n")
            f.write("openpyxl\n")
            f.write("Pillow\n")
        print("  ✔ requirements.txt listo.")


def instalar_dependencias():
    print("\n Instalando dependencias de Python...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print(" Dependencias instaladas correctamente.")
    except Exception as e:
        print(f" Hubo un error instalando las dependencias: {e}")


if __name__ == "__main__":
    print("==================================================")
    print("  INSTALADOR AUTOMÁTICO: SISTEMA APS 2026 (OPEN SOURCE)")
    print("==================================================")
    crear_estructura()
    crear_env_plantilla()
    crear_requirements()
    instalar_dependencias()
    print("==================================================")
    print("✅ INSTALACIÓN FINALIZADA.")
    print("Por favor, abre el archivo '.env' e ingresa tus contraseñas y API Keys.")
    print("Luego ejecuta el sistema con: python app/main.py")
    print("==================================================")