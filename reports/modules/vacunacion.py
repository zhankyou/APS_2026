# -*- coding: utf-8 -*-
"""
Generador de Reportes Excel: Vacunacion Regular APS 2026
Proposito: Extraer datos de PostgreSQL, ajustar zona horaria a Colombia,
filtrar por fechas dinámicamente, formatear fechas a DD/MM/AAAA, eliminar
columnas vacias, usar mapeo estricto, restaurar titulos del JSON, separar
en hojas y emitir resumen analitico.
"""

import os
import json
import logging
import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher
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

load_dotenv()


class GeneradorExcelVacunacionBD:
    def __init__(self):
        self.db_user = os.getenv("DB_USER")
        self.db_password = os.getenv("DB_PASSWORD")
        self.db_host = os.getenv("DB_HOST")
        self.db_port = os.getenv("DB_PORT")
        self.db_name = os.getenv("DB_NAME")

        self.tabla_principal = "vacunacion_aps_2026"
        self.engine = self._conectar_base_datos()

        self.preguntas_oficiales = {}

        # =========================================================
        # DICCIONARIO ESTRICTO PARA CORRECCIONES EXACTAS
        # =========================================================
        self.mapeo_exacto = {
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
            "63_segundo_nombre_de": "SEGUNDO NOMBRE DEL NIÑO"
        }

    def _conectar_base_datos(self) -> Engine:
        logger.info("Conectando con la base de datos PostgreSQL...")
        cadena_conexion = f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
        return create_engine(cadena_conexion)

    def extraer_tabla(self) -> pd.DataFrame:
        logger.info(f"Consultando registros de la tabla: {self.tabla_principal}...")
        try:
            with self.engine.connect() as conexion:
                query = f"SELECT * FROM public.{self.tabla_principal}"
                return pd.read_sql(query, conexion)
        except Exception as e:
            logger.error(f"Error al leer la tabla. Verifica su existencia. Error: {e}")
            return pd.DataFrame()

    def _convertir_zona_horaria_colombia(self, df: pd.DataFrame) -> pd.DataFrame:
        """Ajusta las fechas del servidor (UTC) a la hora local de Colombia (UTC-5)."""
        claves_fecha = ['fecha', 'created_at', 'uploaded_at']

        for col in df.columns:
            if any(clave in str(col).lower() for clave in claves_fecha):
                df[col] = pd.to_datetime(df[col], errors='coerce')

                # Procesamos solo si la columna tiene datos validos
                if df[col].notna().any():
                    try:
                        # Si es ingenua (naive), asumimos que Epicollect la entregó en UTC y la localizamos
                        if df[col].dt.tz is None:
                            df[col] = df[col].dt.tz_localize('UTC')

                        # Convertimos a la zona horaria de Colombia
                        df[col] = df[col].dt.tz_convert('America/Bogota')

                        # Quitamos la zona horaria para que Excel y Pandas no tengan conflictos luego
                        df[col] = df[col].dt.tz_localize(None)
                    except Exception as e:
                        logger.warning(f"No se pudo ajustar la zona horaria de '{col}': {e}")
        return df

    def _filtrar_por_fecha(self, df: pd.DataFrame, f_ini: str, f_fin: str) -> pd.DataFrame:
        """Filtra el DataFrame usando la columna created_at según el rango dado."""
        if not f_ini and not f_fin:
            return df

        col_fecha = next((c for c in df.columns if 'created_at' in str(c).lower()), None)
        if not col_fecha:
            logger.warning("⚠️ No se encontró la columna 'created_at' para filtrar. Se exportará todo.")
            return df

        # Las fechas ya estan en hora Colombia gracias a _convertir_zona_horaria_colombia
        fechas_dt = pd.to_datetime(df[col_fecha], errors='coerce')
        mascara = pd.Series(True, index=df.index)

        if f_ini:
            mascara &= (fechas_dt >= pd.to_datetime(f_ini))
        if f_fin:
            # Sumamos casi 1 día para incluir todo el día final (hasta las 23:59:59)
            limite_fin = pd.to_datetime(f_fin) + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
            mascara &= (fechas_dt <= limite_fin)

        df_filtrado = df[mascara].copy()
        logger.info(
            f"✅ Filtro aplicado: {len(df_filtrado)} registros encontrados en el rango de fechas (Hora Colombia).")
        return df_filtrado

    def _formatear_fechas(self, df: pd.DataFrame) -> pd.DataFrame:
        """Detecta columnas de fecha y las formatea estrictamente a DD/MM/AAAA para el Excel."""
        claves_fecha = ['fecha', 'created_at', 'uploaded_at']

        for col in df.columns:
            if any(clave in str(col).lower() for clave in claves_fecha):
                df[col] = pd.to_datetime(df[col], errors='coerce')
                df[col] = df[col].dt.strftime('%d/%m/%Y')

        return df

    def cargar_json_preguntas(self):
        directorio_actual = os.path.dirname(os.path.abspath(__file__))
        ruta_json = os.path.join(directorio_actual, "formulario_vacunacion.json")

        if not os.path.exists(ruta_json):
            logger.warning(f"No se encontro el archivo '{ruta_json}'.")
            return

        logger.info("Leyendo archivo JSON para restaurar nombres de columnas...")
        try:
            with open(ruta_json, 'r', encoding='utf-8') as f:
                data = json.load(f)

            def extraer_preguntas(elementos):
                for el in elementos:
                    if el.get('type') not in ['readme', 'group']:
                        q_sucia = el.get('question', '').strip()
                        q_limpia = re.sub(r'<[^>]+>', '', q_sucia).strip()
                        if q_limpia:
                            self.preguntas_oficiales[q_limpia] = q_limpia

                    if 'group' in el and isinstance(el['group'], list):
                        extraer_preguntas(el['group'])

            extraer_preguntas(data['data']['form']['inputs'])
            logger.info(f"Se extrajeron {len(self.preguntas_oficiales)} preguntas originales del JSON.")
        except Exception as e:
            logger.error(f"Error procesando el JSON: {e}")

    def _limpiar_texto(self, texto: str) -> str:
        texto = str(texto).lower().replace('_', ' ')
        return unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')

    def encontrar_mejor_coincidencia(self, col_db: str) -> str:
        col_db_normalizada = str(col_db).strip().lower()

        if col_db_normalizada in self.mapeo_exacto:
            return self.mapeo_exacto[col_db_normalizada]

        col_sin_prefijo = re.sub(r'^[\d_]+', '', str(col_db))
        col_busqueda = self._limpiar_texto(col_sin_prefijo)

        mejor_pregunta = str(col_db)
        mejor_ratio = 0.0

        for preg_original in self.preguntas_oficiales.keys():
            preg_comparacion = self._limpiar_texto(preg_original)
            longitud = len(col_busqueda)
            ratio = SequenceMatcher(None, col_busqueda, preg_comparacion[:longitud]).ratio()

            if ratio > mejor_ratio:
                mejor_ratio = ratio
                mejor_pregunta = preg_original

        if mejor_ratio > 0.75:
            return mejor_pregunta
        else:
            return col_sin_prefijo.replace('_', ' ').title()

    def preparar_hoja(self, df_hoja: pd.DataFrame) -> pd.DataFrame:
        df_hoja = df_hoja.replace([r'^\s*$', 'None', 'nan', 'NaN', 'NULL', 'null'], pd.NA, regex=True)
        df_hoja = df_hoja.dropna(axis=1, how='all')

        nuevos_nombres = []
        vistos = {}

        for col in df_hoja.columns:
            nuevo_nombre = self.encontrar_mejor_coincidencia(col)

            if nuevo_nombre in vistos:
                vistos[nuevo_nombre] += 1
                nuevo_nombre = f"{nuevo_nombre} ({vistos[nuevo_nombre]})"
            else:
                vistos[nuevo_nombre] = 0

            nuevos_nombres.append(nuevo_nombre)

        df_hoja.columns = nuevos_nombres
        return df_hoja

    def _reportar_consola(self, df_limpio: pd.DataFrame, nombre_hoja: str):
        total_registros = len(df_limpio)
        logger.info(f"📊 [RESUMEN] Hoja '{nombre_hoja}': {total_registros} registros en total.")

        if total_registros == 0:
            return

        vacunas_keywords = {
            'Fiebre Amarilla': ['fiebre amarilla', 'amarilla'],
            'Influenza': ['influenza', 'cepa'],
            'Hepatitis A': ['hepatitis a', 'hep a'],
            'Hepatitis B': ['hepatitis b', 'hep b'],
            'VPH': ['vph', 'papiloma'],
            'COVID-19': ['covid', 'sars', 'coronavirus'],
            'Neumococo': ['neumococo', 'neumococica'],
            'Rotavirus': ['rotavirus'],
            'Polio': ['polio', 'vop', 'vip'],
            'Pentavalente': ['pentavalente', 'penta'],
            'Hexavalente': ['hexavalente', 'hexa'],
            'DPT': ['dpt'],
            'BCG': ['bcg', 'tuberculosis'],
            'Triple Viral (SRP)': ['triple viral', 'srp', 'sarampion', 'rubeola', 'paperas'],
            'Varicela': ['varicela'],
            'Toxoide Tetánico/Diftérico (Td)': ['toxoide', 'tetano', 'difteria', 'td'],
            'Rabia': ['rabia']
        }

        conteo_vacunas = Counter()
        cols_a_evaluar = [
            c for c in df_limpio.columns
            if 'motivo' not in str(c).lower()
               and 'no aplic' not in str(c).lower()
               and 'pendient' not in str(c).lower()
               and 'proxima' not in str(c).lower()
               and 'próxima' not in str(c).lower()
        ]

        for index, row in df_limpio[cols_a_evaluar].iterrows():
            vacunas_persona = set()

            for col in cols_a_evaluar:
                val = row[col]
                if pd.isna(val):
                    continue

                val_str = str(val).lower().strip()
                col_lower = str(col).lower()

                if val_str in ['none', 'nan', 'null', '2. no', 'no', '0', 'falso', 'false']:
                    continue

                for vac_name, keys in vacunas_keywords.items():
                    if any(k in val_str for k in keys):
                        vacunas_persona.add(vac_name)

                es_fecha = bool(re.search(r'\d{2,4}[-/]\d{2}[-/]\d{2,4}', val_str))
                es_si = ('1. si' in val_str or val_str == 'si' or val_str == 'verdadero' or val_str == 'true')

                if es_fecha or es_si:
                    for vac_name, keys in vacunas_keywords.items():
                        if any(k in col_lower for k in keys):
                            vacunas_persona.add(vac_name)

            for v in vacunas_persona:
                conteo_vacunas[v] += 1

        if conteo_vacunas:
            logger.info(f"   💉 Desglose de vacunas identificadas en '{nombre_hoja}':")
            for vac, cant in conteo_vacunas.most_common():
                logger.info(f"      ➤ {vac}: {cant} paciente(s)")
        else:
            logger.info(f"   ⚠️ No se detectaron vacunas aplicadas explícitamente en '{nombre_hoja}'.")

        logger.info("-" * 60)

    def ejecutar_proceso(self, f_ini="", f_fin=""):
        self.cargar_json_preguntas()
        df_principal = self.extraer_tabla()

        if df_principal.empty:
            logger.warning("No se detectaron datos en la tabla de vacunacion.")
            return

        logger.info(f"🌍 TOTAL DE REGISTROS EN LA BD SIN FILTRAR: {len(df_principal)}")
        logger.info("=" * 60)

        # 1. AJUSTAR ZONA HORARIA A COLOMBIA ANTES DE CUALQUIER FILTRO
        logger.info("Ajustando zona horaria de UTC (Servidor) a America/Bogota (Colombia)...")
        df_principal = self._convertir_zona_horaria_colombia(df_principal)

        # 2. Aplicamos el filtro de fechas usando las fechas ya ajustadas a Colombia
        df_principal = self._filtrar_por_fecha(df_principal, f_ini, f_fin)

        if df_principal.empty:
            logger.warning("❌ No hay datos en el rango de fechas seleccionado. Cancelando reporte.")
            return

        # 3. Formateamos las fechas de la data filtrada para el Excel (DD/MM/AAAA)
        logger.info("Formateando campos de fecha a DD/MM/AAAA...")
        df_principal = self._formatear_fechas(df_principal)

        directorio_actual = os.path.dirname(os.path.abspath(__file__))

        sufijo = f"_{f_ini}_a_{f_fin}" if (f_ini or f_fin) else "_Historico"
        ruta_salida = os.path.join(directorio_actual, f"Reporte_Vacunacion{sufijo}.xlsx")

        if os.path.exists(ruta_salida):
            try:
                os.remove(ruta_salida)
            except Exception as e:
                logger.warning(f"No se pudo reemplazar el archivo previo (¿Abierto en Excel?). Error: {e}")

        logger.info("Separando poblaciones, limpiando columnas vacias y generando reportes...\n")

        col_tipo_bd = next((c for c in df_principal.columns if "tipo_de_vacunaci" in str(c).lower()), None)

        with pd.ExcelWriter(ruta_salida, engine='openpyxl') as escritor:
            if col_tipo_bd:
                df_rn = df_principal[df_principal[col_tipo_bd] == 'Recién Nacidos'].copy()
                df_nn = df_principal[df_principal[col_tipo_bd] == 'Niños y Niñas'].copy()
                df_ad = df_principal[df_principal[col_tipo_bd] == 'Adultos'].copy()
                df_otros = df_principal[
                    ~df_principal[col_tipo_bd].isin(['Recién Nacidos', 'Niños y Niñas', 'Adultos'])].copy()

                if not df_rn.empty:
                    df_rn_limpio = self.preparar_hoja(df_rn)
                    df_rn_limpio.to_excel(escritor, sheet_name='Recién Nacidos', index=False)
                    self._reportar_consola(df_rn_limpio, 'Recién Nacidos')

                if not df_nn.empty:
                    df_nn_limpio = self.preparar_hoja(df_nn)
                    df_nn_limpio.to_excel(escritor, sheet_name='Niños y Niñas', index=False)
                    self._reportar_consola(df_nn_limpio, 'Niños y Niñas')

                if not df_ad.empty:
                    df_ad_limpio = self.preparar_hoja(df_ad)
                    df_ad_limpio.to_excel(escritor, sheet_name='Adultos', index=False)
                    self._reportar_consola(df_ad_limpio, 'Adultos')

                if not df_otros.empty:
                    df_otros_limpio = self.preparar_hoja(df_otros)
                    df_otros_limpio.to_excel(escritor, sheet_name='Sin Clasificar', index=False)
                    self._reportar_consola(df_otros_limpio, 'Sin Clasificar')
            else:
                logger.warning("No se hallo la columna 'Tipo de Vacunación'. Se exportara todo en una hoja.")
                df_limpio = self.preparar_hoja(df_principal)
                df_limpio.to_excel(escritor, sheet_name='Toda la Poblacion', index=False)
                self._reportar_consola(df_limpio, 'Toda la Poblacion')

        logger.info(f"✅ Reporte impecable generado exitosamente. Ruta: {ruta_salida}")


def main():
    print("=" * 60)
    print(" 💉 GENERADOR DE REPORTES DE VACUNACIÓN APS 2026")
    print("=" * 60)
    print("\n📅 FILTRO DE FECHAS (Opcional)")
    print("Formatos aceptados: AAAA-MM-DD (Ejemplo: 2026-05-01)")
    print("Si dejas el espacio en blanco y presionas Enter, traerá todo el historial.\n")

    f_ini = input("➤ Ingresa la fecha de INICIO: ").strip()
    f_fin = input("➤ Ingresa la fecha de FIN: ").strip()
    print("\n" + "=" * 60 + "\n")

    try:
        motor_excel = GeneradorExcelVacunacionBD()
        motor_excel.ejecutar_proceso(f_ini, f_fin)
    except Exception as error:
        logger.critical(f"El proceso fallo: {error}", exc_info=True)


if __name__ == "__main__":
    main()