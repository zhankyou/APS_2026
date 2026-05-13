# -*- coding: utf-8 -*-
"""
Generador de Reportes Excel: Desistimiento APS 2026
Proposito: Extraer datos directamente desde PostgreSQL y transformar los nombres tecnicos
utilizando "Mapeo Inteligente por Subcadenas" para generar un reporte limpio
y amigable para el usuario final.
"""

import os
import logging
import re
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from dotenv import load_dotenv

# Configuracion de registro de eventos (Logging)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | [%(levelname)s] | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Carga de variables de entorno (.env)
load_dotenv()

# =============================================================================
# DICCIONARIO DE MAPEO INTELIGENTE (SUBCADENAS)
# =============================================================================
MAPEO_DESISTIMIENTO_INTELIGENTE = {
    # Coordenadas (Usamos los prefijos fijos)
    "lat_": "2. Geolocalizacion (Latitud)",
    "long_": "2. Geolocalizacion (Longitud)",
    "accuracy_": "2. Geolocalizacion (Precision)",
    "utm_northing": "2. Geolocalizacion (UTM Northing)",
    "utm_easting": "2. Geolocalizacion (UTM Easting)",
    "utm_zone": "2. Geolocalizacion (UTM Zone)",

    # Identificadores exactos para evitar colisiones entre el 3 y el 4
    "3_3_cdigo_hogar": "3. Codigo Hogar",
    "3_cdigo_hogar": "3. Codigo Hogar",
    "4_4_cdigo_hogar": "4. Codigo Hogar",
    "4_cdigo_hogar": "4. Codigo Hogar",
    "5_5_cdigo_familia": "5. Codigo Familia",
    "5_cdigo_familia": "5. Codigo Familia",
    "6_6_cdigo_familia": "6. Codigo Familia",
    "6_cdigo_familia": "6. Codigo Familia",

    # Fragmentos unicos para el resto de preguntas
    "fecha_visita": "1. Fecha Visita",
    "territorio": "7. Territorio",
    "microterritorio": "8. Microterritorio",
    "perfil_profesio": "9. Perfil Profesional",
    "nombre_profesi": "10. Nombre Profesional o Tecnico",
    "tipo_de_docume": "11. Tipo de Documento",
    "numero_de_docu": "12. Numero de Documento del Profesional o Tecnico",
    "qu_tipo_de_ser": "13. ¿Que tipo de servicio o intervencion rechaza el usuario?",
    "atencin_de_qu": "13.1. ¿Atencion de que profesional rechaza la visita?",
    "motivo_princip": "14. Motivo principal del desistimiento",
    "mencione_otro": "14.1. Mencione Otro Motivo",
    "observaciones": "15. Observaciones adicionales"
}


# =============================================================================
# ARQUITECTURA DE CLASES
# =============================================================================

class BaseConexionBD:
    """CLASE PADRE: Administra la conexion al motor de base de datos PostgreSQL."""

    def __init__(self):
        self.db_user = os.getenv("DB_USER")
        self.db_password = os.getenv("DB_PASSWORD")
        self.db_host = os.getenv("DB_HOST")
        self.db_port = os.getenv("DB_PORT")
        self.db_name = os.getenv("DB_NAME")

        self.engine = self._conectar_base_datos()

    def _conectar_base_datos(self) -> Engine:
        """Establece la conexion con PostgreSQL usando SQLAlchemy."""
        logger.info("Conectando con la base de datos PostgreSQL...")
        cadena_conexion = f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        return create_engine(cadena_conexion)

    def extraer_tabla(self, nombre_tabla: str) -> pd.DataFrame:
        """Extrae de forma masiva los registros de la tabla indicada."""
        logger.info(f"Consultando registros de la tabla: {nombre_tabla}...")
        try:
            with self.engine.connect() as conexion:
                query = f"SELECT * FROM public.{nombre_tabla}"
                df = pd.read_sql(query, conexion)
                return df
        except Exception as e:
            logger.error(f"Error al leer la tabla '{nombre_tabla}'. Verifica su existencia. Error: {e}")
            return pd.DataFrame()


