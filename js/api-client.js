/**
 * api-client.js — Centralized HTTP/JSON client for Robobrain UI.
 *
 * Wraps fetch() with standard headers, JSON parsing, and error handling.
 * All API calls should go through this module rather than raw fetch().
 *
 * Usage:
 *   const data = await api.get('/api/opportunities');
 *   const result = await api.post('/api/opportunities', { name: 'Foo' });
 *   await api.put(`/api/opportunities/${id}`, updates);
 *   await api.delete(`/api/opportunities/${id}`);
 */

const api = (() => {
    /**
     * Core fetch wrapper.
     *
     * @param {string} url - API endpoint path (e.g. '/api/opportunities')
     * @param {RequestInit} options - fetch options (method, body, etc.)
     * @returns {Promise<any>} Parsed JSON response body
     * @throws {Error} If response is not ok (includes status code + message)
     */
    async function request(url, options = {}) {
        const defaultHeaders = { 'Content-Type': 'application/json' };
        const config = {
            ...options,
            headers: { ...defaultHeaders, ...(options.headers || {}) },
        };

        const response = await fetch(url, config);

        if (!response.ok) {
            let message = `HTTP ${response.status}`;
            try {
                const err = await response.json();
                message = err.error || err.message || message;
            } catch (_) {
                // response body wasn't JSON — use status text
                message = response.statusText || message;
            }
            const error = new Error(message);
            error.status = response.status;
            throw error;
        }

        // Return null for 204 No Content
        if (response.status === 204) return null;

        return response.json();
    }

    /**
     * GET request.
     * @param {string} url
     * @param {RequestInit} [options]
     * @returns {Promise<any>}
     */
    function get(url, options = {}) {
        return request(url, { ...options, method: 'GET' });
    }

    /**
     * POST request with JSON body.
     * @param {string} url
     * @param {object} [body]
     * @param {RequestInit} [options]
     * @returns {Promise<any>}
     */
    function post(url, body = null, options = {}) {
        return request(url, {
            ...options,
            method: 'POST',
            body: body !== null ? JSON.stringify(body) : undefined,
        });
    }

    /**
     * PUT request with JSON body.
     * @param {string} url
     * @param {object} [body]
     * @param {RequestInit} [options]
     * @returns {Promise<any>}
     */
    function put(url, body = null, options = {}) {
        return request(url, {
            ...options,
            method: 'PUT',
            body: body !== null ? JSON.stringify(body) : undefined,
        });
    }

    /**
     * DELETE request.
     * @param {string} url
     * @param {RequestInit} [options]
     * @returns {Promise<any>}
     */
    function del(url, options = {}) {
        return request(url, { ...options, method: 'DELETE' });
    }

    return { request, get, post, put, delete: del };
})();
