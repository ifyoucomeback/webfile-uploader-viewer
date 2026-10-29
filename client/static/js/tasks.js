async function toggleTask() {
    try {
        const statusResponse =
            await fetch(
                "/api/status?include_queue=false"
            );
        if (
            !statusResponse.ok
        ) {
            throw new Error(
                "读取任务状态失败: HTTP " +
                statusResponse.status
            );
        }
        const status =
            await statusResponse.json();
        const newEnabled = !status.enabled;
        const response =
            await fetch(
                "/api/task", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        enabled: newEnabled
                    })
                }
            );
        if (
            !response.ok
        ) {
            throw new Error(
                "HTTP " +
                response.status
            );
        }
        const result =
            await response.json();
        if (
            !result.success
        ) {
            throw new Error(
                result.error ||
                "操作失败"
            );
        }
        if (
            result.enabled
        ) {
            showMessage(
                "taskMessage",
                "自动扫描上传任务已开启"
            );
        } else {
            showMessage(
                "taskMessage",
                "自动扫描上传任务已暂停"
            );
        }
        await refreshPage();
    } catch (error) {
        showMessage(
            "taskMessage",
            "操作失败: " +
            error.message
        );
    }
}
async function uploadAllFiles() {
    try {
        const response =
            await fetch(
                "/api/upload-all", {
                    method: "POST"
                }
            );
        if (
            !response.ok
        ) {
            throw new Error(
                "HTTP " +
                response.status
            );
        }
        const result =
            await response.json();
        if (
            !result.success
        ) {
            throw new Error(
                result.error ||
                "操作失败"
            );
        }
        showMessage(
            "taskMessage",
            "扫描 " +
            result.scanned +
            " 个文件，加入上传队列 " +
            result.added +
            " 个文件"
        );
        await refreshPage();
    } catch (error) {
        showMessage(
            "taskMessage",
            "手动上传失败: " +
            error.message
        );
    }
}
