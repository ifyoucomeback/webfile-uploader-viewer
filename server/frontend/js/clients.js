document.addEventListener("DOMContentLoaded", async () => {
    if (await requireLogin()) await loadClients();
});
async function loadClients() {
    const table = document.getElementById("clientsTable");
    const nav = document.getElementById("clientFileNavigation");
    table.textContent = "正在加载…";
    try {
        const [stats, directories] = await Promise.all([API.clients(), API.get(
            "/api/admin/file-browser/clients")]);
        nav.replaceChildren();
        directories.items.forEach(item => {
            const link = document.createElement("a");
            link.className = "client-file-card";
            link.href =
                `/frontend/files.html?${new URLSearchParams({client_name: item.client_name})}`;
            const name = document.createElement("strong");
            name.textContent = "📁 " + item.client_name;
            const path = document.createElement("span");
            path.textContent = item.storage_root;
            link.append(name, path);
            nav.appendChild(link);
        });
        if (!directories.items.length) nav.textContent = "暂无客户端存储目录";
        if (!stats.items?.length) {
            table.textContent = "暂无客户端活动记录";
            return;
        }
        table.innerHTML = `<table class="data-table"><thead><tr><th>客户端</th><th>文件数量</th><th>上传任务</th><th>最后活动</th><th>操作</th></tr></thead><tbody>${stats.items.map(item => {
            const href = `/frontend/files.html?${new URLSearchParams({client_name: item.client_name})}`;
            return `<tr><td>${escapeHtml(item.client_name)}</td><td>${item.file_count || 0}</td>
                <td>${item.uploading_count || 0}</td><td>${item.last_activity ? formatDate(item.last_activity * 1000) : "—"}</td>
                <td><a class="btn btn-secondary" href="${escapeHtml(href)}">浏览文件</a></td></tr>`;
        }).join("")}</tbody></table>`;
    } catch (error) {
        table.textContent = error.message;
        nav.textContent = "客户端导航加载失败，请刷新重试";
    }
}
