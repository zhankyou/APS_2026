# -*- coding: utf-8 -*-
"""
Generador de Reportes Excel: Plan de Cuidado Comunitario (PCC) 2026
Proposito: Extraer datos directamente desde PostgreSQL y transformar los nombres tecnicos
de la BD a los titulos exactos de las preguntas definidos en el formulario para generar
un Excel multi-hoja consolidado.
"""

import os
import logging
import re
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from dotenv import load_dotenv

# Configuracion de registro de eventos (Logging) en consola
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | [%(levelname)s] | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Carga de variables de entorno
load_dotenv()

# =============================================================================
# MAPEO ESTRICTO DE COLUMNAS (BD -> NOMBRES OFICIALES)
# =============================================================================
MAPEO_PCC_PRINCIPAL = {
    "lat_1_1_geolocalizacin": "1. Geolocalizacion (Latitud)",
    "long_1_1_geolocalizacin": "1. Geolocalizacion (Longitud)",
    "accuracy_1_1_geolocalizacin": "1. Geolocalizacion (Precision)",
    "utm_northing_1_1_geolocalizacin": "1. Geolocalizacion (UTM Northing)",
    "utm_easting_1_1_geolocalizacin": "1. Geolocalizacion (UTM Easting)",
    "utm_zone_1_1_geolocalizacin": "1. Geolocalizacion (UTM Zone)",
    "2_2_fecha_visita": "2. Fecha Visita",
    "3_3_perfil_profesion": "3. Perfil Profesional o Tecnico",
    "4_4_nombre_del_profe": "4. Nombre del Profesional o Tecnico",
    "5_5_tipo_de_document": "5. Tipo de Documento del Profesional o Tecnico",
    "6_6_numero_de_docume": "6. Numero de Documento del Profesional o Tecnico",
    "8_7_curso_de_vida_y_": "7. Curso de Vida y Promocion de la Salud",
    "9_71_especificar_otr": "7.1. Especificar Otro",
    "10_8_prevencin_espec": "8. Prevencion Especifica y Deteccion Temprana",
    "11_81_especificar_ot": "8.1. Especificar Otro",
    "12_9_salud_mental_y_": "9. Salud Mental y Convivencia",
    "13_91_especificar_ot": "9.1. Especificar Otro",
    "14_10_entorno_saluda": "10. Entorno Saludable",
    "15_101_especificar_o": "10.1. Especificar Otro",
    "16_11_acceso_a_servi": "11. Acceso a servicios y rutas",
    "17_111_especificar_o": "11.1 Especificar Otro",
    "18_12_se_entregaron_": "12. ¿Se entregaron materiales educativos?",
    "19_13_se_identificar": "13. ¿Se identificaron lideres o voceros interesados en replicar el mensaje?",
    "20_14_detalles_jorna": "14. Detalles Jornada Comunitaria",
    "21_integrantes_inter": "Cantidad Integrantes Intervenidos",
    "28_20_descripcin_det": "20. Descripcion Detallada de la Intervencion Realizada"
}

# Diccionario para el subformulario de miembros de la comunidad
MAPEO_PCC_INTEGRANTES = {
    "23_15_nombre_complet": "15. Nombre Completo",
    "24_16_tipo_de_docume": "16. Tipo de Documento",
    "25_17_numero_de_docu": "17. Numero de Documento",
    "26_18_fecha_de_nacim": "18. Fecha de Nacimiento",
    "27_19_sexo": "19. Sexo",
    # Mapeos de respaldo
    "15_nombre_complet": "15. Nombre Completo",
    "16_tipo_de_docume": "16. Tipo de Documento",
    "17_numero_de_docu": "17. Numero de Documento",
    "18_fecha_de_nacim": "18. Fecha de Nacimiento",
    "19_sexo": "19. Sexo"
}


# =============================================================================
# ARQUITECTURA DE CLASES
# =============================================================================

class BaseConexionBD:
    """CLASE PADRE: Encargada de la conexion estable con PostgreSQL."""

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
        """Ejecuta un volcado completo de la tabla hacia un DataFrame."""
        logger.info(f"Consultando registros de la tabla: {nombre_tabla}...")
        try:
            with self.engine.connect() as conexion:
                query = f"SELECT * FROM public.{nombre_tabla}"
                df = pd.read_sql(query, conexion)
                return df
        except Exception as e:
            logger.error(f"Error al leer la tabla '{nombre_tabla}'. Verifica su existencia. Error: {e}")
            return pd.DataFrame()


