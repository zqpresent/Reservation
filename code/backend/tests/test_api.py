"""
自习座位预约系统 - 后端接口集成测试
依赖真实 MySQL 数据库，运行前确保：
  1. MySQL 服务已启动
  2. 已执行 database/init.sql 初始化
  3. backend/.env 已配置正确

运行方式：
    cd backend
    pytest tests/test_api.py -v
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app
from database import SessionLocal
import models
from auth import hash_password, create_token


# -------------------------------------------------------
# Fixture：每个测试前清空业务数据，保留基础数据
# -------------------------------------------------------
@pytest.fixture(autouse=True)
def clean_db():
    """每个测试前清空业务数据，保留自习室、座位及超管账号"""
    db = SessionLocal()
    try:
        db.query(models.NotificationLog).delete()
        db.query(models.Violation).delete()
        db.query(models.Reservation).delete()
        db.query(models.Student).delete()
        # 清理测试创建的非超管管理员，避免跨次运行重复注册
        db.query(models.AdminUser).filter(
            models.AdminUser.username != "admin"
        ).delete()
        # 确保超级管理员存在
        admin = db.query(models.AdminUser).filter_by(username="admin").first()
        if not admin:
            db.add(models.AdminUser(
                username="admin",
                password=hash_password("admin123"),
                name="超级管理员",
                role=models.AdminRole.super_admin,
            ))
        else:
            admin.password = hash_password("admin123")
        db.commit()
    finally:
        db.close()


@pytest_asyncio.fixture
async def client():
    db = SessionLocal()
    try:
        admin = db.query(models.AdminUser).filter_by(username="admin").first()
        admin_id = admin.id if admin else 1
    finally:
        db.close()
    token = create_token({"sub": admin_id, "type": "admin", "role": "super_admin"})
    headers = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as c:
        yield c


# -------------------------------------------------------
# 辅助函数
# 登录后返回 student_id（不再依赖 token）
# -------------------------------------------------------
async def register_and_login_student(
    client: AsyncClient,
    student_no: str = "2024001",
    password: str = "pass123",
    department: str = None,
) -> int:
    """注册并登录学生，返回 student_id"""
    await client.post("/auth/register", json={
        "student_no": student_no,
        "password": password,
        "name": "测试学生",
        "department": department,
    })
    resp = await client.post("/auth/login", json={
        "student_no": student_no,
        "password": password,
    })
    return resp.json()["student_id"]


async def get_first_seat_id(client: AsyncClient) -> int:
    """获取第一个可用座位的 ID"""
    rooms = (await client.get("/rooms")).json()
    seats = (await client.get(f"/rooms/{rooms[0]['id']}/seats")).json()
    return seats[0]["id"]


def tomorrow_date() -> str:
    return (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")


# -------------------------------------------------------
# 1. 认证模块
# -------------------------------------------------------
class TestAuth:

    @pytest.mark.asyncio
    async def test_register_success(self, client):
        resp = await client.post("/auth/register", json={
            "student_no": "2024001",
            "password": "pass123",
            "name": "张三",
            "department": "计算机学院",
        })
        assert resp.status_code == 200
        assert resp.json()["student_no"] == "2024001"

    @pytest.mark.asyncio
    async def test_register_duplicate(self, client):
        body = {"student_no": "2024001", "password": "pass123", "name": "张三"}
        await client.post("/auth/register", json=body)
        resp = await client.post("/auth/register", json=body)
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_student_login_success(self, client):
        await client.post("/auth/register", json={
            "student_no": "2024001", "password": "pass123", "name": "张三"
        })
        resp = await client.post("/auth/login", json={
            "student_no": "2024001", "password": "pass123"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["user_type"] == "student"
        # 登录响应直接返回 student_id
        assert "student_id" in data
        assert isinstance(data["student_id"], int)

    @pytest.mark.asyncio
    async def test_student_login_wrong_password(self, client):
        await client.post("/auth/register", json={
            "student_no": "2024001", "password": "pass123", "name": "张三"
        })
        resp = await client.post("/auth/login", json={
            "student_no": "2024001", "password": "wrong"
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_admin_login_success(self, client):
        resp = await client.post("/auth/admin/login", json={
            "username": "admin", "password": "admin123"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_type"] == "admin"
        # 登录响应直接返回 admin_id、admin_role、admin_name
        assert "admin_id" in data
        assert "admin_role" in data
        assert "admin_name" in data

    @pytest.mark.asyncio
    async def test_get_me_by_student_id(self, client):
        """不再使用 token，改为通过 student_id query 参数获取用户信息"""
        student_id = await register_and_login_student(client)
        resp = await client.get(f"/auth/me?student_id={student_id}")
        assert resp.status_code == 200
        assert resp.json()["student_no"] == "2024001"

    @pytest.mark.asyncio
    async def test_get_me_invalid_student_id(self, client):
        """student_id 不存在时返回 404"""
        resp = await client.get("/auth/me?student_id=99999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_admin_register(self, client):
        resp = await client.post("/auth/admin/register", json={
            "username": "newadmin",
            "password": "admin456",
            "name": "新管理员",
            "role": "normal_admin",
        })
        assert resp.status_code == 200
        assert resp.json()["username"] == "newadmin"

    @pytest.mark.asyncio
    async def test_admin_register_duplicate(self, client):
        body = {"username": "admin", "password": "xxx", "name": "重复"}
        resp = await client.post("/auth/admin/register", json=body)
        assert resp.status_code == 400


# -------------------------------------------------------
# 2. 自习室模块
# -------------------------------------------------------
class TestRooms:

    @pytest.mark.asyncio
    async def test_list_rooms_without_token(self, client):
        """不登录也可以查询自习室（只返回全校通用）"""
        resp = await client.get("/rooms")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_get_room_detail(self, client):
        rooms = (await client.get("/rooms")).json()
        resp = await client.get(f"/rooms/{rooms[0]['id']}")
        assert resp.status_code == 200
        assert "name" in resp.json()

    @pytest.mark.asyncio
    async def test_get_room_seats(self, client):
        rooms = (await client.get("/rooms")).json()
        resp = await client.get(f"/rooms/{rooms[0]['id']}/seats")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    @pytest.mark.asyncio
    async def test_admin_list_all_rooms(self, client):
        """管理员接口不再需要 token"""
        resp = await client.get("/rooms/admin/all")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_admin_create_room(self, client):
        """管理员新增自习室（无需 token）"""
        resp = await client.post("/rooms/admin", json={
            "name": "新自习室",
            "building": "新楼",
            "department": None,
            "open_time": "08:00:00",
            "close_time": "22:00:00",
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "新自习室"

    @pytest.mark.asyncio
    async def test_admin_update_room(self, client):
        rooms = (await client.get("/rooms/admin/all")).json()
        resp = await client.put(f"/rooms/admin/{rooms[0]['id']}", json={
            "name": "修改后的名称"
        })
        assert resp.status_code == 200
        assert resp.json()["name"] == "修改后的名称"

    @pytest.mark.asyncio
    async def test_get_nonexistent_room(self, client):
        resp = await client.get("/rooms/99999")
        assert resp.status_code == 404


# -------------------------------------------------------
# 3. 座位搜索模块
# -------------------------------------------------------
class TestSeats:

    @pytest.mark.asyncio
    async def test_search_available_seats(self, client):
        """搜索参数改为 start_time/end_time 字符串格式"""
        resp = await client.get("/seats/search", params={
            "date": tomorrow_date(),
            "start_time": "14:00:00",
            "end_time": "16:00:00",
        })
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    @pytest.mark.asyncio
    async def test_search_with_power_filter(self, client):
        resp = await client.get("/seats/search", params={
            "date": tomorrow_date(),
            "start_time": "14:00:00",
            "end_time": "16:00:00",
            "has_power": 1,
        })
        assert resp.status_code == 200
        assert all(s["has_power"] == 1 for s in resp.json())

    @pytest.mark.asyncio
    async def test_search_with_window_filter(self, client):
        resp = await client.get("/seats/search", params={
            "date": tomorrow_date(),
            "start_time": "14:00:00",
            "end_time": "16:00:00",
            "by_window": 1,
        })
        assert resp.status_code == 200
        assert all(s["by_window"] == 1 for s in resp.json())

    @pytest.mark.asyncio
    async def test_search_end_before_start(self, client):
        """结束时间早于开始时间应返回 400"""
        resp = await client.get("/seats/search", params={
            "date": tomorrow_date(),
            "start_time": "16:00:00",
            "end_time": "14:00:00",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_search_invalid_date_format(self, client):
        resp = await client.get("/seats/search", params={
            "date": "not-a-date",
            "start_time": "14:00:00",
            "end_time": "16:00:00",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_admin_create_seat(self, client):
        rooms = (await client.get("/rooms/admin/all")).json()
        room_id = rooms[0]["id"]
        # 用时间戳保证座位编号唯一，避免跨次运行冲突
        unique_no = f"T{datetime.now().strftime('%H%M%S%f')}"
        resp = await client.post(f"/seats/admin/{room_id}", json={
            "seat_no": unique_no,
            "has_power": 1,
            "by_window": 0,
        })
        assert resp.status_code == 200
        assert resp.json()["seat_no"] == unique_no

    @pytest.mark.asyncio
    async def test_admin_create_seat_duplicate(self, client):
        rooms = (await client.get("/rooms/admin/all")).json()
        room_id = rooms[0]["id"]
        seats = (await client.get(f"/rooms/{room_id}/seats")).json()
        existing_no = seats[0]["seat_no"]
        resp = await client.post(f"/seats/admin/{room_id}", json={
            "seat_no": existing_no, "has_power": 0, "by_window": 0
        })
        assert resp.status_code == 400


# -------------------------------------------------------
# 4. 预约模块
# -------------------------------------------------------
class TestReservations:

    @pytest.mark.asyncio
    async def test_create_reservation(self, client):
        """预约接口改为传 date/start_time/end_time/student_id"""
        student_id = await register_and_login_student(client)
        seat_id = await get_first_seat_id(client)
        resp = await client.post("/reservations", json={
            "seat_id": seat_id,
            "date": tomorrow_date(),
            "start_time": "14:00:00",
            "end_time": "16:00:00",
            "student_id": student_id,
        })
        assert resp.status_code == 200
        assert resp.json()["status"] == "pending"
        assert resp.json()["student_id"] == student_id

    @pytest.mark.asyncio
    async def test_create_reservation_conflict(self, client):
        student_id = await register_and_login_student(client)
        seat_id = await get_first_seat_id(client)
        body = {
            "seat_id": seat_id,
            "date": tomorrow_date(),
            "start_time": "14:00:00",
            "end_time": "16:00:00",
            "student_id": student_id,
        }
        await client.post("/reservations", json=body)
        resp = await client.post("/reservations", json=body)
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_create_reservation_exceeds_max_hours(self, client):
        student_id = await register_and_login_student(client)
        seat_id = await get_first_seat_id(client)
        resp = await client.post("/reservations", json={
            "seat_id": seat_id,
            "date": tomorrow_date(),
            "start_time": "08:00:00",
            "end_time": "13:00:00",  # 5小时，超过上限4小时
            "student_id": student_id,
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_reservation_without_student_id(self, client):
        """不传 student_id 应返回 400"""
        seat_id = await get_first_seat_id(client)
        resp = await client.post("/reservations", json={
            "seat_id": seat_id,
            "date": tomorrow_date(),
            "start_time": "14:00:00",
            "end_time": "16:00:00",
            # 故意不传 student_id
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_list_my_reservations(self, client):
        """查询我的预约通过 student_id query 参数过滤"""
        student_id = await register_and_login_student(client)
        seat_id = await get_first_seat_id(client)
        await client.post("/reservations", json={
            "seat_id": seat_id,
            "date": tomorrow_date(),
            "start_time": "14:00:00",
            "end_time": "15:00:00",
            "student_id": student_id,
        })
        resp = await client.get(f"/reservations?student_id={student_id}")
        assert resp.status_code == 200
        assert len(resp.json()) == 1
        assert resp.json()[0]["student_id"] == student_id

    @pytest.mark.asyncio
    async def test_list_reservations_filter_by_status(self, client):
        student_id = await register_and_login_student(client)
        seat_id = await get_first_seat_id(client)
        await client.post("/reservations", json={
            "seat_id": seat_id,
            "date": tomorrow_date(),
            "start_time": "14:00:00",
            "end_time": "15:00:00",
            "student_id": student_id,
        })
        resp = await client.get(f"/reservations?student_id={student_id}&status=pending")
        assert resp.status_code == 200
        assert all(r["status"] == "pending" for r in resp.json())

    @pytest.mark.asyncio
    async def test_cancel_reservation(self, client):
        student_id = await register_and_login_student(client)
        seat_id = await get_first_seat_id(client)
        r = (await client.post("/reservations", json={
            "seat_id": seat_id,
            "date": tomorrow_date(),
            "start_time": "14:00:00",
            "end_time": "15:00:00",
            "student_id": student_id,
        })).json()
        resp = await client.delete(f"/reservations/{r['id']}")
        assert resp.status_code == 200
        reservations = (await client.get(f"/reservations?student_id={student_id}")).json()
        assert reservations[0]["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_nonexistent_reservation(self, client):
        resp = await client.delete("/reservations/99999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_already_cancelled_reservation(self, client):
        student_id = await register_and_login_student(client)
        seat_id = await get_first_seat_id(client)
        r = (await client.post("/reservations", json={
            "seat_id": seat_id,
            "date": tomorrow_date(),
            "start_time": "14:00:00",
            "end_time": "15:00:00",
            "student_id": student_id,
        })).json()
        await client.delete(f"/reservations/{r['id']}")
        # 再次取消应该失败
        resp = await client.delete(f"/reservations/{r['id']}")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_reservation_response_contains_room_info(self, client):
        """预约响应包含 room_name、seat_no 等扩展字段"""
        student_id = await register_and_login_student(client)
        seat_id = await get_first_seat_id(client)
        r = (await client.post("/reservations", json={
            "seat_id": seat_id,
            "date": tomorrow_date(),
            "start_time": "14:00:00",
            "end_time": "15:00:00",
            "student_id": student_id,
        })).json()
        assert "room_name" in r
        assert "seat_no" in r
        assert "date" in r

    @pytest.mark.asyncio
    async def test_admin_view_all_reservations(self, client):
        """管理员查看所有预约（无需 token）"""
        student_id = await register_and_login_student(client)
        seat_id = await get_first_seat_id(client)
        await client.post("/reservations", json={
            "seat_id": seat_id,
            "date": tomorrow_date(),
            "start_time": "14:00:00",
            "end_time": "15:00:00",
            "student_id": student_id,
        })
        resp = await client.get("/reservations/admin/all")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    @pytest.mark.asyncio
    async def test_admin_filter_reservations_by_status(self, client):
        student_id = await register_and_login_student(client)
        seat_id = await get_first_seat_id(client)
        await client.post("/reservations", json={
            "seat_id": seat_id,
            "date": tomorrow_date(),
            "start_time": "14:00:00",
            "end_time": "15:00:00",
            "student_id": student_id,
        })
        resp = await client.get("/reservations/admin/all?status=pending")
        assert resp.status_code == 200
        assert all(r["status"] == "pending" for r in resp.json())

    @pytest.mark.asyncio
    async def test_admin_view_violations(self, client):
        """违约记录接口（无需 token）"""
        resp = await client.get("/reservations/admin/violations")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# -------------------------------------------------------
# 5. 第二阶段接口
# -------------------------------------------------------
class TestStageTwoApis:

    @pytest.mark.asyncio
    async def test_system_params_crud(self, client):
        # 新建（批量接口）
        r = await client.put("/system/params", json={"items": [{"key": "X_TEST_PARAM", "value": "1"}]})
        assert r.status_code == 200
        # 单项更新
        r2 = await client.put("/system/params/X_TEST_PARAM", json={"value": "2"})
        assert r2.status_code == 200
        assert r2.json()["value"] == "2"

    @pytest.mark.asyncio
    async def test_admin_create_and_cancel_reservation(self, client):
        student_id = await register_and_login_student(client)
        seat_id = await get_first_seat_id(client)
        r = await client.post("/reservations/admin/create", json={
            "student_id": student_id,
            "seat_id": seat_id,
            "date": tomorrow_date(),
            "start_time": "13:00:00",
            "end_time": "14:00:00",
        })
        assert r.status_code == 200
        rid = r.json()["id"]
        r2 = await client.delete(f"/reservations/admin/{rid}")
        assert r2.status_code == 200

    @pytest.mark.asyncio
    async def test_seat_admin_delete(self, client):
        rooms = (await client.get("/rooms/admin/all")).json()
        room_id = rooms[0]["id"]
        unique_no = f"D{datetime.now().strftime('%H%M%S%f')}"
        created = await client.post(f"/seats/admin/{room_id}", json={
            "seat_no": unique_no,
            "has_power": 0,
            "by_window": 0,
        })
        assert created.status_code == 200
        seat_id = created.json()["id"]
        deleted = await client.delete(f"/seats/admin/{seat_id}")
        assert deleted.status_code == 200

    @pytest.mark.asyncio
    async def test_rbac_role_lifecycle(self, client):
        role = await client.post("/rbac/roles", json={"key": "test_role", "name": "测试角色"})
        assert role.status_code == 200
        role_id = role.json()["id"]
        perms = await client.get("/rbac/permissions")
        assert perms.status_code == 200
        perm_ids = [p["id"] for p in perms.json()[:2]]
        bind = await client.put(f"/rbac/roles/{role_id}/permissions", json={"permission_ids": perm_ids})
        assert bind.status_code == 200

    @pytest.mark.asyncio
    async def test_stats_endpoints(self, client):
        occ = await client.get("/stats/occupancy")
        trend = await client.get("/stats/reservations/trend?days=7")
        assert occ.status_code == 200
        assert trend.status_code == 200
        assert isinstance(occ.json(), list)
        assert isinstance(trend.json(), list)

    @pytest.mark.asyncio
    async def test_notification_logs_endpoint(self, client):
        resp = await client.get("/notifications/logs")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# -------------------------------------------------------
# 6. 健康检查
# -------------------------------------------------------
class TestHealth:

    @pytest.mark.asyncio
    async def test_root(self, client):
        resp = await client.get("/")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
