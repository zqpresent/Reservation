-- 自习座位预约系统 数据库初始化脚本
-- Demo 阶段核心表

CREATE DATABASE IF NOT EXISTS study_room DEFAULT CHARACTER SET utf8mb4;
USE study_room;

-- -------------------------------------------------------
-- 1. 学生表
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS student (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    student_no  VARCHAR(20)  NOT NULL UNIQUE COMMENT '学号',
    password    VARCHAR(255) NOT NULL COMMENT '密码（bcrypt哈希）',
    name        VARCHAR(50)  NOT NULL COMMENT '姓名',
    email       VARCHAR(100) COMMENT '邮箱（用于推送提醒）',
    department  VARCHAR(100) COMMENT '所属院系',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
) COMMENT='学生账号';

-- -------------------------------------------------------
-- 2. 管理员表
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS admin_user (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    username    VARCHAR(50)  NOT NULL UNIQUE COMMENT '用户名',
    password    VARCHAR(255) NOT NULL COMMENT '密码（bcrypt哈希）',
    name        VARCHAR(50)  NOT NULL COMMENT '姓名',
    role        ENUM('super_admin', 'room_admin', 'normal_admin') NOT NULL DEFAULT 'normal_admin' COMMENT '角色',
    is_active   TINYINT(1) DEFAULT 1 COMMENT '是否启用',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
) COMMENT='管理员账号（Demo阶段用枚举简化，第二阶段替换为RBAC表）';

-- -------------------------------------------------------
-- 3. 自习室表
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS room (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    name            VARCHAR(100) NOT NULL COMMENT '自习室名称，如"图书馆B区"',
    building        VARCHAR(100) COMMENT '所在楼栋',
    department      VARCHAR(100) COMMENT '归属院系（NULL表示全校通用）',
    open_time       TIME NOT NULL DEFAULT '07:00:00' COMMENT '每日开放时间',
    close_time      TIME NOT NULL DEFAULT '22:00:00' COMMENT '每日关闭时间',
    is_active       TINYINT(1) DEFAULT 1 COMMENT '是否上线可用',
    checkin_code    VARCHAR(10) COMMENT '当日签到编码（每天刷新）',
    code_updated_at DATE COMMENT '编码最后更新日期',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
) COMMENT='自习室';

-- -------------------------------------------------------
-- 4. 座位表
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS seat (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    room_id         INT          NOT NULL COMMENT '所属自习室',
    seat_no         VARCHAR(20)  NOT NULL COMMENT '座位编号，如"A-01"',
    has_power       TINYINT(1) DEFAULT 0 COMMENT '是否有插座',
    by_window       TINYINT(1) DEFAULT 0 COMMENT '是否靠窗',
    is_active       TINYINT(1) DEFAULT 1 COMMENT '是否可用',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_room_seat (room_id, seat_no),
    FOREIGN KEY (room_id) REFERENCES room(id) ON DELETE CASCADE
) COMMENT='座位';

-- -------------------------------------------------------
-- 5. 预约记录表
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS reservation (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    student_id      INT          NOT NULL COMMENT '预约学生',
    seat_id         INT          NOT NULL COMMENT '预约座位',
    start_time      DATETIME     NOT NULL COMMENT '预约开始时间（整点）',
    end_time        DATETIME     NOT NULL COMMENT '预约结束时间（整点）',
    status          ENUM('pending', 'checked_in', 'cancelled', 'violated') NOT NULL DEFAULT 'pending'
                    COMMENT 'pending=待签到 checked_in=已签到 cancelled=已取消 violated=违约取消',
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES student(id),
    FOREIGN KEY (seat_id)    REFERENCES seat(id)
) COMMENT='预约记录';

-- -------------------------------------------------------
-- 6. 违约记录表
-- -------------------------------------------------------
CREATE TABLE IF NOT EXISTS violation (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    student_id      INT      NOT NULL COMMENT '违约学生',
    reservation_id  INT      NOT NULL COMMENT '对应的预约记录',
    violated_at     DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '违约时间',
    FOREIGN KEY (student_id)     REFERENCES student(id),
    FOREIGN KEY (reservation_id) REFERENCES reservation(id)
) COMMENT='违约记录';

-- -------------------------------------------------------
-- 初始化演示数据
-- -------------------------------------------------------

-- 默认超级管理员（密码: admin123，实际存储时需bcrypt哈希，此处用占位符）
INSERT INTO admin_user (username, password, name, role) VALUES
('admin', '$2b$12$placeholder_will_be_replaced_by_backend', '超级管理员', 'super_admin');

-- 示例自习室
INSERT INTO room (name, building, department, open_time, close_time) VALUES
('图书馆自习室A区', '图书馆', NULL,       '07:00:00', '22:00:00'),
('图书馆自习室B区', '图书馆', NULL,       '07:00:00', '22:00:00'),
('计算机学院自习室', '计算机楼', '计算机学院', '08:00:00', '22:00:00');

-- 示例座位（图书馆A区 10个座位）
INSERT INTO seat (room_id, seat_no, has_power, by_window) VALUES
(1, 'A-01', 1, 0),
(1, 'A-02', 1, 0),
(1, 'A-03', 0, 1),
(1, 'A-04', 0, 1),
(1, 'A-05', 0, 0),
(1, 'A-06', 1, 1),
(1, 'A-07', 0, 0),
(1, 'A-08', 0, 0),
(1, 'A-09', 1, 0),
(1, 'A-10', 0, 1);

-- 示例座位（图书馆B区 5个座位）
INSERT INTO seat (room_id, seat_no, has_power, by_window) VALUES
(2, 'B-01', 0, 1),
(2, 'B-02', 1, 0),
(2, 'B-03', 0, 0),
(2, 'B-04', 1, 1),
(2, 'B-05', 0, 0);
