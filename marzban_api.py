import requests
import os
import time

class MarzbanAPI:
    def __init__(self):
        self.url = os.getenv("MARZBAN_URL", "").rstrip('/')
        self.username = os.getenv("MARZBAN_ADMIN_USERNAME")
        self.password = os.getenv("MARZBAN_ADMIN_PASSWORD")

    def _get_token(self):
        try:
            r = requests.post(
                f"{self.url}/api/admin/token", 
                data={"username": self.username, "password": self.password}, 
                timeout=10
            )
            return r.json().get("access_token") if r.status_code == 200 else None
        except: return None

    def create_user(self, username):
        token = self._get_token()
        if not token: return None
        
        payload = {
            "username": username,
            "proxies": {"vless": {}, "vmess": {}, "shadowsocks": {}, "trojan": {}},
            "data_limit": 50 * 1024 * 1024 * 1024,
            "expire": int(time.time() + 2592000)
        }
        try:
            r = requests.post(f"{self.url}/api/user", json=payload, 
                             headers={"Authorization": f"Bearer {token}"}, timeout=15)
            return r.json() if r.status_code in [200, 201] else None
        except: return None

    def get_user(self, username):
        token = self._get_token()
        if not token: return None
        try:
            r = requests.get(f"{self.url}/api/user/{username}", 
                            headers={"Authorization": f"Bearer {token}"}, timeout=10)
            return r.json() if r.status_code == 200 else None
        except: return None

    def renew_user(self, username):
        user = self.get_user(username)
        if not user: return False
        token = self._get_token()
        new_expire = (user.get('expire') or int(time.time())) + 2592000
        try:
            r = requests.put(f"{self.url}/api/user/{username}", 
                            json={"expire": new_expire}, 
                            headers={"Authorization": f"Bearer {token}"}, timeout=10)
            return r.status_code == 200
        except: return False

    def delete_user(self, username):
        token = self._get_token()
        if token:
            requests.delete(f"{self.url}/api/user/{username}", 
                           headers={"Authorization": f"Bearer {token}"}, timeout=10)
