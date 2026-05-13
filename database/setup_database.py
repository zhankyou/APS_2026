# -*- coding: utf-8 -*-
"""
=============================================================================
SCRIPT PRINCIPAL: Creacion de Base de Datos APS ESE 2026
=============================================================================
Proposito:
    Crea automaticamente la base de datos PostgreSQL y TODAS las tablas
    necesarias para el sistema APS ESE 2026. Incluye un verificador de
    estado para saber si las tablas ya existen y cuantos registros tienen.

Uso:
    python setup_database.py

Requisitos previos:
    1. Tener PostgreSQL instalado y corriendo.
    2. Haber configurado el archivo .env con las variables de conexion.
    3. Haber instalado las dependencias: pip install -r requirements.txt

Tablas que crea:
    - caracterizacion_si_aps_familiar_2026    (Ficha Familiar - Cabeza del hogar)
    - caracterizacion_si_aps_individual_2026  (Integrantes del hogar)
    - desistimiento_aps_2026                  (Familias que desisten del programa)
    - tramites_aps_2026                       (Tramites gestionados en campo)
    - pcf_planes_principal_2026               (Planes de Cuidado Familiar)
    - pcf_psicologia_principal_2026           (Planes de Cuidado Psicologia)
    - pcf_psicologia_seguimientos_2026        (Seguimientos de Psicologia)
    - pcc_principal_2026                      (Plan de Cuidado Comunitario)
    - pcc_integrantes_2026                    (Integrantes del Plan Comunitario)
    - vacunacion_aps_2026                     (Registros de Vacunacion PAI)
=============================================================================
"""

import os
import sys
import logging
from dotenv import load_dotenv

# ─── Intentamos importar sqlalchemy ───────────────────────────────────────────
try:
    from sqlalchemy import create_engine, text, inspect
except ImportError:
    print("\n[ERROR] SQLAlchemy no esta instalado.")
    print("Ejecuta primero: pip install -r requirements.txt\n")
    sys.exit(1)

# ─── Configuracion de Logs ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | [%(levelname)s] | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("Setup_BD_APS")

# ─── Carga del archivo .env ───────────────────────────────────────────────────
load_dotenv()

# =============================================================================
# DEFINICION DE TABLAS (DDL)
# Cada tabla usa TEXT para la mayoria de campos para maxima compatibilidad.
# Las columnas de fecha/numero se castean dinamicamente en el proceso ETL.
# =============================================================================

