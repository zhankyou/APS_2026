# app.py
import os
import time
import random
import logging
from dotenv import load_dotenv
from epicollect_api import EpicollectAPI
from database import ConexionBaseDB

# Configuración del logger heredada de tu Principal.py
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | [%(levelname)s] | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("Orquestador_APS_2026")
load_dotenv()

# =============================================================================
# DICCIONARIO CENTRAL DE MÓDULOS (ETL)
# Aquí consolidamos todos los formularios y ramas de Epicollect
# =============================================================================
MODULOS_ETL = [
    # --- CARACTERIZACIÓN ---
    {
        "nombre": "Ficha Familiar (Caracterización)",
        "slug": os.getenv("API_PROJECT_SLUG_2026"),
        "form_ref": os.getenv("API_FORM_REF_2026"),
        "branch_ref": None,
        "tabla": "caracterizacion_si_aps_familiar_2026",
        "pk": "ec5_uuid"
    },
    {
        "nombre": "Ficha Individual (Miembros)",
        "slug": os.getenv("API_PROJECT_SLUG_2026"),
        "form_ref": os.getenv("API_FORM_REF_2026"),
        "branch_ref": os.getenv("API_BRANCH_REF_2026"),
        "tabla": "caracterizacion_si_aps_individual_2026",
        "pk": "ec5_branch_uuid"
    },
    # --- PLAN DE CUIDADO COMUNITARIO (PCC) ---
    {
        "nombre": "PCC Principal",
        "slug": os.getenv("API_PROJECT_SLUG_PCC_2026"),
        "form_ref": os.getenv("API_FORM_REF_PCC_2026"),
        "branch_ref": None,
        "tabla": "pcc_principal_2026",
        "pk": "ec5_uuid"
    },
    {
        "nombre": "PCC Integrantes",
        "slug": os.getenv("API_PROJECT_SLUG_PCC_2026"),
        "form_ref": os.getenv("API_FORM_REF_PCC_2026"),
        "branch_ref": os.getenv("API_BRANCH_REF_PCC_2026"),
        "tabla": "pcc_integrantes_2026",
        "pk": "ec5_branch_uuid"
    },
    # --- PLAN DE CUIDADO FAMILIAR (PCF) ---
    {
        "nombre": "PCF Principal",
        "slug": os.getenv("API_PROJECT_SLUG_PCF_2026"),
        "form_ref": os.getenv("API_FORM_REF_PCF_2026"),
        "branch_ref": None,
        "tabla": "pcf_planes_principal_2026",
        "pk": "ec5_uuid"
    },
    {
        "nombre": "PCF Integrantes",
        "slug": os.getenv("API_PROJECT_SLUG_PCF_2026"),
        "form_ref": os.getenv("API_FORM_REF_PCF_2026"),
        "branch_ref": os.getenv("API_BRANCH_REF_PCF_INTEGRANTES"),
        "tabla": "pcf_planes_integrantes_2026",
        "pk": "ec5_branch_uuid"
    },
    # --- PSICOLOGÍA ---
    {
        "nombre": "Psicología Principal",
        "slug": os.getenv("API_PROJECT_SLUG_PCF_2026"),
        "form_ref": os.getenv("API_FORM_REF_PCF_PSICOLOGIA"),
        "branch_ref": None,
        "tabla": "pcf_psicologia_principal_2026",
        "pk": "ec5_uuid"
    },
    {
        "nombre": "Psicología Seguimientos",
        "slug": os.getenv("API_PROJECT_SLUG_PCF_2026"),
        "form_ref": os.getenv("API_FORM_REF_PCF_PSICOLOGIA"),
        "branch_ref": os.getenv("API_BRANCH_REF_PCF_SEGUIMIENTOS"),
        "tabla": "pcf_psicologia_seguimientos_2026",
        "pk": "ec5_branch_uuid"
    },
    # --- TRÁMITES Y DESISTIMIENTOS ---
    {
        "nombre": "Trámites APS",
        "slug": os.getenv("API_PROJECT_SLUG_TRAMITES_2026"),
        "form_ref": os.getenv("API_FORM_REF_TRAMITES_2026"),
        "branch_ref": None,
        "tabla": "tramites_aps_2026",
        "pk": "ec5_uuid"
    },
    {
        "nombre": "Desistimientos",
        "slug": os.getenv("API_PROJECT_SLUG_DESISTIMIENTO_2026"),
        "form_ref": os.getenv("API_FORM_REF_DESISTIMIENTO_2026"),
        "branch_ref": None,
        "tabla": "desistimiento_aps_2026",
        "pk": "ec5_uuid"
    },
    # --- VACUNACIÓN ---
    {
        "nombre": "Vacunación APS",
        "slug": os.getenv("API_PROJECT_SLUG_VACUNACION_2026"),
        "form_ref": os.getenv("API_FORM_REF_VACUNACION_2026"),
        "branch_ref": None,
        "tabla": "vacunacion_aps_2026",
        "pk": "ec5_uuid",
        "client_id": os.getenv("VACUNACION_2026_CLIENT_ID"),  # Soporte para credenciales múltiples
        "client_secret": os.getenv("VACUNACION_2026_CLIENT_SECRET")
    }
]


def main():
    logger.info("*" * 60)
    logger.info("   INICIANDO ORQUESTADOR DE BASE DE DATOS - APS 2026   ")
    logger.info("*" * 60)

    # Instanciamos el manejador de base de datos
    db = ConexionBaseDB()
    total_scripts = len(MODULOS_ETL)

    for indice, config in enumerate(MODULOS_ETL):
        logger.info(f"\n{'=' * 60}")
        logger.info(f"====== INICIANDO: {config['nombre']} ======")
        logger.info(f"{'=' * 60}\n")

        # 1. Instanciamos la API dinámicamente (Soporta múltiples Client IDs como en Vacunación)
        api = EpicollectAPI(
            client_id=config.get("client_id"),
            client_secret=config.get("client_secret")
        )

        try:
            # 2. Extracción (Formulario o Rama)
            datos_raw = api.extraer_datos(
                project_slug=config["slug"],
                form_ref=config["form_ref"],
                branch_ref=config["branch_ref"]
            )

            # 3. Carga a la Base de Datos
            # Utiliza la llave primaria (pk) para hacer el UPSERT/DELETE
            db.cargar_y_limpiar_tabla(
                nombre_tabla=config["tabla"],
                datos=datos_raw,
                columna_pk=config["pk"]
            )

            logger.info(f"====== ÉXITO: {config['nombre']} ======\n")

        except Exception as e:
            logger.error(f"ERROR CRÍTICO EN {config['nombre']}: {e}\n")

        # 4. Pausa estratégica (Cool-down) - Exactamente como lo tenías en Principal.py
        if indice < total_scripts - 1:
            tiempo_espera = random.uniform(5, 30)
            logger.info(f" ENFRIAMIENTO DE API: Pausando {tiempo_espera:.2f} segundos antes del siguiente módulo...")
            time.sleep(tiempo_espera)

    logger.info("*" * 60)
    logger.info("   TODOS LOS MÓDULOS SINCRONIZADOS CORRECTAMENTE   ")
    logger.info("*" * 60)


if __name__ == "__main__":
    main()