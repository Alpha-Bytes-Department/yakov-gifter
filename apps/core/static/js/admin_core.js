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

// Authentication is a session cookie set HttpOnly by Django. Script cannot read
// it, which is the point — it replaces the access/refresh tokens that used to
// sit in localStorage where any XSS could lift them. The cookie rides along
// automatically; all we have to supply by hand is the CSRF token.
function getCookie(name) {
    const match = document.cookie.match(new RegExp('(^|;\\s*)' + name + '=([^;]*)'));
    return match ? decodeURIComponent(match[2]) : null;
}

async function logout() {
    try {
        await fetch('/dashboard/session-logout/', {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') || '' },
            credentials: 'same-origin',
        });
    } catch (err) {
        // Falling through to the redirect is fine — the session is server-side,
        // so the worst case is it expires on its own.
    }
    window.location.href = '/dashboard/login/';
}

async function apiFetch(endpoint, options = {}) {
    const method = (options.method || 'GET').toUpperCase();
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };

    // Django exempts the safe methods; everything else needs the token.
    if (!['GET', 'HEAD', 'OPTIONS', 'TRACE'].includes(method)) {
        headers['X-CSRFToken'] = getCookie('csrftoken') || '';
    }

    // FormData sets its own multipart boundary — leave Content-Type alone.
    if (options.body instanceof FormData) {
        delete headers['Content-Type'];
    }

    const res = await fetch(`${BASE_URL}${endpoint}`, {
        ...options,
        headers,
        credentials: 'same-origin',
    });

    if (res.status === 401 || res.status === 403) {
        window.location.href = '/dashboard/login/';
    }
    return res;
}

document.addEventListener('DOMContentLoaded', () => {
    const currentPath = window.location.pathname;

    // The server decides who may see a dashboard page now, so there is no
    // client-side gate to run here. Leaving one would only be decorative.

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
