/* 本地文件浏览适配：目录、预览、下载和删除使用独立接口。 */
let localFileBrowser = null;
async function localFileRequest(url, options = {}) {
    const response = await fetch(url, {
        credentials: "same-origin",
        ...options
    });
    const result = await response.json().catch(() => ({}));
    if (!response.ok || result.success === false) throw new Error(result.detail || result
        .error || `HTTP ${response.status}`);
    return result;
}

function localFileUrl(action, item, location) {
    return `/api/files/${action}?${new URLSearchParams({root: location.root, path: item.path})}`;
}

function ensureLocalFileBrowser() {
    if (localFileBrowser) return localFileBrowser;
    localFileBrowser = new FileBrowser(document.getElementById("localFileBrowser"), {
        virtualRoots: true,
        rootLabel: location => location.root,
        formatSize,
        list: state => localFileRequest(`/api/files/browse?${new URLSearchParams({
            root: state.root || "", path: state.path || "", page: state.page,
            page_size: state.page_size, keyword: state.keyword,
        })}`),
        url: localFileUrl,
        readText: (item, location, signal) => localFileRequest(localFileUrl("preview", item,
            location), {
            signal
        }),
        remove: (item, location) => localFileRequest("/api/files/file", {
            method: "DELETE",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                root: location.root,
                path: item.path
            }),
        }),
        deleteMessage: "此操作只删除本地文件，不删除服务器副本。已排队或等待重试的任务也会移除。",
    });
    return localFileBrowser;
}
async function loadInitialFiles() {
    const browser = ensureLocalFileBrowser();
    if (!browser.data) return browser.open({
        root: "",
        path: ""
    });
    return browser.refresh();
}
async function refreshLocalFiles() {
    if (localFileBrowser) return localFileBrowser.refresh(true);
}
async function loadFilesPage() {
    return loadInitialFiles();
}
