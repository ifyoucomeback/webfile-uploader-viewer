let currentUser = null;
async function loadCurrentUser() {
    try {
        const result = await API.me();
        currentUser = result;
        const usernameElement =
            document.getElementById("currentUsername");
        if (usernameElement) {
            usernameElement.textContent = result.username;
        }
        await updateRootNavigation();
        return result;
    } catch (error) {
        return null;
    }
}
async function requireLogin() {
    const user = await loadCurrentUser();
    if (!user) {
        window.location.href =
            "/frontend/index.html";
        return null;
    }
    return user;
}
async function updateRootNavigation() {
    const nav = document.getElementById("usersNav");
    if (!nav) {
        return;
    }
    try {
        await API.users();
        nav.classList.remove("hidden");
    } catch (error) {
        nav.classList.add("hidden");
    }
}
async function logout() {
    try {
        await API.logout();
    } catch (error) {
        // 即使服务端退出失败，也继续清理前端状态
    }
    currentUser = null;
    window.location.href =
        "/frontend/index.html";
}
