function formatSize(size) {
    if (
        size === null ||
        size === undefined
    ) {
        return "-";
    }
    size = Number(size);
    if (size < 1024) {
        return size + " B";
    }
    if (
        size <
        1024 * 1024
    ) {
        return (
            size / 1024
        ).toFixed(2) + " KB";
    }
    if (
        size <
        1024 * 1024 * 1024
    ) {
        return (
            size /
            (1024 * 1024)
        ).toFixed(2) + " MB";
    }
    return (
        size /
        (1024 * 1024 * 1024)
    ).toFixed(2) + " GB";
}

function formatSpeed(speed) {
    if (
        !speed ||
        speed <= 0
    ) {
        return "0 B/s";
    }
    return formatSize(
        speed
    ) + "/s";
}

function showMessage(
    elementId,
    message
) {
    const element =
        document.getElementById(
            elementId
        );
    element.textContent =
        message;
    setTimeout(
        function() {
            element.textContent =
                "";
        },
        5000
    );
}
