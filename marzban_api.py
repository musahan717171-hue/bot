import requests
import os
import time

class MarzbanAPI:
    def __init__(self):
        self.url = os.getenv("MARZBAN_URL", "").rstrip('/')
        self.username = os.getenv("MARZBAN_ADMIN_USERNAME")
        self.password = os.getenv("MARZBAN_ADMIN_PASSWORD")
        self.token = self._get_token()

    def _get_token(self):
        if not self.url: return None
        
        # Marzban принимает данные для токена как Form Data
        login_data = {"username": self.username, "password": self.password}
        try:
            r = requests.post(f"{self.url}/api/admin/token", data=login_data, timeout=10)
            
            if r.status_code == 200:
                print("✅ [API] Авторизация успешна!")
                return r.json().get("access_token")
            elif r.status_code == 401:
                print("❌ [API] Ошибка: Неверный логин или пароль админа!")
            elif r.status_code == 404:
                print(f"❌ [API] Ошибка: По адресу {self.url} панель Marzban не найдена (404)")
            else:
                print(f"❌ [API] Ошибка: Статус {r.status_code}, Ответ: {r.text}")
            return None
        except Exception as e:
            print(f"❌ [API] Критическая ошибка подключения: {e}")
            return None

    def get_headers(self):
        token = self._get_token() # Обновляем токен при каждом запросе для надежности
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    def create_user(self, username):
        headers = self.get_headers()
        if "None" in str(headers.get("Authorization")):
            return {"error": "auth_failed"}
            
        payload = {
            "username": username,
            "proxies": {"vless": {}, "vmess": {}},
            "expire": int(time.time() + 2592000) # +30 дней
        }
        
        try:
            r = requests.post(f"{self.url}/api/user", json=payload, headers=headers, timeout=10)
            return r.json()
        except Exception as e:
            return {"error": str(e)}