class GeneradorExcelPCCBD(BaseConexionBD):
    """
    CLASE HIJA:
    Toma los datos extraidos desde la BD, cruza los encabezados con los
    diccionarios estandarizados y exporta el archivo Excel final.
    """

    def __init__(self):
        super().__init__()
        # Tablas destino creadas por el Pipeline ETL de PCC
        self.tabla_principal = "pcc_principal_2026"
        self.tabla_integrantes = "pcc_integrantes_2026"

    def _transformar_encabezados(self, df: pd.DataFrame, diccionario_mapeo: dict) -> pd.DataFrame:
        """
        Normaliza los nombres de la BD (snake_case) y los cruza
        con los diccionarios predefinidos para asignar el nombre oficial.
        """
        mapa_metadatos = {
            "ec5_uuid": "ID Ficha PCC",
            "ec5_branch_uuid": "ID Integrante",
            "ec5_parent_uuid": "ID Ficha Relacionada",
            "ec5_branch_owner_uuid": "ID Ficha Relacionada",
            "created_at": "Fecha de Creacion en Sistema",
            "uploaded_at": "Fecha de Sincronizacion",
            "title": "Titulo del Registro",
            "created_by": "Usuario Creador"
        }

        encabezados_procesados = {}

        for col in df.columns:
            # 1. Aseguramos que la comparativa este en minusculas y limpia
            col_normalizada = str(col).strip().replace(" ", "_").replace("-", "_").lower()

            # 2. Asignar metadatos del sistema
            if col_normalizada in mapa_metadatos:
                encabezados_procesados[col] = mapa_metadatos[col_normalizada]
                continue

            # 3. Asignar traduccion estricta de nuestro diccionario
            if col_normalizada in diccionario_mapeo:
                encabezados_procesados[col] = diccionario_mapeo[col_normalizada]
                continue

            # 4. PLAN B (Fallback predictivo): Si se añadieron columnas no documentadas
            nombre_limpio = re.sub(r'^[\d_]+', '', str(col))
            nombre_limpio = nombre_limpio.replace('_', ' ')
            nombre_limpio = nombre_limpio.title().strip()

            encabezados_procesados[col] = nombre_limpio

        # Retorna el DataFrame aplicando el renombramiento
        return df.rename(columns=encabezados_procesados)

    def ejecutar_proceso(self):
        """Orquesta las funciones de descarga, transformacion y exportacion."""
        logger.info("Iniciando extraccion de datos: Formulario Principal (PCC)")
        df_principal = self.extraer_tabla(self.tabla_principal)

        logger.info("Iniciando extraccion de datos: Subformulario (Integrantes)")
        df_integrantes = self.extraer_tabla(self.tabla_integrantes)

        if df_principal.empty and df_integrantes.empty:
            logger.warning("No se detectaron datos en la base de datos para generar el reporte.")
            return

        logger.info("Aplicando mapeo estricto de columnas desde el diccionario...")
        if not df_principal.empty:
            df_principal = self._transformar_encabezados(df_principal, MAPEO_PCC_PRINCIPAL)
        if not df_integrantes.empty:
            df_integrantes = self._transformar_encabezados(df_integrantes, MAPEO_PCC_INTEGRANTES)

        # Ubica la carpeta raiz donde se esta ejecutando este script
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        ruta_salida = os.path.join(directorio_actual, "PCC_2026.xlsx")

        # Eliminamos el archivo viejo de forma segura si existe (evita errores de I/O)
        if os.path.exists(ruta_salida):
            try:
                os.remove(ruta_salida)
            except Exception as e:
                logger.warning(f"No se pudo reemplazar el archivo previo (¿Abierto en Excel?). Error: {e}")

        logger.info("Escribiendo datos consolidados en el archivo Excel multi-hoja...")

        with pd.ExcelWriter(ruta_salida, engine='openpyxl') as escritor:
            if not df_principal.empty:
                df_principal.to_excel(escritor, sheet_name='PCC', index=False)
            if not df_integrantes.empty:
                df_integrantes.to_excel(escritor, sheet_name='Integrantes PCC', index=False)

        logger.info(f"Reporte generado exitosamente. Ruta: {ruta_salida}")


def main():
    """Metodo disparador principal."""
    logger.info("--- INICIO DE CREACION DE REPORTE EXCEL PCC 2026 DESDE BD ---")
    try:
        motor_excel = GeneradorExcelPCCBD()
        motor_excel.ejecutar_proceso()
    except Exception as error:
        logger.critical(f"El proceso se detuvo inesperadamente: {error}", exc_info=True)


if __name__ == "__main__":
    main()