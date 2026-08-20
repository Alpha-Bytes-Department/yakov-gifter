// admin_core.js
// Shared functionality for all Admin Dashboard pages

const BASE_URL = '/api/v1';

function toast(message) {
    let el = document.getElementById("toast");
    if (!el) {
        el = document.createElement("div");
        el.id = "toast";
        el.className = "toast";
        document.body.appendChild(el);
    }
    el.textContent = message;
    el.classList.add("show");
    setTimeout(() => el.classList.remove("show"), 3000);
}

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/dashboard/login/';
}

async function apiFetch(endpoint, options = {}) {
    const token = localStorage.getItem('access_token');
    const defaultOptions = {
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    };
    const res = await fetch(`${BASE_URL}${endpoint}`, { ...defaultOptions, ...options });
    if (res.status === 401 || res.status === 403) {
        // Handle token expiration/refresh later if needed. For now, simple redirect.
        logout();
    }
    return res;
}

document.addEventListener('DOMContentLoaded', () => {
    const currentPath = window.location.pathname;
    const isLoginPage = currentPath.includes('/login');
    
    // Auth Check
    const token = localStorage.getItem('access_token');
    if (!token && !isLoginPage) {
        window.location.href = '/dashboard/login/';
        return;
    }
    if (token && isLoginPage) {
        window.location.href = '/dashboard/';
        return;
    }
    
    // Setup Navigation Highlighting
    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(item => {
        item.classList.remove('active');
        const href = item.getAttribute('href');
        if (href && currentPath === href) {
            item.classList.add('active');
        } else if (href && currentPath.includes(href) && href !== '/dashboard/') {
            item.classList.add('active');
        }
    });
    
    // Add Logout Button to Sidebar
    const sideFooter = document.querySelector('.side-footer');
    if (sideFooter) {
        const logoutBtn = document.createElement('button');
        logoutBtn.className = 'btn';
        logoutBtn.style.marginTop = '10px';
        logoutBtn.style.width = '100%';
        logoutBtn.style.background = 'var(--surface-color)';
        logoutBtn.style.color = 'var(--text-primary)';
        logoutBtn.textContent = 'Log Out';
        logoutBtn.onclick = logout;
        sideFooter.parentElement.appendChild(logoutBtn);
    }

    // Sidebar Toggling functionality globally
    const menuBtn = document.querySelector('.menu-btn');
    const sidebar = document.querySelector('.sidebar');
    if (menuBtn && sidebar) {
        menuBtn.addEventListener('click', () => {
            sidebar.classList.toggle('hidden');
        });
    }
});
