document.addEventListener("DOMContentLoaded", async () => {
    try {
        const result = await API.me();
        if (result && result.username) {
            window.location.href =
                "/frontend/dashboard.html";
            return;
        }
    } catch (error) {
        // 未登录，正常显示登录页面
    }
    const form =
        document.getElementById("loginForm");
    const errorElement =
        document.getElementById("loginError");
    const button =
        document.getElementById("loginButton");
    form.addEventListener("submit", async (event) => {
        event.preventDefault();
        errorElement.classList.add("hidden");
        errorElement.textContent = "";
        const username =
            document.getElementById("username").value.trim();
        const password =
            document.getElementById("password").value;
        if (!username || !password) {
            errorElement.textContent =
                "请输入用户名和密码";
            errorElement.classList.remove("hidden");
            return;
        }
        button.disabled = true;
        button.textContent = "登录中...";
        try {
            const result =
                await API.login(username, password);
            if (!result || !result.success) {
                throw new Error(
                    result?.error || "用户名或密码错误"
                );
            }
            window.location.href =
                "/frontend/dashboard.html";
        } catch (error) {
            errorElement.textContent =
                error.message || "登录失败";
            errorElement.classList.remove("hidden");
            button.disabled = false;
            button.textContent = "登录";
        }
    });
});
