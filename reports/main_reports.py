# -*- coding: utf-8 -*-
"""
Generador Maestro de Excel: Consolidado Completo APS 2026 (Desde PostgreSQL)
Incluye: Caracterización, Trámites, PCF, Psicología, PCC, Desistimiento y Vacunación.
Genera un solo archivo Excel con todas las hojas filtradas por fecha (Zona Horaria Colombia)
y envía métricas por correo.
"""

import os
import json
import logging
import re
import smtplib
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# =============================================================================
# CONFIGURACION E IMPORTACION
# =============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | [%(levelname)s] | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
load_dotenv()

# --- Cargar Diccionarios Generales ---
ruta_json = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "diccionario",
    "mapeos_aps_2026.json"
)
try:
    with open(ruta_json, 'r', encoding='utf-8') as archivo_json:
        DICCIONARIOS = json.load(archivo_json)
    logger.info("Archivo de diccionarios cargado exitosamente.")
except FileNotFoundError:
    logger.error(f"No se encontró el archivo de diccionarios en: {ruta_json}")
    DICCIONARIOS = {}

MAPEO_CARACT_FAMILIAR = DICCIONARIOS.get("CARACTERIZACION_FAMILIAR", {})
MAPEO_CARACT_INDIVIDUAL = DICCIONARIOS.get("CARACTERIZACION_INDIVIDUAL", {})
MAPEO_TRAMITES_EXACTO = DICCIONARIOS.get("TRAMITES_EXACTO", {})
MAPEO_PLANES_PRINCIPAL = DICCIONARIOS.get("PLANES_PRINCIPAL", {})
MAPEO_PLANES_INTEGRANTES = DICCIONARIOS.get("PLANES_INTEGRANTES", {})
MAPEO_PSICOLOGIA_PRINCIPAL = DICCIONARIOS.get("PSICOLOGIA_PRINCIPAL", {})
MAPEO_PSICOLOGIA_SEGUIMIENTOS = DICCIONARIOS.get("PSICOLOGIA_SEGUIMIENTOS", {})
MAPEO_PCC_PRINCIPAL = DICCIONARIOS.get("PCC_PRINCIPAL", {})
MAPEO_PCC_INTEGRANTES = DICCIONARIOS.get("PCC_INTEGRANTES", {})
MAPEO_DESISTIMIENTO = DICCIONARIOS.get("DESISTIMIENTO_EXACTO", {})

# --- Mapeo estricto para columnas ambiguas de Vacunación ---
MAPEO_VACUNACION_EXACTO = {
    "ec5_uuid": "ID Ficha Epicollect",
    "created_at": "Fecha de Creacion (API)",
    "uploaded_at": "Fecha de Sincronizacion",
    "title": "Titulo del Registro",
    "created_by": "Usuario Creador",
    "229_tipo_de_identifi": "TIPO DE IDENTIFICACIÓN",
    "230_numero_de_identi": "NUMERO DE IDENTIFICACIÓN",
    "231_fecha_de_nacimie": "FECHA DE NACIMIENTO",
    "232_primer_apellido": "PRIMER APELLIDO",
    "233_segundo_apellido": "SEGUNDO APELLIDO",
    "234_primer_nombre": "PRIMER NOMBRE",
    "235_segundo_nombre": "SEGUNDO NOMBRE",
    "60_primer_apellido_d": "PRIMER APELLIDO DEL NIÑO",
    "61_segundo_apellido_": "SEGUNDO APELLIDO DEL NIÑO",
    "62_primer_nombre_del": "PRIMER NOMBRE DEL NIÑO",
    "63_segundo_nombre_de": "SEGUNDO NOMBRE DEL NIÑO",
}


# =============================================================================
# FUNCION DE FILTRADO INTERACTIVO
# =============================================================================

