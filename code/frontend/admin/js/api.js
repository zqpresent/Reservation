const BASE_URL = 'http://localhost:8000';

function getAdminId() { return localStorage.getItem('admin_id'); }
function getAdminRole() { return localStorage.getItem('admin_role'); }
function getAdminName() { return localStorage.getItem('admin_name'); }
function setAdminInfo(id, role, name) {
    localStorage.setItem('admin_id', String(id));
    localStorage.setItem('admin_role', role);
    localStorage.setItem('admin_name', name);
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
};
