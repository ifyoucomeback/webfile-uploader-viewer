async function loadPage() {
    try {
        const configResponse =
            await fetch(
                "/api/config"
            );
        if (
            !configResponse.ok
        ) {
            throw new Error(
                "读取配置失败: HTTP " +
                configResponse.status
            );
        }
        const config =
            await configResponse.json();
        setConfig(
            config
        );
        const clientResponse =
            await fetch(
                "/api/client"
            );
        if (
            !clientResponse.ok
        ) {
            throw new Error(
                "读取客户端信息失败: HTTP " +
                clientResponse.status
            );
        }
        const client =
            await clientResponse.json();
        renderClient(
            client
        );
        const statusResponse =
            await fetch(
                "/api/status"
            );
        if (
            !statusResponse.ok
        ) {
            throw new Error(
                "读取客户端状态失败: HTTP " +
                statusResponse.status
            );
        }
        const status =
            await statusResponse.json();
        renderStatus(
            status
        );
        await loadInitialFiles();
    } catch (error) {
        console.error(
            "加载页面失败:",
            error
        );
    }
}
async function refreshPage() {
    try {
        const clientResponse =
            await fetch(
                "/api/client"
            );
        if (
            !clientResponse.ok
        ) {
            return;
        }
        const client =
            await clientResponse.json();
        renderClient(
            client
        );
        const statusResponse =
            await fetch(
                "/api/status"
            );
        if (
            !statusResponse.ok
        ) {
            return;
        }
        const status =
            await statusResponse.json();
        renderStatus(
            status
        );
        await refreshLocalFiles();
    } catch (error) {
        console.error(
            "刷新页面失败:",
            error
        );
    }
}
loadPage();
setInterval(refreshPage, 1000);
