# epicollect_api.py
import requests
import time
import json
import os
import logging

logger = logging.getLogger("EpicollectAPI")


class EpicollectAPI:
    def __init__(self, client_id=None, client_secret=None):
        # Si no se pasan credenciales específicas (como vacunación), usa las globales
        self.client_id = client_id or os.getenv("CLIENT_ID")
        self.client_secret = client_secret or os.getenv("CLIENT_SECRET")
        self.base_url = "https://five.epicollect.net/api"
        # Diferencia la caché para evitar conflictos de tokens entre proyectos distintos
        self.token_file = f"cache_token_{self.client_id[:5]}.json" if self.client_id else "cache_token.json"

    def _obtener_token(self):
        """Maneja el flujo OAuth2 y cachea el token."""
        if os.path.exists(self.token_file):
            with open(self.token_file, "r") as f:
                cache = json.load(f)
                if cache["expires_at"] > time.time():
                    return cache["access_token"]

        logger.info("Generando nuevo token de acceso a Epicollect5...")
        url = f"{self.base_url}/oauth/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }
        resp = requests.post(url, data=payload)
        resp.raise_for_status()

        data = resp.json()
        data["expires_at"] = time.time() + data["expires_in"] - 60
        with open(self.token_file, "w") as f:
            json.dump(data, f)
        return data["access_token"]

    def extraer_datos(self, project_slug, form_ref, branch_ref=None, limite=1000):
        """Descarga registros, adaptándose si es Formulario o Rama (Branch)."""
        token = self._obtener_token()
        headers = {"Authorization": f"Bearer {token}"}

        # Lógica de enrutamiento adaptada de tus scripts
        if branch_ref:
            url = f"{self.base_url}/export/branches/{project_slug}?form_ref={form_ref}&branch_ref={branch_ref}&per_page={limite}"
        else:
            url = f"{self.base_url}/export/entries/{project_slug}?form_ref={form_ref}&per_page={limite}"

        registros = []
        while url:
            resp = requests.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            registros.extend(data["data"]["entries"])
            url = data["links"].get("next")  # Siguiente página de la API

        return registros