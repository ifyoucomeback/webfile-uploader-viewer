/* 通用页码跳转：两端目录列表和客户端上传队列共用。 */
class PageJump {
    constructor(container, onJump) {
        this.onJump = onJump;
        this.currentPage = 1;
        this.totalPages = 0;
        this.busy = false;
        this.dirty = false;
        this.form = document.createElement("form");
        this.form.className = "page-jump";
        this.form.noValidate = true;
        const label = document.createElement("label");
        label.appendChild(document.createTextNode("跳至 "));
        this.input = document.createElement("input");
        this.input.type = "number";
        this.input.min = "1";
        this.input.step = "1";
        this.input.inputMode = "numeric";
        this.input.setAttribute("aria-label", "跳转页码");
        label.appendChild(this.input);
        label.appendChild(document.createTextNode(" 页"));
        this.button = document.createElement("button");
        this.button.type = "submit";
        this.button.textContent = "跳转";
        this.message = document.createElement("span");
        this.message.className = "page-jump-error";
        this.message.setAttribute("role", "alert");
        this.message.hidden = true;
        this.form.append(label, this.button, this.message);
        container.appendChild(this.form);
        this.input.addEventListener("input", () => {
            this.dirty = true;
            this.showError("");
        });
        this.form.addEventListener("submit", event => {
            event.preventDefault();
            this.submit();
        });
        this.update(1, 0);
    }
    showError(message) {
        this.message.textContent = message;
        this.message.hidden = !message;
        this.input.setAttribute("aria-invalid", message ? "true" : "false");
    }
    update(page, totalPages) {
        const changed = page !== this.currentPage;
        const boundsChanged = totalPages !== this.totalPages;
        this.currentPage = page;
        this.totalPages = totalPages;
        if (changed || totalPages <= 1) this.dirty = false;
        this.input.max = String(Math.max(1, totalPages));
        const disabled = this.busy || totalPages <= 1;
        this.input.disabled = disabled;
        this.button.disabled = disabled;
        if (!this.dirty || totalPages <= 1) {
            this.input.value = totalPages ? String(page) : "";
        }
        if (changed || boundsChanged || totalPages <= 1) this.showError("");
    }
    async submit() {
        if (this.busy || this.totalPages <= 1) return;
        const text = this.input.value.trim();
        const page = Number(text);
        if (!/^\d+$/.test(text) || !Number.isSafeInteger(page) || page < 1 || page > this
            .totalPages) {
            this.showError(`请输入 1～${this.totalPages} 的整数页码`);
            this.input.focus();
            return;
        }
        this.showError("");
        this.busy = true;
        this.update(this.currentPage, this.totalPages);
        try {
            await this.onJump(page);
            this.dirty = false;
        } catch (error) {
            this.showError(error.message || "跳转失败，请重试");
        } finally {
            this.busy = false;
            this.update(this.currentPage, this.totalPages);
        }
    }
}
