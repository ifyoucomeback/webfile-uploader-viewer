/* 文本和视频预览；文件内容只写入 textContent，不执行 HTML。 */
class FilePreview {
    constructor(options) {
        this.options = options;
        this.sequence = 0;
        this.overlay = document.createElement("div");
        this.overlay.className = "fb-modal";
        this.overlay.hidden = true;
        this.overlay.innerHTML = `
            <section class="fb-modal-panel" role="dialog" aria-modal="true" aria-label="文件预览">
                <header><h2>文件预览</h2><button type="button" data-close aria-label="关闭预览">×</button></header>
                <div class="fb-modal-body"><p data-path></p><p data-origin></p><p data-message role="status"></p>
                    <pre data-text hidden></pre><video data-video controls preload="metadata" hidden></video>
                </div>
                <footer><a class="fb-button fb-primary" data-download>下载文件</a>
                    <button class="fb-danger" type="button" data-delete>删除文件</button>
                    <button type="button" data-close>关闭</button></footer>
            </section>`;
        document.body.appendChild(this.overlay);
        this.text = this.overlay.querySelector("[data-text]");
        this.video = this.overlay.querySelector("[data-video]");
        this.message = this.overlay.querySelector("[data-message]");
        this.overlay.querySelectorAll("[data-close]").forEach(button => {
            button.addEventListener("click", () => this.close());
        });
        this.overlay.addEventListener("click", event => {
            if (event.target === this.overlay) this.close();
        });
        document.addEventListener("keydown", event => {
            if (event.key === "Escape" && this.isOpen) this.close();
        });
        this.video.addEventListener("error", () => {
            if (this.isOpen && !this.video.hidden) this.message.textContent =
                "浏览器无法播放该文件，可能不支持此视频编码，请下载后查看。";
        });
    }
    get isOpen() {
        return !this.overlay.hidden;
    }
    close() {
        this.sequence++;
        if (this.controller) this.controller.abort();
        this.video.pause();
        this.video.removeAttribute("src");
        this.video.load();
        this.overlay.hidden = true;
        if (this.previousFocus) this.previousFocus.focus();
    }
    async open(item, location) {
        this.close();
        const sequence = ++this.sequence;
        this.previousFocus = document.activeElement;
        this.controller = new AbortController();
        this.overlay.hidden = false;
        this.text.hidden = true;
        this.text.textContent = "";
        this.video.hidden = true;
        this.message.textContent = "正在加载预览…";
        this.overlay.querySelector("h2").textContent = item.name;
        this.overlay.querySelector("[data-path]").textContent =
            (item.stored_path ? "服务器路径：" : "文件路径：") +
            (item.stored_path || item.absolute_path || (location.root ? location.root + "/" :
                "") + item.path);
        this.overlay.querySelector("[data-origin]").textContent =
            item.original_path ? "原始路径：" + item.original_path : "";
        this.overlay.querySelector("[data-download]").href = this.options.url("download", item,
            location);
        const remove = this.overlay.querySelector("[data-delete]");
        remove.disabled = !!item.busy;
        remove.onclick = () => this.options.remove(item, {
            ...location
        });
        this.overlay.querySelector("[data-close]").focus();
        if (item.preview_kind === "video") {
            this.video.hidden = false;
            this.video.src = this.options.url("stream", item, location);
            this.message.textContent = "支持浏览器原生格式的视频可直接播放、拖动；不支持的编码请下载查看。";
            return;
        }
        if (item.preview_kind !== "text") {
            this.message.textContent = "该格式暂不支持在线预览，可以下载后查看。";
            return;
        }
        try {
            const result = await this.options.readText(item, location, this.controller.signal);
            if (sequence !== this.sequence) return;
            this.text.textContent = result.text;
            this.text.hidden = false;
            this.message.textContent = `编码：${result.encoding}` +
                (result.truncated ? ` · 仅显示前 ${Math.round(result.limit / 1024)} KB，完整内容请下载。` :
                    "");
        } catch (error) {
            if (sequence === this.sequence && error.name !== "AbortError")
                this.message.textContent = error.message || "预览加载失败";
        }
    }
}
