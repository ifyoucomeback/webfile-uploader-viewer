function escapeHtml(value) {
    if (value === null || value === undefined) {
        return "";
    }
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function formatBytes(bytes) {
    const value = Number(bytes);
    if (!Number.isFinite(value) || value < 0) {
        return "-";
    }
    if (value < 1024) {
        return `${value} B`;
    }
    if (value < 1024 * 1024) {
        return `${(value / 1024).toFixed(2)} KB`;
    }
    if (value < 1024 * 1024 * 1024) {
        return `${(value / 1024 / 1024).toFixed(2)} MB`;
    }
    if (value < 1024 * 1024 * 1024 * 1024) {
        return `${(value / 1024 / 1024 / 1024).toFixed(2)} GB`;
    }
    return `${(
        value /
        1024 /
        1024 /
        1024 /
        1024
    ).toFixed(2)} TB`;
}

function formatDate(value) {
    if (!value) {
        return "-";
    }
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) {
        return value;
    }
    return date.toLocaleString("zh-CN", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit"
    });
}

function formatPercent(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) {
        return "-";
    }
    return `${number.toFixed(2)}%`;
}

function showError(element, message) {
    if (!element) {
        return;
    }
    element.textContent = message || "操作失败";
    element.classList.remove("hidden");
}

function hideError(element) {
    if (!element) {
        return;
    }
    element.textContent = "";
    element.classList.add("hidden");
}

function confirmDelete(message) {
    return window.confirm(
        message || "确定要删除吗？"
    );
}
