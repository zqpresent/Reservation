from typing import Optional

from langchain_core.tools import tool

from clients.backend_client import BackendAPIError, BackendClient


def _normalize_time(time_str: str) -> str:
    value = time_str.strip()
    parts = value.split(":")
    if len(parts) == 2:
        return f"{parts[0]}:{parts[1]}:00"
    return value


def build_student_tools(backend_client: BackendClient, student_id: int):
    @tool
    async def search_seats(
        date: str,
        start_time: str,
        end_time: str,
        room_id: Optional[int] = None,
        need_power: Optional[bool] = None,
        need_window: Optional[bool] = None,
    ) -> dict:
        """按日期和时间段搜索可用座位，可选偏好：插座、靠窗、指定自习室。"""
        try:
            seats = await backend_client.search_seats(
                date=date,
                start_time=_normalize_time(start_time),
                end_time=_normalize_time(end_time),
                room_id=room_id,
                has_power=1 if need_power else None,
                by_window=1 if need_window else None,
            )
            return {"success": True, "count": len(seats), "data": seats}
        except BackendAPIError as exc:
            return {"success": False, "error": exc.detail, "status_code": exc.status_code}

    @tool
    async def my_reservations(status: str = "") -> dict:
        """查看当前学生的预约列表，status 可为 pending/checked_in/cancelled/violated。"""
        try:
            rows = await backend_client.list_my_reservations(student_id=student_id, status=status)
            return {"success": True, "count": len(rows), "data": rows}
        except BackendAPIError as exc:
            return {"success": False, "error": exc.detail, "status_code": exc.status_code}

    @tool
    async def create_reservation(seat_id: int, date: str, start_time: str, end_time: str) -> dict:
        """为当前学生创建预约，时间格式支持 HH:MM 或 HH:MM:SS。"""
        try:
            reservation = await backend_client.create_reservation(
                student_id=student_id,
                seat_id=seat_id,
                date=date,
                start_time=_normalize_time(start_time),
                end_time=_normalize_time(end_time),
            )
            return {"success": True, "data": reservation}
        except BackendAPIError as exc:
            return {"success": False, "error": exc.detail, "status_code": exc.status_code}

    @tool
    async def cancel_reservation(reservation_id: int) -> dict:
        """取消当前学生某条待签到预约。"""
        try:
            result = await backend_client.cancel_reservation(reservation_id=reservation_id)
            return {"success": True, "data": result}
        except BackendAPIError as exc:
            return {"success": False, "error": exc.detail, "status_code": exc.status_code}

    return [search_seats, my_reservations, create_reservation, cancel_reservation]
