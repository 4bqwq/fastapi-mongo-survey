const TOKEN_KEY = 'survey_token';

function setToken(token) {
    localStorage.setItem(TOKEN_KEY, token);
}

function getToken() {
    return localStorage.getItem(TOKEN_KEY);
}

function removeToken() {
    localStorage.removeItem(TOKEN_KEY);
}

async function authenticatedFetch(url, options = {}) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
        ...options,
        headers
    });

    if (response.status === 401) {
        // Token might be expired or invalid
        removeToken();
        window.location.href = '/login';
    }

    return response;
}

function isLoggedIn() {
    return !!getToken();
}
