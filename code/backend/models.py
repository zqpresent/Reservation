from sqlalchemy import Column, Integer, SmallInteger, String, Enum, DateTime, Date, Time, ForeignKey
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
