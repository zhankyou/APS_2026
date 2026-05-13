# 🏥 Sistema APS ESE 2026 — Código Abierto

> **Atención Primaria en Salud · ESE · Colombia**
> Sistema local de sincronización, almacenamiento y reporte de datos APS a partir de formularios Epicollect5 y PostgreSQL. Diseñado para funcionar **con o sin** acceso a la plataforma SI-APS del Ministerio de Salud.

---

## 📋 Tabla de Contenidos

1. [¿Qué hace este sistema?](#1-qué-hace-este-sistema)
2. [Arquitectura y estructura de carpetas](#2-arquitectura-y-estructura-de-carpetas)
3. [¿Qué formularios maneja?](#3-qué-formularios-maneja)
4. [Requisitos del sistema](#4-requisitos-del-sistema)
5. [Instalación de Python 3.11](#5-instalación-de-python-311)
6. [Instalación de PostgreSQL](#6-instalación-de-postgresql)
7. [Clonar el repositorio](#7-clonar-el-repositorio)
8. [Instalar dependencias del proyecto](#8-instalar-dependencias-del-proyecto)
9. [Configurar el archivo `.env`](#9-configurar-el-archivo-env)
10. [Cómo obtener las claves API de Epicollect5](#10-cómo-obtener-las-claves-api-de-epicollect5)
11. [Crear la base de datos y las tablas](#11-crear-la-base-de-datos-y-las-tablas)
12. [Ejecutar la sincronización principal](#12-ejecutar-la-sincronización-principal)
13. [Generar reportes en Excel](#13-generar-reportes-en-excel)
14. [Descargar evidencias fotográficas](#14-descargar-evidencias-fotográficas)
15. [Proceso de contingencia (SI-APS caído)](#15-proceso-de-contingencia-si-aps-caído)
16. [Solución de errores comunes](#16-solución-de-errores-comunes)
17. [Preguntas frecuentes](#17-preguntas-frecuentes)
18. [Contribuir al proyecto](#18-contribuir-al-proyecto)
19. [Licencia](#19-licencia)

---

## 1. ¿Qué hace este sistema?

Este proyecto automatiza el flujo completo de datos del programa **Atención Primaria en Salud (APS)** de una **ESE (Empresa Social del Estado)** en Colombia. Resuelve tres problemas reales del trabajo de campo:

| Problema | Solución |
|---|---|
| Los datos de campo quedan en Epicollect5 sin un lugar centralizado | Descarga y sincroniza todo a una base de datos PostgreSQL local |
| SI-APS (plataforma del Ministerio) falla o no está disponible | El sistema funciona completamente offline con los datos locales |
| Generar reportes manuales en Excel toma horas | Un solo comando genera el consolidado completo con todos los módulos |

### Flujo completo del sistema

```
  [Equipos de campo]
        │
        ▼ llenan formularios en el celular
  [Epicollect5 App / Web]
        │
        ▼ API OAuth2 (este sistema descarga automáticamente)
  [PostgreSQL LOCAL]
        │
        ├──▶ Reportes Excel  (reports/main_reports.py)
        ├──▶ Evidencias PDF  (reports/evidences/)
        └──▶ Contingencia SI-APS  (datos siempre disponibles localmente)
```

---

## 2. Arquitectura y estructura de carpetas

```
APS_2026/
│
├── app/
│   ├── main.py              ← 🚀 PUNTO DE ENTRADA PRINCIPAL (sincroniza todo)
│   └── epicollet_api.py     ← Módulo de conexión a la API de Epicollect5
│
├── database/
│   └── setup_database.py    ← Crea la BD y todas las tablas en PostgreSQL
│
├── forms/
│   ├── caracterizacion-si-aps-2026__...json   ← Formulario de caracterización
│   ├── desistimiento-aps__...json             ← Formulario de desistimiento
│   ├── aps-pcf-2026__...json                  ← Plan de Cuidado Familiar
│   ├── aps-pcc-2026__...json                  ← Plan de Cuidado Comunitario
│   ├── aps-tramites-2026__...json             ← Trámites APS
│   └── aps-vacunacion-regular__...json        ← Vacunación PAI
│
├── reports/
│   ├── main_reports.py      ← Genera el consolidado Excel completo
│   ├── diccionario/
│   │   └── mapeos_aps_2026.json  ← Traduce nombres técnicos a nombres legibles
│   ├── modules/             ← Un módulo Excel por cada tipo de formulario
│   │   ├── caracterizacion.py
│   │   ├── tramites.py
│   │   ├── PCF.py
│   │   ├── PCF_Psicologia.py
│   │   ├── PCC.py
│   │   ├── desistimiento.py
│   │   └── vacunacion.py
│   └── evidences/
│       └── evidencias_tramites.py  ← Descarga fotos y genera PDFs
│
├── install.py               ← Instalador automático (primera vez)
├── requirements.txt         ← Dependencias Python
└── .env                     ← ⚠️ TUS CREDENCIALES (debes crearlo tú)
```

---

## 3. ¿Qué formularios maneja?

| Formulario | Tabla en BD | Descripción |
|---|---|---|
| Caracterización Familiar | `caracterizacion_si_aps_familiar_2026` | Ficha principal del hogar (barrido) |
| Caracterización Individual | `caracterizacion_si_aps_individual_2026` | Datos de cada integrante del hogar |
| Plan de Cuidado Familiar (PCF) | `pcf_planes_principal_2026` | Planes de cuidado por familia |
| PCF – Integrantes | `pcf_planes_integrantes_2026` | Subformulario de integrantes del PCF |
| Psicología – Principal | `pcf_psicologia_principal_2026` | Atenciones psicológicas |
| Psicología – Seguimientos | `pcf_psicologia_seguimientos_2026` | Seguimiento de cada sesión |
| Plan de Cuidado Comunitario (PCC) | `pcc_principal_2026` | Actividades colectivas |
| PCC – Integrantes | `pcc_integrantes_2026` | Asistentes a la actividad comunitaria |
| Trámites APS | `tramites_aps_2026` | Gestiones (afiliación, SISBEN, medicamentos, etc.) |
| Desistimiento | `desistimiento_aps_2026` | Familias que se retiran del programa |
| Vacunación PAI | `vacunacion_aps_2026` | Registro de vacunas aplicadas |

---

## 4. Requisitos del sistema

| Componente | Versión recomendada | Obligatorio |
|---|---|---|
| Python | **3.11** | ✅ Sí |
| PostgreSQL | **16** o superior | ✅ Sí |
| Git | Cualquier versión reciente | ✅ Sí |
| Conexión a internet | Para sincronizar desde Epicollect5 | ✅ (solo al sincronizar) |
| Cuenta en Epicollect5 | five.epicollect.net | ✅ Sí |

> ⚠️ **Importante:** Una vez sincronizados los datos, el sistema funciona completamente sin internet. Los reportes y evidencias se generan desde la base de datos local.

---

## 5. Instalación de Python 3.11

### 🪟 Windows

**Paso 1 — Descargar el instalador**

1. Abre tu navegador y ve a: **https://www.python.org/downloads/release/python-3119/**
2. Baja hasta la sección **"Files"** al final de la página.
3. Descarga **`Windows installer (64-bit)`** → `python-3.11.9-amd64.exe`

**Paso 2 — Instalar**

1. Ejecuta el archivo descargado como **Administrador** (clic derecho → *Ejecutar como administrador*).
2. **MUY IMPORTANTE:** Antes de hacer clic en *Install Now*, marca la casilla:
   ```
   ☑ Add Python 3.11 to PATH
   ```
   Si no marcas esto, Python no funcionará desde la consola.
3. Haz clic en **Install Now**.
4. Espera a que finalice y haz clic en **Close**.

**Paso 3 — Verificar la instalación**

Abre el **Símbolo del sistema** (busca `cmd` en el menú de inicio) y escribe:

```cmd
python --version
```

Debe mostrar:
```
Python 3.11.9
```

Si muestra una versión diferente o un error, reinicia el equipo e intenta de nuevo.

---

### 🍎 macOS

**Paso 1 — Descargar el instalador**

1. Ve a: **https://www.python.org/downloads/release/python-3119/**
2. Descarga **`macOS 64-bit universal2 installer`** → `python-3.11.9-macos11.pkg`

**Paso 2 — Instalar**

1. Abre el archivo `.pkg` descargado.
2. Sigue el asistente de instalación (Continuar → Instalar).
3. Al finalizar, busca la carpeta **Python 3.11** en tus Aplicaciones y ejecuta `Install Certificates.command` haciendo doble clic en él.

**Paso 3 — Verificar**

Abre **Terminal** y escribe:

```bash
python3.11 --version
```

---

### 🐧 Linux (Ubuntu / Debian)

```bash
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev
python3.11 --version
```

---

## 6. Instalación de PostgreSQL

### 🪟 Windows

**Paso 1 — Descargar**

1. Ve a: **https://www.enterprisedb.com/downloads/postgres-postgresql-downloads**
2. En la fila de la versión **16**, columna **Windows x86-64**, haz clic en **Download**.

**Paso 2 — Instalar**

1. Ejecuta el instalador como **Administrador**.
2. Sigue el asistente:
   - **Installation Directory:** deja el predeterminado.
   - **Components:** asegúrate que estén marcados:
     - ☑ PostgreSQL Server
     - ☑ pgAdmin 4
     - ☑ Command Line Tools
   - **Data Directory:** deja el predeterminado.
   - **Password:** Escribe una contraseña **y anótala**. La necesitarás para el archivo `.env`.
     > Ejemplo: `MiClave2026!`
   - **Port:** deja `5432` (no cambiar).
   - **Locale:** deja el predeterminado.
3. Haz clic en **Next** y luego **Finish**.
4. Cuando pregunte si quieres abrir Stack Builder, puedes hacer clic en **Cancel**.

**Paso 3 — Crear la base de datos del proyecto**

1. Busca **pgAdmin 4** en el menú de inicio y ábrelo.
2. Se abrirá en el navegador. Ingresa la contraseña que configuraste.
3. En el panel izquierdo, expande: **Servers → PostgreSQL 16 → Databases**.
4. Clic derecho en **Databases** → **Create → Database...**
5. En el campo **Database**, escribe: `aps_2026`
6. Haz clic en **Save**.

Alternativamente, desde el **Símbolo del sistema**:
```cmd
"C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -c "CREATE DATABASE aps_2026;"
```
Te pedirá la contraseña del usuario `postgres`.

---

### 🍎 macOS

```bash
# Instalar con Homebrew (si no tienes Homebrew: https://brew.sh)
brew install postgresql@16
brew services start postgresql@16

# Crear la base de datos
createdb aps_2026
```

---

### 🐧 Linux (Ubuntu / Debian)

```bash
sudo apt update
sudo apt install -y postgresql postgresql-contrib

# Iniciar el servicio
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Configurar contraseña del usuario postgres
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'MiClave2026!';"

# Crear la base de datos
sudo -u postgres createdb aps_2026
```

---

### Verificar que PostgreSQL funciona

Desde la consola (reemplaza `tu_contraseña` por la que configuraste):

```bash
# Windows
"C:\Program Files\PostgreSQL\16\bin\psql.exe" -U postgres -d aps_2026 -c "SELECT version();"

# macOS / Linux
psql -U postgres -d aps_2026 -c "SELECT version();"
```

Debe mostrar algo como:
```
PostgreSQL 16.x on x86_64-pc-...
```

---

## 7. Clonar el repositorio

Abre la consola/terminal y navega a la carpeta donde quieres instalar el proyecto:

```bash
# Ejemplo: ir al escritorio
cd ~/Desktop          # macOS / Linux
cd %USERPROFILE%\Desktop  # Windows CMD

# Clonar el repositorio
git clone https://github.com/zhankyou/APS_2026.git

# Entrar a la carpeta
cd APS_2026
```

> 💡 Si no tienes Git instalado: descárgalo en **https://git-scm.com/downloads** e instálalo con las opciones predeterminadas.

---

## 8. Instalar dependencias del proyecto

Desde la carpeta `APS_2026`, ejecuta el instalador automático:

```bash
python install.py
```

Este script hace tres cosas automáticamente:
1. **Crea las carpetas** necesarias (`reports/excel`, `reports/evidences`, etc.)
2. **Genera el archivo `.env`** con plantilla vacía (si no existe).
3. **Instala todas las librerías** de Python desde `requirements.txt`.

Las librerías que se instalan son:

| Librería | Versión | Uso |
|---|---|---|
| `pandas` | 2.2.1 | Procesamiento de datos en memoria |
| `requests` | 2.31.0 | Llamadas HTTP a la API de Epicollect5 |
| `SQLAlchemy` | 2.0.29 | Conexión y operaciones con PostgreSQL |
| `psycopg2-binary` | 2.9.9 | Driver de PostgreSQL para Python |
| `python-dotenv` | 1.0.1 | Lectura del archivo `.env` |
| `openpyxl` | 3.1.2 | Generación de archivos Excel |
| `Pillow` | 10.3.0 | Procesamiento de imágenes para PDFs |

> Si el instalador falla, instala manualmente:
> ```bash
> pip install -r requirements.txt
> ```

---

## 9. Configurar el archivo `.env`

El archivo `.env` es el **corazón de la configuración**. Contiene todas las contraseñas y claves del sistema. Después de ejecutar `install.py`, encontrarás un archivo `.env` en la raíz del proyecto con valores vacíos.

Ábrelo con cualquier editor de texto (Bloc de notas, VS Code, Notepad++).

### Contenido completo del archivo `.env`

```dotenv
# ============================================================
# CONFIGURACIÓN DE BASE DE DATOS (POSTGRESQL)
# ============================================================
DB_USER=postgres
DB_PASSWORD=MiClave2026!
DB_HOST=localhost
DB_PORT=5432
DB_NAME=aps_2026

# ============================================================
# CREDENCIALES GLOBALES DE EPICOLLECT5
# (Úsalas si todos tus formularios están bajo una sola cuenta)
# ============================================================
CLIENT_ID=PEGAR_AQUI_TU_CLIENT_ID
CLIENT_SECRET=PEGAR_AQUI_TU_CLIENT_SECRET

# ============================================================
# CARACTERIZACIÓN SI-APS 2026
# ============================================================
API_PROJECT_SLUG_2026=caracterizacion-si-aps-2026
API_FORM_REF_2026=90b389fd24684ce49435089f2655259b_68af3127d5893
API_BRANCH_REF_2026=90b389fd24684ce49435089f2655259b_68af3127d5893_65d3666739f12

# ============================================================
# DESISTIMIENTO APS 2026
# ============================================================
API_PROJECT_SLUG_DESISTIMIENTO_2026=desistimiento-aps
API_FORM_REF_DESISTIMIENTO_2026=b6826db07ab84940b556eabd6845e948_67f1e7981908d

# ============================================================
# TRÁMITES APS 2026
# (Si usan credenciales distintas, completa abajo; si no, dejar vacío)
# ============================================================
API_PROJECT_SLUG_TRAMITES_2026=aps-tramites-2026
API_FORM_REF_TRAMITES_2026=cef31d77db594feca6504a0ce2db8583_67390434a2f7b
TRAMITES_2026_CLIENT_ID=
TRAMITES_2026_CLIENT_SECRET=

# ============================================================
# PLAN DE CUIDADO FAMILIAR (PCF) 2026
# ============================================================
API_PROJECT_SLUG_PCF_2026=aps-pcf-2026
API_FORM_REF_PCF_2026=f1be01a4e3b14b92874d6aaf75fc6ffb_69ac4b860d96c
API_BRANCH_REF_PCF_INTEGRANTES=f1be01a4e3b14b92874d6aaf75fc6ffb_69ac4b860d96c_66f752939db7d
API_FORM_REF_PCF_PSICOLOGIA=PEGAR_AQUI_EL_FORM_REF_DE_PSICOLOGIA
API_BRANCH_REF_PCF_SEGUIMIENTOS=PEGAR_AQUI_EL_BRANCH_REF_DE_SEGUIMIENTOS

# ============================================================
# PLAN DE CUIDADO COMUNITARIO (PCC) 2026
# ============================================================
API_PROJECT_SLUG_PCC_2026=aps-pcc-2026
API_FORM_REF_PCC_2026=946be735ead74d1b928ad7e083a91b82_67293ee17554a
API_BRANCH_REF_PCC_2026=946be735ead74d1b928ad7e083a91b82_67293ee17554a_66f752939db7d

# ============================================================
# VACUNACIÓN APS 2026
# (Si el formulario de vacunación usa credenciales distintas)
# ============================================================
API_PROJECT_SLUG_VACUNACION_2026=aps-vacunacion-regular
API_FORM_REF_VACUNACION_2026=e47229c2c2d94082acf68c6ebccccdf2_68295f748388d
VACUNACION_2026_CLIENT_ID=
VACUNACION_2026_CLIENT_SECRET=

# ============================================================
# CONFIGURACIÓN DE CORREO ELECTRÓNICO (Opcional - para reportes)
# ============================================================
GMAIL_SENDER=tu_correo@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

### Explicación de cada variable

#### Variables de Base de Datos

| Variable | Descripción | Ejemplo |
|---|---|---|
| `DB_USER` | Usuario de PostgreSQL | `postgres` |
| `DB_PASSWORD` | Contraseña del usuario de PostgreSQL | `MiClave2026!` |
| `DB_HOST` | Servidor de la base de datos | `localhost` (en el mismo computador) |
| `DB_PORT` | Puerto de PostgreSQL | `5432` (no cambiar) |
| `DB_NAME` | Nombre de la base de datos que creaste | `aps_2026` |

#### Variables de Epicollect5

| Variable | Descripción |
|---|---|
| `CLIENT_ID` | ID de la aplicación OAuth en Epicollect5 (ver sección 10) |
| `CLIENT_SECRET` | Secreto de la aplicación OAuth (ver sección 10) |
| `API_PROJECT_SLUG_*` | Nombre corto del proyecto en la URL de Epicollect5 |
| `API_FORM_REF_*` | Identificador único del formulario (ver sección 10) |
| `API_BRANCH_REF_*` | Identificador único del subformulario/rama |

---

## 10. Cómo obtener las claves API de Epicollect5

Esta es la parte más importante. Necesitas obtener **CLIENT_ID** y **CLIENT_SECRET** para que el sistema pueda descargar los datos automáticamente.

---

### Paso 1 — Iniciar sesión en Epicollect5

1. Ve a **https://five.epicollect.net**
2. Haz clic en **Login** (arriba a la derecha).
3. Inicia sesión con tu cuenta de Google o correo institucional.

---

### Paso 2 — Ir a tu proyecto

1. Una vez dentro, haz clic en **My Projects** (Mis Proyectos).
2. Busca tu proyecto (por ejemplo: *CARACTERIZACIÓN SI-APS 2026*) y haz clic en él.

---

### Paso 3 — Obtener el CLIENT_ID y CLIENT_SECRET

1. Dentro del proyecto, haz clic en la pestaña superior **Developer** (o **Desarrollador**).

   > Si no ves esta pestaña, significa que no tienes permisos de administrador en ese proyecto. Pídele al creador del proyecto que te los dé.

2. En la sección **Client Credentials**, verás dos valores:
   - **Client ID:** Un código largo, ejemplo: `10`  o `"nombre-proyecto-client"`
   - **Client Secret:** Una cadena larga de letras y números

3. Haz clic en el botón de copiar junto a cada valor y pégalos en tu archivo `.env`.

```
CLIENT_ID=      ← pega aquí el Client ID
CLIENT_SECRET=  ← pega aquí el Client Secret
```

> ⚠️ **Nunca compartas** el `CLIENT_SECRET`. Es como una contraseña. No lo subas a GitHub.

---

### Paso 4 — Obtener el PROJECT_SLUG

El **slug** es el identificador del proyecto en la URL. Lo encuentras mirando la dirección del navegador cuando estás dentro del proyecto:

```
https://five.epicollect.net/project/caracterizacion-si-aps-2026
                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                    Este es el slug
```

En el `.env`:
```
API_PROJECT_SLUG_2026=caracterizacion-si-aps-2026
```

> 📌 Los slugs de los formularios incluidos en este repositorio ya están precargados en el `.env` de ejemplo de la sección anterior.

---

### Paso 5 — Obtener el FORM_REF

El `form_ref` es el identificador interno del formulario. Hay dos maneras de obtenerlo:

**Manera 1 — Desde los archivos JSON (recomendada)**

Los archivos `.json` en la carpeta `forms/` ya contienen el `form_ref`. Abre cualquiera con un editor de texto y busca el campo `"ref"` al inicio:

```json
{
  "data": {
    "form": {
      "ref": "90b389fd24684ce49435089f2655259b_68af3127d5893",
      ...
    }
  }
}
```

Ese valor largo es tu `API_FORM_REF_*`.

**Manera 2 — Desde la API de Epicollect5**

Ve a esta URL (reemplaza `TU_SLUG` con el slug de tu proyecto):
```
https://five.epicollect.net/api/project/TU_SLUG
```

Busca en la respuesta JSON el campo `"ref"` dentro de `"form"`.

---

### Paso 6 — Obtener el BRANCH_REF (subformularios)

Los subformularios (como los integrantes del hogar) tienen su propio `branch_ref`. También está en el archivo JSON del formulario. Busca entradas de tipo `"branch"`:

```json
{
  "type": "branch",
  "ref": "90b389fd24684ce49435089f2655259b_68af3127d5893_65d3666739f12",
  "question": "4.1. Identificación de cada uno de los miembros..."
}
```

---

### Paso 7 — Si tienes múltiples proyectos con credenciales distintas

Algunos formularios (como Vacunación o Trámites) pueden estar en proyectos Epicollect5 diferentes, con su propio CLIENT_ID y CLIENT_SECRET. En ese caso, agrega los valores específicos:

```dotenv
VACUNACION_2026_CLIENT_ID=el_client_id_del_proyecto_vacunacion
VACUNACION_2026_CLIENT_SECRET=el_secret_del_proyecto_vacunacion
```

Si no los llenas, el sistema automáticamente usará `CLIENT_ID` y `CLIENT_SECRET` como respaldo.

---

### Paso 8 — Configurar el correo Gmail (Opcional)

Si quieres recibir los reportes por correo electrónico:

1. Ve a **https://myaccount.google.com/security**
2. Activa la **Verificación en dos pasos** (si no está activa).
3. Busca **Contraseñas de aplicaciones** (App Passwords).
4. Crea una nueva contraseña para "Correo" → "Otro (nombre personalizado)" → `APS_2026`.
5. Google te dará un código de 16 caracteres (ejemplo: `abcd efgh ijkl mnop`).
6. Pégalo en tu `.env`:

```dotenv
GMAIL_SENDER=tu_correo@gmail.com
GMAIL_APP_PASSWORD=abcd efgh ijkl mnop
```

---

## 11. Crear la base de datos y las tablas

Una vez que el archivo `.env` esté configurado correctamente, ejecuta:

```bash
python database/setup_database.py
```

Este script:
1. Se conecta a PostgreSQL con las credenciales del `.env`.
2. Verifica qué tablas ya existen.
3. Crea las tablas que faltan (es seguro ejecutarlo múltiples veces).
4. Muestra un resumen del estado de la base de datos.

Salida esperada:

```
2026-01-01 10:00:00 | [INFO] | Conexión exitosa a PostgreSQL: localhost:5432/aps_2026
2026-01-01 10:00:00 | [INFO] | ============================================================
2026-01-01 10:00:00 | [INFO] |   INICIANDO CREACIÓN DE TABLAS - APS ESE 2026
2026-01-01 10:00:00 | [INFO] | ============================================================
2026-01-01 10:00:00 | [INFO] |   [CREADA]  caracterizacion_si_aps_familiar_2026
2026-01-01 10:00:00 | [INFO] |   [CREADA]  caracterizacion_si_aps_individual_2026
2026-01-01 10:00:00 | [INFO] |   [CREADA]  tramites_aps_2026
...
2026-01-01 10:00:00 | [INFO] |   Tablas nuevas creadas : 11
```

---

## 12. Ejecutar la sincronización principal

```bash
python app/main.py
```

Este es el comando más importante. Descarga todos los formularios de Epicollect5 y los sincroniza con PostgreSQL. El proceso:

1. Se autentica en la API con tu CLIENT_ID y CLIENT_SECRET.
2. Descarga cada formulario página por página (500 registros por página).
3. Aplica **UPSERT**: inserta registros nuevos y actualiza los existentes.
4. Aplica **DELETE**: elimina registros que fueron borrados en Epicollect5.
5. Pausa entre módulos (5-30 segundos aleatorios) para evitar bloqueos de la API.

Ejemplo de salida exitosa:

```
2026-01-01 10:00:00 | [INFO] | ************************************************************
2026-01-01 10:00:00 | [INFO] |    INICIANDO ORQUESTADOR DE BASE DE DATOS - APS 2026
2026-01-01 10:00:00 | [INFO] | ************************************************************
2026-01-01 10:00:00 | [INFO] | ====== INICIANDO: Ficha Familiar (Caracterización) ======
2026-01-01 10:00:10 | [INFO] | Generando nuevo token de acceso a Epicollect5...
2026-01-01 10:00:12 | [INFO] | Descargando página 1...
2026-01-01 10:00:15 | [INFO] | Descargando página 2...
...
2026-01-01 10:05:00 | [INFO] | ====== ÉXITO: Ficha Familiar (Caracterización) ======
2026-01-01 10:05:00 | [INFO] | ⏳ ENFRIAMIENTO DE API: Pausando 12.34 segundos...
```

> 💡 **Tip:** La primera sincronización puede tardar varios minutos si hay muchos registros acumulados. Las siguientes son más rápidas porque solo descarga los cambios.

---

## 13. Generar reportes en Excel

```bash
python reports/main_reports.py
```

Genera un archivo Excel consolidado con todas las hojas del programa. El archivo se guarda en `reports/excel/` con la fecha del día.

Cada hoja del Excel corresponde a un módulo:
- **CARACTERIZACIÓN FAMILIAR**
- **CARACTERIZACIÓN INDIVIDUAL**
- **TRÁMITES**
- **PLAN DE CUIDADO FAMILIAR**
- **PSICOLOGÍA**
- **PLAN COMUNITARIO**
- **DESISTIMIENTO**
- **VACUNACIÓN**

Las columnas usan **nombres legibles en español**, no los nombres técnicos de la base de datos, gracias al archivo `reports/diccionario/mapeos_aps_2026.json`.

También puedes generar módulos individuales:

```bash
python reports/modules/caracterizacion.py
python reports/modules/tramites.py
python reports/modules/vacunacion.py
python reports/modules/PCF.py
python reports/modules/PCF_Psicologia.py
python reports/modules/PCC.py
python reports/modules/desistimiento.py
```

---

## 14. Descargar evidencias fotográficas

Los trámites incluyen fotos (documentos de identidad, evidencias de resolutividad). Para descargarlas y convertirlas a PDF:

```bash
python reports/evidences/evidencias_tramites.py
```

Las imágenes se guardan en:
```
reports/evidences/ARCHIVOS/IMAGENES/
reports/evidences/ARCHIVOS/PDF/
```

> ⚠️ El descargador respeta el límite de 30 imágenes por minuto de Epicollect5, esperando 2.5 segundos entre cada descarga.

---

## 15. Proceso de contingencia (SI-APS caído)

Cuando la plataforma **SI-APS del Ministerio de Salud** no esté disponible, el flujo de trabajo cambia así:

### ¿Qué se puede hacer sin SI-APS?

| Actividad | Sin SI-APS | Con este sistema |
|---|---|---|
| Recolección de datos en campo | ✅ Epicollect5 funciona sin internet | ✅ |
| Consultar datos recolectados | ❌ SI-APS caído | ✅ Datos en PostgreSQL local |
| Generar reportes de avance | ❌ | ✅ `python reports/main_reports.py` |
| Ver evidencias fotográficas | ❌ | ✅ `python reports/evidences/evidencias_tramites.py` |
| Reportar al MSPS cuando vuelva | ❌ en tiempo real | ✅ Data lista para ingreso masivo |

### Proceso paso a paso durante contingencia

```
1. Los equipos de campo siguen registrando normalmente en Epicollect5 App.
   └── Epicollect5 funciona sin internet y sincroniza cuando hay señal.

2. Ejecutar sincronización local (requiere internet, no SI-APS):
   └── python app/main.py

3. Consultar datos en pgAdmin 4 (herramienta visual de PostgreSQL):
   └── Abrir pgAdmin → Conectar a aps_2026 → Consultar tablas

4. Generar reportes Excel para supervisión y auditoría interna:
   └── python reports/main_reports.py

5. Cuando SI-APS vuelva:
   └── Los datos ya están organizados y listos para ser ingresados o cargados.
```

### Consultas SQL útiles durante contingencia

Puedes abrir pgAdmin 4 y ejecutar estas consultas para monitorear:

```sql
-- Total de familias caracterizadas
SELECT COUNT(*) FROM caracterizacion_si_aps_familiar_2026;

-- Familias por territorio
SELECT territorio, COUNT(*) as total
FROM caracterizacion_si_aps_familiar_2026
GROUP BY territorio ORDER BY total DESC;

-- Trámites del mes actual
SELECT * FROM tramites_aps_2026
WHERE DATE(uploaded_at) >= DATE_TRUNC('month', CURRENT_DATE);

-- Vacunas aplicadas por tipo
SELECT tipo_vacunacion, COUNT(*) as dosis
FROM vacunacion_aps_2026
GROUP BY tipo_vacunacion;
```

---

## 16. Solución de errores comunes

### ❌ `ModuleNotFoundError: No module named 'dotenv'`

**Causa:** Las dependencias no están instaladas.

**Solución:**
```bash
pip install -r requirements.txt
```

---

### ❌ `could not connect to server: Connection refused`

**Causa:** PostgreSQL no está corriendo.

**Solución:**

```bash
# Windows
net start postgresql-x64-16

# macOS
brew services start postgresql@16

# Linux
sudo systemctl start postgresql
```

---

### ❌ `password authentication failed for user "postgres"`

**Causa:** La contraseña en el `.env` no coincide con la de PostgreSQL.

**Solución:**
1. Abre el `.env` y revisa el campo `DB_PASSWORD`.
2. Asegúrate que sea exactamente la contraseña que escribiste al instalar PostgreSQL.

---

### ❌ `BLOQUEO DE API (429): Has superado el límite de 10 tokens por hora`

**Causa:** El sistema solicitó más de 10 tokens OAuth en una hora.

**Solución:** Espera 60 minutos antes de volver a ejecutar. El sistema cachea el token automáticamente para que esto no ocurra en condiciones normales. No interrumpas el proceso mientras está corriendo.

---

### ❌ `ERROR 400 (Bad Request)`

**Causa:** El `form_ref` o `branch_ref` en el `.env` es incorrecto.

**Solución:**
1. Revisa los valores de `API_FORM_REF_*` en tu `.env`.
2. Compáralos con los que están en los archivos JSON de la carpeta `forms/`.
3. Asegúrate de no tener espacios adicionales al inicio o al final de los valores.

---

### ❌ `database "aps_2026" does not exist`

**Causa:** La base de datos no fue creada en PostgreSQL.

**Solución:**
```bash
# Windows (ejecutar en CMD)
"C:\Program Files\PostgreSQL\16\bin\createdb.exe" -U postgres aps_2026

# macOS / Linux
createdb -U postgres aps_2026
```

---

### ❌ `La tabla destino 'X' no existe o no tiene columnas`

**Causa:** Las tablas no han sido creadas todavía.

**Solución:** Ejecuta primero el setup de la base de datos:
```bash
python database/setup_database.py
```

---

### ❌ Error al generar Excel: `No se encontró el archivo de diccionarios`

**Causa:** Falta el archivo `reports/diccionario/mapeos_aps_2026.json`.

**Solución:** Verifica que el archivo exista en esa ruta. Si lo borraste accidentalmente, clona el repositorio de nuevo o descárgalo desde GitHub.

---

## 17. Preguntas frecuentes

**¿Puedo usar este sistema para otros municipios/ESEs?**
Sí. Solamente necesitas reemplazar los valores del `.env` con los slugs y referencias de los formularios Epicollect5 de tu ESE.

**¿Cada cuánto tiempo debo sincronizar?**
Depende de la intensidad del trabajo de campo. Se recomienda al menos una vez al día, o antes de generar reportes. Puedes automatizarlo con el Programador de Tareas de Windows o `cron` en Linux.

**¿Los datos en Epicollect5 se borran cuando sincronizo?**
No. La sincronización es de lectura. Los datos en Epicollect5 no se modifican ni se borran.

**¿Qué pasa si el mismo registro existe en la BD y llega de nuevo desde la API?**
El sistema hace **UPSERT**: si el `ec5_uuid` ya existe, actualiza los campos. Si no existe, lo inserta. Nunca hay duplicados.

**¿Puedo modificar los formularios JSON de la carpeta `forms/`?**
Esos archivos son solo de referencia (exportaciones de Epicollect5). No los modifican los scripts. Los cambios reales se hacen en Epicollect5 directamente.

**¿Cómo agrego un nuevo formulario que no está en el sistema?**
1. Crea el proyecto en Epicollect5.
2. Agrega las variables al `.env`.
3. Agrega la tabla en `database/setup_database.py`.
4. Agrega la entrada en `MODULOS_ETL` en `app/main.py`.
5. Crea el módulo de reporte en `reports/modules/`.

---

## 18. Contribuir al proyecto

Este es un proyecto de **código abierto** pensado para que cualquier ESE o institución pública de salud en Colombia pueda usarlo y mejorarlo.

Para contribuir:

1. Haz un **fork** del repositorio en GitHub.
2. Crea una rama para tu mejora:
   ```bash
   git checkout -b mejora/nuevo-modulo-crecimiento
   ```
3. Realiza tus cambios y haz commit:
   ```bash
   git commit -m "Agrega módulo de seguimiento de crecimiento y desarrollo"
   ```
4. Envía un **Pull Request** describiendo los cambios.

### Ideas para contribuir

- Módulo de seguimiento de crecimiento y desarrollo (niños < 5 años)
- Panel web de estadísticas con Streamlit o Flask
- Integración directa con SI-APS cuando esté disponible
- Soporte para otros años (2027, 2028...)
- Traducción de mensajes al inglés para proyectos internacionales

---

## 19. Licencia

Este proyecto se distribuye bajo la licencia **MIT**. Puedes usarlo, modificarlo y distribuirlo libremente, incluso para uso institucional o comercial, siempre que mantengas el aviso de copyright.

```
MIT License

Copyright (c) 2026 ESE APS Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software...
```

---

## 📞 Soporte

Si encuentras un error o tienes dudas, abre un **Issue** en GitHub:
**https://github.com/zhankyou/APS_2026/issues**

Describe:
- ¿Qué comando ejecutaste?
- ¿Qué error te apareció?
- ¿Qué sistema operativo usas?
- ¿Qué versión de Python y PostgreSQL tienes?

---

<div align="center">

**Hecho con ❤️ para los equipos de salud pública de Colombia**

*"La información bien gestionada salva vidas"*

</div>