TABLAS = {

    # ── 1. CARACTERIZACION FAMILIAR (Formulario principal de barrido) ──────────
    "caracterizacion_si_aps_familiar_2026": """
        CREATE TABLE IF NOT EXISTS public.caracterizacion_si_aps_familiar_2026 (
            ec5_uuid                TEXT PRIMARY KEY,
            created_at              TIMESTAMP,
            uploaded_at             TIMESTAMP,
            title                   TEXT,
            lat_georreferenciacion  TEXT,
            long_georreferenciacion TEXT,
            accuracy_georreferenciacion TEXT,
            territorio              TEXT,
            microterritorio         TEXT,
            codigo_hogar            TEXT,
            codigo_familia          TEXT,
            perfil_profesional      TEXT,
            nombre_profesional      TEXT,
            tipo_documento_profesional TEXT,
            numero_documento_profesional TEXT,
            tipo_vivienda           TEXT,
            tenencia_vivienda       TEXT,
            estrato                 TEXT,
            numero_cuartos          TEXT,
            servicios_publicos      TEXT,
            fuente_agua             TEXT,
            tratamiento_agua        TEXT,
            disposicion_residuos    TEXT,
            animales_domesticos     TEXT,
            riesgos_ambientales     TEXT,
            observaciones           TEXT,
            nombre_jefe_hogar       TEXT,
            tipo_documento_jefe     TEXT,
            numero_documento_jefe   TEXT,
            sexo_jefe               TEXT,
            fecha_nacimiento_jefe   TEXT,
            edad_jefe               TEXT,
            nivel_educativo_jefe    TEXT,
            ocupacion_jefe          TEXT,
            regimen_afiliacion      TEXT,
            eps_jefe                TEXT,
            discapacidad_jefe       TEXT,
            enfermedad_cronica_jefe TEXT,
            numero_integrantes      TEXT,
            ingresado_si_aps        TEXT,
            observaciones_finales   TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_familiar_territorio
            ON public.caracterizacion_si_aps_familiar_2026 (territorio);
        CREATE INDEX IF NOT EXISTS idx_familiar_codigo_hogar
            ON public.caracterizacion_si_aps_familiar_2026 (codigo_hogar);
        CREATE INDEX IF NOT EXISTS idx_familiar_uploaded
            ON public.caracterizacion_si_aps_familiar_2026 (uploaded_at);
    """,

    # ── 2. CARACTERIZACION INDIVIDUAL (Subformulario por integrante) ───────────
    "caracterizacion_si_aps_individual_2026": """
        CREATE TABLE IF NOT EXISTS public.caracterizacion_si_aps_individual_2026 (
            ec5_branch_uuid         TEXT PRIMARY KEY,
            ec5_uuid                TEXT,
            created_at              TIMESTAMP,
            uploaded_at             TIMESTAMP,
            title                   TEXT,
            primer_nombre           TEXT,
            segundo_nombre          TEXT,
            primer_apellido         TEXT,
            segundo_apellido        TEXT,
            tipo_documento          TEXT,
            numero_documento        TEXT,
            fecha_nacimiento        TEXT,
            edad                    TEXT,
            tipo_edad               TEXT,
            sexo                    TEXT,
            genero                  TEXT,
            orientacion_sexual      TEXT,
            estado_civil            TEXT,
            nivel_educativo         TEXT,
            ocupacion               TEXT,
            regimen_afiliacion      TEXT,
            eps                     TEXT,
            grupo_etnico            TEXT,
            enfoque_diferencial     TEXT,
            discapacidad            TEXT,
            tipo_discapacidad       TEXT,
            enfermedad_cronica      TEXT,
            cual_enfermedad         TEXT,
            embarazo                TEXT,
            semanas_gestacion       TEXT,
            fecha_probable_parto    TEXT,
            requiere_atencion_pyp   TEXT,
            requiere_vacunacion     TEXT,
            requiere_tramites       TEXT,
            codigo_hogar            TEXT,
            codigo_familia          TEXT,
            territorio              TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_individual_ec5_uuid
            ON public.caracterizacion_si_aps_individual_2026 (ec5_uuid);
        CREATE INDEX IF NOT EXISTS idx_individual_documento
            ON public.caracterizacion_si_aps_individual_2026 (numero_documento);
        CREATE INDEX IF NOT EXISTS idx_individual_territorio
            ON public.caracterizacion_si_aps_individual_2026 (territorio);
    """,

    # ── 3. DESISTIMIENTO ──────────────────────────────────────────────────────
    "desistimiento_aps_2026": """
        CREATE TABLE IF NOT EXISTS public.desistimiento_aps_2026 (
            ec5_uuid                TEXT PRIMARY KEY,
            created_at              TIMESTAMP,
            uploaded_at             TIMESTAMP,
            title                   TEXT,
            lat_georreferenciacion  TEXT,
            long_georreferenciacion TEXT,
            territorio              TEXT,
            microterritorio         TEXT,
            perfil_profesional      TEXT,
            nombre_profesional      TEXT,
            tipo_documento_profesional TEXT,
            numero_documento_profesional TEXT,
            codigo_hogar            TEXT,
            codigo_familia          TEXT,
            primer_nombre           TEXT,
            segundo_nombre          TEXT,
            primer_apellido         TEXT,
            segundo_apellido        TEXT,
            tipo_documento          TEXT,
            numero_documento        TEXT,
            edad                    TEXT,
            sexo                    TEXT,
            motivo_desistimiento    TEXT,
            otro_motivo             TEXT,
            observaciones           TEXT,
            firma_desistimiento     TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_desistimiento_territorio
            ON public.desistimiento_aps_2026 (territorio);
        CREATE INDEX IF NOT EXISTS idx_desistimiento_uploaded
            ON public.desistimiento_aps_2026 (uploaded_at);
    """,

    # ── 4. TRAMITES ───────────────────────────────────────────────────────────
    "tramites_aps_2026": """
        CREATE TABLE IF NOT EXISTS public.tramites_aps_2026 (
            ec5_uuid                TEXT PRIMARY KEY,
            created_at              TIMESTAMP,
            uploaded_at             TIMESTAMP,
            title                   TEXT,
            lat_georreferenciacion  TEXT,
            long_georreferenciacion TEXT,
            accuracy_georreferenciacion TEXT,
            codigo_hogar            TEXT,
            codigo_familia          TEXT,
            territorio              TEXT,
            microterritorio         TEXT,
            perfil_profesional      TEXT,
            nombre_profesional      TEXT,
            tipo_documento_profesional TEXT,
            numero_documento_profesional TEXT,
            primer_nombre           TEXT,
            segundo_nombre          TEXT,
            primer_apellido         TEXT,
            segundo_apellido        TEXT,
            tipo_documento          TEXT,
            numero_documento        TEXT,
            edad                    TEXT,
            tipo_edad               TEXT,
            sexo                    TEXT,
            numero_celular          TEXT,
            numero_celular_alterno  TEXT,
            direccion_residencia    TEXT,
            eapb                    TEXT,
            requiere_atencion_pyp   TEXT,
            requiere_vacunacion     TEXT,
            requiere_afiliacion     TEXT,
            realizo_resolutividad_afiliacion TEXT,
            requiere_citas_demoradas TEXT,
            realizo_resolutividad_citas TEXT,
            requiere_medicamentos   TEXT,
            realizo_resolutividad_medicamentos TEXT,
            requiere_sisben         TEXT,
            realizo_resolutividad_sisben TEXT,
            requiere_discapacidad   TEXT,
            realizo_resolutividad_discapacidad TEXT,
            requiere_desescolarizado TEXT,
            requiere_colombia_mayor TEXT,
            requiere_devolucion_iva TEXT,
            requiere_renta_ciudadana TEXT,
            observaciones           TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_tramites_territorio
            ON public.tramites_aps_2026 (territorio);
        CREATE INDEX IF NOT EXISTS idx_tramites_documento
            ON public.tramites_aps_2026 (numero_documento);
        CREATE INDEX IF NOT EXISTS idx_tramites_uploaded
            ON public.tramites_aps_2026 (uploaded_at);
    """,

    # ── 5. PLAN DE CUIDADO FAMILIAR (Principal) ───────────────────────────────
    "pcf_planes_principal_2026": """
        CREATE TABLE IF NOT EXISTS public.pcf_planes_principal_2026 (
            ec5_uuid                TEXT PRIMARY KEY,
            created_at              TIMESTAMP,
            uploaded_at             TIMESTAMP,
            title                   TEXT,
            territorio              TEXT,
            microterritorio         TEXT,
            codigo_hogar            TEXT,
            codigo_familia          TEXT,
            perfil_profesional      TEXT,
            nombre_profesional      TEXT,
            tipo_documento_profesional TEXT,
            numero_documento_profesional TEXT,
            primer_nombre           TEXT,
            segundo_nombre          TEXT,
            primer_apellido         TEXT,
            segundo_apellido        TEXT,
            tipo_documento          TEXT,
            numero_documento        TEXT,
            fecha_nacimiento        TEXT,
            edad                    TEXT,
            sexo                    TEXT,
            regimen_afiliacion      TEXT,
            eps                     TEXT,
            diagnostico_cie10       TEXT,
            descripcion_diagnostico TEXT,
            objetivo_plan           TEXT,
            actividades_plan        TEXT,
            fecha_seguimiento       TEXT,
            estado_plan             TEXT,
            observaciones           TEXT,
            firma_paciente          TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_pcf_territorio
            ON public.pcf_planes_principal_2026 (territorio);
        CREATE INDEX IF NOT EXISTS idx_pcf_documento
            ON public.pcf_planes_principal_2026 (numero_documento);
    """,

    # ── 6. PLAN DE CUIDADO PSICOLOGIA (Principal) ─────────────────────────────
    "pcf_psicologia_principal_2026": """
        CREATE TABLE IF NOT EXISTS public.pcf_psicologia_principal_2026 (
            ec5_uuid                TEXT PRIMARY KEY,
            created_at              TIMESTAMP,
            uploaded_at             TIMESTAMP,
            title                   TEXT,
            territorio              TEXT,
            microterritorio         TEXT,
            codigo_hogar            TEXT,
            codigo_familia          TEXT,
            nombre_profesional      TEXT,
            tipo_documento_profesional TEXT,
            numero_documento_profesional TEXT,
            primer_nombre           TEXT,
            segundo_nombre          TEXT,
            primer_apellido         TEXT,
            segundo_apellido        TEXT,
            tipo_documento          TEXT,
            numero_documento        TEXT,
            fecha_nacimiento        TEXT,
            edad                    TEXT,
            sexo                    TEXT,
            regimen_afiliacion      TEXT,
            eps                     TEXT,
            motivo_consulta         TEXT,
            diagnostico_presuntivo  TEXT,
            plan_terapeutico        TEXT,
            numero_sesiones         TEXT,
            estado_proceso          TEXT,
            observaciones           TEXT,
            firma_consentimiento    TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_psico_territorio
            ON public.pcf_psicologia_principal_2026 (territorio);
        CREATE INDEX IF NOT EXISTS idx_psico_documento
            ON public.pcf_psicologia_principal_2026 (numero_documento);
    """,

    # ── 7. PLAN DE CUIDADO PSICOLOGIA (Seguimientos) ─────────────────────────
    "pcf_psicologia_seguimientos_2026": """
        CREATE TABLE IF NOT EXISTS public.pcf_psicologia_seguimientos_2026 (
            ec5_branch_uuid         TEXT PRIMARY KEY,
            ec5_uuid                TEXT,
            created_at              TIMESTAMP,
            uploaded_at             TIMESTAMP,
            fecha_seguimiento       TEXT,
            tipo_sesion             TEXT,
            descripcion_sesion      TEXT,
            avance_objetivos        TEXT,
            proxima_sesion          TEXT,
            observaciones           TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_psico_seg_uuid
            ON public.pcf_psicologia_seguimientos_2026 (ec5_uuid);
    """,

    # ── 8. PLAN DE CUIDADO COMUNITARIO (Principal) ────────────────────────────
    "pcc_principal_2026": """
        CREATE TABLE IF NOT EXISTS public.pcc_principal_2026 (
            ec5_uuid                TEXT PRIMARY KEY,
            created_at              TIMESTAMP,
            uploaded_at             TIMESTAMP,
            title                   TEXT,
            territorio              TEXT,
            microterritorio         TEXT,
            nombre_colectivo        TEXT,
            tipo_colectivo          TEXT,
            nombre_profesional      TEXT,
            tipo_documento_profesional TEXT,
            numero_documento_profesional TEXT,
            fecha_actividad         TEXT,
            lugar_actividad         TEXT,
            tema_principal          TEXT,
            objetivo_actividad      TEXT,
            metodologia             TEXT,
            numero_participantes    TEXT,
            resultados_esperados    TEXT,
            resultados_obtenidos    TEXT,
            compromisos             TEXT,
            fecha_seguimiento       TEXT,
            observaciones           TEXT,
            evidencia_fotografica   TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_pcc_territorio
            ON public.pcc_principal_2026 (territorio);
        CREATE INDEX IF NOT EXISTS idx_pcc_uploaded
            ON public.pcc_principal_2026 (uploaded_at);
    """,

    # ── 9. PLAN DE CUIDADO COMUNITARIO (Integrantes) ──────────────────────────
    "pcc_integrantes_2026": """
        CREATE TABLE IF NOT EXISTS public.pcc_integrantes_2026 (
            ec5_branch_uuid         TEXT PRIMARY KEY,
            ec5_uuid                TEXT,
            created_at              TIMESTAMP,
            uploaded_at             TIMESTAMP,
            primer_nombre           TEXT,
            segundo_nombre          TEXT,
            primer_apellido         TEXT,
            segundo_apellido        TEXT,
            tipo_documento          TEXT,
            numero_documento        TEXT,
            edad                    TEXT,
            sexo                    TEXT,
            regimen_afiliacion      TEXT,
            eps                     TEXT,
            telefono                TEXT,
            firma_asistencia        TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_pcc_int_uuid
            ON public.pcc_integrantes_2026 (ec5_uuid);
        CREATE INDEX IF NOT EXISTS idx_pcc_int_documento
            ON public.pcc_integrantes_2026 (numero_documento);
    """,

    # ── 10. VACUNACION PAI ────────────────────────────────────────────────────
    "vacunacion_aps_2026": """
        CREATE TABLE IF NOT EXISTS public.vacunacion_aps_2026 (
            ec5_uuid                TEXT PRIMARY KEY,
            created_at              TIMESTAMP,
            uploaded_at             TIMESTAMP,
            title                   TEXT,
            fecha_vacunacion        TIMESTAMP,
            lugar_vacunacion        TEXT,
            tipo_vacunacion         TEXT,
            nombre_vacunador        TEXT,
            equipo_vacunador        TEXT,
            tipo_identificacion_madre TEXT,
            numero_identificacion_madre TEXT,
            primer_nombre_madre     TEXT,
            segundo_nombre_madre    TEXT,
            primer_apellido_madre   TEXT,
            segundo_apellido_madre  TEXT,
            regimen_afiliacion_madre TEXT,
            aseguradora_madre       TEXT,
            tipo_identificacion     TEXT,
            numero_identificacion   TEXT,
            fecha_nacimiento        TEXT,
            sexo                    TEXT,
            area_residencia         TEXT,
            grupo_etnico            TEXT,
            enfoque_diferencial     TEXT,
            condicion_usuario       TEXT,
            semanas_gestacion       TEXT,
            fecha_probable_parto    TEXT,
            dpto_residencia         TEXT,
            municipio_residencia    TEXT,
            barrio_vereda           TEXT,
            direccion_residencia    TEXT,
            telefono                TEXT,
            correo_electronico      TEXT,
            vacuna_bcg              TEXT,
            dosis_bcg               TEXT,
            lote_bcg                TEXT,
            vacuna_hepatitis_b      TEXT,
            dosis_hepatitis_b       TEXT,
            lote_hepatitis_b        TEXT,
            vacuna_hexavalente      TEXT,
            dosis_hexavalente       TEXT,
            lote_hexavalente        TEXT,
            vacuna_pentavalente     TEXT,
            dosis_pentavalente      TEXT,
            vacuna_polio_vpi        TEXT,
            dosis_polio_vpi         TEXT,
            vacuna_rotavirus        TEXT,
            dosis_rotavirus         TEXT,
            vacuna_neumococo        TEXT,
            dosis_neumococo         TEXT,
            vacuna_triple_viral     TEXT,
            dosis_triple_viral      TEXT,
            vacuna_hepatitis_a      TEXT,
            dosis_hepatitis_a       TEXT,
            vacuna_varicela         TEXT,
            dosis_varicela          TEXT,
            vacuna_fiebre_amarilla  TEXT,
            dosis_fiebre_amarilla   TEXT,
            vacuna_vph              TEXT,
            dosis_vph               TEXT,
            vacuna_influenza        TEXT,
            dosis_influenza         TEXT,
            vacuna_td               TEXT,
            dosis_td                TEXT,
            vacuna_tdap             TEXT,
            dosis_tdap              TEXT,
            vacuna_dengue           TEXT,
            dosis_dengue            TEXT,
            vacuna_sr               TEXT,
            dosis_sr                TEXT,
            vacuna_meningococo      TEXT,
            dosis_meningococo       TEXT,
            vacuna_vsr              TEXT,
            dosis_vsr               TEXT,
            vacuna_antirrabica      TEXT,
            dosis_antirrabica       TEXT,
            vacuna_monkeypox        TEXT,
            dosis_monkeypox         TEXT,
            esquema_completo        TEXT,
            ips_vacunadora          TEXT,
            ingresado_paiweb        TEXT,
            observaciones           TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_vacunacion_uploaded
            ON public.vacunacion_aps_2026 (uploaded_at);
        CREATE INDEX IF NOT EXISTS idx_vacunacion_vacunador
            ON public.vacunacion_aps_2026 (nombre_vacunador);
        CREATE INDEX IF NOT EXISTS idx_vacunacion_documento
            ON public.vacunacion_aps_2026 (numero_identificacion);
    """
}


