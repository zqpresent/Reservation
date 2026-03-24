const BASE_URL = 'http://localhost:8000';

function getToken() {
    return localStorage.getItem('token');
}

function setToken(token) {
    localStorage.setItem('token', token);
}

function getStudentId() {
    return localStorage.getItem('student_id');
}

function setStudentId(id) {
    localStorage.setItem('student_id', String(id));
}

function clearToken() {
    localStorage.removeItem('token');
    localStorage.removeItem('student_id');
    localStorage.removeItem('user');
}

async function request(method, path, body = null) {
    const headers = { 'Content-Type': 'application/json' };
    const options = { method, headers };
    if (body) options.body = JSON.stringify(body);

    const resp = await fetch(BASE_URL + path, options);
    const data = await resp.json();

    if (!resp.ok) {
        const msg = data.detail || '请求失败';
        const err = new Error(msg);
        err.status = resp.status;
        throw err;
    }
    return data;
}

const api = {
    register: (data) => request('POST', '/auth/register', data),
    login: (data) => request('POST', '/auth/login', data),
    getMe: () => request('GET', `/auth/me?student_id=${getStudentId()}`),

    getRooms: () => request('GET', '/rooms'),
    getRoomSeats: (roomId) => request('GET', `/rooms/${roomId}/seats`),

    searchSeats: (params) => {
        const q = new URLSearchParams(params).toString();
        return request('GET', `/seats/search?${q}`);
    },

    createReservation: (data) => request('POST', '/reservations', {
        ...data,
        student_id: parseInt(getStudentId())
    }),

    getMyReservations: (status = '') => {
        const sid = getStudentId();
        const q = new URLSearchParams();
        if (sid) q.append('student_id', sid);
        if (status) q.append('status', status);
        return request('GET', `/reservations?${q.toString()}`);
    },

    cancelReservation: (id) => request('DELETE', `/reservations/${id}`),
    checkIn: (data) => request('POST', '/reservations/checkin', data),
};
