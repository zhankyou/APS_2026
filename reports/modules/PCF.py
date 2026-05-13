# -*- coding: utf-8 -*-
"""
Generador de Reportes Excel: Planes de Cuidado Familiar (PCF) 2026
Proposito: Extraer datos directamente desde PostgreSQL (Formulario Padre e Integrantes),
transformando los nombres tecnicos de la base de datos a titulos legibles
mediante Mapeo Estricto por Prefijo de Seguridad.
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
# DICCIONARIOS DE MAPEO: SUBCADENAS ESTRICTAS
# =============================================================================

MAPEO_PLANES_PRINCIPAL = {
    "lat_": "1. Geolocalizacion (Latitud)",
    "long_": "1. Geolocalizacion (Longitud)",
    "accuracy_": "1. Geolocalizacion (Precision)",
    "utm_northing": "1. Geolocalizacion (UTM Northing)",
    "utm_easting": "1. Geolocalizacion (UTM Easting)",
    "utm_zone": "1. Geolocalizacion (UTM Zone)",
    "2_fecha_vi": "2. Fecha Visita",
    "3_perfil_p": "3. Perfil Profesional o Tecnico",
    "4_nombre_d": "4. Nombre del Profesional o Tecnico",
    "5_tipo_de_d": "5. Tipo de Documento del Profesional",
    "6_numero_de": "6. Numero de Documento del Profesional",
    "7_territori": "7. Territorio",
    "8_microter": "8. Microterritorio",
    "9_identific": "9. Identificacion del Hogar",
    "91_identifi": "9.1 Identificacion del Hogar",
    "10_identifi": "10. Identificacion de la Familia",
    "101_identif": "10.1 Identificacion de la Familia",
    "11_riesgo_e": "11. Riesgo Entorno - Hogar",
    "111_mencion": "11.1 Mencione Otro Riesgo Hogar",
    "12_condicio": "12. Condiciones de salud",
    "121_mencion": "12.1 Mencione Otras Condiciones de Salud",
    "13_condicio": "13. Condiciones socioeducativas",
    "131_mencion": "13.1 Mencione Otras Condiciones Socioeduc.",
    "14_riesgos_": "14. Riesgos sociales",
    "141_mencion": "14.1 Mencione Otro Riesgo Social",
    "15_riesgo_e": "15. Riesgo Entorno laboral",
    "151_mencion": "15.1 Mencione Otro Riesgo Laboral",
    "16_cules_co": "16. Compromisos asumidos por la familia",
    "161_especif": "16.1 Especificar Otro compromiso",
    "17_realizar": "17. Realizara la Evaluacion de la Familia",
    "18_recibi_": "18. ¿Recibio la informacion de manera clara?",
    "19_el_trato": "19. ¿El trato del personal fue respetuoso?",
    "20_sinti_ac": "20. ¿Sintio acompanamiento en el proceso?",
    "21_se_cumpl": "21. ¿Se cumplieron las visitas prometidas?",
    "22_not_algn": "22. ¿Noto algun cambio positivo?",
    "23_est_sati": "23. ¿Esta satisfecho con el plan de cuidado?",
    "24_recomen": "24. ¿Recomendaria este plan de cuidado?",
    "25_se_logr_": "25. ¿Se logro el objetivo principal?",
    "26_las_acci": "26. ¿Acciones adecuadas para la situacion?",
    "27_el_usuar": "27. ¿La familia adopto las recomendaciones?",
    "28_se_ident": "28. ¿Mejoras en condiciones de salud?",
    "29_fue_nece": "29. ¿Fue necesario modificar el plan?",
    "30_el_usuar": "30. ¿La familia cumplio compromisos?",
    "31_el_equip": "31. ¿El equipo APS cumplio compromisos?",
    "32_se_logr_": "32. ¿Se logro articular con otras instituciones?",
    "33_el_plan_": "33. ¿El plan de cuidado finalizo satisfactoriamente?",
    "34_se_dej_c": "34. ¿Se dejo constancia en historia clinica?",
    "35_se_infor": "35. ¿Se informo el cierre del plan?",
    "36_consider": "36. ¿Necesario dar continuidad?",
    "37_nivel_de": "37. Nivel de impacto logrado",
    "resumen_de_intervenci": "Resumen de Intervencion Familiar"
}

MAPEO_PLANES_INTEGRANTES = {
    "1_primer_no": "1. Primer Nombre",
    "2_segundo_n": "2. Segundo Nombre",
    "3_primer_ap": "3. Primer Apellido",
    "4_segundo_a": "4. Segundo Apellido",
    "5_tipo_de_d": "5. Tipo de Documento",
    "6_numero_de": "6. Numero de Documento",
    "7_soporte_f": "7. Soporte Documento Identidad",
    "8_fecha_de_": "8. Fecha de Nacimiento",
    "9_edad": "9. Edad",
    "10_seleccio": "10. Seleccione tipo de Edad",
    "11_sexo": "11. Sexo",
    "12_peso": "12. Peso (En Kilogramos)",
    "13_talla": "13. Talla (En Centimetros)",
    "14_tipo_de_": "14. Tipo de Sangre",
    "15_tipo_de_": "15. Tipo de RH",
    "16_numero_": "16. Numero de Celular",
    "17_falta_de": "17. Falta intervencion Promocion/Prevencion",
    "171_mencion": "17.1 Mencione Otro (Promocion/Prevencion)",
    "18_falta_de": "18. Falta detecciones tempranas",
    "181_mencion": "18.1 Mencione Otro (Deteccion temprana)",
    "19_ausencia": "19. Ausencia controles por curso de vida",
    "191_mencion": "19.1 Mencione Otro (Controles curso de vida)",
    "20_falta_de": "20. Falta de cobertura PAI",
    "211_mencion": "21.1 Mencione Otro (Falta cobertura)",
    "22_atencin_": "22. Atencion salud curso de vida no garantizada",
    "221_mencion": "22.1 Mencione Otro (Atencion salud)",
    "23_que_tipo": "23. Tipo de Consulta a Realizar",
    "231_educaci": "23.1 Educacion en Prevencion",
    "232_consult": "23.2 Consultas Jefes de Enfermeria",
    "233_mencion": "23.3 Mencione Otro (Consulta)",
    "234_educaci": "23.4 Educacion en la Prevencion",
    "235_consult": "23.5 Consultas Medico",
    "236_mencion": "23.6 Mencione Otro (Consulta Medicina)",
    "237_tema_ce": "23.7 Tema Central Educacion",
    "238_mencion": "23.8 Mencione Otro (Tema Educacion)",
    "239_metodol": "23.9 Metodologia Educativa Aplicada",
    "2310_identi": "23.10 ¿Identifico signo de alarma?",
    "2311_ruta_s": "23.11 Ruta sugerida para derivacion",
    "24_resumen_": "24. Resumen de Valoracion Individual"
}


# =============================================================================
# ARQUITECTURA DE CLASES
# =============================================================================

class BaseConexionBD:
    """CLASE PADRE: Encargada de establecer la conexion segura con PostgreSQL."""

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
        """Extrae el contenido completo de una tabla hacia un DataFrame de Pandas."""
        logger.info(f"Consultando registros de la tabla: {nombre_tabla}...")
        try:
            with self.engine.connect() as conexion:
                query = f"SELECT * FROM public.{nombre_tabla}"
                df = pd.read_sql(query, conexion)
                return df
        except Exception as e:
            logger.error(f"Error al leer la tabla '{nombre_tabla}'. Verifica su existencia. Error: {e}")
            return pd.DataFrame()


class GeneradorExcelPCFBD(BaseConexionBD):
    """
    CLASE HIJA: Extrae los datos desde la BD, cruza los encabezados con los
    diccionarios aplicando busqueda de prefijos, y exporta el archivo Excel.
    """

    def __init__(self):
        super().__init__()
        # Nombres de las tablas generadas por nuestro pipeline ETL
        self.tabla_planes = "pcf_planes_principal_2026"
        self.tabla_integrantes = "pcf_planes_integrantes_2026"

    def _transformar_encabezados(self, df: pd.DataFrame, diccionario_mapeo: dict) -> pd.DataFrame:
        """Aplica el mapeo estricto evaluando prefijos o subcadenas seguras en las columnas de la BD."""
        mapa_metadatos = {
            "ec5_uuid": "ID Ficha Principal",
            "ec5_branch_uuid": "ID Subformulario",
            "ec5_parent_uuid": "ID Ficha Relacionada",
            "ec5_branch_owner_uuid": "ID Ficha Relacionada",
            "created_at": "Fecha de Creacion (App)",
            "uploaded_at": "Fecha de Sincronizacion",
            "title": "Titulo del Registro",
            "created_by": "Usuario Creador"
        }

        encabezados_procesados = {}

        for col in df.columns:
            # 1. Normalizacion estricta (Las columnas de BD ya vienen en minuscula, pero aseguramos)
            col_normalizada = str(col).strip().lower()

            # 2. Metadatos del sistema
            if col_normalizada in mapa_metadatos:
                encabezados_procesados[col] = mapa_metadatos[col_normalizada]
                continue

            # 3. Mapeo Blindado (Busqueda de prefijos / subcadenas)
            mapeado = False
            for llave_api, nombre_oficial in diccionario_mapeo.items():
                if col_normalizada.startswith(llave_api) or f"_{llave_api}" in col_normalizada:
                    encabezados_procesados[col] = nombre_oficial
                    mapeado = True
                    break

            if mapeado:
                continue

            # 4. Plan B Predictivo (Para columnas nuevas no mapeadas)
            nombre_limpio = re.sub(r'^[\d_]+', '', str(col))
            nombre_limpio = nombre_limpio.replace('_', ' ').title().strip()
            encabezados_procesados[col] = nombre_limpio

        return df.rename(columns=encabezados_procesados)

    def ejecutar_proceso(self):
        logger.info("Iniciando extraccion de Planes de Cuidado desde PostgreSQL...")

        df_planes_ppal = self.extraer_tabla(self.tabla_planes)
        df_planes_integ = self.extraer_tabla(self.tabla_integrantes)

        if df_planes_ppal.empty and df_planes_integ.empty:
            logger.warning("No se encontraron registros en la BD para generar el Excel.")
            return

        logger.info("Aplicando mapeos estrictos de seguridad a los nombres de las columnas...")
        if not df_planes_ppal.empty:
            df_planes_ppal = self._transformar_encabezados(df_planes_ppal, MAPEO_PLANES_PRINCIPAL)
        if not df_planes_integ.empty:
            df_planes_integ = self._transformar_encabezados(df_planes_integ, MAPEO_PLANES_INTEGRANTES)

        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        ruta_salida = os.path.join(directorio_actual, "PCF_General_2026.xlsx")

        # Eliminacion segura del archivo si ya existe
        if os.path.exists(ruta_salida):
            try:
                os.remove(ruta_salida)
            except Exception as e:
                logger.warning(f"No se pudo reemplazar el archivo previo (Posiblemente abierto). Error: {e}")

        logger.info("Consolidando datos en el archivo Excel multi-hoja...")
        with pd.ExcelWriter(ruta_salida, engine='openpyxl') as escritor:
            if not df_planes_ppal.empty:
                df_planes_ppal.to_excel(escritor, sheet_name='Planes_Cuidado', index=False)
            if not df_planes_integ.empty:
                df_planes_integ.to_excel(escritor, sheet_name='PCF_Integrantes', index=False)

        logger.info(f"Reporte generado exitosamente. Ruta: {ruta_salida}")


def main():
    logger.info("--- INICIO DE EXPORTACION EXCEL PCF 2026 DESDE BD ---")
    try:
        motor_excel = GeneradorExcelPCFBD()
        motor_excel.ejecutar_proceso()
    except Exception as error:
        logger.critical(f"El proceso se detuvo inesperadamente: {error}", exc_info=True)


if __name__ == "__main__":
    main()