/* 各页面只初始化自身功能，共用客户端信息和连接状态刷新。 */
const clientPage = document.body.dataset.page;
let pageRefreshTimer = null;
let pageRefreshing = false;
let pageClosed = false;
let pageLoadError = null;

async function readPageData(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`读取数据失败：HTTP ${response.status}`);
    return response.json();
}

function showPageError(error) {
    const message = document.getElementById("pageMessage");
    message.textContent = error ? error.message : "";
    message.hidden = !error;
}

async function loadPage() {
    try {
        if (clientPage === "settings") setConfig(await readPageData("/api/config"));
        if (clientPage === "files") await loadInitialFiles();
    } catch (error) {
        pageLoadError = error;
        showPageError(error);
        return;
    }
    await refreshPage();
}

async function refreshPage() {
    if (pageRefreshing || pageClosed || document.hidden) return;
    pageRefreshing = true;
    try {
        const [client, status] = await Promise.all([
            readPageData("/api/client"),
            readPageData("/api/status?include_queue=false"),
        ]);
        if (pageClosed) return;
        renderClient(client);
        renderStatus(status);
        if (clientPage === "queue") await refreshCurrentQueuePage(true);
        if (clientPage === "files") await refreshLocalFiles();
        showPageError(pageLoadError);
    } catch (error) {
        showPageError(error);
    } finally {
        pageRefreshing = false;
    }
}

window.addEventListener("pagehide", () => {
    pageClosed = true;
    clearInterval(pageRefreshTimer);
});
document.addEventListener("visibilitychange", () => {
    if (!document.hidden) refreshPage();
});
window.addEventListener("pageshow", event => {
    if (event.persisted) {
        pageClosed = false;
        refreshPage();
        pageRefreshTimer = setInterval(refreshPage, 1000);
    }
});

loadPage().finally(() => {
    if (!pageClosed) pageRefreshTimer = setInterval(refreshPage, 1000);
});
