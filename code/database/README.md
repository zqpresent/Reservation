# 数据库设计说明

## 技术选型
- **数据库**：MySQL 8.0
- **字符集**：utf8mb4（支持中文及 emoji）

## 表结构总览

```
student          学生账号
admin_user       管理员账号
room             自习室
seat             座位
reservation      预约记录
violation        违约记录
```

## 表关系

```
room  1──N  seat  1──N  reservation  N──1  student
                              |
                              1
                              |
                          violation
```

## 核心设计说明

### reservation.status 枚举值
| 值 | 含义 |
|---|---|
| `pending` | 已预约，待签到 |
| `checked_in` | 已签到，正在使用 |
| `cancelled` | 学生主动取消 |
| `violated` | 超时未签到，系统自动取消并记录违约 |

### room.checkin_code
每日由后端定时任务刷新的 4-6 位动态编码，学生 Web 端签到时输入此编码。`code_updated_at` 记录最后刷新日期，后端每次签到前检查是否需要刷新。

### room.department / student.department
`room.department` 为 NULL 表示全校通用；有值则仅对该院系的学生开放。后端在返回自习室列表时，根据当前登录学生的院系进行过滤。

### admin_user.role（Demo 阶段）
Demo 阶段用枚举简化权限控制，第二阶段替换为完整的 RBAC 三表结构（role、permission、role_permission）。

## 如何初始化

```bash
mysql -u root -p < init.sql
```

或通过 docker-compose 启动时会自动执行（挂载到 `/docker-entrypoint-initdb.d/`）。

## 演示数据说明
脚本末尾插入了：
- 1 个超级管理员账号（用户名 `admin`，密码由后端初始化时生成）
- 3 个自习室（图书馆A区、B区，以及计算机学院专属）
- 15 个座位（含插座/靠窗等不同属性）
