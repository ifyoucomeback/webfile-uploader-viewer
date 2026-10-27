/* 服务端适配：客户端导航 + 实际存储路径，不改变已有上传目录。 */
let serverFileBrowser = null;

function storedFileUrl(action, item, location) {
    return `/api/admin/file-browser/${action}?${new URLSearchParams({
        client_name: location.client_name, path: item.path,
    })}`;
}

function markClientNavigation(name) {
    document.querySelectorAll("#fileClientNavigation a").forEach(link => {
        link.classList.toggle("active", link.dataset.client === name);
    });
}
async function selectFileClient(clientName, path = "") {
    document.getElementById("serverFileBrowser").hidden = false;
    document.getElementById("fileBrowserWelcome").hidden = true;
    document.getElementById("selectedClientTitle").textContent = "客户端：" + clientName;
    markClientNavigation(clientName);
    return serverFileBrowser.open({
        client_name: clientName,
        path
    });
}
async function loadFileClients() {
    const nav = document.getElementById("fileClientNavigation");
    const message = document.getElementById("clientNavigationMessage");
    message.textContent = "正在加载客户端…";
    try {
        const result = await API.get("/api/admin/file-browser/clients");
        nav.replaceChildren();
        result.items.forEach(item => {
            const link = document.createElement("a");
            link.textContent = "📁 " + item.client_name;
            link.dataset.client = item.client_name;
            link.href =
                `/frontend/files.html?${new URLSearchParams({client_name: item.client_name})}`;
            link.title = item.storage_root;
            link.onclick = event => {
                if (event.ctrlKey || event.metaKey || event.shiftKey) return;
                event.preventDefault();
                selectFileClient(item.client_name);
            };
            nav.appendChild(link);
        });
        message.textContent = result.items.length ? `共 ${result.items.length} 个客户端` :
            "暂无客户端存储目录";
        markClientNavigation(serverFileBrowser.location.client_name);
    } catch (error) {
        message.textContent = error.message;
    }
}
document.addEventListener("DOMContentLoaded", async () => {
    if (!await requireLogin()) return;
    serverFileBrowser = new FileBrowser(document.getElementById("serverFileBrowser"), {
        virtualRoots: false,
        rootLabel: location => location.client_name,
        formatSize: formatBytes,
        list: state => API.get(`/api/admin/file-browser?${new URLSearchParams({
            client_name: state.client_name, path: state.path || "", page: state.page,
            page_size: state.page_size, keyword: state.keyword,
        })}`),
        url: storedFileUrl,
        readText: (item, location, signal) => API.request(storedFileUrl(
            "preview", item, location), {
            signal
        }),
        remove: (item, location) => API.delete("/api/admin/file-browser/file", {
            client_name: location.client_name,
            path: item.path,
        }),
        deleteMessage: "此操作只删除服务器上的文件及对应索引，不删除客户端原文件；后续同步可能重新上传。",
        onNavigate: location => {
            document.getElementById("selectedClientTitle").textContent =
                "客户端：" + location.client_name;
            markClientNavigation(location.client_name);
            const url =
                `/frontend/files.html?${new URLSearchParams({client_name: location.client_name, path: location.path || ""})}`;
            if (window.location.pathname + window.location.search !== url)
                history.pushState(null, "", url);
        },
    });
    document.getElementById("refreshFileClients").onclick = loadFileClients;
    await loadFileClients();
    const query = new URLSearchParams(window.location.search);
    if (query.get("client_name")) await selectFileClient(query.get("client_name"), query
        .get("path") || "");
    window.addEventListener("popstate", () => {
        const query = new URLSearchParams(window.location.search);
        if (query.get("client_name")) selectFileClient(query.get("client_name"),
            query.get("path") || "");
        else {
            serverFileBrowser.preview.close();
            document.getElementById("serverFileBrowser").hidden = true;
            document.getElementById("fileBrowserWelcome").hidden = false;
            document.getElementById("selectedClientTitle").textContent =
                "请选择客户端";
            markClientNavigation("");
        }
    });
});
