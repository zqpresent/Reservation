# 当前实现情况说明

> 第一阶段 Demo 完成状态

---

## 数据库

**技术**：MySQL 8.0，使用 `init.sql` 初始化。

### 表结构

| 表名 | 说明 |
|---|---|
| `student` | 学生账号，字段：学号、密码（bcrypt）、姓名、邮箱、院系 |
| `admin_user` | 管理员账号，字段：用户名、密码、姓名、角色（枚举：super_admin / room_admin / normal_admin） |
| `room` | 自习室，字段：名称、楼栋、归属院系、开放时间、关闭时间、签到码、签到码更新日期 |
| `seat` | 座位，字段：所属自习室、座位编号、有插座、靠窗、是否可用 |
| `reservation` | 预约记录，字段：学生、座位、开始时间、结束时间、状态（pending / checked_in / cancelled / violated） |
| `violation` | 违约记录，字段：学生、对应预约、违约时间 |

### 初始数据

- 自习室：图书馆A区（10个座位）、图书馆B区（5个座位，全校通用）、计算机学院自习室（院系限定）
- 默认超级管理员账号：`admin` / `admin123`

---

## 后端

**技术**：Python 3.10 + FastAPI + SQLAlchemy + PyMySQL，运行在 `localhost:8000`。

### 已实现接口

#### 认证（`/auth`）
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/auth/register` | 学生注册 |
| POST | `/auth/login` | 学生登录，返回 token 和 student_id |
| POST | `/auth/admin/login` | 管理员登录 |
| GET | `/auth/me?student_id=` | 获取当前学生信息 |

#### 自习室（`/rooms`）
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/rooms` | 查询可用自习室列表（按院系过滤，无需登录） |
| GET | `/rooms/{id}` | 查询单个自习室详情 |
| GET | `/rooms/{id}/seats` | 查询教室内所有座位 |
| POST | `/rooms/admin` | 管理员新增自习室 |
| PUT | `/rooms/admin/{id}` | 管理员修改自习室 |
| DELETE | `/rooms/admin/{id}` | 管理员注销自习室 |

#### 座位（`/seats`）
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/seats/search` | 搜索可用座位（按日期、时间段、插座、靠窗、自习室筛选） |
| POST | `/seats/admin/{room_id}` | 管理员新增座位 |
| PUT | `/seats/admin/{seat_id}` | 管理员更新座位属性 |

#### 预约（`/reservations`）
| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/reservations` | 新增预约（传入 student_id、seat_id、date、start_time、end_time） |
| GET | `/reservations?student_id=&status=` | 查询预约列表 |
| DELETE | `/reservations/{id}` | 取消预约 |
| POST | `/reservations/checkin` | 签到（输入教室当日动态码） |
| GET | `/reservations/admin/all` | 管理员查看所有预约 |
| GET | `/reservations/admin/violations` | 管理员查看违约记录 |

### 后台定时任务（APScheduler）

- **每分钟**：自动取消超过预约开始时间 15 分钟未签到的预约，并生成违约记录
- **每天凌晨**：为每个自习室刷新当日签到码

### 业务规则

- 单次预约最长 4 小时，时间必须为整点
- 冲突检测：同一座位同一时间段不可重复预约
- 签到可提前 5 分钟，超过 15 分钟自动取消
- 院系限制：有院系归属的自习室只对对应院系学生可见

---

## 学生端前端

**技术**：纯 HTML + Tailwind CSS（CDN）+ 原生 JS，运行在 `localhost:3000`。

### 页面说明

#### `login.html` — 登录 / 注册
- 学生使用学号 + 密码登录或注册
- 登录成功后将 `student_id` 存入 `localStorage`，用于后续所有请求

#### `index.html` — 首页
- 展示所有可用自习室卡片，标注开放/关闭状态、开放时间、所属院系
- 显示今日待签到预约提醒
- 点击自习室卡片弹窗查看座位总览（含 🔌 插座、🪟 靠窗标记）

#### `search.html` — 搜索座位 + 预约
- 按日期、开始/结束时间、自习室、有插座、靠窗筛选可用座位
- 搜索结果展示座位卡片，点击弹窗确认预约
- 预约成功后跳转到我的预约页

#### `reservations.html` — 我的预约
- Tab 切换查看：待签到 / 已签到 / 已取消 / 违约取消
- 待签到的预约支持：
  - **签到**：弹窗输入教室当日动态签到码
  - **取消预约**：弹窗二次确认

#### `history.html` — 历史记录
- 顶部统计卡片：历史预约总数 / 成功签到次数 / 违约次数
- 有违约记录时顶部显示警告提示
- 历史列表支持「再次预约」（跳转搜索页）

---

## 启动方式

```bash
# 1. 启动 MySQL
sudo service mysql start

# 2. 初始化数据库（首次）
mysql -u root -proot123 < code/database/init.sql

# 3. 启动后端
cd code/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 4. 启动前端（另开终端）
cd code/frontend-student
python3 -m http.server 3000
```

浏览器访问：`http://localhost:3000/login.html`

后端接口文档：`http://localhost:8000/docs`
