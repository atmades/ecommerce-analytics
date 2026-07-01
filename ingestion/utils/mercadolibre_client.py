"""
Клиент для MercadoLibre API с автоматическим управлением OAuth2 токеном.

Flow: Client Credentials — наше приложение аутентифицируется само,
без участия пользователя (в отличие от Authorization Code flow).
"""
import time
import logging
import requests

from utils.secrets import get_secret
from utils.config import config

logger = logging.getLogger(__name__)

TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
API_BASE_URL = "https://api.mercadolibre.com"


class MercadoLibreClient:
    def __init__(self):
        self.client_id = get_secret("mercadolibre-client-id", config.project_id)
        self.client_secret = get_secret("mercadolibre-client-secret", config.project_id)
        self._token: str | None = None
        self._token_expires_at: float = 0

    def _get_token(self) -> str:
        """
        Возвращает действующий токен. Если токен истёк или скоро истечёт
        (запас 60 секунд) — запрашивает новый.
        """
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token

        logger.info("Запрашиваем новый OAuth2 токен")
        response = requests.post(TOKEN_URL, data={
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        })
        response.raise_for_status()

        data = response.json()
        self._token = data["access_token"]
        self._token_expires_at = time.time() + data["expires_in"]

        logger.info(f"Токен получен, действует {data['expires_in']} секунд")
        return self._token

    def get(self, endpoint: str, params: dict | None = None) -> dict:
        """
        GET-запрос к MercadoLibre API.

        Args:
            endpoint: путь после базового URL, например '/sites/MLB/categories'
            params: query-параметры запроса
        """
        headers = {"Authorization": f"Bearer {self._get_token()}"}
        url = f"{API_BASE_URL}{endpoint}"

        response = requests.get(url, headers=headers, params=params)

        # Токен истёк раньше времени — обновляем и повторяем один раз
        if response.status_code == 401:
            logger.warning("Токен невалиден (401), обновляем")
            self._token_expires_at = 0
            headers = {"Authorization": f"Bearer {self._get_token()}"}
            response = requests.get(url, headers=headers, params=params)

        response.raise_for_status()
        return response.json()
