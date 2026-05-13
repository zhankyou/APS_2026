# -*- coding: utf-8 -*-
"""
Generador de Reportes Excel: Trámites APS 2026
Propósito: Extraer datos directamente desde la base de datos PostgreSQL (evitando
saturar la API de Epicollect), transformar los nombres técnicos leyendo el archivo
mapeos_aps_2026.json y exportar a Excel previniendo columnas duplicadas.
"""

import os
import json
import logging
import re
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Configuración de registro de eventos (Logging)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | [%(levelname)s] | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Carga de variables de entorno (.env)
load_dotenv()


# =============================================================================
# ARQUITECTURA DE CLASES (HERENCIA)
# =============================================================================

class ConexionBaseDB:
    """CLASE PADRE: Encargada exclusivamente de la conexión a PostgreSQL."""

    def __init__(self):
        self.db_user = os.getenv("DB_USER")
        self.db_password = os.getenv("DB_PASSWORD")
        self.db_host = os.getenv("DB_HOST")
        self.db_port = os.getenv("DB_PORT", "5432")
        self.db_name = os.getenv("DB_NAME")

        if not all([self.db_user, self.db_password, self.db_host, self.db_name]):
            logger.error("Faltan credenciales de base de datos en el archivo .env")

        self.engine = self._conectar_base_datos()

    def _conectar_base_datos(self):
        """Establece la conexión segura con SQLAlchemy."""
        cadena = f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        return create_engine(cadena)

    def extraer_tabla(self, nombre_tabla: str) -> pd.DataFrame:
        """Descarga la tabla completa desde PostgreSQL."""
        try:
            logger.info(f"Consultando la tabla '{nombre_tabla}' en PostgreSQL...")
            with self.engine.connect() as con:
                df = pd.read_sql(text(f"SELECT * FROM public.{nombre_tabla};"), con)
                logger.info(f"Se extrajeron {len(df)} registros exitosamente.")
                return df
        except Exception as e:
            logger.error(f"Fallo al extraer la tabla '{nombre_tabla}': {e}")
            return pd.DataFrame()


class GeneradorExcelTramites(ConexionBaseDB):
    """
    CLASE HIJA: Lee el JSON externo, transforma los datos extraídos de la BD
    y previene errores de columnas duplicadas al exportar a Excel.
    """

    def __init__(self):
        super().__init__()  # Inicializa la conexión a PostgreSQL
        self.tabla_objetivo = "tramites_aps_2026"
        self.diccionario_mapeo = self._cargar_diccionario_externo()

    def _cargar_diccionario_externo(self) -> dict:
        """
        Busca y carga el archivo mapeos_aps_2026.json de forma dinámica.
        """
        directorio_actual = os.path.dirname(os.path.abspath(__file__))

        # Opciones de ruta para encontrar la carpeta DICCIONARIO
        rutas_posibles = [
            os.path.join(directorio_actual, "DICCIONARIO", "mapeos_aps_2026.json"),
            os.path.join(os.path.dirname(directorio_actual), "DICCIONARIO", "mapeos_aps_2026.json"),
            os.path.join(directorio_actual, "mapeos_aps_2026.json")
        ]

        for ruta in rutas_posibles:
            if os.path.exists(ruta):
                try:
                    with open(ruta, 'r', encoding='utf-8') as f:
                        data_json = json.load(f)
                        logger.info(f"Diccionario cargado exitosamente desde: {ruta}")
                        # Extraemos estrictamente el bloque de trámites
                        return data_json.get("TRAMITES_EXACTO", {})
                except Exception as e:
                    logger.error(f"Error leyendo el JSON en {ruta}: {e}")

        logger.warning(
            "¡ATENCIÓN! No se encontró el archivo mapeos_aps_2026.json. Se usará el mapeo automático predictivo.")
        return {}

    def _transformar_encabezados(self, df: pd.DataFrame) -> pd.DataFrame:
        """Traduce los nombres de las columnas y evita duplicados para Excel."""
        mapa_metadatos = {
            "ec5_uuid": "ID Ficha Trámite",
            "created_at": "Fecha de Creación (App)",
            "uploaded_at": "Fecha de Sincronización",
            "title": "Título del Registro",
            "created_by": "Usuario Creador"
        }

        nombres_finales = []
        vistos = set()

        for col in df.columns:
            col_normalizada = str(col).strip().lower()
            nuevo_nombre = ""

            # 1. Metadatos del sistema
            if col_normalizada in mapa_metadatos:
                nuevo_nombre = mapa_metadatos[col_normalizada]

            # 2. MAPEO EXACTO 1 a 1 (Desde el JSON externo)
            elif col_normalizada in self.diccionario_mapeo:
                nuevo_nombre = self.diccionario_mapeo[col_normalizada]

            # 3. Plan B predictivo (Si agregaste una columna y olvidaste ponerla en el JSON)
            else:
                nombre_limpio = re.sub(r'^[\d_]+', '', str(col))
                nuevo_nombre = nombre_limpio.replace('_', ' ').title().strip()
                if not nuevo_nombre:
                    nuevo_nombre = "Columna_Sin_Nombre"

            # =========================================================
            # FILTRO DE DESDUPLICACIÓN (Evita el error al guardar en Excel)
            # =========================================================
            if nuevo_nombre in vistos:
                contador = 2
                while f"{nuevo_nombre}_{contador}" in vistos:
                    contador += 1
                nuevo_nombre = f"{nuevo_nombre}_{contador}"

            vistos.add(nuevo_nombre)
            nombres_finales.append(nuevo_nombre)

        # Asignar los nombres limpios y únicos al DataFrame
        df.columns = nombres_finales
        return df

    def ejecutar_proceso(self):
        # 1. Extraer de PostgreSQL
        df_tramites = self.extraer_tabla(self.tabla_objetivo)

        if df_tramites.empty:
            logger.warning(f"No se encontraron datos en la tabla {self.tabla_objetivo}.")
            return

        # 2. Limpiar nombres de columnas
        logger.info("Aplicando mapeo estricto 1 a 1 y filtrando columnas...")
        df_tramites = self._transformar_encabezados(df_tramites)

        # 3. Guardar en Excel
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        ruta_salida = os.path.join(directorio_actual, "Tramites_2026.xlsx")

        logger.info("Escribiendo datos en el archivo Excel...")
        with pd.ExcelWriter(ruta_salida, engine='openpyxl') as escritor:
            df_tramites.to_excel(escritor, sheet_name='Tramites', index=False)

        logger.info(f"Reporte generado exitosamente. Ruta: {ruta_salida}")


def main():
    logger.info("--- INICIO DE EXPORTACIÓN EXCEL TRÁMITES (VÍA POSTGRESQL) ---")
    try:
        motor_excel = GeneradorExcelTramites()
        motor_excel.ejecutar_proceso()
    except Exception as error:
        logger.critical(f"El proceso se detuvo inesperadamente: {error}", exc_info=True)


if __name__ == "__main__":
    main()