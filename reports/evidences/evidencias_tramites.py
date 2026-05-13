# -*- coding: utf-8 -*-
"""
Descargador Automático de Evidencias: Trámites APS 2026
Propósito: Extraer registros de PostgreSQL (usando la conexión centralizada),
escanear nombres de fotos, solicitar la descarga a la API y aplicar un
Control de Tráfico Estricto (2.5s) para evadir el límite de 30 imgs/min.
Finalmente, convierte a PDF y emite un log detallado.
"""

import logging
import os
import re
import sys
import time
from datetime import datetime
import pandas as pd
import requests
from dotenv import load_dotenv
from PIL import Image

# Agregar la ruta raíz al sistema para poder importar nuestra base de datos centralizada
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from database.setup_database import ConexionBaseDB

# --- Configuración del Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s | [%(levelname)s] | %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')
load_dotenv()


class ConfigAPI:
    """Configuración exclusiva para la API de Epicollect"""
    # Usa las credenciales de trámites o hace fallback a las globales
    API_CLIENT_ID = os.getenv("TRAMITES_2026_CLIENT_ID") or os.getenv("CLIENT_ID")
    API_CLIENT_SECRET = os.getenv("TRAMITES_2026_CLIENT_SECRET") or os.getenv("CLIENT_SECRET")
    API_PROJECT_SLUG = os.getenv("API_PROJECT_SLUG_TRAMITES_2026", "formulario-tramites")
    API_BASE_URL = "https://five.epicollect.net/api"


def get_api_token() -> str | None:
    logging.info("Solicitando token de acceso a la API para multimedia...")
    url = f"{ConfigAPI.API_BASE_URL}/oauth/token"
    payload = {
        'grant_type': 'client_credentials',
        'client_id': ConfigAPI.API_CLIENT_ID,
        'client_secret': ConfigAPI.API_CLIENT_SECRET
    }

    for intento in range(3):
        try:
            response = requests.post(url, data=payload, timeout=30)
            if response.status_code == 429:
                logging.warning("Límite de Tokens alcanzado. Esperando 60 segs antes de reintentar...")
                time.sleep(60)
                continue
            response.raise_for_status()
            return response.json().get("access_token")
        except requests.RequestException as e:
            logging.error(f"Fallo en la obtención del token (Intento {intento + 1}/3): {e}")
            time.sleep(5)

    return None


def fetch_data_from_db() -> pd.DataFrame | None:
    logging.info("Extrayendo tabla de trámites desde PostgreSQL (Conexión Central)...")
    db = ConexionBaseDB()
    try:
        query = "SELECT * FROM public.tramites_aps_2026;"
        df = pd.read_sql(query, con=db.engine)
        return df
    except Exception as e:
        logging.error(f"Error al consultar la base de datos: {e}")
        return None


def sanitize_filename(name: str) -> str:
    """Limpia caracteres inválidos para nombres de archivo en Windows."""
    return re.sub(r'[\\/*?:"<>|]', "", str(name)).strip()


def get_doc_abbrev(val: str) -> str:
    """Traduce el tipo de documento del paciente a una sigla corta."""
    v = str(val).lower()
    if "ciudadan" in v: return "CC"
    if "extranjer" in v: return "CE"
    if "identidad" in v: return "TI"
    if "registro" in v: return "RC"
    if "pasaporte" in v: return "PAS"
    if "especial" in v: return "PEP"
    if "protecci" in v: return "PPT"
    if "adulto" in v: return "AS"
    if "menor" in v: return "MS"
    if "nacido" in v: return "CNV"
    if "salvoconducto" in v: return "SC"
    return "DOC"


def get_tramite_real_name(col_name: str) -> str:
    """Mapea el nombre crudo de la BD a un nombre de trámite estético para el archivo PDF."""
    c = str(col_name).lower()
    if "enfermer" in c or "pyp_por_en" in c: return "PYP_Enfermeria"
    elif "medicina" in c or "pyp_por_me" in c: return "PYP_Medicina"
    elif "psicolog" in c or "psicol" in c: return "Psicologia"
    elif "vacunaci" in c or "pai" in c: return "Vacunacion"
    elif "afiliaci" in c or "aseguramiento" in c: return "Afiliacion_Salud"
    elif "demorada" in c or "citas" in c: return "PQR_Citas"
    elif "medicamento" in c or "pendientes" in c: return "PQR_Medicamentos"
    elif "sisben" in c: return "Tramite_SISBEN"
    elif "discapacidad" in c: return "Certif_Discapacidad"
    elif "desescolarizado" in c or "niño" in c or "nio" in c: return "Menor_Desescolarizado"
    elif "colombia_mayor" in c or "colombia" in c: return "Colombia_Mayor"
    elif "iva" in c or "devoluci" in c: return "Devolucion_IVA"
    elif "renta" in c or "ciudadana" in c: return "Renta_Ciudadana"
    elif "ayuda" in c or "banco" in c: return "Banco_Ayudas"
    elif "vida" in c: return "Centros_Vida"
    elif "protecci" in c: return "Proteccion_Social"
    elif "habitante" in c or "calle" in c: return "Habitante_Calle"
    else:
        raw = re.sub(r'^.*requiere_', '', c, flags=re.IGNORECASE)
        raw = re.sub(r'^.*resolutividad_', '', raw, flags=re.IGNORECASE)
        return sanitize_filename(raw.title().replace("_", ""))[:15]


