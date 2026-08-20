document.addEventListener('DOMContentLoaded', () => {
    const loginScreen = document.getElementById('login-screen');
    const dashboardScreen = document.getElementById('dashboard-screen');
    const loginForm = document.getElementById('login-form');
    const loginError = document.getElementById('login-error');
    
    const BASE_URL = '/api/v1';
    
    // Check auth state
    const token = localStorage.getItem('access_token');
    if (token) {
        showDashboard();
    }
    
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const email = document.getElementById('login-email').value;
            const password = document.getElementById('login-password').value;
            
            try {
                const response = await fetch(`${BASE_URL}/accounts/login/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });
                
                const responseData = await response.json();
                
                if (response.ok && responseData.success !== false) {
                    const payload = responseData.data || responseData;
                    if(payload.tokens) {
                        localStorage.setItem('access_token', payload.tokens.access);
                        localStorage.setItem('refresh_token', payload.tokens.refresh);
                        showDashboard();
                    } else {
                        throw new Error('Tokens not received');
                    }
                } else {
                    const errPayload = responseData.errors || responseData;
                    loginError.textContent = errPayload.detail || errPayload.non_field_errors?.[0] || responseData.message || 'Invalid email or password';
                    loginError.style.display = 'block';
                }
            } catch (err) {
                loginError.textContent = 'Network error occurred. ' + err.message;
                loginError.style.display = 'block';
            }
        });
    }
    function showDashboard() {
        if (loginScreen) loginScreen.classList.add('hidden');
        if (dashboardScreen) dashboardScreen.classList.remove('hidden');
        
        if (typeof loadSummary === 'function' && document.getElementById('stat-total-users')) loadSummary();
        if (typeof loadUsers === 'function' && document.getElementById('users-table-body')) loadUsers();
    }
    
    window.apiFetch = async function(endpoint, options = {}) {
        const token = localStorage.getItem('access_token');
        const defaultOptions = {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        };
        const res = await fetch(`${BASE_URL}${endpoint}`, { ...defaultOptions, ...options });
        if (res.status === 401 || res.status === 403) {
            logout();
            if (loginError) {
                loginError.textContent = 'Access denied or session expired. Please log in as an administrator.';
                loginError.style.display = 'block';
            }
        }
        return res;
    }
    
    function logout() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        if (dashboardScreen) dashboardScreen.classList.add('hidden');
        if (loginScreen) loginScreen.classList.remove('hidden');
        if (!loginScreen && !window.location.pathname.endsWith('/dashboard/')) {
            window.location.href = '/dashboard/';
        }
    }
    
    // Load summary stats
    async function loadSummary() {
        try {
            const res = await apiFetch('/core/admin/summary/');
            if (res.ok) {
                const responseData = await res.json();
                const data = responseData.data || responseData;
                console.log('Summary data:', data);
                
                const elTotal = document.getElementById('stat-total-users');
                if(elTotal) elTotal.textContent = data.total_users;
                
                const elPro = document.getElementById('stat-pro-users');
                if(elPro) elPro.textContent = data.pro_users;
                
                const elAudio = document.getElementById('stat-audio-files');
                if(elAudio) elAudio.textContent = data.audio_files;
            }
        } catch (err) {
            console.error('Error fetching summary', err);
        }
    }
    
    async function loadUsers() {
        try {
            const res = await apiFetch('/accounts/users/');
            if (res.ok) {
                const responseData = await res.json();
                const data = responseData.data || responseData;
                console.log('Users data:', data);
                const tbody = document.getElementById('users-table-body');
                if (tbody && data.results) {
                    tbody.innerHTML = '';
                    data.results.forEach((user, index) => {
                        const bgClass = `g${(index % 5) + 1}`;
                        const initials = (user.first_name?.[0] || '') + (user.last_name?.[0] || '');
                        const name = `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.email;
                        const planLabel = user.is_pro ? 'Pro' : 'Free';
                        const planClass = user.is_pro ? 'pro' : 'free';
                        const date = new Date(user.date_joined).toLocaleDateString();
                        
                        const row = `
                            <div class="utbl-row" style="border-bottom:1px solid rgba(221,216,204,0.7);">
                                <div class="td-check"></div>
                                <div class="user-cell">
                                    <div class="user-av ${bgClass}">${initials || 'U'}</div>
                                    <div><div class="user-n">${name}</div><div class="user-em">${user.email}</div></div>
                                </div>
                                <div class="td" style="font-size:9px;">${user.email}</div>
                                <div><span class="plan-tag ${planClass}">${planLabel}</span></div>
                                <div class="td">-</div>
                                <div class="td" style="font-size:9px;">${date}</div>
                                <div class="td-actions"><div class="td-act-btn">👁</div><div class="td-act-btn">✎</div></div>
                            </div>
                        `;
                        tbody.innerHTML += row;
                    });
                }
            }
        } catch (err) {
            console.error('Error fetching users', err);
        }
    }
    
    // Setup tab navigation
    const navItems = document.querySelectorAll('.adm-nav-item');
    navItems.forEach(item => {
        item.addEventListener('click', (e) => {
            // Ignore if it's the logout button
            if (item.textContent.includes('Log Out')) {
                logout();
                return;
            }
            
            navItems.forEach(nav => nav.classList.remove('on'));
            item.classList.add('on');
            
            const text = item.textContent.trim().toLowerCase();
            document.querySelectorAll('.tab-content').forEach(tab => tab.classList.add('hidden'));
            
            if (text.includes('overview')) {
                const tab = document.getElementById('tab-overview');
                if(tab) tab.classList.remove('hidden');
            } else if (text.includes('users')) {
                const tab = document.getElementById('tab-users');
                if(tab) tab.classList.remove('hidden');
            }
        });
    });
});
