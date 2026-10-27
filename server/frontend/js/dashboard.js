document.addEventListener("DOMContentLoaded", async () => {
    const user = await requireLogin();
    if (!user) {
        return;
    }
    await loadDashboard();
});
async function loadDashboard() {
    try {
        const result =
            await API.dashboard();
        if (!result.success) {
            throw new Error("获取仪表盘数据失败");
        }
        const files =
            result.files || {};
        const uploads =
            result.uploads || {};
        const clients =
            result.clients || {};
        const storage =
            result.storage || {};
        document.getElementById("fileCount").textContent =
            files.count ?? 0;
        document.getElementById("uploadCount").textContent =
            uploads.count ?? 0;
        document.getElementById("clientCount").textContent =
            clients.count ?? 0;
        document.getElementById("storagePercent").textContent =
            formatPercent(storage.used_percent);
        document.getElementById("storageUsed").textContent =
            formatBytes(storage.used);
        document.getElementById("storageTotal").textContent =
            formatBytes(storage.total);
        const progress =
            Math.min(
                100,
                Math.max(
                    0,
                    Number(storage.used_percent) || 0
                )
            );
        document.getElementById("storageProgress")
            .style.width = `${progress}%`;
        renderRecentUploads();
        await loadDashboardClients();
    } catch (error) {
        console.error(error);
        document.getElementById("recentUploads").innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;
    }
}
async function renderRecentUploads() {
    const container =
        document.getElementById("recentUploads");
    try {
        const result =
            await API.uploads();
        if (!result.success || !result.items?.length) {
            container.innerHTML =
                `<div class="empty">当前没有上传任务</div>`;
            return;
        }
        const items =
            result.items.slice(0, 5);
        container.innerHTML =
            items.map(item => {
                const progress =
                    Number(item.progress) || 0;
                return `
                    <div class="mini-list-item">

                        <div style="min-width:0">

                            <div class="mini-list-name">
                                ${escapeHtml(item.file_name)}
                            </div>

                            <div class="mini-list-meta">
                                ${escapeHtml(item.client_name)}
                            </div>

                        </div>

                        <div class="progress-wrapper">

                            <div class="progress">
                                <div
                                    class="progress-bar"
                                    style="width:${progress}%"
                                ></div>
                            </div>

                            <div class="progress-text">
                                ${formatPercent(progress)}
                            </div>

                        </div>

                    </div>
                `;
            }).join("");
    } catch (error) {
        container.innerHTML =
            `<div class="empty">${escapeHtml(error.message)}</div>`;
    }
}
async function loadDashboardClients() {
    const container =
        document.getElementById("clientsList");
    try {
        const result =
            await API.clients();
        if (!result.success || !result.items?.length) {
            container.innerHTML =
                `<div class="empty">暂无客户端</div>`;
            return;
        }
        const items =
            result.items.slice(0, 10);
        container.innerHTML = `
            <table class="data-table">

                <thead>
                    <tr>
                        <th>客户端</th>
                        <th>文件数量</th>
                        <th>上传任务</th>
                        <th>最后活动</th>
                    </tr>
                </thead>

                <tbody>

                    ${items.map(item => `
                        <tr>

                            <td>
                                <div class="file-name">
                                    ${escapeHtml(item.client_name)}
                                </div>
                            </td>

                            <td>
                                ${item.file_count ?? 0}
                            </td>

                            <td>
                                ${item.upload_count ?? 0}
                            </td>

                            <td>
                                ${formatDate(item.last_activity)}
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
