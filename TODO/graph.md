# 自习座位预约系统 - 需求思维导图

> 按 Feature → Story → Task 三层展开。✅ 已实现　⬜ 待实现
> 🔵 后端　🟢 学生端前端　🟠 管理端前端

---

```
自习座位预约系统
│
├── Feature 1：账号与登录
│   ├── Story US-001/002/003 学生注册、登录、退出 ✅
│   │   ├── Task 🔵 /auth/register、/auth/login 接口
│   │   └── Task 🟢 登录注册页面（login.html）
│   └── Story US-031 管理员登录与注册 ✅
│       ├── Task 🔵 /auth/admin/login、/auth/admin/register 接口
│       └── Task 🟠 管理员登录页面（login.html）
│
├── Feature 2：自习室与座位查看
│   ├── Story US-004/005/006 查看自习室列表、开放时间、院系过滤 ✅
│   │   ├── Task 🔵 GET /rooms 接口（含院系过滤）
│   │   └── Task 🟢 首页自习室卡片（index.html）
│   └── Story US-007/008 查看座位状态与特殊标记 ✅
│       ├── Task 🔵 GET /rooms/{id}/seats 接口
│       └── Task 🟢 座位列表展示（search.html）
│
├── Feature 3：座位搜索
│   └── Story US-014~017 按时间、插座、靠窗、自习室搜索 ✅
│       ├── Task 🔵 GET /seats/search 接口（冲突排除 + 多参数过滤）
│       └── Task 🟢 搜索表单与结果展示（search.html）
│
├── Feature 4：座位预约
│   ├── Story US-009~012 按整点预约、最多4小时、冲突检测、确认提示 ✅
│   │   ├── Task 🔵 POST /reservations 接口（时长校验 + 冲突检测）
│   │   └── Task 🟢 预约确认弹窗（search.html）
│   └── Story US-013 取消预约 ✅
│       ├── Task 🔵 DELETE /reservations/{id} 接口
│       └── Task 🟢 取消按钮（reservations.html）
│
├── Feature 5：签到
│   ├── Story US-018 Web端输入动态编码签到 ✅
│   │   ├── Task 🔵 POST /reservations/checkin 接口 + 每日刷新签到码定时任务
│   │   └── Task 🟢 签到码输入（reservations.html）
│   └── Story US-019 微信小程序扫码签到 ⬜
│       └── Task 🟢 小程序二维码扫描页面
│
├── Feature 6：提醒与违约
│   ├── Story US-021/022 预约前15分钟、超时10分钟推送提醒 ⬜
│   │   └── Task 🔵 APScheduler 定时任务 + 邮件推送
│   └── Story US-023 超时15分钟自动取消并记录违约 ✅
│       └── Task 🔵 自动取消 + 写入 violation 表（定时任务）
│
├── Feature 7：历史记录
│   └── Story US-024/025/026 历史预约、一键再次预约、违约记录 ✅
│       ├── Task 🔵 GET /reservations?student_id= 接口
│       └── Task 🟢 历史记录与违约页面（history.html）
│
├── Feature 8：智能助手
│   └── Story US-027~030 自然语言查询空座、按偏好找座、查预约、直接预约 ⬜
│       ├── Task 🔵 大语言模型接口集成 + 意图解析
│       └── Task 🟢 聊天框 UI（学生端）
│
├── Feature 9：自习室与座位管理（管理端）
│   ├── Story US-031~034 新增、编辑、注销自习室、设置院系限制 ✅
│   │   ├── Task 🔵 POST/PUT/DELETE /rooms/admin 接口
│   │   └── Task 🟠 自习室管理页面（rooms.html）
│   └── Story US-035~038 登记、编辑、禁用、注销座位 ✅/⬜
│       ├── Task 🔵 POST/PUT /seats/admin 接口
│       └── Task 🟠 座位管理弹窗（rooms.html）
│
├── Feature 10：预约与违约管理（管理端）
│   └── Story US-039~042 查看/取消预约、代为预约、查看违约记录 ✅/⬜
│       ├── Task 🔵 GET /reservations/admin/all、/violations 接口
│       └── Task 🟠 预约列表与违约记录页面（reservations.html、violations.html）
│
├── Feature 11：RBAC 与系统参数（管理端）
│   ├── Story US-043~046 角色管理、权限分配、按角色展示菜单 ⬜
│   │   ├── Task 🔵 角色 CRUD 接口
│   │   └── Task 🟠 角色管理页面 + 前端权限路由
│   └── Story US-047~049 调整最大预约时长、签到超时、提醒时间 ✅/⬜
│       ├── Task 🔵 系统参数在线配置接口
│       └── Task 🟠 参数配置页面
│
├── Feature 12：数据统计（管理端）
│   └── Story US-050/051 座位占用率、近期预约趋势 ⬜
│       ├── Task 🔵 统计与趋势查询接口
│       └── Task 🟠 图表展示（index.html）
│
└── Feature 13：DevOps
    ├── Task：代码仓库托管（DevCloud / GitHub）⬜
    ├── Task：编译构建 + 自动化测试（pytest）⬜
    └── Task：CI/CD 流水线配置与自动部署 ⬜
```

---

## 完成情况统计

| Feature | ✅ 已完成 | ⬜ 待完成 |
|---------|---------|-----------|
| 账号与登录 | ✅ | — |
| 自习室与座位查看 | ✅ | — |
| 座位搜索 | ✅ | — |
| 座位预约 | ✅ | — |
| 签到 | Web端✅ | 小程序⬜ |
| 提醒与违约 | 自动取消✅ | 消息推送⬜ |
| 历史记录 | ✅ | — |
| 智能助手 | — | ⬜ |
| 自习室与座位管理 | 大部分✅ | 注销座位⬜ |
| 预约与违约管理 | 大部分✅ | 代为预约⬜ |
| RBAC 与系统参数 | 基础✅ | 完整实现⬜ |
| 数据统计 | — | ⬜ |
| DevOps | — | ⬜ |
