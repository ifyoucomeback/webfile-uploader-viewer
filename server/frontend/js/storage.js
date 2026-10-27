document.addEventListener("DOMContentLoaded", async () => {
    const user = await requireLogin();
    if (!user) {
        return;
    }
    await loadStorage();
});
async function loadStorage() {
    try {
        const result =
            await API.storage();
        if (!result.success) {
            throw new Error("获取存储信息失败");
        }
        const storage =
            result.storage || {};
        const percent =
            Math.min(
                100,
                Math.max(
                    0,
                    Number(storage.used_percent) || 0
                )
            );
        document.getElementById("storagePercent")
            .textContent =
            formatPercent(storage.used_percent);
        document.getElementById("storageUsed")
            .textContent =
            formatBytes(storage.used);
        document.getElementById("storageFree")
            .textContent =
            formatBytes(storage.free);
        document.getElementById("storageTotal")
            .textContent =
            formatBytes(storage.total);
        document.getElementById("storagePath")
            .textContent =
            storage.path || "-";
        document.getElementById("storageProgress")
            .style.width =
            `${percent}%`;
    } catch (error) {
        alert(error.message);
    }
}
