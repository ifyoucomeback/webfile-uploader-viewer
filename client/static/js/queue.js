/* 队列在服务端分页，轮询只传输当前页，不改变实际上传顺序。 */
const QUEUE_PAGE_SIZE = 50;
let currentQueuePage = 1;
let currentQueueTotalPages = 0;
let queuePageJump = null;
let queueRequestSequence = 0;
let queueLoading = false;

function renderQueue(result) {
    currentQueuePage = result.page;
    currentQueueTotalPages = result.total_pages;
    document.getElementById("queueCount").textContent = result.total;
    const table = document.getElementById("queueTable");
    table.replaceChildren();
    if (!result.items.length) {
        const cell = table.insertRow().insertCell();
        cell.colSpan = 4;
        cell.className = "empty";
        cell.textContent = "没有等待上传的文件";
    }
    result.items.forEach(file => {
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

async function loadQueuePage(page, quiet = false) {
    if (quiet && queueLoading) return;
    const sequence = ++queueRequestSequence;
    queueLoading = true;
    try {
        const result = await readPageData(`/api/queue?page=${page}&page_size=${QUEUE_PAGE_SIZE}`);
        if (sequence !== queueRequestSequence) return;
        renderQueue(result);
    } finally {
        if (sequence === queueRequestSequence) queueLoading = false;
    }
}

async function goToQueuePage(page) {
    if (!Number.isSafeInteger(page) || page < 1 || page > currentQueueTotalPages) return;
    try {
        await loadQueuePage(page);
        showPageError(null);
    } catch (error) {
        showPageError(error);
    }
}

function previousQueuePage() {
    return goToQueuePage(currentQueuePage - 1);
}

function nextQueuePage() {
    return goToQueuePage(currentQueuePage + 1);
}

function refreshCurrentQueuePage(quiet = false) {
    return loadQueuePage(currentQueuePage, quiet);
}
