import requests
import os
import time

class MarzbanAPI:
    def __init__(self):
        self.url = os.getenv("MARZBAN_URL", "").rstrip('/')
        self.admin_username = os.getenv("MARZBAN_ADMIN_USERNAME")
        self.admin_password = os.getenv("MARZBAN_ADMIN_PASSWORD")
        self.token = self._get_token()

    def _get_token(self):
        # Если URL пустой или не начинается с http
        if not self.url.startswith('http'):
            print(f"❌ ОШИБКА: URL '{self.url}' неверный. Должен начинаться с http:// или https://")
            return None

        login_url = f"{self.url}/api/admin/token"
        print(f"🔄 Попытка авторизации по адресу: {login_url}")
        
        try:
            response = requests.post(
                login_url,
                data={"username": self.admin_username, "password": self.admin_password},
                timeout=10,
                headers={"User-Agent": "MarzbanBot/1.0"} # Некоторые сервера блокируют запросы без User-Agent
            )
            
            if response.status_code == 200:
                print("✅ Авторизация успешна!")
                return response.json().get("access_token")
            else:
                print(f"❌ ОШИБКА: Панель ответила статусом {response.status_code}")
                print(f"Ответ сервера: {response.text}")
                return None
                
        except requests.exceptions.ConnectionError:
            print("❌ ОШИБКА: Сервер сбросил соединение. Возможно, неверный порт или включен Cloudflare.")
            return None
        except Exception as e:
            print(f"❌ НЕПРЕДВИДЕННАЯ ОШИБКА: {e}")
            return None

    def get_headers(self):
        if not self.token:
            self.token = self._get_token() # Пробуем переавторизоваться
        return {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}

    def create_user(self, username):
        if not self.token:
            return {"error": "No token"}
        
        expire_time = int(time.time() + (30 * 86400))
        payload = {
            "username": username,
            "proxies": {"vless": {}, "vmess": {}}, 
            "expire": expire_time
        }
        try:
            r = requests.post(f"{self.url}/api/user", json=payload, headers=self.get_headers(), timeout=10)
            return r.json()
        except Exception as e:
            print(f"Ошибка при создании: {e}")
            return {"error": str(e)}