def generar_reporte_txt(ruta_reporte: str, stats: dict):
    """Genera el log en formato de texto."""
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    contenido = f"""================================================================
REPORTE DE DESCARGA DE EVIDENCIAS - TRÁMITES APS 2026
================================================================
Fecha y Hora de Ejecución : {fecha_actual}
================================================================
RESUMEN DE GESTIÓN:
----------------------------------------------------------------
Total de Soportes Identificados en la BD   : {stats['total']}
Soportes Descargados (.JPG) de la API      : {stats['descargados']}
Soportes Convertidos a PDF                 : {stats['convertidos']}
Soportes Omitidos (Ya existían previamente): {stats['ya_existian']}
Soportes con Errores (API/No encontrados)  : {stats['errores']}
================================================================
ESTRUCTURA DE ARCHIVOS GUARDADOS:
[TipoDoc]_[NumeroDoc]_[EPS]_[Tramite]_[S1/Res].pdf
================================================================"""
    try:
        with open(ruta_reporte, "w", encoding="utf-8") as f:
            f.write(contenido)
    except Exception as e:
        logging.error(f"No se pudo generar el reporte TXT: {e}")


def main():
    logging.info("================================================================")
    logging.info("   INICIANDO PROCESO MAESTRO DE EVIDENCIAS (TRÁMITES 2026)      ")
    logging.info("================================================================")

    # --- 1. RUTAS DE SALIDA (Ajustadas a la nueva arquitectura) ---
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    dir_archivos = os.path.join(directorio_actual, "ARCHIVOS")
    dir_imagenes = os.path.join(dir_archivos, "IMAGENES")
    dir_pdf = os.path.join(dir_archivos, "PDF")
    ruta_reporte = os.path.join(dir_archivos, "Reporte_Descargas_Tramites.txt")

    os.makedirs(dir_imagenes, exist_ok=True)
    os.makedirs(dir_pdf, exist_ok=True)

    access_token = get_api_token()
    if not access_token:
        logging.critical("No se pudo obtener el Token de acceso. Abortando script.")
        return

    # Usamos nuestra función adaptada a la BD Central
    df = fetch_data_from_db()
    if df is None or df.empty:
        logging.warning("La tabla de trámites está vacía. No hay evidencias que descargar.")
        return

    # --- 2. IDENTIFICAR COLUMNAS CLAVE DEL PACIENTE ---
    col_tipo_doc, col_doc, col_eps = None, None, None
    for c in df.columns:
        c_clean = str(c).lower().strip()
        if "18_14_tipo" in c_clean or "14_tipo" in c_clean:
            col_tipo_doc = c
        elif "19_15_numero" in c_clean or "15_numero" in c_clean:
            col_doc = c
        elif "26_22_eapb" in c_clean or "22_eapb" in c_clean:
            col_eps = c

    download_jobs = []
    columnas = list(df.columns)

    logging.info("Analizando base de datos para mapear archivos y armar la nomenclatura...")

    for index, fila in df.iterrows():
        # Tipo de Documento
        t_doc = get_doc_abbrev(fila[col_tipo_doc]) if col_tipo_doc and pd.notnull(fila[col_tipo_doc]) else "DOC"

        # Número de Documento
        n_doc_raw = str(fila[col_doc]).strip() if col_doc and pd.notnull(fila[col_doc]) else ""
        n_doc = sanitize_filename(n_doc_raw) if n_doc_raw and n_doc_raw.lower() not in ['nan', 'none'] else "SD"

        # Nombre de la EPS
        raw_eps = str(fila[col_eps]).strip() if col_eps and pd.notnull(fila[col_eps]) else "SINEPS"
        if "No Aplica" in raw_eps or "Sin EAPB" in raw_eps or raw_eps.lower() in ['nan', 'none', '']:
            eps_val = "SINEPS"
        elif '.' in raw_eps:
            eps_val = sanitize_filename(raw_eps.split('.', 1)[-1].strip().replace(" ", ""))[:15]
        else:
            eps_val = sanitize_filename(raw_eps.replace(" ", ""))[:15]

        prefijo_paciente = f"{t_doc}_{n_doc}_{eps_val}"

        # Escaneo Secuencial de Evidencias en Bloques
        for i, col in enumerate(columnas):
            col_lower = str(col).lower()
            val = str(fila.iloc[i]).strip().lower()

            if val in ["si", "1. si", "sí"]:
                is_requiere = "requiere_" in col_lower or "requiere " in col_lower
                is_resolut = "resolutivid" in col_lower

                if is_requiere or is_resolut:
                    tramite_name = get_tramite_real_name(col_lower)
                    foto_idx = 1

                    for j in range(i + 1, len(columnas)):
                        next_col = str(columnas[j]).lower()
                        if "resolutivid" in next_col or "requiere_" in next_col or "requiere " in next_col:
                            break

                        foto_val = str(fila.iloc[j]).strip()

                        if foto_val.lower().endswith(('.jpg', '.jpeg', '.png')):
                            sufijo = f"Res_{foto_idx}" if is_resolut else f"S{foto_idx}"
                            filename_base = f"{prefijo_paciente}_{tramite_name}_{sufijo}"
                            download_jobs.append((foto_val, filename_base))
                            foto_idx += 1

    if not download_jobs:
        logging.info("No se encontraron adjuntos fotográficos en la base de datos.")
        return

    # --- 3. FASE DE DESCARGA SECUENCIAL CON RETARDO (ANTI-429) ---
    stats = {
        "total": len(download_jobs),
        "descargados": 0,
        "convertidos": 0,
        "ya_existian": 0,
        "errores": 0
    }

    logging.info("--- FASE 1: DESCARGA SECUENCIAL ---")
    logging.info(f"Imágenes programadas: {stats['total']}. Pausa de 2.5s activada para cumplir límite (30 req/min)...")

    headers = {"Authorization": f"Bearer {access_token}"}
    session = requests.Session()

    for idx, (img_name, base_name) in enumerate(download_jobs):
        ext = os.path.splitext(img_name)[1]
        img_path = os.path.join(dir_imagenes, f"{base_name}{ext}")
        pdf_path = os.path.join(dir_pdf, f"{base_name}.pdf")

        if os.path.exists(pdf_path):
            stats["ya_existian"] += 1
            continue

        if os.path.exists(img_path):
            continue

        url = f"{ConfigAPI.API_BASE_URL}/export/media/{ConfigAPI.API_PROJECT_SLUG}?type=photo&format=entry_original&name={img_name}"

        exito_descarga = False
        for intento in range(3):
            try:
                response = session.get(url, headers=headers, stream=True, timeout=60)

                if response.status_code == 404:
                    stats["errores"] += 1
                    logging.warning(f"[{idx + 1}/{stats['total']}] (404) Imagen eliminada en API: {img_name}")
                    break

                if response.status_code == 429:
                    logging.warning(f"[{idx + 1}/{stats['total']}] (429) Límite multimedia alcanzado. Pausando 30s...")
                    time.sleep(30)
                    continue

                if response.status_code == 401:
                    logging.error("Token caducado. Abortando.")
                    break

                response.raise_for_status()

                with open(img_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)

                stats["descargados"] += 1
                logging.info(f"[{idx + 1}/{stats['total']}] Descarga Exitosa: {base_name}{ext}")
                exito_descarga = True

                time.sleep(2.5) # Retardo Crítico
                break

            except requests.exceptions.RequestException as e:
                logging.error(f"[{idx + 1}/{stats['total']}] Fallo de red intentando descargar {img_name}: {e}")
                time.sleep(5)

        if not exito_descarga and response and response.status_code != 404:
            stats["errores"] += 1

    # --- 4. FASE DE CONVERSIÓN MASIVA A PDF ---
    logging.info("--- FASE 2: CONVERSIÓN DE JPG A PDF ---")

    for idx, (img_name, base_name) in enumerate(download_jobs):
        ext = os.path.splitext(img_name)[1]
        img_path = os.path.join(dir_imagenes, f"{base_name}{ext}")
        pdf_path = os.path.join(dir_pdf, f"{base_name}.pdf")

        if os.path.exists(pdf_path):
            continue

        if os.path.exists(img_path):
            try:
                with Image.open(img_path) as img:
                    img.convert('RGB').save(pdf_path)
                stats["convertidos"] += 1
                logging.info(f"Convertido a PDF: {base_name}.pdf")
            except Exception as e:
                logging.error(f"Error convirtiendo a PDF ({base_name}): {e}")

    # --- 5. REPORTE FINAL ---
    generar_reporte_txt(ruta_reporte, stats)

    logging.info("================================================================")
    logging.info("          PROCESO COMPLETADO EXITOSAMENTE                       ")
    logging.info(f"          Log guardado en: {ruta_reporte}                      ")
    logging.info("================================================================")


if __name__ == "__main__":
    main()