class GeneradorExcelDesistimientoBD(BaseConexionBD):
    """
    CLASE HIJA: Transforma los encabezados en bruto de la base de datos
    mediante mapeo por subcadenas y exporta los datos a Excel.
    """

    def __init__(self):
        super().__init__()
        # Tabla destino alimentada por nuestro pipeline ETL
        self.tabla_destino = "desistimiento_aps_2026"

    def _transformar_encabezados(self, df: pd.DataFrame, diccionario_mapeo: dict) -> pd.DataFrame:
        """
        Aplica el algoritmo de busqueda por subcadenas para limpiar los nombres
        de las columnas provenientes de la BD.
        """
        mapa_metadatos = {
            "ec5_uuid": "ID Ficha Desistimiento",
            "created_at": "Fecha de Creacion (App)",
            "uploaded_at": "Fecha de Sincronizacion",
            "title": "Titulo del Registro",
            "created_by": "Usuario Creador"
        }

        encabezados_procesados = {}

        for col in df.columns:
            # Normalizacion en memoria asegurando snake_case comparativo
            col_normalizada = str(col).strip().replace(" ", "_").replace("-", "_").lower()

            # 1. Asignar metadatos del sistema (Coincidencia exacta)
            if col_normalizada in mapa_metadatos:
                encabezados_procesados[col] = mapa_metadatos[col_normalizada]
                continue

            # 2. Mapeo Inteligente (Busqueda por subcadena)
            mapeado = False
            for llave_fragmento, nombre_oficial_json in diccionario_mapeo.items():
                if llave_fragmento in col_normalizada:
                    encabezados_procesados[col] = nombre_oficial_json
                    mapeado = True
                    break  # Detiene la busqueda al encontrar la primera coincidencia

            if mapeado:
                continue

            # 3. Plan B predictivo para columnas huérfanas o nuevas
            nombre_limpio = re.sub(r'^[\d_]+', '', str(col))
            nombre_limpio = nombre_limpio.replace('_', ' ').title().strip()
            encabezados_procesados[col] = nombre_limpio

        return df.rename(columns=encabezados_procesados)

    def ejecutar_proceso(self):
        logger.info("Iniciando extraccion de datos: Formulario Desistimiento")
        df_principal = self.extraer_tabla(self.tabla_destino)

        if df_principal.empty:
            logger.warning("No se detectaron datos en la base de datos para generar el reporte.")
            return

        logger.info("Aplicando mapeo inteligente de columnas (Basado en subcadenas)...")
        df_principal = self._transformar_encabezados(df_principal, MAPEO_DESISTIMIENTO_INTELIGENTE)

        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        ruta_salida = os.path.join(directorio_actual, "Desistimiento_2026.xlsx")

        # Eliminamos el archivo previo de forma segura si existe
        if os.path.exists(ruta_salida):
            try:
                os.remove(ruta_salida)
            except Exception as e:
                logger.warning(f"No se pudo reemplazar el archivo previo. ¿Esta abierto en Excel? Error: {e}")

        logger.info("Escribiendo datos en el archivo Excel...")
        with pd.ExcelWriter(ruta_salida, engine='openpyxl') as escritor:
            df_principal.to_excel(escritor, sheet_name='Desistimientos', index=False)

        logger.info(f"Reporte generado exitosamente. Ruta: {ruta_salida}")


def main():
    logger.info("--- INICIO DE EXPORTACION EXCEL DESISTIMIENTO 2026 DESDE BD ---")
    try:
        motor_excel = GeneradorExcelDesistimientoBD()
        motor_excel.ejecutar_proceso()
    except Exception as error:
        logger.critical(f"El proceso se detuvo inesperadamente: {error}", exc_info=True)


if __name__ == "__main__":
    main()