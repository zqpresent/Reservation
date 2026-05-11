const BASE_URL = 'http://localhost:8000';

function getAdminId() { return localStorage.getItem('admin_id'); }
function getAdminRole() { return localStorage.getItem('admin_role'); }
function getAdminName() { return localStorage.getItem('admin_name'); }
function getAdminToken() { return localStorage.getItem('admin_token'); }
function hasAdminAuth() { return !!getAdminId(); }
function setAdminInfo(id, role, name, token = null) {
    localStorage.setItem('admin_id', String(id));
    localStorage.setItem('admin_role', role);
    localStorage.setItem('admin_name', name);
    if (token) localStorage.setItem('admin_token', token);
}
function clearAdmin() {
    ['admin_id','admin_role','admin_name','admin_token'].forEach(k => localStorage.removeItem(k));
}

async function request(method, path, body = null) {
    const headers = { 'Content-Type': 'application/json' };
    const options = { method, headers };
    if (body) options.body = JSON.stringify(body);
    const resp = await fetch(BASE_URL + path, options);
    const data = await resp.json();
    if (!resp.ok) {
        const err = new Error(data.detail || '请求失败');
        err.status = resp.status;
        throw err;
    }
    return data;
}

const api = {
    // 认证
    adminLogin: (data) => request('POST', '/auth/admin/login', data),
    adminRegister: (data) => request('POST', '/auth/admin/register', data),

    // 自习室
    getAllRooms: () => request('GET', '/rooms/admin/all'),
    createRoom: (data) => request('POST', '/rooms/admin', data),
    updateRoom: (id, data) => request('PUT', `/rooms/admin/${id}`, data),
    deleteRoom: (id) => request('DELETE', `/rooms/admin/${id}`),
    getRoomSeats: (roomId) => request('GET', `/rooms/${roomId}/seats`),

    // 座位
    createSeat: (roomId, data) => request('POST', `/seats/admin/${roomId}`, data),
    deleteSeat: (seatId) => request('DELETE', `/seats/admin/${seatId}`),
    updateSeat: (seatId, params) => {
        const q = new URLSearchParams(params).toString();
        return request('PUT', `/seats/admin/${seatId}?${q}`);
    },

    // 预约
    getAllReservations: (params = {}) => {
        const q = new URLSearchParams(params).toString();
        return request('GET', `/reservations/admin/all${q ? '?' + q : ''}`);
    },
    cancelReservation: (id) => request('DELETE', `/reservations/${id}`),

    // 违约
    getViolations: () => request('GET', '/reservations/admin/violations'),
    getViolationSummary: () => request('GET', '/reservations/admin/violations/summary'),

    // 代学生预约
    adminCreateReservation: (data) => request('POST', '/reservations/admin/create', data),
    adminCancelReservation: (id) => request('DELETE', `/reservations/admin/${id}`),

    // 通知
    getNotificationLogs: (params = {}) => {
        const q = new URLSearchParams(params).toString();
        return request('GET', `/notifications/logs${q ? '?' + q : ''}`);
    },

    // RBAC
    getPermissions: () => request('GET', '/rbac/permissions'),
    getRoles: () => request('GET', '/rbac/roles'),
    createRole: (data) => request('POST', '/rbac/roles', data),
    updateRole: (id, data) => request('PUT', `/rbac/roles/${id}`, data),
    updateRolePermissions: (id, permission_ids) => request('PUT', `/rbac/roles/${id}/permissions`, { permission_ids }),
    getAdminUsersForRbac: () => request('GET', '/rbac/admin-users'),
    assignAdminRoles: (adminId, role_ids) => request('PUT', `/rbac/admin-users/${adminId}/roles`, { role_ids }),
    getMyMenus: () => request('GET', `/rbac/me/menus?admin_id=${getAdminId()}`),

    // 管理员账号
    getAdminUsers: () => request('GET', '/auth/admin/users'),
    updateAdminStatus: (adminId, isActive) => request('PUT', `/auth/admin/users/${adminId}/status?is_active=${isActive}`),
    deleteAdminUser: (adminId) => request('DELETE', `/auth/admin/users/${adminId}`),

    // 系统参数
    getSystemParams: () => request('GET', '/system/params'),
    updateSystemParam: (key, value) => request('PUT', `/system/params/${key}`, { value }),
    batchUpdateSystemParams: (items) => request('PUT', '/system/params', { items }),

    // 统计
    getOccupancyStats: (params = {}) => {
        const q = new URLSearchParams(params).toString();
        return request('GET', `/stats/occupancy${q ? '?' + q : ''}`);
    },
    getReservationTrend: (days = 7) => request('GET', `/stats/reservations/trend?days=${days}`),
};
