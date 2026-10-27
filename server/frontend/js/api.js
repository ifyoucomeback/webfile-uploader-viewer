const API = {
    async request(url, options = {}) {
        const config = {
            credentials: "same-origin",
            ...options
        };
        if (
            config.body &&
            typeof config.body === "object" &&
            !(config.body instanceof FormData)
        ) {
            config.headers = {
                "Content-Type": "application/json",
                ...(config.headers || {})
            };
            config.body = JSON.stringify(config.body);
        }
        const response = await fetch(url, config);
        let data = null;
        try {
            data = await response.json();
        } catch (error) {
            data = null;
        }
        if (response.status === 401) {
            if (!window.location.pathname.endsWith("/index.html")) {
                window.location.href = "/frontend/index.html";
            }
            throw new Error(
                data?.detail || data?.error || "登录已失效"
            );
        }
        if (response.status === 403) {
            throw new Error(
                data?.detail || data?.error || "没有权限执行此操作"
            );
        }
        if (!response.ok) {
            throw new Error(
                data?.detail ||
                data?.error ||
                `请求失败：HTTP ${response.status}`
            );
        }
        return data;
    },
    get(url) {
        return this.request(url, {
            method: "GET"
        });
    },
    post(url, body) {
        return this.request(url, {
            method: "POST",
            body
        });
    },
    put(url, body) {
        return this.request(url, {
            method: "PUT",
            body
        });
    },
    delete(url, body = undefined) {
        return this.request(url, {
            method: "DELETE",
            body
        });
    },
    login(username, password) {
        return this.post("/api/auth/login", {
            username,
            password
        });
    },
    logout() {
        return this.post("/api/auth/logout", {});
    },
    me() {
        return this.get("/api/auth/me");
    },
    dashboard() {
        return this.get("/api/admin/dashboard");
    },
    files(page = 1, pageSize = 50, clientName = "", keyword = "") {
        const params = new URLSearchParams();
        params.set("page", page);
        params.set("page_size", pageSize);
        if (clientName) {
            params.set("client_name", clientName);
        }
        if (keyword) {
            params.set("keyword", keyword);
        }
        return this.get(`/api/admin/files?${params.toString()}`);
    },
    uploads() {
        return this.get("/api/admin/uploads");
    },
    clients() {
        return this.get("/api/admin/clients");
    },
    storage() {
        return this.get("/api/admin/storage");
    },
    users() {
        return this.get("/api/admin/users");
    },
    createUser(username, password) {
        return this.post("/api/admin/users", {
            username,
            password
        });
    },
    changeUserPassword(username, password) {
        return this.put(
            `/api/admin/users/${encodeURIComponent(username)}/password`, {
                password
            }
        );
    },
    deleteUser(username) {
        return this.delete(
            `/api/admin/users/${encodeURIComponent(username)}`
        );
    },
    deleteFile(clientName, relativePath) {
        return this.delete("/api/admin/file", {
            client_name: clientName,
            relative_path: relativePath
        });
    },
    deleteFiles(files) {
        return this.delete("/api/admin/files", {
            files
        });
    },
    videoStreamUrl(clientName, relativePath) {
        const params = new URLSearchParams();
        params.set("client_name", clientName);
        params.set("relative_path", relativePath);
        return `/api/video/stream?${params.toString()}`;
    },
    videoDownloadUrl(clientName, relativePath) {
        const params = new URLSearchParams();
        params.set("client_name", clientName);
        params.set("relative_path", relativePath);
        return `/api/video/download?${params.toString()}`;
    }
};
