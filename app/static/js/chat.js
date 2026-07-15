(function () {
    "use strict";

    var state = {
        conversations: [], models: [], employees: [], currentId: null,
        sending: false, charts: []
    };
    var els = {};
    var commands = [
        { mark: "/", title: "新建对话", subtitle: "创建一个空白任务", action: "new" },
        { mark: "数", title: "系统数据概览", subtitle: "查询核心业务数据", prompt: "请给出系统数据概览" },
        { mark: "图", title: "用户状态报表", subtitle: "生成用户状态饼图", prompt: "生成用户状态分布图表" },
        { mark: "线", title: "仓库数据趋势", subtitle: "生成入库趋势折线图", prompt: "生成数据仓库入库趋势图表" }
    ];

    function xsrfToken() {
        var match = document.cookie.match(/(?:^|; )_xsrf=([^;]+)/);
        return match ? decodeURIComponent(match[1]) : "";
    }

    async function api(url, options) {
        options = options || {};
        options.headers = Object.assign({}, options.headers || {}, { "X-Xsrftoken": xsrfToken() });
        if (options.body && typeof options.body !== "string") {
            options.headers["Content-Type"] = "application/json";
            options.body = JSON.stringify(options.body);
        }
        var response = await fetch(url, options);
        var data;
        try { data = await response.json(); } catch (_error) { throw new Error("服务响应格式异常"); }
        if (!response.ok || data.ok === false) throw new Error(data.message || "请求失败");
        return data;
    }

    function escapeHtml(value) {
        return String(value == null ? "" : value)
            .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;").replace(/'/g, "&#039;");
    }

    function intentLabel(intent) {
        return {
            general_chat: "普通问答", database_query: "数据库问数", data_report: "数据报表",
            digital_employee: "数字员工", employee_not_found: "数字员工"
        }[intent] || "智能路由";
    }

    function currentConversation() {
        return state.conversations.find(function (item) { return item.id === state.currentId; });
    }

    function updateHeader(conversation) {
        els.conversationTitle.textContent = conversation ? conversation.title : "新对话";
        var model = state.models.find(function (item) {
            return conversation && item.id === conversation.model_id;
        });
        els.conversationMeta.textContent = model ? model.name : "智能意图路由";
    }

    function renderModels() {
        els.modelSelect.innerHTML = "";
        if (!state.models.length) {
            els.modelSelect.innerHTML = '<option value="">暂无可用模型</option>';
            els.modelSelect.disabled = true;
            return;
        }
        els.modelSelect.disabled = false;
        state.models.forEach(function (model) {
            var option = document.createElement("option");
            option.value = model.id;
            option.textContent = model.name + (model.is_default ? "（默认）" : "");
            els.modelSelect.appendChild(option);
        });
        var conversation = currentConversation();
        var selected = conversation && conversation.model_id;
        if (selected) els.modelSelect.value = String(selected);
    }

    function renderConversations() {
        els.conversationList.innerHTML = "";
        if (!state.conversations.length) {
            els.conversationList.innerHTML = '<div class="conversation-empty">暂无对话任务</div>';
            return;
        }
        state.conversations.forEach(function (conversation) {
            var button = document.createElement("button");
            button.className = "conversation-item" + (conversation.id === state.currentId ? " active" : "");
            button.innerHTML = '<i class="layui-icon layui-icon-dialogue"></i><span>' + escapeHtml(conversation.title) + "</span>";
            button.addEventListener("click", function () { loadConversation(conversation.id); });
            els.conversationList.appendChild(button);
        });
    }

    function appendMessage(message, extra) {
        extra = extra || {};
        els.emptyState.classList.add("hidden");
        var row = document.createElement("div");
        row.className = "message-row " + message.role;
        var isUser = message.role === "user";
        var avatar = isUser ? document.getElementById("chatApp").dataset.username.charAt(0).toUpperCase() : "AI";
        row.innerHTML = '<div class="message-avatar">' + escapeHtml(avatar) + '</div>' +
            '<div class="message-body"><div class="message-name">' + (isUser ? "我" : "智能助手") + '</div>' +
            '<div class="message-bubble">' + escapeHtml(message.content) + '</div></div>';
        var body = row.querySelector(".message-body");
        if (!isUser && message.intent) {
            var tag = document.createElement("span");
            tag.className = "intent-tag";
            tag.textContent = intentLabel(message.intent);
            body.appendChild(tag);
        }
        els.messageStream.appendChild(row);
        var report = extra.report || message.report;
        if (report) renderReport(body, report);
        if (extra.card) renderCard(body, extra.card);
        els.dialogZone.scrollTop = els.dialogZone.scrollHeight;
        return row;
    }

    function appendTyping() {
        var row = document.createElement("div");
        row.className = "message-row assistant";
        row.innerHTML = '<div class="message-avatar">AI</div><div class="message-body"><div class="message-name">智能助手</div>' +
            '<div class="message-bubble"><div class="typing"><span></span><span></span><span></span></div></div></div>';
        els.messageStream.appendChild(row);
        els.dialogZone.scrollTop = els.dialogZone.scrollHeight;
        return row;
    }

    function renderReport(parent, report) {
        var panel = document.createElement("div");
        panel.className = "report-panel";
        panel.innerHTML = '<div class="report-title">' + escapeHtml(report.title || "数据报表") + '</div><div class="report-chart"></div>';
        parent.appendChild(panel);
        var chartElement = panel.querySelector(".report-chart");
        if (!window.echarts) {
            chartElement.className = "report-fallback";
            chartElement.textContent = JSON.stringify(report, null, 2);
            return;
        }
        var chart = window.echarts.init(chartElement);
        var option;
        if (report.type === "pie") {
            option = {
                tooltip: { trigger: "item" }, legend: { bottom: 0, textStyle: { color: "#667680" } },
                series: [{ type: "pie", radius: ["38%", "66%"], center: ["50%", "45%"],
                    itemStyle: { borderColor: "#fff", borderWidth: 2 }, label: { color: "#44545d" }, data: report.data || [] }]
            };
        } else {
            option = {
                color: ["#087f8c"], tooltip: { trigger: "axis" },
                grid: { left: 42, right: 20, top: 22, bottom: 52, containLabel: true },
                xAxis: { type: "category", data: report.labels || [], axisLabel: { color: "#667680", interval: 0, rotate: (report.labels || []).length > 5 ? 22 : 0 } },
                yAxis: { type: "value", axisLabel: { color: "#667680" }, splitLine: { lineStyle: { color: "#edf1f2" } } },
                series: (report.series || []).map(function (series) {
                    return { name: series.name, type: report.type || "bar", data: series.data, smooth: true,
                        barMaxWidth: 34, areaStyle: report.type === "line" ? { opacity: .08 } : undefined };
                })
            };
        }
        chart.setOption(option);
        state.charts.push(chart);
    }

    function renderCard(parent, card) {
        var element = document.createElement("div");
        element.className = "data-card";
        element.innerHTML = '<div class="data-card-title">' + escapeHtml(card.title || "数据结果") + '</div><pre>' +
            escapeHtml(typeof card.data === "string" ? card.data : JSON.stringify(card.data, null, 2)) + "</pre>";
        parent.appendChild(element);
    }

    function clearMessages() {
        state.charts.forEach(function (chart) { chart.dispose(); });
        state.charts = [];
        els.messageStream.innerHTML = "";
        els.emptyState.classList.remove("hidden");
    }

    async function createConversation() {
        closeMenu();
        var modelId = els.modelSelect.value ? Number(els.modelSelect.value) : null;
        var data = await api("/api/chat/conversations", { method: "POST", body: { model_id: modelId } });
        state.conversations.unshift(data.conversation);
        state.currentId = data.conversation.id;
        renderConversations(); renderModels(); updateHeader(data.conversation); clearMessages();
        closeSidebar(); els.messageInput.focus();
    }

    async function loadConversation(id) {
        closeMenu();
        var data = await api("/api/chat/conversations/" + id);
        state.currentId = id;
        var local = state.conversations.find(function (item) { return item.id === id; });
        if (local) Object.assign(local, data.conversation);
        clearMessages();
        data.messages.forEach(function (message) { appendMessage(message); });
        renderConversations(); renderModels(); updateHeader(data.conversation); closeSidebar();
    }

    async function deleteConversation() {
        if (!state.currentId) return;
        if (!window.confirm("确定删除当前对话及全部消息吗？")) return;
        await api("/api/chat/conversations/" + state.currentId, { method: "DELETE" });
        state.conversations = state.conversations.filter(function (item) { return item.id !== state.currentId; });
        state.currentId = null;
        if (state.conversations.length) await loadConversation(state.conversations[0].id);
        else await createConversation();
    }

    async function sendMessage(text) {
        text = (text == null ? els.messageInput.value : text).trim();
        if (!text || state.sending) return;
        if (!state.currentId) await createConversation();
        state.sending = true; els.sendButton.disabled = true; closeMenu();
        els.messageInput.value = ""; resizeInput(); updateCharCount();
        appendMessage({ role: "user", content: text });
        var typing = appendTyping();
        els.intentStatus.textContent = "正在识别意图并调度能力";
        try {
            var data = await api("/api/chat/messages", {
                method: "POST",
                body: { conversation_id: state.currentId, model_id: els.modelSelect.value || null, message: text }
            });
            typing.remove();
            appendMessage(data.message, { report: data.report, card: data.card });
            var conversation = state.conversations.find(function (item) { return item.id === state.currentId; });
            if (conversation) Object.assign(conversation, data.conversation);
            els.intentStatus.textContent = intentLabel(data.intent) + (data.employee ? " · " + data.employee : "");
            renderConversations(); updateHeader(data.conversation);
        } catch (error) {
            typing.remove();
            appendMessage({ role: "assistant", content: error.message, intent: "blocked" });
            els.intentStatus.textContent = "请求未完成";
        } finally {
            state.sending = false; els.sendButton.disabled = false; els.messageInput.focus();
        }
    }

    function renderCommandMenu(items, mode) {
        els.commandMenu.innerHTML = "";
        if (!items.length) {
            els.commandMenu.innerHTML = '<div class="conversation-empty">没有匹配项</div>';
        }
        items.forEach(function (item) {
            var button = document.createElement("button");
            button.className = "menu-item";
            var title = mode === "employee" ? item.name : item.title;
            var subtitle = mode === "employee" ? (item.description || (item.emp_type === "llm" ? "LLM 型数字员工" : "API 型数字员工")) : item.subtitle;
            button.innerHTML = '<span class="menu-mark">' + escapeHtml(mode === "employee" ? (item.avatar || "AI") : item.mark) + '</span>' +
                '<span class="menu-copy"><strong>' + escapeHtml(title) + '</strong><span>' + escapeHtml(subtitle) + "</span></span>";
            button.addEventListener("click", function () {
                if (mode === "employee") {
                    els.messageInput.value = "@" + item.name + " ";
                    resizeInput(); closeMenu(); els.messageInput.focus();
                } else if (item.action === "new") {
                    createConversation();
                } else {
                    els.messageInput.value = item.prompt;
                    resizeInput(); closeMenu(); els.messageInput.focus();
                }
            });
            els.commandMenu.appendChild(button);
        });
        els.commandMenu.classList.add("visible");
    }

    function inspectTrigger() {
        var value = els.messageInput.value;
        if (value.charAt(0) === "/") {
            var query = value.slice(1).toLowerCase();
            renderCommandMenu(commands.filter(function (item) { return item.title.toLowerCase().indexOf(query) >= 0; }), "command");
        } else if (value.charAt(0) === "@") {
            var name = value.slice(1).split(/\s/)[0].toLowerCase();
            renderCommandMenu(state.employees.filter(function (item) { return item.name.toLowerCase().indexOf(name) >= 0; }), "employee");
        } else closeMenu();
    }

    function closeMenu() { els.commandMenu.classList.remove("visible"); }
    function resizeInput() { els.messageInput.style.height = "38px"; els.messageInput.style.height = Math.min(150, els.messageInput.scrollHeight) + "px"; }
    function updateCharCount() { els.charCount.textContent = els.messageInput.value.length + " / 4000"; }
    function openSidebar() { document.getElementById("chatApp").classList.add("sidebar-visible"); }
    function closeSidebar() { document.getElementById("chatApp").classList.remove("sidebar-visible"); }

    function bindEvents() {
        els.newConversation.addEventListener("click", createConversation);
        els.deleteConversation.addEventListener("click", deleteConversation);
        els.sendButton.addEventListener("click", function () { sendMessage(); });
        els.messageInput.addEventListener("input", function () { resizeInput(); updateCharCount(); inspectTrigger(); });
        els.messageInput.addEventListener("keydown", function (event) {
            if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); sendMessage(); }
            if (event.key === "Escape") closeMenu();
        });
        els.slashButton.addEventListener("click", function () { els.messageInput.value = "/"; resizeInput(); inspectTrigger(); els.messageInput.focus(); });
        els.mentionButton.addEventListener("click", function () { els.messageInput.value = "@"; resizeInput(); inspectTrigger(); els.messageInput.focus(); });
        document.querySelectorAll("[data-prompt]").forEach(function (button) {
            button.addEventListener("click", function () { sendMessage(button.dataset.prompt); });
        });
        document.getElementById("sidebarOpen").addEventListener("click", openSidebar);
        document.getElementById("sidebarClose").addEventListener("click", closeSidebar);
        document.getElementById("sidebarMask").addEventListener("click", closeSidebar);
        window.addEventListener("resize", function () { state.charts.forEach(function (chart) { chart.resize(); }); });
        document.addEventListener("click", function (event) {
            if (!event.target.closest(".compose-zone")) closeMenu();
        });
    }

    async function bootstrap() {
        var data = await api("/api/chat/bootstrap");
        state.models = data.models; state.employees = data.employees; state.conversations = data.conversations;
        renderModels(); renderConversations();
        if (state.conversations.length) await loadConversation(state.conversations[0].id);
        else await createConversation();
    }

    document.addEventListener("DOMContentLoaded", function () {
        ["conversationList", "modelSelect", "conversationTitle", "conversationMeta", "dialogZone",
            "messageStream", "emptyState", "messageInput", "sendButton", "commandMenu", "newConversation",
            "deleteConversation", "slashButton", "mentionButton", "intentStatus", "charCount"].forEach(function (id) {
            els[id] = document.getElementById(id);
        });
        bindEvents();
        bootstrap().catch(function (error) {
            els.emptyState.querySelector("h1").textContent = error.message;
        });
    });
})();