def obtener_filtro_fechas():
    """Genera la consulta SQL (WHERE) basada en la decisión del usuario."""
    print("\n" + "=" * 60)
    print("   📊 GENERADOR DE REPORTES MAESTRO APS 2026")
    print("=" * 60)
    print("1. Descargar TODO el historial")
    print("2. Filtrar por rango de fechas (Zona Horaria Colombia)")
    opcion = input("Seleccione una opción (1 o 2): ")

    if opcion == "2":
        fecha_inicio = input("Fecha de INICIO (YYYY-MM-DD): ")
        fecha_fin = input("Fecha de FIN (YYYY-MM-DD): ")

        # Filtro potente: convierte la hora UTC a la hora local de Bogotá antes de filtrar
        where_sql = f"""
            WHERE DATE(created_at AT TIME ZONE 'UTC' AT TIME ZONE 'America/Bogota') 
            BETWEEN '{fecha_inicio}' AND '{fecha_fin}'
        """
        rango_str = f"{fecha_inicio}_a_{fecha_fin}"
        rango_legible = f"Desde {fecha_inicio} hasta {fecha_fin}"
        return where_sql, rango_str, rango_legible

    return "", "Historico_Completo", "Todo el historial"


# =============================================================================
# CLASE BASE: CONEXION A POSTGRESQL
# =============================================================================

