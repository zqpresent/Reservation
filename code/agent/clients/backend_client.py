from typing import Any, Optional

import httpx


class BackendAPIError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class BackendClient:
    def __init__(self, base_url: str, timeout_seconds: float = 15):
        self.base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout_seconds)

    async def aclose(self):
        await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json_body: Optional[dict[str, Any]] = None,
    ) -> Any:
        try:
            response = await self._client.request(method, path, params=params, json=json_body)
        except httpx.RequestError as exc:
            raise BackendAPIError(
                503,
                f"无法连接后端服务 {self.base_url}，请确认 backend 已启动",
            ) from exc
        if response.is_success:
            if response.content:
                return response.json()
            return None

        detail = "backend request failed"
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = str(payload.get("detail", payload))
            else:
                detail = str(payload)
        except Exception:
            detail = response.text or detail
        raise BackendAPIError(response.status_code, detail)

    async def search_seats(
        self,
        *,
        date: str,
        start_time: str,
        end_time: str,
        room_id: Optional[int] = None,
        has_power: Optional[int] = None,
        by_window: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
        }
        if room_id is not None:
            params["room_id"] = room_id
        if has_power is not None:
            params["has_power"] = has_power
        if by_window is not None:
            params["by_window"] = by_window
        data = await self._request("GET", "/seats/search", params=params)
        return data if isinstance(data, list) else []

    async def list_my_reservations(self, student_id: int, status: str = "") -> list[dict[str, Any]]:
        params: dict[str, Any] = {"student_id": student_id}
        if status:
            params["status"] = status
        data = await self._request("GET", "/reservations", params=params)
        return data if isinstance(data, list) else []

    async def create_reservation(
        self,
        *,
        student_id: int,
        seat_id: int,
        date: str,
        start_time: str,
        end_time: str,
    ) -> dict[str, Any]:
        body = {
            "student_id": student_id,
            "seat_id": seat_id,
            "date": date,
            "start_time": start_time,
            "end_time": end_time,
        }
        data = await self._request("POST", "/reservations", json_body=body)
        return data if isinstance(data, dict) else {"raw": data}

    async def cancel_reservation(self, reservation_id: int) -> dict[str, Any]:
        data = await self._request("DELETE", f"/reservations/{reservation_id}")
        return data if isinstance(data, dict) else {"raw": data}

    async def health(self) -> dict[str, Any]:
        data = await self._request("GET", "/")
        return data if isinstance(data, dict) else {"raw": data}
