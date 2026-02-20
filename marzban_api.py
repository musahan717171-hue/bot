import requests
import os
import time

class MarzbanAPI:
    def __init__(self):
        self.url = os.getenv("MARZBAN_URL").rstrip('/')
        self.admin_username = os.getenv("MARZBAN_ADMIN_USERNAME")
        self.admin_password = os.getenv("MARZBAN_ADMIN_PASSWORD")
        self.token = self._get_token()

    def _get_token(self):
        try:
            response = requests.post(
                f"{self.url}/api/admin/token",
                data={"username": self.admin_username, "password": self.admin_password},
                timeout=10
            )
            return response.json().get("access_token")
        except Exception as e:
            print(f"Ошибка авторизации Marzban: {e}")
            return None

    def get_headers(self):
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def create_user(self, username):
        # Настройки: 30 дней (в секундах), лимит 50ГБ
        expire_time = int(time.time() + (30 * 86400))
        payload = {
            "username": username,
            "proxies": {"vless": {}, "vmess": {}, "trojan": {}, "shadowsocks": {}},
            "data_limit": 50 * 1024 * 1024 * 1024,
            "expire": expire_time
        }
        r = requests.post(f"{self.url}/api/user", json=payload, headers=self.get_headers())
        return r.json()

    def get_user(self, username):
        r = requests.get(f"{self.url}/api/user/{username}", headers=self.get_headers())
        return r.json() if r.status_code == 200 else None

    def renew_user(self, username, days=30):
        user = self.get_user(username)
        if not user: return False
        
        current_expire = user.get('expire') or int(time.time())
        new_expire = current_expire + (days * 86400)
        
        r = requests.put(f"{self.url}/api/user/{username}", 
                         json={"expire": new_expire}, headers=self.get_headers())
        return r.status_code == 200

    def delete_user(self, username):
        r = requests.delete(f"{self.url}/api/user/{username}", headers=self.get_headers())
        return r.status_code == 200
