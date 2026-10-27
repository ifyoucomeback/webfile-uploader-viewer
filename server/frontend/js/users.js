document.addEventListener("DOMContentLoaded", async () => {
    const user = await requireLogin();
    if (!user) {
        return;
    }
    try {
        await API.users();
    } catch (error) {
        document.getElementById("usersTable").innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;
        return;
    }
    await loadUsers();
    document
        .getElementById("createUserForm")
        .addEventListener("submit", createUser);
    document
        .getElementById("passwordForm")
        .addEventListener("submit", changePassword);
});
async function loadUsers() {
    const container =
        document.getElementById("usersTable");
    container.innerHTML =
        `<div class="loading">正在加载...</div>`;
    try {
        const result =
            await API.users();
        if (!result.success) {
            throw new Error("获取用户列表失败");
        }
        const users =
            result.users || [];
        if (!users.length) {
            container.innerHTML =
                `<div class="empty">暂无普通用户</div>`;
            return;
        }
        container.innerHTML = `
            <table class="data-table">

                <thead>

                    <tr>
                        <th>用户名</th>
                        <th>操作</th>
                    </tr>

                </thead>

                <tbody>

                    ${users.map(username => `

                        <tr>

                            <td>
                                <div class="file-name">
                                    ${escapeHtml(username)}
                                </div>
                            </td>

                            <td>

                                <div class="action-group">

                                    <button
                                        type="button"
                                        class="btn btn-secondary btn-small"
                                        onclick="openPasswordModal(${JSON.stringify(username)})"
                                    >
                                        修改密码
                                    </button>

                                    <button
                                        type="button"
                                        class="btn btn-danger btn-small"
                                        onclick="deleteUser(${JSON.stringify(username)})"
                                    >
                                        删除
                                    </button>

                                </div>

                            </td>

                        </tr>

                    `).join("")}

                </tbody>

            </table>
        `;
    } catch (error) {
        container.innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;
    }
}

function openCreateUserModal() {
    document
        .getElementById("newUsername")
        .value = "";
    document
        .getElementById("newPassword")
        .value = "";
    hideError(
        document.getElementById("createUserError")
    );
    document
        .getElementById("createUserModal")
        .classList.remove("hidden");
}

function closeCreateUserModal() {
    document
        .getElementById("createUserModal")
        .classList.add("hidden");
}
async function createUser(event) {
    event.preventDefault();
    const username =
        document
        .getElementById("newUsername")
        .value
        .trim();
    const password =
        document
        .getElementById("newPassword")
        .value;
    const errorElement =
        document.getElementById("createUserError");
    hideError(errorElement);
    if (!username || !password) {
        showError(
            errorElement,
            "用户名和密码不能为空"
        );
        return;
    }
    try {
        const result =
            await API.createUser(
                username,
                password
            );
        if (!result.success) {
            throw new Error(
                result.error || "创建用户失败"
            );
        }
        closeCreateUserModal();
        await loadUsers();
    } catch (error) {
        showError(
            errorElement,
            error.message
        );
    }
}

function openPasswordModal(username) {
    document
        .getElementById("passwordUsername")
        .value = username;
    document
        .getElementById("passwordUsernameDisplay")
        .value = username;
    document
        .getElementById("newUserPassword")
        .value = "";
    hideError(
        document.getElementById("passwordError")
    );
    document
        .getElementById("passwordModal")
        .classList.remove("hidden");
}

function closePasswordModal() {
    document
        .getElementById("passwordModal")
        .classList.add("hidden");
}
async function changePassword(event) {
    event.preventDefault();
    const username =
        document
        .getElementById("passwordUsername")
        .value;
    const password =
        document
        .getElementById("newUserPassword")
        .value;
    const errorElement =
        document.getElementById("passwordError");
    hideError(errorElement);
    if (!password) {
        showError(
            errorElement,
            "新密码不能为空"
        );
        return;
    }
    try {
        const result =
            await API.changeUserPassword(
                username,
                password
            );
        if (!result.success) {
            throw new Error(
                result.error || "修改密码失败"
            );
        }
        closePasswordModal();
        await loadUsers();
        alert(
            `用户 ${username} 的密码已经修改`
        );
    } catch (error) {
        showError(
            errorElement,
            error.message
        );
    }
}
async function deleteUser(username) {
    if (
        !confirmDelete(
            `确定删除用户“${username}”吗？`
        )
    ) {
        return;
    }
    try {
        const result =
            await API.deleteUser(username);
        if (!result.success) {
            throw new Error(
                result.error || "删除用户失败"
            );
        }
        await loadUsers();
    } catch (error) {
        alert(error.message);
    }
}
