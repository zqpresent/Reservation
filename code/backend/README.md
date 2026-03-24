# 后端说明

## 技术栈
- **框架**：FastAPI
- **ORM**：SQLAlchemy 2.0
- **数据库驱动**：PyMySQL
- **认证**：JWT（python-jose）+ bcrypt 密码哈希
- **定时任务**：APScheduler
- **Python 版本**：3.11+

## 目录结构

```
backend/
├── main.py             # 应用入口，注册路由、启动定时任务
├── database.py         # 数据库连接配置
├── models.py           # SQLAlchemy 数据模型
├── schemas.py          # Pydantic 请求/响应结构
├── auth.py             # JWT 生成/验证、权限依赖
├── scheduler.py        # 定时任务（超时取消、签到码刷新）
├── routers/
│   ├── auth.py         # 登录注册接口
│   ├── rooms.py        # 自习室接口
│   ├── seats.py        # 座位接口
│   └── reservations.py # 预约接口
├── requirements.txt
├── Dockerfile
└── .env.example        # 环境变量模板
```

## 本地启动

**1. 安装依赖**
```bash
cd backend
pip install -r requirements.txt
```

**2. 配置环境变量**
```bash
cp .env.example .env
# 编辑 .env，填入数据库密码和 JWT_SECRET
```

**3. 确保 MySQL 已运行并初始化数据库**
```bash
mysql -u root -p < ../database/init.sql
```

**4. 启动服务**
```bash
uvicorn main:app --reload --port 8000
```

启动后访问：
- 接口文档（Swagger UI）：http://localhost:8000/docs
- 健康检查：http://localhost:8000/

## 接口一览

### 认证
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/auth/register` | 学生注册 |
| POST | `/auth/login` | 学生登录 |
| POST | `/auth/admin/login` | 管理员登录 |
| GET | `/auth/me` | 获取当前学生信息 |
| GET | `/auth/admin/me` | 获取当前管理员信息 |

### 自习室
| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/rooms` | 学生 | 查询对我可见的自习室 |
| GET | `/rooms/{id}` | 学生 | 查询单个自习室 |
| GET | `/rooms/{id}/seats` | 学生 | 查询教室内座位 |
| GET | `/rooms/admin/all` | 管理员 | 查询所有自习室 |
| POST | `/rooms/admin` | room_admin+ | 新增自习室 |
| PUT | `/rooms/admin/{id}` | room_admin+ | 修改自习室 |
| DELETE | `/rooms/admin/{id}` | room_admin+ | 注销自习室 |

### 座位
| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/seats/search` | 学生 | 按条件搜索可用座位 |
| POST | `/seats/admin/{room_id}` | room_admin+ | 新增座位 |
| PUT | `/seats/admin/{seat_id}` | room_admin+ | 更新座位属性 |

### 预约
| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/reservations` | 学生 | 新增预约 |
| GET | `/reservations` | 学生 | 查询我的预约 |
| DELETE | `/reservations/{id}` | 学生 | 取消预约 |
| POST | `/reservations/checkin` | 学生 | 签到 |
| GET | `/reservations/admin/all` | 管理员 | 查看所有预约 |
| GET | `/reservations/admin/violations` | 管理员 | 查看违约记录 |

## 认证方式

所有需要登录的接口，请求头中携带：
```
Authorization: Bearer <token>
```

Token 通过登录接口获取，有效期 8 小时（可在 .env 中调整 `JWT_EXPIRE_MINUTES`）。

## 定时任务说明

| 任务 | 触发频率 | 说明 |
|---|---|---|
| `auto_cancel_overdue` | 每1分钟 | 检查超时15分钟未签到的预约，自动改为 violated 状态并写入违约表 |
| `refresh_checkin_codes` | 每天0点 | 为所有可用自习室生成新的6位数字签到码 |

## 管理员角色权限

| 角色 | 说明 | 可用接口 |
|---|---|---|
| `normal_admin` | 普通管理员 | 查看预约、违约记录 |
| `room_admin` | 教室管理员 | 自习室/座位增删改 |
| `super_admin` | 超级管理员 | 所有接口 |

默认超级管理员账号：`admin`，密码在 `.env` 的 `INIT_ADMIN_PASSWORD` 中配置（默认 `admin123`）。
