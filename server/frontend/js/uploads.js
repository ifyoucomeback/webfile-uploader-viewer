let uploadRefreshTimer = null;

document.addEventListener("DOMContentLoaded", async () => {
    const user = await requireLogin();
    if (!user) {
        return;
    }
    await loadUploads();
    uploadRefreshTimer = setInterval(loadUploads, 5000);
});

window.addEventListener("beforeunload", () => {
    if (uploadRefreshTimer) {
        clearInterval(uploadRefreshTimer);
    }
});

function renderUploadRow(item) {
    const value = Number(item.progress);
    const progress = Number.isFinite(value) ? Math.min(100, Math.max(0, value)) : 0;
    const uploaded = Array.isArray(item.uploaded_chunks)
        ? item.uploaded_chunks.length
        : Number(item.uploaded_chunks) || 0;
    const total = Number(item.total_chunks) || 0;
    const status = item.expired ? "已过期" : "上传中";
    const statusClass = item.expired ? "text-danger" : "text-success";

    return `
        <tr>
            <td>
                <div class="file-name">${escapeHtml(item.file_name)}</div>
                <div class="file-path">${escapeHtml(item.relative_path)}</div>
            </td>
            <td>${escapeHtml(item.client_name)}</td>
            <td>${formatBytes(item.file_size)}</td>
            <td>
                <div class="progress-wrapper">
                    <div class="progress">
                        <div class="progress-bar" style="width:${progress}%"></div>
                    </div>
                    <div class="progress-text">${formatPercent(progress)}</div>
                </div>
            </td>
            <td>${uploaded} / ${total}</td>
            <td>${escapeHtml(formatDate(item.created_time))}</td>
            <td>${escapeHtml(formatDate(item.updated_time))}</td>
            <td><span class="${statusClass}">${status}</span></td>
        </tr>
    `;
}

async function loadUploads() {
    const container = document.getElementById("uploadsTable");
    try {
        const result = await API.uploads();
        if (!result.success || !result.items?.length) {
            container.innerHTML = '<div class="empty">当前没有上传任务</div>';
            return;
        }
        container.innerHTML = `
            <table class="data-table">
                <thead>
                    <tr>
                        <th>文件</th>
                        <th>客户端</th>
                        <th>大小</th>
                        <th>进度</th>
                        <th>分片</th>
                        <th>开始时间</th>
                        <th>最后活动</th>
                        <th>状态</th>
                    </tr>
                </thead>
                <tbody>${result.items.map(renderUploadRow).join("")}</tbody>
            </table>
        `;
    } catch (error) {
        container.innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`;
    }
}
