import requests
import os

class MarzbanAPI:
    def __init__(self):
        self.url = os.getenv("MARZBAN_URL").rstrip('/')
        self.admin_user = os.getenv("MARZBAN_ADMIN_USERNAME")
        self.admin_pass = os.getenv("MARZBAN_ADMIN_PASSWORD")
        self.token = self._get_token()

    def _get_token(self):
        try:
            r = requests.post(f"{self.url}/api/admin/token", 
                            data={"username": self.admin_user, "password": self.admin_pass})
            return r.json().get("access_token")
        except: return None

    def create_user(self, username, days=30):
        headers = {"Authorization": f"Bearer {self.token}"}
        # Упрощенный пример создания (проверьте параметры в доках вашей версии Marzban)
        payload = {
            "username": username,
            "proxies": {"vless": {}},
            "expire": int((days * 86400) + 0) # Нужна логика времени
        }
        r = requests.post(f"{self.url}/api/user", json=payload, headers=headers)
        return r.json()

    def delete_user(self, username):
        headers = {"Authorization": f"Bearer {self.token}"}
        r = requests.delete(f"{self.url}/api/user/{username}", headers=headers)
        return r.status_code == 200