# =============================================================================
# FUNCIONES PRINCIPALES
# =============================================================================

def obtener_engine():
    """Crea y retorna el motor de conexion a PostgreSQL usando variables del .env"""
    db_user     = os.getenv("DB_USER")
    db_password = os.getenv("DB_PASSWORD")
    db_host     = os.getenv("DB_HOST", "localhost")
    db_port     = os.getenv("DB_PORT", "5432")
    db_name     = os.getenv("DB_NAME")

    if not all([db_user, db_password, db_name]):
        logger.error("Faltan variables de BD en el .env (DB_USER, DB_PASSWORD, DB_NAME).")
        logger.error("Configura primero el archivo .env. Ver .env.example como guia.")
        sys.exit(1)

    cadena = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
    try:
        engine = create_engine(cadena, connect_args={"connect_timeout": 10})
        # Prueba la conexion
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(f"Conexion exitosa a PostgreSQL: {db_host}:{db_port}/{db_name}")
        return engine
    except Exception as e:
        logger.error(f"No se pudo conectar a PostgreSQL: {e}")
        logger.error("\nVerifica que:")
        logger.error("  1. PostgreSQL este corriendo.")
        logger.error("  2. Las credenciales en .env sean correctas.")
        logger.error("  3. La base de datos exista (puede crearla con: createdb <nombre_bd>).")
        sys.exit(1)


