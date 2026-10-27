"""Instagram API with Instagram Login: publish reels and carousels from public media URLs."""
import time

import requests

API_VERSION = "v23.0"
BASE = f"https://graph.instagram.com/{API_VERSION}"
TOKEN_ERROR_CODE = 190


class InstagramError(RuntimeError):
    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


class InstagramClient:
    def __init__(self, user_id: str, token: str, *, session=None, sleep=time.sleep, poll_seconds=10, max_polls=60):
        self.user_id = user_id
        self.token = token
        self.session = session or requests.Session()
        self.sleep = sleep
        self.poll_seconds = poll_seconds
        self.max_polls = max_polls

    def _request(self, method, path: str, **kwargs):
        try:
            return method(f"{BASE}/{path}", timeout=60, **kwargs)
        except requests.RequestException as exc:
            # requests echoes the URL (with the token in the query string) in its messages; the message
            # ends up in queue.json, which is committed to a public repo, so redact and drop the chain.
            raise InstagramError(f"network error: {str(exc).replace(self.token, '***')}") from None

    def _post(self, path: str, **fields) -> dict:
        return self._json(self._request(self.session.post, path, data={**fields, "access_token": self.token}))

    def _get(self, path: str, **params) -> dict:
        return self._json(self._request(self.session.get, path, params={**params, "access_token": self.token}))

    @staticmethod
    def _json(response) -> dict:
        try:
            data = response.json()
        except ValueError:
            raise InstagramError(f"HTTP {response.status_code}: non-JSON response")
        if response.status_code >= 400 or "error" in data:
            error = data.get("error", {})
            raise InstagramError(f"HTTP {response.status_code}: {error.get('message', 'unknown error')}",
                                 code=error.get("code"))
        return data

    def wait_until_ready(self, container_id: str) -> None:
        for _ in range(self.max_polls):
            data = self._get(container_id, fields="status_code,status")
            status = data.get("status_code")
            if status == "FINISHED":
                return
            if status in ("ERROR", "EXPIRED"):
                raise InstagramError(f"container {container_id} status {status}: {data.get('status', '')}")
            self.sleep(self.poll_seconds)
        raise InstagramError(f"container {container_id} not ready after {self.max_polls * self.poll_seconds}s")

    def _publish(self, container_id: str) -> str:
        self.wait_until_ready(container_id)
        return self._post(f"{self.user_id}/media_publish", creation_id=container_id)["id"]

    def publish_reel(self, video_url: str, caption: str) -> str:
        container = self._post(f"{self.user_id}/media", media_type="REELS", video_url=video_url,
                               caption=caption, share_to_feed="true")["id"]
        return self._publish(container)

    def publish_carousel(self, image_urls: list[str], caption: str) -> str:
        children = [self._post(f"{self.user_id}/media", image_url=url, is_carousel_item="true")["id"]
                    for url in image_urls]
        for child in children:
            self.wait_until_ready(child)
        container = self._post(f"{self.user_id}/media", media_type="CAROUSEL", children=",".join(children),
                               caption=caption)["id"]
        return self._publish(container)
