# -*- coding: utf-8 -*-
"""
Generador de Reportes Excel: Caracterizacion SI-APS 2026
Proposito: Extraer datos (Familias e Integrantes) directamente desde PostgreSQL
y transformar los nombres tecnicos (snake_case) utilizando un Mapeo Estricto 1 a 1
para generar un archivo Excel limpio y amigable para el usuario final.
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
# DICCIONARIOS DE MAPEO ESTRICTO 1 A 1
# =============================================================================
MAPEO_FAMILIAR_EXACTO = {
    "1_1_consentimiento_i": "1. Consentimiento Informado",
    "2_numero_de_identifi": "Numero de Identificacion del Equipo Basico de Salud",
    "3_tipo_de_identifica": "Tipo de identificacion del responsable",
    "4_nmero_de_identific": "Numero de identificacion del responsable",
    "5_responsable_de_la_": "Responsable de la evaluacion",
    "6_fecha_diligenciami": "Fecha diligenciamiento de la ficha",
    "7_nombre_completo_de": "Nombre Completo de Quien Recibe",
    "8_nmero_de_documento": "Numero de Documento",
    "9_2_departamento_no_": "2. Departamento",
    "10_3_unidad_zonal_de": "3. Unidad Zonal de Planeacion",
    "11_3_municipio__rea_": "3. Municipio",
    "12_4_territorio": "4. Territorio",
    "13_5_microterritorio": "5. Microterritorio",
    "14_7_direccin": "7. Direccion",
    "lat_15_8_geo_punto_georr": "8. Geo Punto (Latitud)",
    "long_15_8_geo_punto_georr": "8. Geo Punto (Longitud)",
    "accuracy_15_8_geo_punto_georr": "8. Geo Punto (Precision)",
    "utm_northing_15_8_geo_punto_georr": "8. Geo Punto (UTM Northing)",
    "utm_easting_15_8_geo_punto_georr": "8. Geo Punto (UTM Easting)",
    "utm_zone_15_8_geo_punto_georr": "8. Geo Punto (UTM Zone)",
    "16_9_ubicacin_del_ho": "9. Ubicacion del hogar",
    "18_10_cdigo_hogar": "10. Codigo Hogar",
    "19_101_cdigo_hogar": "10.1 Codigo Hogar",
    "21_11_cdigo_familia": "11. Codigo Familia",
    "22_111_cdigo_familia": "11.1 Codigo Familia",
    "23_12_estrato_socioe": "12. Estrato Socioeconomico",
    "24_13_numero_de_hoga": "13. Numero de Hogares",
    "25_14_numero_de_fami": "14. Numero de Familias",
    "26_15_numero_de_pers": "15. Numero de Personas",
    "27_22_cdigo_de_la_fi": "22. Codigo de la ficha",
    "28_16_nmero_de_ident": "16. Numero de identificacion del EBS",
    "29_17_prestador_prim": "17. Prestador Primario",
    "30_18_tipo_de_identi": "18. Tipo de identificacion responsable",
    "31_19_nmero_de_ident": "19. Numero de identificacion responsable",
    "32_20_responsable_de": "20. Responsable de la evaluacion",
    "33_21_perfil_de_quie": "21. Perfil de quien realiza la evaluacion",
    "34_23_fecha_diligenc": "23. Fecha diligenciamiento de la ficha",
    "35_24_tipo_de_la_viv": "24. Tipo de la Vivienda",
    "36_241_cual_escriba_": "24.1 ¿Cual?",
    "37_25_cul_es_el_mate": "25. Material predominante de las paredes",
    "38_251_cual_escriba_": "25.1 ¿Cual?",
    "39_26_cul_es_el_mate": "26. Material predominante del piso",
    "40_261_cual_escriba_": "26.1 ¿Cual?",
    "41_27_cul_es_el_mate": "27. Material predominante del techo",
    "42_271_cual_escriba_": "27.1 ¿Cual?",
    "43_28_de_cuntos_cuar": "28. Numero de cuartos o piezas",
    "44_29_hacinamiento": "29. Hacinamiento",
    "45_30_se_identifican": "30. Escenarios de riesgo de accidente",
    "46_31_desde_la_vivie": "31. Accesibilidad desde la vivienda",
    "47_32_cul_fuente_de_": "32. Fuente de energia o combustible",
    "48_321_cual_escriba_": "32.1 ¿Cual?",
    "49_33_se_observa_cer": "33. Criaderos o reservorios (vectores)",
    "50_34_observe_si_cer": "34. Observacion del entorno",
    "51_341_especifique_e": "34.1 ¿Especifique?",
    "52_35_al_interior_de": "35. Actividad Economica al Interior",
    "53_36_seale_los_anim": "36. Animales que conviven con la familia",
    "54_361_cual_escriba_": "36.1 ¿Cual?",
    "55_362_registrar_can": "36.2 Registrar Cantidad",
    "56_37_cul_es_la_prin": "37. Principal fuente de abastecimiento de agua",
    "57_371_cual_escriba_": "37.1 ¿Cual?",
    "58_38_cul_es_el_sist": "38. Sistema de disposicion de excretas",
    "59_381_cul_escriba_e": "38.1 ¿Cual?",
    "60_39_cul_es_el_sist": "39. Sistema de disposicion de aguas residuales",
    "61_391_cual_escriba_": "39.1 ¿Cual?",
    "62_40_como_se_realiz": "40. Disposicion final de los residuos solidos",
    "63_401_cual_escriba_": "40.1 ¿Cual?",
    "64_41_tipo_de_famili": "41. Tipo de Familia",
    "65_42_nmero_de_perso": "42. Numero de personas que conforman la familia",
    "66_43_estructura_y_d": "43. Estructura y dinamica familiar (Familiograma)",
    "67_431_seleccione_el": "43.1 Seleccione el tipo de riesgo",
    "68_44_observaciones_": "44. Observaciones",
    "69_45_funcionalidad_": "45. Funcionalidad de la familia (Apgar)",
    "70_451_evidencia_apg": "45.1 Evidencia Apgar",
    "71_46_en_la_familia_": "46. Cuidador principal identificado",
    "72_47_si_la_respuest": "47. Escala ZARIT",
    "73_471_imagen_escala": "47.1 Imagen Escala ZARIT",
    "74_48_interrelacione": "48. Interrelaciones de la familia (ECOMAPA)",
    "75_49_familia_con_ni": "49. Familia con ninas, ninos y adolescentes",
    "76_50_gestante_en_la": "50. Gestante en la familia",
    "77_51_familia_con_pe": "51. Familia con personas adultos mayores",
    "78_52_familia_vctima": "52. Familia victima del conflicto armado",
    "79_53_familia_que_co": "53. Familia con personas con discapacidad",
    "80_54_familia_que_co": "54. Familia con enfermedad cronica o huerfana",
    "81_55_familia_que_co": "55. Familia con enfermedad transmisible",
    "82_551_cual_escriba_": "55.1 ¿Cual?",
    "83_56_familia_con_vi": "56. Sucesos vitales normativos y no normativos",
    "84_57_familia_en_sit": "57. Vulnerabilidad social",
    "85_58_familias_con_p": "58. Practicas de cuidado criticas",
    "86_59_familia_con_in": "59. Antecedentes cronicos",
    "87_591_si_la_respues": "59.1 Indique Cuales",
    "88_60_cmo_obtiene_su": "60. Como obtiene sus alimentos",
    "89_601_cuales_escrib": "60.1 ¿Cuales?",
    "90_61_hbitos_de_vida": "61. Habitos de vida saludable",
    "91_62_recursos_socio": "62. Recursos socioemocionales",
    "92_63_prcticas_para_": "63. Practicas para cuidado de entornos",
    "93_64_prcticas_de_fa": "64. Relaciones sanas y constructivas",
    "94_65_recursos_socia": "65. Recursos sociales y comunitarios",
    "95_66_prcticas_para_": "66. Autonomia de personas mayores",
    "96_67_prcticas_para_": "67. Prevencion de enfermedades",
    "97_68_prcticas_de_cu": "68. Saberes ancestrales/tradicionales",
    "98_69_capacidades_de": "69. Capacidades para exigibilidad",
    "99_41_identificacin_": "4.1 Identificacion de miembros",
    "147_70_observaciones": "70. Observaciones generales"
}

MAPEO_INDIVIDUAL_EXACTO = {
    "100_1_primer_nombre": "1. Primer Nombre",
    "101_2_segundo_nombre": "2. Segundo Nombre",
    "102_3_primer_apellid": "3. Primer Apellido",
    "103_4_segundo_apelli": "4. Segundo Apellido",
    "104_5_tipo_de_identi": "5. Tipo de Identificacion",
    "105_6_numero_de_iden": "6. Numero de Identificacion",
    "106_numero_celular": "Numero Celular",
    "107_7_fecha_de_nacim": "7. Fecha de Nacimiento",
    "108_8_sexo": "8. Sexo",
    "109_9_se_encuentra_e": "9. ¿Se encuentra en periodo de gestacion?",
    "110_10_rol_dentro_de": "10. Rol Dentro de la Familia",
    "111_11_ocupacion": "11. Ocupacion",
    "112_12_nivel_educati": "12. Nivel Educativo",
    "113_13_rgimen_de_afi": "13. Regimen de afiliacion",
    "114_14_eapb": "14. EAPB",
    "115_15_pertenencia_a": "15. Pertenencia a un grupo poblacional",
    "116_16_pertenencia_t": "16. Pertenencia Etnica",
    "117_17_si_pertenece_": "17. Acompanamiento por medicina tradicional",
    "118_18_comunidad_o_p": "18. Comunidad o Pueblo Indigena",
    "119_19_reconoce_algu": "19. Reconoce Alguna Discapacidad",
    "120_20_peso_en_kilog": "20. Peso (en Kilogramos)",
    "121_21_talla_en_cent": "21. Talla (en centimetros)",
    "122_el_integrante_es": "El integrante es menor de 5 anos?",
    "123_22_diagnstico_nu": "22. Diagnostico nutricional (Menor 5 anos)",
    "124_23_medida_comple": "23. Perimetro Braquial",
    "125_22_diagnstico_nu": "22. Diagnostico nutricional",
    "126_24_el_integrante": "24. Condiciones de salud cronica",
    "127_25_cumple_con_el": "25. Cumple con Esquema (Promocion y Mantenimiento)",
    "128_26_a_qu_etapa_de": "26. Etapa del Ciclo de Vida",
    "129_vaco__preguntas_": "Vacio - Preguntas Multiples",
    "130_261_intervencion": "26.1. Intervenciones Pendientes (Primera Infancia)",
    "131_262_intervencion": "26.2. Intervenciones Pendientes (Infancia)",
    "132_263_intervencion": "26.3. Intervenciones Pendientes (Adolescente)",
    "133_264_intervencion": "26.4. Intervenciones Pendientes (Juventud)",
    "134_265_intervencion": "26.5. Intervenciones Pendientes (Adultez)",
    "135_266_intervencion": "26.6. Intervenciones Pendientes (Vejez)",
    "136_267_el_usuario_e": "26.7. Embarazada o Postparto",
    "137_268_intervencion": "26.8. Intervenciones Pendientes (Embarazo)",
    "138_27_motivo_por_el": "27. Motivo de no atencion de promocion",
    "139_28_realiza_algun": "28. ¿Realiza alguna practica deportiva?",
    "140_29_si_es_menor_d": "29. Lactancia materna exclusiva",
    "141_30_si_es_menor_d": "30. Lactancia materna (en meses)",
    "142_31_se_identifica": "31. Signos fisicos de desnutricion aguda",
    "143_32_actualmente_p": "32. Enfermedad en el ultimo mes",
    "144_321_cuales_escri": "32.1 ¿Cuales?",
    "145_33_esta_recibien": "33. Atencion y tratamiento actual",
    "146_34_si_la_respues": "34. Motivo de no atencion o tratamiento"
}


# =============================================================================
# ARQUITECTURA DE CLASES
# =============================================================================

class BaseConexionBD:
    """CLASE PADRE: Encargada de la conexion con PostgreSQL."""

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
            logger.error(f"Error al leer la tabla '{nombre_tabla}'. Verifica que exista. Error: {e}")
            return pd.DataFrame()


class GeneradorExcelCaracterizacionBD(BaseConexionBD):
    """
    CLASE HIJA: Transforma los datos crudos extraidos de la BD usando mapeo
    exacto 1 a 1 y genera el libro de Excel consolidado con nombres formales.
    """

    def __init__(self):
        super().__init__()
        # Nombres de las tablas generadas por nuestro proceso ETL
        self.tabla_familias = "caracterizacion_si_aps_familiar_2026"
        self.tabla_integrantes = "caracterizacion_si_aps_individual_2026"

    def _transformar_encabezados(self, df: pd.DataFrame, diccionario_mapeo: dict) -> pd.DataFrame:
        """Aplica el mapeo estricto para recuperar nombres formales en Excel."""
        mapa_metadatos = {
            "ec5_uuid": "ID Ficha Familiar",
            "ec5_branch_uuid": "ID Integrante",
            "ec5_parent_uuid": "ID Ficha (Relacion)",
            "ec5_branch_owner_uuid": "ID Ficha (Relacion)",
            "created_at": "Fecha de Creacion (App)",
            "uploaded_at": "Fecha de Sincronizacion",
            "title": "Titulo del Registro",
            "created_by": "Usuario Creador"
        }

        encabezados_procesados = {}

        for col in df.columns:
            # Los nombres en BD ya están en lowercase y snake_case
            col_normalizada = str(col).strip().lower()

            # 1. Asignacion de metadatos del sistema
            if col_normalizada in mapa_metadatos:
                encabezados_procesados[col] = mapa_metadatos[col_normalizada]
                continue

            # 2. Asignacion exacta desde el diccionario
            if col_normalizada in diccionario_mapeo:
                encabezados_procesados[col] = diccionario_mapeo[col_normalizada]
                continue

            # 3. Plan B predictivo (Si hay campos nuevos en la BD no mapeados)
            nombre_limpio = re.sub(r'^[\d_]+', '', str(col))
            nombre_limpio = nombre_limpio.replace('_', ' ')
            nombre_limpio = re.sub(r'\s*\(no editar\)', '', nombre_limpio, flags=re.IGNORECASE)
            nombre_limpio = re.sub(r'\s*\(escriba el texto.*?\)', '', nombre_limpio, flags=re.IGNORECASE)
            encabezados_procesados[col] = nombre_limpio.title().strip()

        return df.rename(columns=encabezados_procesados)

    def ejecutar_proceso(self):
        # 1. Extraccion directa desde la Base de Datos
        df_familias = self.extraer_tabla(self.tabla_familias)
        df_integrantes = self.extraer_tabla(self.tabla_integrantes)

        if df_familias.empty and df_integrantes.empty:
            logger.warning("No se detectaron datos en la base de datos para generar el Excel.")
            return

        # 2. Transformacion de encabezados (Data Cleansing)
        logger.info("Aplicando mapeo exacto de columnas para el Excel...")
        if not df_familias.empty:
            # Como SQL puede devolver fechas como datetime, forzamos todo a string si es necesario,
            # pero Pandas to_excel maneja fechas nativas excelentemente bien.
            df_familias = self._transformar_encabezados(df_familias, MAPEO_FAMILIAR_EXACTO)

        if not df_integrantes.empty:
            df_integrantes = self._transformar_encabezados(df_integrantes, MAPEO_INDIVIDUAL_EXACTO)

        # 3. Generacion del archivo Excel
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        ruta_salida = os.path.join(directorio_actual, "Caracterizacion_2026.xlsx")

        logger.info("Escribiendo datos en el archivo Excel multi-hoja...")

        # Eliminar el archivo viejo si existe (opcional, evita problemas de bloqueo a veces)
        if os.path.exists(ruta_salida):
            try:
                os.remove(ruta_salida)
            except Exception as e:
                logger.warning(f"No se pudo reemplazar el archivo previo (¿Esta abierto?). Error: {e}")

        with pd.ExcelWriter(ruta_salida, engine='openpyxl') as escritor:
            if not df_familias.empty:
                df_familias.to_excel(escritor, sheet_name='Familias', index=False)
            if not df_integrantes.empty:
                df_integrantes.to_excel(escritor, sheet_name='Integrantes', index=False)

        logger.info(f"Reporte Excel generado exitosamente. Ruta: {ruta_salida}")


def main():
    logger.info("--- INICIO DE EXPORTACION EXCEL CARACTERIZACION 2026 DESDE BD ---")
    try:
        motor_excel = GeneradorExcelCaracterizacionBD()
        motor_excel.ejecutar_proceso()
    except Exception as error:
        logger.critical(f"El proceso se detuvo inesperadamente: {error}", exc_info=True)


if __name__ == "__main__":
    main()