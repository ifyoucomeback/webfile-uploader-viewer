function renderClient(client) {
    document.getElementById("clientName").textContent = client.name || "-";
    document.getElementById("clientIP").textContent = client.ip || "-";
}

function renderServerConnection(status) {
    const element = document.getElementById("serverConnected");
    element.textContent = status.server_connected ? "已连接" : "未连接";
    element.className = status.server_connected ? "status-connected" : "status-disconnected";
}

function renderStatus(status) {
    const running = document.getElementById("clientRunning");
    running.textContent = status.running ? "运行中" : "已停止";
    running.className = status.running ? "status-enabled" : "status-disabled";
    renderServerConnection(status);
    const taskStatus = document.getElementById("taskStatus");
    const taskButton = document.getElementById("taskButton");
    taskStatus.textContent = status.enabled ? "已开启" : "已暂停（进行中的上传将继续完成）";
    taskStatus.className = status.enabled ? "status-enabled" : "status-disabled";
    taskButton.textContent = status.enabled ? "暂停任务" : "开始任务";
    taskButton.className = status.enabled ? "task-button" : "task-button start";
    renderUploadStatus(status);
}

function renderUploadStatus(status) {
    const files = status.currents || (status.current ? [status.current] : []);
    const limit = status.max_concurrent_uploads || 1;
    document.getElementById("concurrencyStatus").textContent =
        `${status.active_count || files.length} / ${limit} 个文件`;
    document.getElementById("uploadSpeed").textContent = formatSpeed(status.speed || 0);
    const table = document.getElementById("activeUploadTable");
    table.replaceChildren();
    if (files.length === 0) {
        const cell = table.insertRow().insertCell();
        cell.colSpan = 6;
        cell.textContent = "暂无正在上传的文件";
    }
    const stages = {hashing: "计算摘要", uploading: "上传中", completing: "服务端合并校验"};
    files.forEach(file => {
        const row = table.insertRow();
        row.insertCell().textContent = file.path || file.relative_path || file.name;
        row.insertCell().textContent = formatSize(file.size);
        row.insertCell().textContent = formatSize(file.uploaded_bytes);
        const percentage = file.size > 0 ? Math.max(0, Math.min(100,
            100 * file.uploaded_bytes / file.size)) : (file.stage === "completing" ? 100 : 0);
        const cell = row.insertCell();
        const progress = document.createElement("progress");
        progress.max = 100;
        progress.value = percentage;
        progress.setAttribute("aria-label", `${file.name} 上传进度`);
        cell.appendChild(progress);
        cell.appendChild(document.createTextNode(percentage.toFixed(1) + "%"));
        row.insertCell().textContent = stages[file.stage] || "上传中";
        row.insertCell().textContent = formatSpeed(file.speed || 0);
    });
    const retrying = status.retrying || [];
    document.getElementById("retrySummary").textContent = retrying.length
        ? `另有 ${retrying.length} 个文件等待重试，不占用上传名额。` : "";
    renderQueue(status.queue || []);
}