def crear_todas_las_tablas(engine):
    """Ejecuta el DDL de cada tabla en la base de datos."""
    logger.info("=" * 60)
    logger.info("  INICIANDO CREACION DE TABLAS - APS ESE 2026")
    logger.info("=" * 60)

    tablas_creadas = 0
    tablas_existentes = 0

    inspector = inspect(engine)
    tablas_en_bd = inspector.get_table_names(schema="public")

    for nombre_tabla, ddl in TABLAS.items():
        if nombre_tabla in tablas_en_bd:
            logger.info(f"  [OK - YA EXISTE] {nombre_tabla}")
            tablas_existentes += 1
        else:
            try:
                with engine.begin() as conn:
                    conn.execute(text(ddl))
                logger.info(f"  [CREADA]         {nombre_tabla}")
                tablas_creadas += 1
            except Exception as e:
                logger.error(f"  [ERROR]          {nombre_tabla}: {e}")

    logger.info("=" * 60)
    logger.info(f"  Resumen:")
    logger.info(f"    - Tablas nuevas creadas : {tablas_creadas}")
    logger.info(f"    - Tablas ya existentes  : {tablas_existentes}")
    logger.info(f"    - Total tablas          : {len(TABLAS)}")
    logger.info("=" * 60)


def verificar_estado_tablas(engine):
    """Muestra cuantos registros tiene cada tabla."""
    logger.info("\n" + "=" * 60)
    logger.info("  ESTADO ACTUAL DE LA BASE DE DATOS")
    logger.info("=" * 60)

    with engine.connect() as conn:
        for nombre_tabla in TABLAS.keys():
            try:
                resultado = conn.execute(
                    text(f"SELECT COUNT(*) FROM public.{nombre_tabla}")
                )
                total = resultado.scalar()
                logger.info(f"  {nombre_tabla:<55} {total:>8,} registros")
            except Exception:
                logger.warning(f"  {nombre_tabla:<55} [tabla no encontrada]")

    logger.info("=" * 60)


def main():
    logger.info("\n SISTEMA APS ESE 2026 - CONFIGURACION DE BASE DE DATOS\n")

    # 1. Conectar a PostgreSQL
    engine = obtener_engine()

    # 2. Crear todas las tablas
    crear_todas_las_tablas(engine)

    # 3. Mostrar estado de la BD
    verificar_estado_tablas(engine)

    logger.info("\n Base de datos lista. Ahora puedes ejecutar el orquestador principal:")
    logger.info("   python \"APS ESE 2026/Principal.py\"\n")


if __name__ == "__main__":
    main()