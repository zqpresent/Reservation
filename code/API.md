# 系统架构与接口说明文档

> 自习座位预约系统 · 技术说明

---

## 一、整体架构

```
浏览器（前端）
    │  HTTP 请求 (JSON)
    ▼
FastAPI 后端  ←→  SQLAlchemy ORM  ←→  MySQL 数据库
    │
    └── APScheduler 定时任务（自动处理超时/违约）
```

- **前端**：纯 HTML + Tailwind CSS + Alpine.js，通过 `fetch` 发起 HTTP 请求
- **后端**：FastAPI（Python），监听 `http://localhost:8000`
- **数据库**：MySQL，通过 SQLAlchemy ORM 映射为 Python 对象
- **跨域**：后端配置 `CORS allow_origins=["*"]`，允许本地前端（任意端口）访问

---

## 二、数据库表结构

### 2.1 student（学生）

| 字段          | 类型         | 说明           |
|---------------|--------------|----------------|
| id            | INT PK       | 自增主键       |
| student_no    | VARCHAR(20)  | 学号（唯一）   |
| password      | VARCHAR(255) | bcrypt 哈希    |
| name          | VARCHAR(50)  | 姓名           |
| email         | VARCHAR(100) | 邮箱（可选）   |
| department    | VARCHAR(100) | 学院（可选）   |
| created_at    | DATETIME     | 注册时间       |

### 2.2 admin_user（管理员）

| 字段       | 类型         | 说明                                              |
|------------|--------------|---------------------------------------------------|
| id         | INT PK       | 自增主键                                          |
| username   | VARCHAR(50)  | 用户名（唯一）                                    |
| password   | VARCHAR(255) | bcrypt 哈希                                       |
| name       | VARCHAR(50)  | 显示名                                            |
| role       | ENUM         | `super_admin` / `room_admin` / `normal_admin`     |
| is_active  | INT          | 是否启用（1 启用 / 0 禁用）                       |
| created_at | DATETIME     | 注册时间                                          |

### 2.3 room（自习室）

| 字段           | 类型        | 说明                           |
|----------------|-------------|--------------------------------|
| id             | INT PK      | 自增主键                       |
| name           | VARCHAR(100)| 自习室名称                     |
| building       | VARCHAR(100)| 所在楼栋                       |
| department     | VARCHAR(100)| 所属学院（NULL 表示全校通用）  |
| open_time      | TIME        | 开放时间                       |
| close_time     | TIME        | 关闭时间                       |
| is_active      | INT         | 是否启用                       |
| checkin_code   | VARCHAR(10) | 当日签到码（每日自动更新）     |
| code_updated_at| DATE        | 签到码最后更新日期             |

### 2.4 seat（座位）

| 字段      | 类型        | 说明                     |
|-----------|-------------|--------------------------|
| id        | INT PK      | 自增主键                 |
| room_id   | INT FK      | 所属自习室               |
| seat_no   | VARCHAR(20) | 座位编号（如 "A01"）     |
| has_power | INT         | 是否有插座（1/0）        |
| by_window | INT         | 是否靠窗（1/0）          |
| is_active | INT         | 是否启用                 |

### 2.5 reservation（预约）

| 字段       | 类型     | 说明                                                              |
|------------|----------|-------------------------------------------------------------------|
| id         | INT PK   | 自增主键                                                          |
| student_id | INT FK   | 关联 student.id                                                   |
| seat_id    | INT FK   | 关联 seat.id                                                      |
| start_time | DATETIME | 预约开始时间                                                      |
| end_time   | DATETIME | 预约结束时间                                                      |
| status     | ENUM     | `pending`（待签到）/ `checked_in`（已签到）/ `cancelled`（已取消）/ `violated`（违约） |
| created_at | DATETIME | 创建时间                                                          |

### 2.6 violation（违约记录）

| 字段           | 类型     | 说明            |
|----------------|----------|-----------------|
| id             | INT PK   | 自增主键        |
| student_id     | INT FK   | 关联 student.id |
| reservation_id | INT FK   | 关联 reservation.id |
| violated_at    | DATETIME | 违约时间        |

---

## 三、后端与数据库的连接方式

```
后端 (Python) → SQLAlchemy → PyMySQL driver → MySQL
```

1. `database.py` 读取 `.env` 中的 `DATABASE_URL` 创建 `engine`
2. `models.py` 定义 ORM 模型类（每个类对应一张表）
3. 路由函数通过 `db: Session = Depends(database.get_db)` 获取数据库会话
4. 所有增删改查均通过 `db.query(...)` / `db.add()` / `db.commit()` 完成

---

## 四、API 接口清单

### 基础说明

- **Base URL**：`http://localhost:8000`
- **数据格式**：请求体和响应体均为 JSON
- **认证**：Demo 阶段已移除 Token 强制验证，`student_id` / `admin_id` 直接通过参数传递

---

### 4.1 认证模块 `/auth`

#### `POST /auth/register` — 学生注册

