const QUEUE_PAGE_SIZE = 50;
let currentQueuePage = 1;
let currentQueueTotalPages = 0;

function renderQueue(
    queue
) {
    const queueCount =
        document.getElementById(
            "queueCount"
        );
    const queueTable =
        document.getElementById(
            "queueTable"
        );
    const previousButton =
        document.getElementById(
            "queuePreviousPageButton"
        );
    const nextButton =
        document.getElementById(
            "queueNextPageButton"
        );
    const paginationCurrent =
        document.getElementById(
            "queuePaginationCurrent"
        );
    if (
        !queue
    ) {
        queue = [];
    }
    /*
     * 显示全部等待任务数量
     */
    queueCount.textContent =
        queue.length;
    /*
     * 计算总页数
     */
    currentQueueTotalPages =
        queue.length > 0 ?
        Math.ceil(
            queue.length /
            QUEUE_PAGE_SIZE
        ) :
        0;
    /*
     * 如果任务完成导致当前页不存在，
     * 自动回到最后一页。
     */
    if (
        currentQueueTotalPages === 0
    ) {
        currentQueuePage = 1;
    } else if (
        currentQueuePage >
        currentQueueTotalPages
    ) {
        currentQueuePage =
            currentQueueTotalPages;
    }
    /*
     * 当前页数据
     */
    const start =
        (
            currentQueuePage - 1
        ) *
        QUEUE_PAGE_SIZE;
    const end =
        start +
        QUEUE_PAGE_SIZE;
    const pageQueue =
        queue.slice(
            start,
            end
        );
    queueTable.innerHTML =
        "";
    if (
        pageQueue.length === 0
    ) {
        const row =
            document.createElement(
                "tr"
            );
        const cell =
            document.createElement(
                "td"
            );
        cell.colSpan = 4;
        cell.className =
            "empty";
        cell.textContent =
            "没有等待上传的文件";
        row.appendChild(
            cell
        );
        queueTable.appendChild(
            row
        );
    } else {
        pageQueue.forEach(
            function(file) {
                const row =
                    document.createElement(
                        "tr"
                    );
                const nameCell =
                    document.createElement(
                        "td"
                    );
                nameCell.textContent =
                    file.name || "-";
                const pathCell =
                    document.createElement(
                        "td"
                    );
                pathCell.className =
                    "file-path";
                pathCell.textContent =
                    file.relative_path ||
                    file.name ||
                    "-";
                const sizeCell =
                    document.createElement(
                        "td"
                    );
                sizeCell.textContent =
                    formatSize(
                        file.size
                    );
                const extensionCell =
                    document.createElement(
                        "td"
                    );
                extensionCell.textContent =
                    file.extension || "-";
                row.appendChild(
                    nameCell
                );
                row.appendChild(
                    pathCell
                );
                row.appendChild(
                    sizeCell
                );
                row.appendChild(
                    extensionCell
                );
                queueTable.appendChild(
                    row
                );
            }
        );
    }
    /*
     * 更新分页信息
     */
    if (
        currentQueueTotalPages > 0
    ) {
        paginationCurrent.textContent =
            "第 " +
            currentQueuePage +
            " / " +
            currentQueueTotalPages +
            " 页";
    } else {
        paginationCurrent.textContent =
            "第 0 / 0 页";
    }
    /*
     * 上一页按钮
     */
    previousButton.disabled =
        currentQueueTotalPages === 0 ||
        currentQueuePage <= 1;
    /*
     * 下一页按钮
     */
    nextButton.disabled =
        currentQueueTotalPages === 0 ||
        currentQueuePage >=
        currentQueueTotalPages;
}

function previousQueuePage() {
    if (
        currentQueuePage <= 1
    ) {
        return;
    }
    currentQueuePage--;
    /*
     * 这里不重新请求服务器。
     * 当前 status.queue 已经保存在页面内，
     * 下一次刷新时 renderQueue 会继续使用当前页。
     */
    refreshCurrentQueuePage();
}

function nextQueuePage() {
    if (
        currentQueuePage >=
        currentQueueTotalPages
    ) {
        return;
    }
    currentQueuePage++;
    refreshCurrentQueuePage();
}

function refreshCurrentQueuePage() {
    /*
     * 重新获取当前状态，保证翻页时看到的是最新队列。
     */
    fetch(
            "/api/status"
        )
        .then(
            function(response) {
                if (!response.ok) {
                    throw new Error(
                        "HTTP " +
                        response.status
                    );
                }
                return response.json();
            }
        )
        .then(
            function(status) {
                renderQueue(
                    status.queue || []
                );
            }
        )
        .catch(
            function(error) {
                console.error(
                    "刷新上传队列失败:",
                    error
                );
            }
        );
}
