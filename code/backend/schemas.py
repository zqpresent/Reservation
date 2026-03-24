from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime, time
from models import ReservationStatus, AdminRole


# -------------------------------------------------------
# 通用响应
# -------------------------------------------------------
class MessageResponse(BaseModel):
    message: str


# -------------------------------------------------------
# 学生
# -------------------------------------------------------
class StudentRegister(BaseModel):
    student_no: str
    password: str
    name: str
    email: Optional[str] = None
    department: Optional[str] = None


class StudentLogin(BaseModel):
    student_no: str
    password: str


class StudentInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_no: str
    name: str
    email: Optional[str]
    department: Optional[str]


# -------------------------------------------------------
# 管理员
# -------------------------------------------------------
class AdminRegister(BaseModel):
    username: str
    password: str
    name: str
    role: Optional[str] = "normal_admin"


class AdminLogin(BaseModel):
    username: str
    password: str


class AdminInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    name: str
    role: AdminRole


# -------------------------------------------------------
# Token
# -------------------------------------------------------
class Token(BaseModel):
    access_token: str
    token_type: str
    user_type: str
    student_id: Optional[int] = None
    admin_id: Optional[int] = None
    admin_role: Optional[str] = None
    admin_name: Optional[str] = None


# -------------------------------------------------------
# 自习室
# -------------------------------------------------------
class RoomBase(BaseModel):
    name: str
    building: Optional[str] = None
    department: Optional[str] = None
    open_time: time
    close_time: time


class RoomCreate(RoomBase):
    pass


class RoomUpdate(BaseModel):
    name: Optional[str] = None
    building: Optional[str] = None
    open_time: Optional[time] = None
    close_time: Optional[time] = None
    is_active: Optional[int] = None


class RoomInfo(RoomBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: int
    checkin_code: Optional[str]


# -------------------------------------------------------
# 座位
# -------------------------------------------------------
class SeatBase(BaseModel):
    seat_no: str
    has_power: Optional[int] = 0
    by_window: Optional[int] = 0


class SeatCreate(SeatBase):
    pass


class SeatInfo(SeatBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int
    is_active: int


class SeatDetail(SeatInfo):
    model_config = ConfigDict(from_attributes=True)

    room: RoomInfo


# -------------------------------------------------------
# 预约
# -------------------------------------------------------
class ReservationCreate(BaseModel):
    seat_id: int
    date: str           # YYYY-MM-DD
    start_time: str     # HH:MM 或 HH:MM:SS
    end_time: str       # HH:MM 或 HH:MM:SS
    student_id: Optional[int] = None  # demo 阶段可直接传入，无需 token


class ReservationInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    seat_id: int
    start_time: datetime
    end_time: datetime
    status: ReservationStatus
    created_at: datetime
    seat: Optional[SeatDetail] = None
    # 计算字段，由 router 层填入
    date: Optional[str] = None
    room_name: Optional[str] = None
    seat_no: Optional[str] = None


# -------------------------------------------------------
# 签到
# -------------------------------------------------------
class CheckInRequest(BaseModel):
    reservation_id: int
    checkin_code: str


# -------------------------------------------------------
# 搜索
# -------------------------------------------------------
class SeatSearchParams(BaseModel):
    date: str
    start_hour: int
    end_hour: int
    has_power: Optional[int] = None
    by_window: Optional[int] = None
    room_id: Optional[int] = None