class ConexionPostgreSQL:
    def __init__(self):
        self.db_user = os.getenv("DB_USER")
        self.db_password = os.getenv("DB_PASSWORD")
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = os.getenv("DB_PORT", "5432")
        self.db_name = os.getenv("DB_NAME")
        self.engine = self._conectar_base_datos()

    def _conectar_base_datos(self):
        cadena = (
            f"postgresql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )
        return create_engine(cadena)

    def extraer_tabla(self, nombre_tabla: str, where_sql: str = "") -> pd.DataFrame:
        """Extrae la tabla inyectando el filtro de fechas SQL."""
        try:
            with self.engine.connect() as conexion:
                query = text(f"SELECT * FROM public.{nombre_tabla} {where_sql};")
                return pd.read_sql(query, conexion)
        except Exception as e:
            logger.warning(f"No se pudo extraer '{nombre_tabla}': {e}")
            return pd.DataFrame()


# =============================================================================
# CLASE PRINCIPAL: GENERADOR MAESTRO
# =============================================================================

class GeneradorReporteMaestroDB(ConexionPostgreSQL):
    def __init__(self, where_sql="", rango_str="", rango_legible=""):
        super().__init__()
        self.where_sql = where_sql
        self.rango_str = rango_str
        self.rango_legible = rango_legible
        self.preguntas_vacunacion = {}
        self._cargar_json_vacunacion()

    # -------------------------------------------------------------------------
    # UTILIDADES GENERALES
    # -------------------------------------------------------------------------

    def _transformar_y_filtrar(
            self,
            df: pd.DataFrame,
            diccionario: dict,
            modo_estricto_1_a_1: bool = False
    ) -> pd.DataFrame:
        """Renombra columnas según diccionario. El filtro de fechas ya se hizo en SQL."""
        if df.empty:
            return df

        mapa_metadatos = {
            "ec5_uuid": "ID Ficha Principal",
            "ec5_parent_uuid": "ID Ficha Padre Relacionada",
            "ec5_branch_uuid": "ID Subformulario",
            "ec5_branch_owner_uuid": "ID Ficha Relacionada",
            "created_at": "Fecha de Creacion (App)",
            "uploaded_at": "Fecha de Sincronizacion",
            "created_by": "Usuario Creador",
            "title": "Titulo del Registro",
        }

        encabezados = {}
        for col in df.columns:
            col_norm = str(col).strip().lower()
            if col_norm in mapa_metadatos:
                encabezados[col] = mapa_metadatos[col_norm]
                continue

            mapeado = False
            if modo_estricto_1_a_1:
                if col_norm in diccionario:
                    encabezados[col] = diccionario[col_norm]
                    mapeado = True
            else:
                for llave, nombre in diccionario.items():
                    if col_norm.startswith(llave) or f"_{llave}" in col_norm:
                        encabezados[col] = nombre
                        mapeado = True
                        break

            if not mapeado:
                encabezados[col] = (
                    re.sub(r'^[\d_]+', '', str(col))
                    .replace('_', ' ')
                    .title()
                    .strip()
                )

        df = df.rename(columns=encabezados)

        # Formateo de fechas para mayor legibilidad
        if "Fecha de Creacion (App)" in df.columns:
            df["Fecha de Creacion (App)"] = pd.to_datetime(df["Fecha de Creacion (App)"], errors='coerce').dt.strftime(
                '%d/%m/%Y %H:%M')

        return df

    def _extraer_novedad_relevante(self, df: pd.DataFrame, palabras_clave: list) -> str:
        """Retorna el valor más frecuente en columnas de texto descriptivo."""
        if df.empty:
            return "Sin registros"
        for col in df.columns:
            if any(p in str(col).lower() for p in palabras_clave):
                valores = df[col].dropna().astype(str).str.strip()
                valores = valores[
                    ~valores.str.contains('no aplica|ningun', case=False, na=False)
                ]
                if not valores.empty:
                    return valores.value_counts().index[0]
        return "No se encontraron novedades específicas"

    # -------------------------------------------------------------------------
    # UTILIDADES ESPECÍFICAS PARA VACUNACIÓN
    # -------------------------------------------------------------------------

    def _cargar_json_vacunacion(self):
        ruta = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "formulario_vacunacion.json"
        )
        if not os.path.exists(ruta):
            return

        try:
            with open(ruta, 'r', encoding='utf-8') as f:
                data = json.load(f)

            def extraer_preguntas(elementos):
                for el in elementos:
                    if el.get('type') not in ['readme', 'group']:
                        q = re.sub(r'<[^>]+>', '', el.get('question', '')).strip()
                        if q:
                            self.preguntas_vacunacion[q] = q
                    if 'group' in el and isinstance(el['group'], list):
                        extraer_preguntas(el['group'])

            extraer_preguntas(data['data']['form']['inputs'])
        except Exception as e:
            logger.error(f"Error procesando JSON de vacunación: {e}")

    @staticmethod
    def _limpiar_texto(texto: str) -> str:
        texto = str(texto).lower().replace('_', ' ')
        return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')

    def _mejor_coincidencia_vacunacion(self, col_db: str) -> str:
        col_norm = str(col_db).strip().lower()
        if col_norm in MAPEO_VACUNACION_EXACTO:
            return MAPEO_VACUNACION_EXACTO[col_norm]

        col_sin_prefijo = re.sub(r'^[\d_]+', '', str(col_db))
        col_busqueda = self._limpiar_texto(col_sin_prefijo)

        mejor_pregunta = col_sin_prefijo
        mejor_ratio = 0.0

        for preg in self.preguntas_vacunacion:
            preg_cmp = self._limpiar_texto(preg)
            ratio = SequenceMatcher(None, col_busqueda, preg_cmp[:len(col_busqueda)]).ratio()
            if ratio > mejor_ratio:
                mejor_ratio = ratio
                mejor_pregunta = preg

        if mejor_ratio > 0.75:
            return mejor_pregunta
        return col_sin_prefijo.replace('_', ' ').title()

    def _formatear_fechas_df(self, df: pd.DataFrame) -> pd.DataFrame:
        claves_fecha = ['fecha', 'created_at', 'uploaded_at']
        for col in df.columns:
            if any(c in str(col).lower() for c in claves_fecha):
                df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%d/%m/%Y')
        return df

    def _preparar_hoja_vacunacion(self, df: pd.DataFrame) -> pd.DataFrame:
        if df.empty: return df
        df = df.replace([r'^\s*$', 'None', 'nan', 'NaN', 'NULL', 'null'], pd.NA, regex=True)
        df = df.dropna(axis=1, how='all')

        nuevos_nombres, vistos = [], {}
        for col in df.columns:
            nombre = self._mejor_coincidencia_vacunacion(col)
            if nombre in vistos:
                vistos[nombre] += 1
                nombre = f"{nombre} ({vistos[nombre]})"
            else:
                vistos[nombre] = 0
            nuevos_nombres.append(nombre)
        df.columns = nuevos_nombres
        return df

    def _procesar_vacunacion(self) -> tuple[dict, dict]:
        logger.info("Procesando módulo: Vacunación...")
        df_vac = self.extraer_tabla("vacunacion_aps_2026", self.where_sql)

        metricas_vacias = {
            'vac_total': 0, 'vac_recien_nacidos': 0, 'vac_ninos': 0,
            'vac_adultos': 0, 'vac_sin_clasificar': 0, 'vac_dosis_total': 0
        }

        if df_vac.empty: return {}, metricas_vacias

        df_vac = self._formatear_fechas_df(df_vac)
        col_tipo = next((c for c in df_vac.columns if 'tipo_de_vacunaci' in str(c).lower()), None)

        hojas_vac = {}
        conteos = {'Recién Nacidos': 0, 'Niños y Niñas': 0, 'Adultos': 0, 'Sin Clasificar': 0}

        if col_tipo:
            grupos = {
                'Recién Nacidos': df_vac[df_vac[col_tipo] == 'Recién Nacidos'].copy(),
                'Niños y Niñas': df_vac[df_vac[col_tipo] == 'Niños y Niñas'].copy(),
                'Adultos': df_vac[df_vac[col_tipo] == 'Adultos'].copy(),
            }
            df_otros = df_vac[~df_vac[col_tipo].isin(['Recién Nacidos', 'Niños y Niñas', 'Adultos'])].copy()
            if not df_otros.empty: grupos['Sin Clasificar'] = df_otros

            for nombre_hoja, df_grupo in grupos.items():
                if not df_grupo.empty:
                    hojas_vac[f'Vac_{nombre_hoja.replace(" ", "_")}'] = self._preparar_hoja_vacunacion(df_grupo)
                    conteos[nombre_hoja] = len(df_grupo)
        else:
            hojas_vac['Vacunacion_Completa'] = self._preparar_hoja_vacunacion(df_vac)
            conteos['Sin Clasificar'] = len(df_vac)

        col_dosis = [c for c in df_vac.columns if 'dosis' in str(c).lower()]
        total_dosis = int(df_vac[col_dosis].notna().any(axis=1).sum()) if col_dosis else len(df_vac)

        metricas_vac = {
            'vac_total': len(df_vac),
            'vac_recien_nacidos': conteos.get('Recién Nacidos', 0),
            'vac_ninos': conteos.get('Niños y Niñas', 0),
            'vac_adultos': conteos.get('Adultos', 0),
            'vac_sin_clasificar': conteos.get('Sin Clasificar', 0),
            'vac_dosis_total': total_dosis,
        }

        return hojas_vac, metricas_vac

    # -------------------------------------------------------------------------
    # METODO PRINCIPAL
    # -------------------------------------------------------------------------

    def ejecutar(self):
        logger.info("=" * 60)
        logger.info(f"  INICIANDO EXTRACCIÓN - Filtro: {self.rango_legible}")
        logger.info("=" * 60)

        metricas = {'rango_fechas': self.rango_legible}

        # --- 1. CARACTERIZACIÓN ---
        logger.info("Procesando módulo: Caracterización...")
        df_caract_fam = self._transformar_y_filtrar(
            self.extraer_tabla("caracterizacion_si_aps_familiar_2026", self.where_sql), MAPEO_CARACT_FAMILIAR)
        df_caract_ind = self._transformar_y_filtrar(
            self.extraer_tabla("caracterizacion_si_aps_individual_2026", self.where_sql), MAPEO_CARACT_INDIVIDUAL)
        metricas['caract_familias'] = len(df_caract_fam)
        metricas['caract_personas'] = len(df_caract_ind)

        # --- 2. TRÁMITES ---
        logger.info("Procesando módulo: Trámites...")
        df_tramites = self._transformar_y_filtrar(self.extraer_tabla("tramites_aps_2026", self.where_sql),
                                                  MAPEO_TRAMITES_EXACTO, modo_estricto_1_a_1=True)
        metricas['tramites_total'] = len(df_tramites)

        col_doc_idx = next(
            (i for i, c in enumerate(df_tramites.columns) if "numero de docu" in str(c).lower() or "15" in str(c)),
            None)
        metricas['tramites_personas'] = df_tramites.iloc[
            :, col_doc_idx].nunique() if col_doc_idx is not None and not df_tramites.empty else metricas[
            'tramites_total']

        cols_resolutivas_idx = [i for i, c in enumerate(df_tramites.columns) if "resolutiv" in str(c).lower()]
        metricas['tramites_resolutivos'] = sum(
            df_tramites.iloc[:, i].astype(str).str.contains('Si', case=False, na=False).sum() for i in
            cols_resolutivas_idx) if not df_tramites.empty else 0

        cols_requiere_idx = [i for i, c in enumerate(df_tramites.columns) if "requiere" in str(c).lower()]
        conteo_req = {
            df_tramites.columns[i]: df_tramites.iloc[:, i].astype(str).str.contains('Si', case=False, na=False).sum()
            for i in cols_requiere_idx} if not df_tramites.empty else {}

        tramite_top_raw = max(conteo_req, key=conteo_req.get) if conteo_req and max(conteo_req.values()) > 0 else "N/A"
        metricas['tramite_top'] = self._traducir_tramite(tramite_top_raw)

        # --- 3. PCF Y PSICOLOGÍA ---
        logger.info("Procesando módulo: PCF y Psicología...")
        df_planes_p = self._transformar_y_filtrar(self.extraer_tabla("pcf_planes_principal_2026", self.where_sql),
                                                  MAPEO_PLANES_PRINCIPAL)
        df_planes_i = self._transformar_y_filtrar(self.extraer_tabla("pcf_planes_integrantes_2026", self.where_sql),
                                                  MAPEO_PLANES_INTEGRANTES)

        df_psico_general = pd.DataFrame()
        if not df_planes_p.empty and "3. Perfil Profesional o Tecnico" in df_planes_p.columns:
            es_psicologo = df_planes_p["3. Perfil Profesional o Tecnico"].str.contains("Psicolog", case=False, na=False)
            df_psico_general = df_planes_p[es_psicologo]
            df_planes_p = df_planes_p[~es_psicologo]

        df_psico_integ = self._transformar_y_filtrar(
            self.extraer_tabla("pcf_psicologia_principal_2026", self.where_sql), MAPEO_PSICOLOGIA_PRINCIPAL)
        df_psico_seg = self._transformar_y_filtrar(
            self.extraer_tabla("pcf_psicologia_seguimientos_2026", self.where_sql), MAPEO_PSICOLOGIA_SEGUIMIENTOS)

        metricas['pcf_familias'] = len(df_planes_p)
        metricas['pcf_personas'] = len(df_planes_i)
        metricas['psico_familias'] = len(df_psico_general)
        metricas['psico_individual'] = len(df_psico_integ)
        metricas['psico_seguimientos'] = len(df_psico_seg)
        metricas['psico_novedad'] = self._extraer_novedad_relevante(df_psico_integ,
                                                                    ["motivo", "observacion", "diagnostico", "riesgo"])

        # --- 4. PCC ---
        logger.info("Procesando módulo: Plan de Cuidado Comunitario (PCC)...")
        df_pcc_p = self._transformar_y_filtrar(self.extraer_tabla("pcc_principal_2026", self.where_sql),
                                               MAPEO_PCC_PRINCIPAL)
        df_pcc_i = self._transformar_y_filtrar(self.extraer_tabla("pcc_integrantes_2026", self.where_sql),
                                               MAPEO_PCC_INTEGRANTES)

        metricas['pcc_planes'] = len(df_pcc_p)
        metricas['pcc_personas'] = len(df_pcc_i)
        metricas['pcc_novedad'] = self._extraer_novedad_relevante(df_pcc_p,
                                                                  ["novedad", "tema", "actividad", "observacion"])

        # --- 5. DESISTIMIENTO ---
        logger.info("Procesando módulo: Desistimiento...")
        df_desis = self._transformar_y_filtrar(self.extraer_tabla("desistimiento_aps_2026", self.where_sql),
                                               MAPEO_DESISTIMIENTO, modo_estricto_1_a_1=True)
        metricas['desis_total'] = len(df_desis)
        metricas['desis_novedad'] = self._extraer_novedad_relevante(df_desis,
                                                                    ["motivo", "causa", "razon", "observacion"])

        # --- 6. VACUNACIÓN ---
        hojas_vac, metricas_vac = self._procesar_vacunacion()
        metricas.update(metricas_vac)

        # --- 7. GENERACIÓN DEL EXCEL MAESTRO ---
        logger.info("Generando el archivo Excel Maestro...")
        fecha_hoy = datetime.now().strftime("%Y%m%d_%H%M")

        # Guardamos en la carpeta excel si existe, si no en la raíz
        dir_excel = os.path.join(os.path.dirname(os.path.abspath(__file__)), "excel")
        os.makedirs(dir_excel, exist_ok=True)

        ruta_salida = os.path.join(
            dir_excel,
            f"Reporte_Maestro_APS_{self.rango_str}_{fecha_hoy}.xlsx"
        )

        hojas_principales = {
            'Caract_Familiar': df_caract_fam,
            'Caract_Individual': df_caract_ind,
            'Tramites': df_tramites,
            'PCF_Principal': df_planes_p,
            'PCF_Integrantes': df_planes_i,
            'Psicologia_General': df_psico_general,
            'Psicologia_Integrantes': df_psico_integ,
            'Psicologia_Seguimientos': df_psico_seg,
            'PCC_Principal': df_pcc_p,
            'PCC_Integrantes': df_pcc_i,
            'Desistimientos': df_desis,
        }

        with pd.ExcelWriter(ruta_salida, engine='openpyxl') as escritor:
            for nombre_hoja, df_hoja in hojas_principales.items():
                if not df_hoja.empty:
                    df_hoja.to_excel(escritor, sheet_name=nombre_hoja, index=False)
                    logger.info(f"  ✔ Hoja '{nombre_hoja}' ({len(df_hoja)} filas)")

            for nombre_hoja, df_hoja in hojas_vac.items():
                if not df_hoja.empty:
                    df_hoja.to_excel(escritor, sheet_name=nombre_hoja, index=False)
                    logger.info(f"  ✔ Hoja '{nombre_hoja}' ({len(df_hoja)} filas)")

        logger.info(f"Excel Maestro generado exitosamente → {ruta_salida}")
        return ruta_salida, metricas

    # -------------------------------------------------------------------------
    # TRADUCTOR DE TRÁMITES
    # -------------------------------------------------------------------------

    @staticmethod
    def _traducir_tramite(tramite_top_raw: str) -> str:
        t = str(tramite_top_raw).lower()
        if "n/a" in t or t == "nan":           return "N/A"
        if "enfermer" in t or "pyp por en" in t: return "Atención PYP por Enfermería"
        if "medicina" in t or "pyp por me" in t: return "Atención PYP por Medicina"
        if "psicolog" in t or "psicol" in t:    return "Atención por Psicología"
        if "desescolarizado" in t or "niño" in t or "nio" in t: return "Atención a Menor Desescolarizado"
        if "vacunaci" in t or "pai" in t:       return "Vacunación (PAI)"
        if "afiliaci" in t or "aseguramiento" in t: return "Afiliación o Aseguramiento en Salud"
        if "demorada" in t or "citas" in t:     return "PQR - Citas Médicas Demoradas"
        if "medicamento" in t or "pendientes" in t: return "PQR - Pendientes con Medicamentos"
        if "sisben" in t:                        return "Trámite SISBÉN"
        if "discapacidad" in t:                  return "Certificado de Discapacidad"
        if "colombia mayor" in t or (
                "mayor" in t and "vida" not in t and "protecci" not in t): return "Inscripción Programa Colombia Mayor"
        if "iva" in t or "devoluci" in t:        return "Devolución del IVA"
        if "renta" in t or "ciudadana" in t:     return "Programa Renta Ciudadana"
        if "ayuda" in t or "banco" in t:         return "Acceso al Banco de Ayudas"
        if "vida" in t:                           return "Centros Vida (Adulto Mayor)"
        if "protecci" in t:                       return "Centros de Protección Social (Adulto Mayor)"
        if "habitante" in t or "calle" in t:     return "Certificado Habitante de Calle"
        if "pyp" in t:                            return "Atención PYP"
        fallback = re.sub(r'^requiere\s+', '', tramite_top_raw, flags=re.IGNORECASE).strip()
        return "Atención PYP General" if fallback.lower() in ["atencin", "atención", "atenci"] else fallback.title()


