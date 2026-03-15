from locust import HttpUser, task, between
import random
import string

def random_string(length=8):
    return "".join(random.choices(string.ascii_lowercase, k=length))


class AnonymousUser(HttpUser):
    """Имитирует анонимного пользователя: создаёт и открывает ссылки"""
    wait_time = between(1, 3)
    host = "http://localhost:8000"

    def on_start(self):
        """Создаём одну ссылку при старте, будем её переоткрывать"""
        response = self.client.post("/links/shorten", json={
            "original_url": "https://example.com"
        })
        if response.status_code == 201:
            self.short_code = response.json()["short_code"]
        else:
            self.short_code = None

    @task(3)
    def redirect(self):
        """Редирект — самый частый сценарий, с весом 3"""
        if self.short_code:
            self.client.get(
                f"/{self.short_code}",
                allow_redirects=False,
                name="/{short_code} [redirect]"
            )

    @task(2)
    def create_link(self):
        """Создание новой ссылки, с весом 2"""
        self.client.post("/links/shorten", json={
            "original_url": f"https://example.com/{random_string()}"
        }, name="/links/shorten [create]")

    @task(1)
    def get_stats(self):
        """Получение статистики, с весом 1"""
        if self.short_code:
            self.client.get(
                f"/links/{self.short_code}/stats",
                name="/links/{short_code}/stats"
            )


class RegisteredUser(HttpUser):
    """Имитирует зарегистрированного пользователя"""
    wait_time = between(2, 5)
    host = "http://localhost:8000"

    def on_start(self):
        """Регистрируемся и логинимся при старте"""
        username = random_string()
        password = "testpass123"

        self.client.post("/users/register", json={
            "username": username,
            "email": f"{username}@example.com",
            "password": password
        })

        response = self.client.post("/users/login", data={
            "username": username,
            "password": password
        })

        if response.status_code == 200:
            token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {token}"}
        else:
            self.headers = {}

        # Создаём ссылку для дальнейших операций
        response = self.client.post("/links/shorten", json={
            "original_url": "https://example.com"
        }, headers=self.headers)
        if response.status_code == 201:
            self.short_code = response.json()["short_code"]
        else:
            self.short_code = None

    @task(2)
    def redirect(self):
        if self.short_code:
            self.client.get(
                f"/{self.short_code}",
                allow_redirects=False,
                name="/{short_code} [redirect]"
            )

    @task(1)
    def update_link(self):
        if self.short_code:
            self.client.put(
                f"/links/{self.short_code}",
                json={"original_url": f"https://updated.com/{random_string()}"},
                headers=self.headers,
                name="/links/{short_code} [update]"
            )

    @task(1)
    def get_stats(self):
        if self.short_code:
            self.client.get(
                f"/links/{self.short_code}/stats",
                name="/links/{short_code}/stats"
            )