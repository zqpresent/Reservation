from sqlalchemy import Column, Integer, SmallInteger, String, Enum, DateTime, Date, Time, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class ReservationStatus(str, enum.Enum):
    pending = "pending"
    checked_in = "checked_in"
    cancelled = "cancelled"
    violated = "violated"


class AdminRole(str, enum.Enum):
    super_admin = "super_admin"
    room_admin = "room_admin"
    normal_admin = "normal_admin"


class NotificationType(str, enum.Enum):
    before_start = "before_start"
    after_start = "after_start"
    auto_cancel = "auto_cancel"


class NotificationStatus(str, enum.Enum):
    sent = "sent"
    failed = "failed"


class Student(Base):
    __tablename__ = "student"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    student_no  = Column(String(20), unique=True, nullable=False)
    password    = Column(String(255), nullable=False)
    name        = Column(String(50), nullable=False)
    email       = Column(String(100))
    department  = Column(String(100))
    created_at  = Column(DateTime, server_default=func.now())

    reservations = relationship("Reservation", back_populates="student")
    violations   = relationship("Violation", back_populates="student")


class AdminUser(Base):
    __tablename__ = "admin_user"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    username   = Column(String(50), unique=True, nullable=False)
    password   = Column(String(255), nullable=False)
    name       = Column(String(50), nullable=False)
    role       = Column(Enum(AdminRole), nullable=False, default=AdminRole.normal_admin)
    is_active  = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    user_roles = relationship("AdminUserRole", back_populates="admin", cascade="all, delete-orphan")


class Room(Base):
    __tablename__ = "room"

    id              = Column(Integer, primary_key=True, autoincrement=True)
    name            = Column(String(100), nullable=False)
    building        = Column(String(100))
    department      = Column(String(100))
    open_time       = Column(Time, nullable=False)
    close_time      = Column(Time, nullable=False)
    is_active       = Column(Integer, default=1)
    checkin_code    = Column(String(10))
    code_updated_at = Column(Date)
    created_at      = Column(DateTime, server_default=func.now())

    seats = relationship("Seat", back_populates="room", cascade="all, delete-orphan")


class Seat(Base):
    __tablename__ = "seat"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    room_id    = Column(Integer, ForeignKey("room.id", ondelete="CASCADE"), nullable=False)
    seat_no    = Column(String(20), nullable=False)
    has_power  = Column(Integer, default=0)
    by_window  = Column(Integer, default=0)
    is_active  = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())

    room         = relationship("Room", back_populates="seats")
    reservations = relationship("Reservation", back_populates="seat")


class Reservation(Base):
    __tablename__ = "reservation"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    student_id = Column(Integer, ForeignKey("student.id"), nullable=False)
    seat_id    = Column(Integer, ForeignKey("seat.id"), nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time   = Column(DateTime, nullable=False)
    status     = Column(Enum(ReservationStatus), nullable=False, default=ReservationStatus.pending)
    created_at = Column(DateTime, server_default=func.now())

    student   = relationship("Student", back_populates="reservations")
    seat      = relationship("Seat", back_populates="reservations")
    violation = relationship("Violation", back_populates="reservation", uselist=False)


class Violation(Base):
    __tablename__ = "violation"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    student_id     = Column(Integer, ForeignKey("student.id"), nullable=False)
    reservation_id = Column(Integer, ForeignKey("reservation.id"), nullable=False)
    violated_at    = Column(DateTime, server_default=func.now())

    student     = relationship("Student", back_populates="violations")
    reservation = relationship("Reservation", back_populates="violation")


class Role(Base):
    __tablename__ = "role"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    key        = Column(String(50), unique=True, nullable=False)
    name       = Column(String(100), nullable=False)
    is_active  = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())

    role_permissions = relationship("RolePermission", back_populates="role", cascade="all, delete-orphan")
    user_roles = relationship("AdminUserRole", back_populates="role", cascade="all, delete-orphan")


class Permission(Base):
    __tablename__ = "permission"

    id         = Column(Integer, primary_key=True, autoincrement=True)
    code       = Column(String(100), unique=True, nullable=False)
    name       = Column(String(100), nullable=False)
    resource   = Column(String(100), nullable=False)
    action     = Column(String(100), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    role_permissions = relationship("RolePermission", back_populates="permission", cascade="all, delete-orphan")


class RolePermission(Base):
    __tablename__ = "role_permission"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    role_id       = Column(Integer, ForeignKey("role.id", ondelete="CASCADE"), nullable=False)
    permission_id = Column(Integer, ForeignKey("permission.id", ondelete="CASCADE"), nullable=False)

    role = relationship("Role", back_populates="role_permissions")
    permission = relationship("Permission", back_populates="role_permissions")


class AdminUserRole(Base):
    __tablename__ = "admin_user_role"

    id       = Column(Integer, primary_key=True, autoincrement=True)
    admin_id = Column(Integer, ForeignKey("admin_user.id", ondelete="CASCADE"), nullable=False)
    role_id  = Column(Integer, ForeignKey("role.id", ondelete="CASCADE"), nullable=False)

    admin = relationship("AdminUser", back_populates="user_roles")
    role = relationship("Role", back_populates="user_roles")


class SystemParam(Base):
    __tablename__ = "system_param"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    key         = Column(String(100), unique=True, nullable=False)
    value       = Column(String(255), nullable=False)
    description = Column(String(255))
    updated_at  = Column(DateTime, server_default=func.now(), onupdate=func.now())


class NotificationLog(Base):
    __tablename__ = "notification_log"

    id             = Column(Integer, primary_key=True, autoincrement=True)
    student_id     = Column(Integer, ForeignKey("student.id"), nullable=False)
    reservation_id = Column(Integer, ForeignKey("reservation.id"), nullable=False)
    type           = Column(Enum(NotificationType), nullable=False)
    channel        = Column(String(50), nullable=False, default="in_app")
    title          = Column(String(100), nullable=False)
    content        = Column(Text, nullable=False)
    status         = Column(Enum(NotificationStatus), nullable=False, default=NotificationStatus.sent)
    created_at     = Column(DateTime, server_default=func.now())