# =============================================================================
# ENVIO DE CORREO
# =============================================================================

def enviar_correo_reporte(ruta_excel: str, metricas: dict):
    """Muestra el borrador y envía el correo con el reporte adjunto."""
    sender_email = os.getenv("GMAIL_SENDER")
    sender_password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender_email or not sender_password:
        logger.error(
            "Credenciales GMAIL_SENDER / GMAIL_APP_PASSWORD no encontradas en .env. Omitiendo envío de correo.")
        return

    cuerpo_mensaje = f"""
Hola Equipo APS,

Adjunto el Consolidado Maestro actualizado del programa APS 2026.
A continuación, un resumen de la gestión:

📅 Rango de Fechas Evaluado: {metricas.get('rango_fechas', 'Todo el historial')}

📊 1. CARACTERIZACIÓN SI-APS:
   - Familias Caracterizadas  : {metricas['caract_familias']}
   - Personas Caracterizadas  : {metricas['caract_personas']}

📑 2. TRÁMITES APS:
   - Total de Trámites           : {metricas['tramites_total']}
   - Personas Únicas con Trámites: {metricas['tramites_personas']}
   - Trámites Gestionados (Resolutivos): {metricas['tramites_resolutivos']}
   - Requerimiento más frecuente : {metricas['tramite_top']}

🩺 3. PLANES DE CUIDADO FAMILIAR (PCF):
   - Planes Familiares Activos  : {metricas['pcf_familias']}
   - Personas Intervenidas      : {metricas['pcf_personas']}

🧠 4. MÓDULO PSICOLOGÍA:
   - Planes Familiares           : {metricas['psico_familias']}
   - Planes Individuales         : {metricas['psico_individual']}
   - Seguimientos Realizados     : {metricas['psico_seguimientos']}
   - Novedad Relevante           : {metricas['psico_novedad']}

🏘️ 5. PLAN DE CUIDADO COMUNITARIO (PCC):
   - Planes Comunitarios Creados : {metricas['pcc_planes']}
   - Personas Atendidas          : {metricas['pcc_personas']}
   - Novedad Relevante           : {metricas['pcc_novedad']}

❌ 6. DESISTIMIENTOS:
   - Total de Desistimientos     : {metricas['desis_total']}
   - Motivo Más Frecuente        : {metricas['desis_novedad']}

💉 7. VACUNACIÓN REGULAR APS:
   - Total de Registros          : {metricas['vac_total']}
   - Recién Nacidos              : {metricas['vac_recien_nacidos']}
   - Niños y Niñas               : {metricas['vac_ninos']}
   - Adultos                     : {metricas['vac_adultos']}
   - Sin Clasificar              : {metricas['vac_sin_clasificar']}
   - Total Dosis Registradas     : {metricas['vac_dosis_total']}

Este reporte fue generado automáticamente desde la Base de Datos PostgreSQL.
El archivo Excel adjunto contiene el detalle completo en hojas separadas.
"""

    print("\n" + "=" * 60)
    print("               BORRADOR DEL CORREO")
    print("=" * 60)
    print(cuerpo_mensaje)
    print("=" * 60 + "\n")

    destinatarios_raw = input(
        "Ingresa los correos destinatarios separados por coma\n"
        "(o presiona Enter para cancelar el envío): "
    ).strip()

    if not destinatarios_raw:
        logger.info("Envío de correo cancelado por el usuario.")
        return

    lista_destinatarios = [e.strip() for e in destinatarios_raw.split(",")]

    logger.info("Preparando envío de correo...")
    mensaje = MIMEMultipart()
    mensaje['From'] = sender_email
    mensaje['To'] = ", ".join(lista_destinatarios)
    mensaje['Subject'] = " Reporte Maestro y Métricas - Programa APS 2026"
    mensaje.attach(MIMEText(cuerpo_mensaje, 'plain'))

    try:
        with open(ruta_excel, "rb") as adjunto:
            parte = MIMEApplication(adjunto.read(), Name=os.path.basename(ruta_excel))
        parte['Content-Disposition'] = f'attachment; filename="{os.path.basename(ruta_excel)}"'
        mensaje.attach(parte)
    except Exception as e:
        logger.error(f"No se pudo adjuntar el archivo Excel: {e}")
        return

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as servidor:
            servidor.login(sender_email, sender_password)
            servidor.send_message(mensaje)
        logger.info(f"Correo enviado exitosamente a: {', '.join(lista_destinatarios)}")
    except Exception as e:
        logger.error(f"Error al enviar el correo: {e}")


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    # 1. Obtener la decisión del usuario (Filtro por fecha en SQL o Histórico)
    where_sql, rango_str, rango_legible = obtener_filtro_fechas()

    # 2. Ejecutar el orquestador inyectando el filtro SQL
    app = GeneradorReporteMaestroDB(where_sql=where_sql, rango_str=rango_str, rango_legible=rango_legible)
    ruta_excel_generado, metricas_calculadas = app.ejecutar()

    # 3. Enviar métricas por correo
    enviar_correo_reporte(ruta_excel_generado, metricas_calculadas)