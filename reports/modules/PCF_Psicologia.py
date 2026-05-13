# -*- coding: utf-8 -*-
"""
Generador de Reportes Excel: PCF y Modulo Psicologia 2026
Proposito: Extraer datos directamente desde PostgreSQL para 3 entidades,
transformar los encabezados mediante Mapeo Absoluto, y aplicar un FILTRO
ESTRATEGICO en el formulario Padre para exportar unicamente las
intervenciones realizadas por el Perfil de Psicologia.
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
# DICCIONARIOS DE MAPEO ABSOLUTO
# =============================================================================

MAPEO_PLANES_PRINCIPAL = {
    "lat_1_1_": "1. Geolocalizacion (Latitud)",
    "long_1_1_": "1. Geolocalizacion (Longitud)",
    "accuracy_1_1_": "1. Geolocalizacion (Precision)",
    "utm_northing_1_1_": "1. Geolocalizacion (UTM Northing)",
    "utm_easting_1_1_": "1. Geolocalizacion (UTM Easting)",
    "utm_zone_1_1_": "1. Geolocalizacion (UTM Zone)",
    "2_2_": "2. Fecha Visita",
    "4_3_": "3. Perfil Profesional o Tecnico",
    "5_4_": "4. Nombre del Profesional o Tecnico",
    "6_5_": "5. Tipo de Documento del Profesional",
    "7_6_": "6. Numero de Documento del Profesional",
    "9_7_": "7. Territorio",
    "10_8_": "8. Microterritorio",
    "11_9_": "9. Identificacion del Hogar",
    "12_91_": "9.1 Identificacion del Hogar",
    "13_10_": "10. Identificacion de la Familia",
    "14_101_": "10.1 Identificacion de la Familia",
    "16_11_": "11. Riesgo Entorno - Hogar",
    "17_111_": "11.1 Mencione Otro Riesgo Hogar",
    "18_12_": "12. Condiciones de salud",
    "19_121_": "12.1 Mencione Otras Condiciones de Salud",
    "20_13_": "13. Condiciones socioeducativas",
    "21_131_": "13.1 Mencione Otras Condiciones Socioeduc.",
    "22_14_": "14. Riesgos sociales",
    "23_141_": "14.1 Mencione Otro Riesgo Social",
    "24_15_": "15. Riesgo Entorno laboral",
    "25_151_": "15.1 Mencione Otro Riesgo Laboral",
    "27_16_": "16. Compromisos asumidos por la familia",
    "28_161_": "16.1 Especificar Otro compromiso",
    "73_17_": "17. Realizara la Evaluacion de la Familia",
    "75_18_": "18. ¿Recibio la informacion de manera clara?",
    "76_19_": "19. ¿El trato del personal fue respetuoso?",
    "77_20_": "20. ¿Sintio acompanamiento en el proceso?",
    "78_21_": "21. ¿Se cumplieron las visitas prometidas?",
    "79_22_": "22. ¿Noto algun cambio positivo?",
    "80_23_": "23. ¿Esta satisfecho con el plan de cuidado?",
    "81_24_": "24. ¿Recomendaria este plan de cuidado?",
    "83_25_": "25. ¿Se logro el objetivo principal?",
    "84_26_": "26. ¿Acciones adecuadas para la situacion?",
    "85_27_": "27. ¿La familia adopto las recomendaciones?",
    "86_28_": "28. ¿Mejoras en condiciones de salud?",
    "87_29_": "29. ¿Fue necesario modificar el plan?",
    "89_30_": "30. ¿La familia cumplio compromisos?",
    "90_31_": "31. ¿El equipo APS cumplio compromisos?",
    "91_32_": "32. ¿Se logro articular con otras instituciones?",
    "93_33_": "33. ¿El plan de cuidado finalizo satisfactoriamente?",
    "94_34_": "34. ¿Se dejo constancia en historia clinica?",
    "95_35_": "35. ¿Se informo el cierre del plan?",
    "96_36_": "36. ¿Necesario dar continuidad?",
    "97_37_": "37. Nivel de impacto logrado",
    "98_resumen_de_interv": "Resumen de Intervencion Familiar"
}

MAPEO_PSICOLOGIA_PRINCIPAL = {
    "100_1_": "1. Primer Nombre",
    "101_2_": "2. Segundo Nombre",
    "102_3_": "3. Primer Apellido",
    "103_4_": "4. Segundo Apellido",
    "104_5_": "5. Tipo de Documento",
    "105_6_": "6. Numero de Documento",
    "106_7_": "7. Soporte Documento Identidad",
    "107_8_": "8. Fecha de Nacimiento",
    "108_9_": "9. Edad",
    "109_10_": "10. Seleccione tipo de Edad",
    "110_11_": "11. Sexo",
    "111_12_": "12. Peso (En Kilogramos)",
    "112_13_": "13. Talla (En Centimetros)",
    "113_14_": "14. Tipo de Sangre",
    "114_15_": "15. Tipo de RH",
    "115_16_": "16. Numero de Celular",
    "116_17_": "17. Falta de intervencion Promocion/Prevencion",
    "117_171_": "17.1 Mencione Otro (Promocion)",
    "118_18_": "18. Falta de detecciones tempranas",
    "119_181_": "18.1 Mencione Otro (Deteccion)",
    "120_19_": "19. Ausencia de controles curso de vida",
    "121_191_": "19.1 Mencione Otro (Controles)",
    "122_20_": "20. Falta cobertura PAI",
    "123_201_": "20.1 Mencione Otro (Cobertura)",
    "124_21_": "21. Atencion salud curso de vida no garantizada",
    "125_211_": "21.1 Mencione Otro (Atencion)",
    "133_28_": "28. Resumen de Valoracion Individual"
}

MAPEO_PSICOLOGIA_SEGUIMIENTOS = {
    "127_22_": "22. Fecha Consulta o Seguimientos",
    "128_23_": "23. Consulta por Psicologia",
    "129_24_": "24. Tareas de Refuerzo e Intervencion",
    "130_25_": "25. Requiere Control o Seguimientos",
    "131_26_": "26. Compromisos y Acuerdos",
    "132_27_": "27. Evaluacion de Logros y Compromisos"
}


# =============================================================================
# ARQUITECTURA DE CLASES
# =============================================================================

class BaseConexionBD:
    """CLASE PADRE: Maneja la conexion con la base de datos PostgreSQL."""

    def __init__(self):
        self.db_user = os.getenv("DB_USER")
        self.db_password = os.getenv("DB_PASSWORD")
        self.db_host = os.getenv("DB_HOST")
        self.db_port = os.getenv("DB_PORT")
        self.db_name = os.getenv("DB_NAME")

        self.engine = self._conectar_base_datos()

    def _conectar_base_datos(self) -> Engine:
        logger.info("Estableciendo conexion con PostgreSQL...")
        cadena_conexion = f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        return create_engine(cadena_conexion)

    def extraer_tabla(self, nombre_tabla: str) -> pd.DataFrame:
        """Extrae todos los registros de una tabla a un DataFrame."""
        logger.info(f"Consultando registros de la tabla: {nombre_tabla}...")
        try:
            with self.engine.connect() as conexion:
                query = f"SELECT * FROM public.{nombre_tabla}"
                df = pd.read_sql(query, conexion)
                return df
        except Exception as e:
            logger.error(f"Error al leer la tabla '{nombre_tabla}'. Verifica su existencia. Error: {e}")
            return pd.DataFrame()


class GeneradorExcelPsicologiaBD(BaseConexionBD):
    """
    CLASE HIJA: Extrae las 3 entidades desde BD, mapea encabezados y filtra
    los registros exclusivos de Psicologia en el formulario Padre.
    """

    def __init__(self):
        super().__init__()
        # Tablas destino alimentadas por el Pipeline ETL
        self.tabla_planes = "pcf_planes_principal_2026"
        self.tabla_psico = "pcf_psicologia_principal_2026"
        self.tabla_seguimientos = "pcf_psicologia_seguimientos_2026"

    def _transformar_encabezados(self, df: pd.DataFrame, diccionario_mapeo: dict) -> pd.DataFrame:
        """Aplica el mapeo usando startswith() sobre las columnas de la BD."""
        mapa_metadatos = {
            "ec5_uuid": "ID Ficha Principal",
            "ec5_parent_uuid": "ID Ficha Padre Relacionada",
            "ec5_branch_uuid": "ID Subformulario",
            "ec5_branch_owner_uuid": "ID Ficha Relacionada",
            "created_at": "Fecha de Creacion (App)",
            "uploaded_at": "Fecha de Sincronizacion",
            "title": "Titulo del Registro",
            "created_by": "Usuario Creador"
        }

        encabezados_procesados = {}

        for col in df.columns:
            # Aseguramos un string limpio y consistente
            col_normalizada = str(col).strip().replace(" ", "_").replace("-", "_").lower()

            if col_normalizada in mapa_metadatos:
                encabezados_procesados[col] = mapa_metadatos[col_normalizada]
                continue

            mapeado = False
            for llave_api, nombre_oficial in diccionario_mapeo.items():
                # Busca el inicio de la cadena usando la llave del diccionario
                if col_normalizada.startswith(llave_api):
                    encabezados_procesados[col] = nombre_oficial
                    mapeado = True
                    break

            if mapeado:
                continue

            # Fallback en caso de columnas nuevas no dictadas
            nombre_limpio = re.sub(r'^[\d_]+', '', str(col))
            nombre_limpio = nombre_limpio.replace('_', ' ').title().strip()
            encabezados_procesados[col] = nombre_limpio

        return df.rename(columns=encabezados_procesados)

    def ejecutar_proceso(self):
        logger.info("Iniciando extraccion de entidades desde PostgreSQL para Modulo Psicologia...")

        df_planes_ppal = self.extraer_tabla(self.tabla_planes)
        df_psico_ppal = self.extraer_tabla(self.tabla_psico)
        df_psico_seg = self.extraer_tabla(self.tabla_seguimientos)

        if df_planes_ppal.empty and df_psico_ppal.empty and df_psico_seg.empty:
            logger.warning("No se encontraron registros en la BD para generar el Excel de Psicologia.")
            return

        logger.info("Aplicando mapeos absolutos a los encabezados...")

        if not df_planes_ppal.empty:
            df_planes_ppal = self._transformar_encabezados(df_planes_ppal, MAPEO_PLANES_PRINCIPAL)

            # --- FILTRO EXCLUSIVO PARA PSICOLOGIA ---
            logger.info("Filtrando el Formulario Padre unicamente para 'Profesional Psicologia'...")
            col_perfil = "3. Perfil Profesional o Tecnico"
            if col_perfil in df_planes_ppal.columns:
                # Utilizamos str.contains ignorando mayusculas/minusculas
                filtro = df_planes_ppal[col_perfil].str.contains("Psicolog", case=False, na=False)
                df_planes_ppal = df_planes_ppal[filtro]
                logger.info(f"Filtro aplicado con exito. Registros de Psicologia retenidos: {len(df_planes_ppal)}")
            else:
                logger.warning(f"No se encontro la columna '{col_perfil}' para aplicar el filtro.")

        if not df_psico_ppal.empty:
            df_psico_ppal = self._transformar_encabezados(df_psico_ppal, MAPEO_PSICOLOGIA_PRINCIPAL)

        if not df_psico_seg.empty:
            df_psico_seg = self._transformar_encabezados(df_psico_seg, MAPEO_PSICOLOGIA_SEGUIMIENTOS)

        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        ruta_salida = os.path.join(directorio_actual, "PCF_Psicologia_2026.xlsx")

        # Eliminacion segura si el archivo ya existe (previene errores I/O)
        if os.path.exists(ruta_salida):
            try:
                os.remove(ruta_salida)
            except Exception as e:
                logger.warning(f"No se pudo reemplazar el archivo previo (¿Abierto en Excel?). Error: {e}")

        logger.info("Consolidando datos en el archivo Excel...")
        with pd.ExcelWriter(ruta_salida, engine='openpyxl') as escritor:
            if not df_planes_ppal.empty:
                df_planes_ppal.to_excel(escritor, sheet_name='Planes_Cuidado', index=False)
            if not df_psico_ppal.empty:
                df_psico_ppal.to_excel(escritor, sheet_name='Psicologia_General', index=False)
            if not df_psico_seg.empty:
                df_psico_seg.to_excel(escritor, sheet_name='Psicologia_Seguimientos', index=False)

        logger.info(f"Reporte generado exitosamente. Ruta: {ruta_salida}")


def main():
    logger.info("--- INICIO DE EXPORTACION EXCEL PSICOLOGIA (PCF) 2026 DESDE BD ---")
    try:
        motor_excel = GeneradorExcelPsicologiaBD()
        motor_excel.ejecutar_proceso()
    except Exception as error:
        logger.critical(f"El proceso se detuvo inesperadamente: {error}", exc_info=True)


if __name__ == "__main__":
    main()