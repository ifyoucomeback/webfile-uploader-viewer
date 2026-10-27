/* 两端共用的目录浏览、面包屑、分页及文件操作组件。 */
class FileBrowser {
    constructor(container, options) {
        this.container = container;
        this.options = options;
        this.location = {};
        this.selected = new Set();
        this.page = 1;
        this.sequence = 0;
        this.lastRefresh = 0;
        container.classList.add("fb-browser");
        container.innerHTML = `
            <div class="fb-toolbar"><button type="button" data-up>↑ 上一级</button>
                <button type="button" data-refresh>刷新</button>
                <form data-search><input aria-label="搜索当前目录" placeholder="搜索当前目录的文件或文件夹" type="search">
                    <button type="submit">搜索</button></form>
                <button type="button" class="fb-danger" data-bulk disabled>删除选中文件</button></div>
            <nav class="fb-breadcrumbs" aria-label="目录层级"></nav>
            <p class="fb-absolute"></p><p class="fb-error" role="alert" hidden></p>
            <div class="fb-table-scroll"><table><thead><tr>
                <th><input type="checkbox" data-all aria-label="选择本页全部文件"></th>
                <th>名称</th><th>大小</th><th>修改时间</th><th>操作</th>
            </tr></thead><tbody></tbody></table></div>
            <div class="fb-pagination"><button type="button" data-previous>上一页</button>
                <span data-page></span><button type="button" data-next>下一页</button>
                <div data-jump></div></div>`;
        this.table = container.querySelector("tbody");
        this.error = container.querySelector(".fb-error");
        this.search = container.querySelector("input[type=search]");
        this.pageJump = new PageJump(container.querySelector("[data-jump]"), page => this.load(page));
        this.preview = new FilePreview({
            url: options.url,
            readText: options.readText,
            remove: (item, location) => this.deleteFile(item, location),
        });
        container.querySelector("[data-up]").onclick = () => this.goUp();
        container.querySelector("[data-refresh]").onclick = () => this.refresh();
        container.querySelector("[data-previous]").onclick = () => this.load(this.page - 1);
        container.querySelector("[data-next]").onclick = () => this.load(this.page + 1);
        container.querySelector("[data-search]").onsubmit = event => {
            event.preventDefault();
            this.load(1);
        };
        container.querySelector("[data-bulk]").onclick = () => this.deleteSelected();
        container.querySelector("[data-all]").onchange = event => {
            this.selected.clear();
            if (event.target.checked) this.items.filter(item => item.kind === "file" && !
                    item.busy)
                .forEach(item => this.selected.add(item.path));
            this.renderRows();
        };
        this.items = [];
    }
    button(text, action, className = "") {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = text;
        button.className = className;
        button.onclick = action;
        return button;
    }
    showError(message) {
        this.error.textContent = message;
        this.error.hidden = !message;
    }
    async open(location) {
        this.location = {
            ...location
        };
        this.search.value = "";
        this.selected.clear();
        this.preview.close();
        this.items = [];
        this.page = 1;
        this.data = {
            path: location.path || "",
            total: 0,
            total_pages: 0
        };
        this.renderBreadcrumbs();
        this.renderRows();
        return this.load(1);
    }
    async load(page = this.page) {
        const sequence = ++this.sequence;
        this.loading = true;
        this.showError("");
        this.container.setAttribute("aria-busy", "true");
        try {
            const result = await this.options.list({
                ...this.location,
                page,
                page_size: 50,
                keyword: this.search.value.trim()
            });
            if (sequence !== this.sequence) return;
            if (!result || !result.success) throw new Error(result?.error || "读取目录失败");
            this.data = result;
            this.page = result.page;
            this.items = result.items;
            this.location.path = result.path;
            const paths = new Set(this.items.filter(item => item.kind === "file").map(item =>
                item.path));
            this.selected = new Set([...this.selected].filter(path => paths.has(path)));
            this.renderBreadcrumbs();
            this.renderRows();
            this.lastRefresh = Date.now();
            if (this.options.onNavigate) this.options.onNavigate(this.location);
        } catch (error) {
            if (sequence === this.sequence) {
                this.data = {
                    path: this.location.path || "",
                    total: 0,
                    total_pages: 0
                };
                this.items = [];
                this.selected.clear();
                this.renderBreadcrumbs();
                this.renderRows();
                this.showError(error.message || "读取目录失败");
            }
        } finally {
            if (sequence === this.sequence) {
                this.loading = false;
                this.container.removeAttribute("aria-busy");
            }
        }
    }
    async refresh(quiet = false) {
        if (quiet && (this.loading || this.deleting || this.preview.isOpen || this.selected
                .size ||
                this.container.contains(document.activeElement) || Date.now() - this
                .lastRefresh < 5000)) return;
        return this.load();
    }
    goUp() {
        if (this.location.path) {
            const parts = this.location.path.split("/");
            parts.pop();
            return this.open({
                ...this.location,
                path: parts.join("/")
            });
        }
        if (this.options.virtualRoots && this.location.root) return this.open({
            root: "",
            path: ""
        });
    }
    renderBreadcrumbs() {
        const nav = this.container.querySelector(".fb-breadcrumbs");
        nav.replaceChildren();
        const add = (label, location) => nav.appendChild(this.button(label, () => this.open(
            location)));
        if (this.options.virtualRoots) add("监控目录", {
            root: "",
            path: ""
        });
        if (this.location.root || this.location.client_name) {
            add(this.options.rootLabel(this.location), {
                ...this.location,
                path: ""
            });
            const parts = (this.location.path || "").split("/").filter(Boolean);
            parts.forEach((part, index) => {
                const separator = document.createElement("span");
                separator.textContent = "›";
                nav.appendChild(separator);
                add(part, {
                    ...this.location,
                    path: parts.slice(0, index + 1).join("/")
                });
            });
        }
        this.container.querySelector(".fb-absolute").textContent = this.data.absolute_path ?
            (this.options.virtualRoots ? "本地路径：" : "服务器路径：") + this.data.absolute_path :
            (this.options.virtualRoots ? "请选择一个监控目录" : "请选择客户端或刷新目录");
        this.container.querySelector("[data-up]").disabled = !this.location.path && !(this
            .options.virtualRoots && this.location.root);
    }
    renderRows() {
        this.table.replaceChildren();
        if (!this.items.length) {
            const cell = this.table.insertRow().insertCell();
            cell.colSpan = 5;
            cell.className = "fb-empty";
            cell.textContent = "当前目录没有符合条件的文件或文件夹";
        }
        this.items.forEach(item => {
            const location = {
                ...this.location
            };
            const row = this.table.insertRow();
            const checkCell = row.insertCell();
            if (item.kind === "file") {
                const check = document.createElement("input");
                check.type = "checkbox";
                check.setAttribute("aria-label", "选择 " + item.name);
                check.checked = this.selected.has(item.path);
                check.disabled = !!item.busy;
                check.onchange = () => {
                    if (check.checked) this.selected.add(item.path);
                    else this.selected.delete(item.path);
                    this.updateSelection();
                };
                checkCell.appendChild(check);
            }
            const name = row.insertCell();
            const activate = () => item.kind === "directory" ?
                this.open({
                    ...location,
                    root: item.root || location.root,
                    path: item.path
                }) :
                this.preview.open(item, location);
            name.appendChild(this.button((item.kind === "directory" ? "📁 " : "📄 ") +
                item.name, activate, "fb-name"));
            if (Object.hasOwn ? Object.hasOwn(item, "original_path") : Object.prototype
                .hasOwnProperty.call(item, "original_path")) {
                const origin = document.createElement("div");
                origin.className = "fb-origin";
                origin.textContent = "原始路径：" + (item.original_path || "未记录");
                name.appendChild(origin);
            }
            row.insertCell().textContent = item.kind === "directory" ? "文件夹" : this
                .options.formatSize(item.size);
            row.insertCell().textContent = item.modified_time ? new Date(item
                .modified_time * 1000).toLocaleString("zh-CN") : "—";
            const actions = row.insertCell();
            actions.className = "fb-actions";
            if (item.kind === "directory") {
                actions.appendChild(this.button(item.available === false ? "目录不可用" :
                    "进入", activate));
                actions.lastChild.disabled = item.available === false;
            } else {
                actions.appendChild(this.button("预览", activate));
                const link = document.createElement("a");
                link.className = "fb-button";
                link.textContent = "下载";
                link.href = this.options.url("download", item, location);
                actions.appendChild(link);
                const remove = this.button(item.busy ? "上传中" : "删除", () => this
                    .deleteFile(item, location), "fb-danger");
                remove.disabled = !!item.busy;
                actions.appendChild(remove);
            }
        });
        const totalPages = this.data?.total_pages || 0;
        this.container.querySelector("[data-page]").textContent =
            `第 ${totalPages ? this.page : 0} / ${totalPages} 页 · 当前目录共 ${this.data?.total || 0} 项`;
        this.container.querySelector("[data-previous]").disabled = this.page <= 1;
        this.container.querySelector("[data-next]").disabled = this.page >= totalPages;
        this.pageJump.update(this.page, totalPages);
        this.updateSelection();
    }
    updateSelection() {
        const bulk = this.container.querySelector("[data-bulk]");
        bulk.disabled = this.selected.size === 0;
        bulk.textContent = this.selected.size ? `删除选中文件 (${this.selected.size})` : "删除选中文件";
        const eligible = this.items.filter(item => item.kind === "file" && !item.busy);
        const all = this.container.querySelector("[data-all]");
        all.checked = eligible.length > 0 && eligible.every(item => this.selected.has(item
            .path));
        all.indeterminate = this.selected.size > 0 && !all.checked;
    }
    async deleteFile(item, location = this.location) {
        if (!window.confirm(`确定删除「${item.name}」？\n${this.options.deleteMessage}`)) return;
        await this.removeItems([item], location);
    }
    async deleteSelected() {
        const items = this.items.filter(item => this.selected.has(item.path));
        if (!items.length || !window.confirm(
                `确定删除选中的 ${items.length} 个文件？\n${this.options.deleteMessage}`)) return;
        await this.removeItems(items);
    }
    async removeItems(items, scope = this.location) {
        if (this.deleting) return;
        this.deleting = true;
        const location = {
            ...scope
        };
        this.preview.close();
        const failures = [];
        for (const item of items) {
            try {
                await this.options.remove(item, location);
                this.selected.delete(item.path);
            } catch (error) {
                failures.push(item.name + "：" + error.message);
            }
        }
        await this.load();
        this.deleting = false;
        if (failures.length) this.showError(failures.join("；"));
    }
}
