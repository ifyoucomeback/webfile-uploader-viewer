function parseExtensions(
    text
) {
    return text
        .split(
            /[\n,\s]+/
        )
        .map(
            function(item) {
                return item.trim();
            }
        )
        .filter(
            function(item) {
                return item.length > 0;
            }
        );
}

function renderDirectories(
    directories
) {
    const container =
        document.getElementById(
            "directoryList"
        );
    const empty =
        document.getElementById(
            "directoryEmpty"
        );
    container.innerHTML = "";
    if (
        !directories ||
        directories.length === 0
    ) {
        empty.style.display =
            "block";
        return;
    }
    empty.style.display =
        "none";
    directories.forEach(
        function(directory, index) {
            const row =
                document.createElement(
                    "div"
                );
            row.className =
                "directory-config-row";
            const input =
                document.createElement(
                    "input"
                );
            input.type = "text";
            input.value =
                directory;
            input.dataset.index =
                index;
            const removeButton =
                document.createElement(
                    "button"
                );
            removeButton.type =
                "button";
            removeButton.className =
                "directory-remove-button";
            removeButton.textContent =
                "删除";
            removeButton.onclick =
                function() {
                    removeDirectory(
                        index
                    );
                };
            row.appendChild(
                input
            );
            row.appendChild(
                removeButton
            );
            container.appendChild(
                row
            );
        }
    );
}

function getDirectoriesFromUI() {
    const container =
        document.getElementById(
            "directoryList"
        );
    const inputs =
        container.querySelectorAll(
            "input"
        );
    const directories = [];
    inputs.forEach(
        function(input) {
            const value =
                input.value.trim();
            if (
                value &&
                directories.indexOf(
                    value
                ) === -1
            ) {
                directories.push(
                    value
                );
            }
        }
    );
    return directories;
}

function addDirectory() {
    const input =
        document.getElementById(
            "newMonitorDirectory"
        );
    const directory =
        input.value.trim();
    if (!directory) {
        return;
    }
    const directories =
        getDirectoriesFromUI();
    if (
        directories.indexOf(
            directory
        ) === -1
    ) {
        directories.push(
            directory
        );
    }
    renderDirectories(
        directories
    );
    input.value = "";
}

function removeDirectory(
    index
) {
    const directories =
        getDirectoriesFromUI();
    if (
        index < 0 ||
        index >= directories.length
    ) {
        return;
    }
    directories.splice(
        index,
        1
    );
    renderDirectories(
        directories
    );
}

function setConfig(
    config
) {
    document.getElementById("maxConcurrentUploads").value =
        config.upload.max_concurrent_uploads || 1;
    document.getElementById(
            "serverHost"
        ).value =
        config.server.host;
    document.getElementById(
            "serverPort"
        ).value =
        config.server.port;
    renderDirectories(
        config.monitor.directories || []
    );
    document.getElementById(
            "includeExtensions"
        ).value =
        config.monitor.include_extensions.join(
            "\n"
        );
    document.getElementById(
            "excludeExtensions"
        ).value =
        config.monitor.exclude_extensions.join(
            "\n"
        );
    document.getElementById(
            "monitorInterval"
        ).value =
        config.monitor.interval;
    document.getElementById(
            "maxBandwidth"
        ).value =
        config.upload.max_bandwidth;
    document.getElementById(
            "uploadPsk"
        ).value =
        config.upload.psk || "";
}
async function saveConfig() {
    const concurrency = Number(document.getElementById("maxConcurrentUploads").value);
    if (!Number.isInteger(concurrency) || concurrency < 1 || concurrency > 5) {
        showMessage("configMessage", "同时上传文件数必须是 1～5 的整数");
        return;
    }
    const currentConfigResponse =
        await fetch(
            "/api/config"
        );
    if (
        !currentConfigResponse.ok
    ) {
        showMessage(
            "configMessage",
            "读取当前配置失败"
        );
        return;
    }
    const currentConfig =
        await currentConfigResponse.json();
    const config = {
        server: {
            host: document.getElementById(
                "serverHost"
            ).value.trim(),
            port: parseInt(
                document.getElementById(
                    "serverPort"
                ).value,
                10
            )
        },
        monitor: {
            directories: getDirectoriesFromUI(),
            include_extensions: parseExtensions(
                document.getElementById(
                    "includeExtensions"
                ).value
            ),
            exclude_extensions: parseExtensions(
                document.getElementById(
                    "excludeExtensions"
                ).value
            ),
            interval: parseInt(
                document.getElementById(
                    "monitorInterval"
                ).value,
                10
            )
        },
        upload: {
            enabled: currentConfig.upload.enabled,
            max_concurrent_uploads: concurrency,
            max_bandwidth: parseInt(
                document.getElementById(
                    "maxBandwidth"
                ).value,
                10
            ),
            psk: document.getElementById(
                "uploadPsk"
            ).value
        }
    };
    try {
        const response =
            await fetch(
                "/api/config", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(
                        config
                    )
                }
            );
        if (
            !response.ok
        ) {
            const error = await response.json().catch(() => ({}));
            throw new Error(
                error.detail || ("HTTP " + response.status)
            );
        }
        const result =
            await response.json();
        if (
            !result.success
        ) {
            throw new Error(
                result.error ||
                "保存失败"
            );
        }
        showMessage(
            "configMessage",
            "配置保存成功"
        );
        setConfig(
            result.config
        );
        await refreshPage();
    } catch (error) {
        showMessage(
            "configMessage",
            "保存失败: " +
            error.message
        );
    }
}

function togglePskVisibility(
    button
) {
    const input =
        document.getElementById(
            "uploadPsk"
        );
    if (
        input.type === "password"
    ) {
        input.type = "text";
        button.textContent =
            "隐藏";
    } else {
        input.type = "password";
        button.textContent =
            "显示";
    }
}
