/* 等待队列已包含在状态响应中，翻页只切换本地视图，不改变上传顺序。 */
const QUEUE_PAGE_SIZE = 50;
let currentQueuePage = 1;
let currentQueueTotalPages = 0;
let latestQueue = [];
let queuePageJump = null;

function renderQueue(queue) {
    latestQueue = Array.isArray(queue) ? queue : [];
    document.getElementById("queueCount").textContent = latestQueue.length;
    currentQueueTotalPages = Math.ceil(latestQueue.length / QUEUE_PAGE_SIZE);
    currentQueuePage = Math.min(Math.max(1, currentQueuePage), currentQueueTotalPages || 1);
    const start = (currentQueuePage - 1) * QUEUE_PAGE_SIZE;
    const table = document.getElementById("queueTable");
    table.replaceChildren();
    const items = latestQueue.slice(start, start + QUEUE_PAGE_SIZE);
    if (!items.length) {
        const cell = table.insertRow().insertCell();
        cell.colSpan = 4;
        cell.className = "empty";
        cell.textContent = "没有等待上传的文件";
    }
    items.forEach(file => {
        const row = table.insertRow();
        row.insertCell().textContent = file.name || "-";
        const path = row.insertCell();
        path.className = "file-path";
        path.textContent = file.relative_path || file.name || "-";
        row.insertCell().textContent = formatSize(file.size);
        row.insertCell().textContent = file.extension || "-";
    });
    document.getElementById("queuePaginationCurrent").textContent = currentQueueTotalPages ?
        `第 ${currentQueuePage} / ${currentQueueTotalPages} 页` : "第 0 / 0 页";
    document.getElementById("queuePreviousPageButton").disabled =
        currentQueueTotalPages === 0 || currentQueuePage <= 1;
    document.getElementById("queueNextPageButton").disabled =
        currentQueueTotalPages === 0 || currentQueuePage >= currentQueueTotalPages;
    if (!queuePageJump) {
        queuePageJump = new PageJump(document.getElementById("queuePageJump"), goToQueuePage);
    }
    queuePageJump.update(currentQueuePage, currentQueueTotalPages);
}

function goToQueuePage(page) {
    if (!Number.isSafeInteger(page) || page < 1 || page > currentQueueTotalPages) return;
    currentQueuePage = page;
    refreshCurrentQueuePage();
}

function previousQueuePage() {
    goToQueuePage(currentQueuePage - 1);
}

function nextQueuePage() {
    goToQueuePage(currentQueuePage + 1);
}

function refreshCurrentQueuePage() {
    renderQueue(latestQueue);
}