**请求体：**
```json
{
  "student_no": "22300000",
  "password": "123456",
  "name": "张三",
  "email": "zhangsan@example.com",
  "department": "计算机科学学院"
}
```

**响应：**
```json
{
  "id": 1,
  "student_no": "22300000",
  "name": "张三",
  "email": "zhangsan@example.com",
  "department": "计算机科学学院"
}
```

**数据库操作：** 向 `student` 表插入一条记录，密码先经 bcrypt 哈希处理。

---

#### `POST /auth/login` — 学生登录

**请求体：**
```json
{ "student_no": "22300000", "password": "123456" }
```

**响应：**
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user_type": "student",
  "student_id": 1
}
```

**数据库操作：** 查询 `student` 表，验证密码哈希；返回的 `student_id` 由前端存入 `localStorage`，后续请求携带此 ID 代替 Token。

---

#### `GET /auth/me?student_id=1` — 获取学生信息

**查询参数：** `student_id`（必填）

**响应：** 返回该学生的基本信息（同注册响应结构）

**数据库操作：** 按 `id` 查询 `student` 表。

---

#### `POST /auth/admin/register` — 管理员注册

**请求体：**
```json
{
  "username": "admin01",
  "password": "123456",
  "name": "管理员甲",
  "role": "normal_admin"
}
```

**响应：** 返回管理员基本信息。

**数据库操作：** 向 `admin_user` 表插入记录。

---

#### `POST /auth/admin/login` — 管理员登录

**请求体：**
```json
{ "username": "admin01", "password": "123456" }
```

**响应：**
```json
{
  "access_token": "<jwt>",
  "token_type": "bearer",
  "user_type": "admin",
  "admin_id": 1,
  "admin_role": "normal_admin",
  "admin_name": "管理员甲"
}
```

**数据库操作：** 查询 `admin_user` 表，验证密码，检查 `is_active`；前端将 `admin_id`、`admin_role`、`admin_name` 存入 `localStorage`。

---

### 4.2 自习室模块 `/rooms`

#### `GET /rooms` — 学生查询可用自习室

**说明：** 若请求携带有效 Token 且学生有院系信息，则返回全校通用 + 本院系自习室；否则只返回全校通用（`department = NULL`）。

**响应：**
```json
[
  {
    "id": 1,
    "name": "图书馆一楼自习室",
    "building": "图书馆",
    "department": null,
    "open_time": "08:00:00",
    "close_time": "22:00:00",
    "is_active": 1
  }
]
```

**数据库操作：** 查询 `room` 表，`is_active = 1`，按院系过滤。

---

#### `GET /rooms/{room_id}` — 查询单个自习室详情

**路径参数：** `room_id`

**数据库操作：** 按主键查询 `room` 表。

---

#### `GET /rooms/{room_id}/seats` — 查询教室内所有座位

**响应：**
```json
[
  { "id": 1, "room_id": 1, "seat_no": "A01", "has_power": 1, "by_window": 0, "is_active": 1 }
]
```

**数据库操作：** 查询 `seat` 表，过滤 `room_id` 和 `is_active = 1`。

---

#### `GET /rooms/admin/all` — 管理员查询所有自习室（含未启用）

**数据库操作：** 查询 `room` 表全部记录（不过滤 `is_active`）。

---

#### `POST /rooms/admin` — 管理员新增自习室

**请求体：**
```json
{
  "name": "新自习室",
  "building": "教学楼",
  "department": null,
  "open_time": "08:00",
  "close_time": "22:00"
}
```

**数据库操作：** 向 `room` 表插入记录。

---

#### `PUT /rooms/admin/{room_id}` — 管理员修改自习室

**请求体：** 同新增，字段均为可选（仅传需要修改的字段）。

**数据库操作：** 按主键更新 `room` 表对应字段。

---

#### `DELETE /rooms/admin/{room_id}` — 管理员注销自习室

**说明：** 软删除，将 `is_active` 置为 `0`，不删除记录。

---

### 4.3 座位模块 `/seats`

#### `GET /seats/search` — 搜索可用座位

**查询参数：**

| 参数       | 类型   | 必填 | 说明                      |
|------------|--------|------|---------------------------|
| date       | string | 是   | 日期，格式 `YYYY-MM-DD`   |
| start_time | string | 是   | 开始时间，格式 `HH:MM:SS` |
| end_time   | string | 是   | 结束时间，格式 `HH:MM:SS` |
| has_power  | int    | 否   | 需要插座传 `1`            |
| by_window  | int    | 否   | 需要靠窗传 `1`            |
| room_id    | int    | 否   | 限定自习室                |

**搜索逻辑：**
1. 查询满足属性条件的所有活跃座位
2. 从中排除该时间段内已有 `pending` 或 `checked_in` 状态预约的座位
3. 返回剩余可用座位列表

**响应：** 每条数据包含座位信息及所属自习室名称（`room_name`）。

**数据库操作：** 联表查询 `seat` + `room`；子查询 `reservation` 表排除冲突座位。

---

#### `POST /seats/admin/{room_id}` — 管理员新增座位

**请求体：**
```json
{ "seat_no": "B02", "has_power": 1, "by_window": 0 }
```

**数据库操作：** 检查座位编号不重复后向 `seat` 表插入。

---

#### `PUT /seats/admin/{seat_id}` — 管理员更新座位属性

**查询参数：** `has_power`、`by_window`、`is_active`（均为整数 0/1，传哪个改哪个）

**数据库操作：** 按主键更新 `seat` 表。

---

### 4.4 预约模块 `/reservations`

#### `POST /reservations` — 学生新增预约

**请求体：**
```json
{
  "seat_id": 1,
  "date": "2026-03-21",
  "start_time": "09:00:00",
  "end_time": "11:00:00",
  "student_id": 1
}
```

**业务逻辑：**
1. 校验时长（1～4 小时）
2. 检查座位是否存在且可用
3. 检测时间冲突（同一座位同一时段不能有 `pending`/`checked_in` 预约）
4. 写入 `reservation` 表，状态默认 `pending`

**响应：** 返回完整预约信息，含 `room_name`、`seat_no`、`has_power`、`by_window`。

**数据库操作：** 查询 `seat` 表验证存在；查询 `reservation` 表检测冲突；插入新记录。

---

#### `GET /reservations` — 查询预约列表

**查询参数：**

| 参数       | 类型   | 说明                                          |
|------------|--------|-----------------------------------------------|
| student_id | int    | 只返回该学生的预约（学生端传自己的 ID）       |
| status     | string | 按状态过滤：`pending` / `checked_in` / `cancelled` / `violated` |

**数据库操作：** 联表查询 `reservation` + `seat` + `room`，按时间倒序。

---

#### `DELETE /reservations/{reservation_id}` — 取消预约

**说明：** 只有 `pending` 状态的预约可以取消，取消后状态改为 `cancelled`。

**数据库操作：** 按主键查询并更新 `reservation` 表。

---

#### `POST /reservations/checkin` — 签到

**请求体：**
```json
{ "reservation_id": 1, "checkin_code": "AB12" }
```

**业务逻辑：**
1. 校验预约状态为 `pending`
2. 允许提前 5 分钟签到，超过开始时间 15 分钟则拒绝
3. 对比自习室当日签到码（`room.checkin_code` 且 `code_updated_at == 今日`）
4. 通过后将状态改为 `checked_in`

**数据库操作：** 查询 `reservation`、`seat`、`room` 表；更新预约状态。

---

#### `GET /reservations/admin/all` — 管理员查看所有预约

**查询参数：** `status`、`student_id`、`room_id`（均可选）

**数据库操作：** 联表查询，支持多条件过滤。

---

#### `GET /reservations/admin/violations` — 管理员查看违约记录

**响应：**
```json
[
  {
    "id": 1,
    "student_id": 1,
    "student_name": "张三",
    "student_no": "22300000",
    "reservation_id": 5,
    "violated_at": "2026-03-21T10:15:00"
  }
]
```

**数据库操作：** 联表查询 `violation` + `student` + `reservation`，按时间倒序。

---

## 五、前端与后端的调用方式

### 统一请求封装（`js/api.js`）

前端通过封装的 `request` 函数发起所有请求：

```javascript
async function request(method, path, body = null) {
    const headers = { 'Content-Type': 'application/json' };
    const options = { method, headers };
    if (body) options.body = JSON.stringify(body);

    const resp = await fetch('http://localhost:8000' + path, options);
    const data = await resp.json();

    if (!resp.ok) {
        const err = new Error(data.detail || '请求失败');
        err.status = resp.status;
        throw err;
    }
    return data;
}
```

### 登录态管理

| 端     | 存储键                           | 说明                     |
|--------|----------------------------------|--------------------------|
| 学生端 | `localStorage.student_id`        | 登录后存储，请求时附带   |
| 管理端 | `localStorage.admin_id`          | 登录后存储               |
| 管理端 | `localStorage.admin_role`        | 用于前端页面权限判断     |
| 管理端 | `localStorage.admin_name`        | 用于显示当前登录人姓名   |

> **注意**：从统一入口（`index.html`）进入时会自动清空对应端的 `localStorage`，确保每次都需要重新登录。

---

## 六、定时任务说明

后端启动时由 `APScheduler` 注册两个定时任务：

| 任务               | 触发频率 | 逻辑                                                                     |
|--------------------|----------|--------------------------------------------------------------------------|
| 超时未签到处理     | 每 5 分钟 | 将开始时间已过 15 分钟且仍为 `pending` 的预约改为 `violated`，并在 `violation` 表写入违约记录 |
| 更新每日签到码     | 每天 0 时 | 为所有活跃自习室生成新的 4 位随机签到码，更新 `room.checkin_code` 和 `code_updated_at` |
