/**
 * Sales Forecast Engine — Main Client JavaScript
 */

document.addEventListener("DOMContentLoaded", () => {
    App.init();
});

const App = {
    currentTab: "tab-dashboard",
    currentCrudEntity: "quotes",
    forecastData: null,
    settingsData: null,
    uploadedRawData: [],
    uploadedColumns: [],

    init() {
        this.bindEvents();
        this.loadForecast();
        this.loadSettings();
        this.loadDirectories();
    },

    bindEvents() {
        // Navigation Tab Switching
        document.querySelectorAll(".nav-btn").forEach(btn => {
            btn.addEventListener("click", (e) => {
                const targetTab = btn.getAttribute("data-tab");
                this.switchTab(targetTab);
            });
        });

        // Recalculate Button
        document.getElementById("btn-recalculate").addEventListener("click", () => {
            this.loadForecast();
        });

        // Workbench toggle between Quotes and Backlog
        document.getElementById("btn-view-quotes").addEventListener("click", (e) => {
            e.target.classList.add("active");
            document.getElementById("btn-view-backlog").classList.remove("active");
            this.currentCrudEntity = "quotes";
            this.loadCrudTable();
        });

        document.getElementById("btn-view-backlog").addEventListener("click", (e) => {
            e.target.classList.add("active");
            document.getElementById("btn-view-quotes").classList.remove("active");
            this.currentCrudEntity = "backlog";
            this.loadCrudTable();
        });

        // Search Filter
        document.getElementById("search-workbench").addEventListener("input", (e) => {
            this.filterCrudTable(e.target.value);
        });

        // Add Record Button
        document.getElementById("btn-add-record").addEventListener("click", () => {
            this.openCrudModal();
        });

        // Modal Close
        document.getElementById("modal-crud-close").addEventListener("click", () => {
            document.getElementById("modal-crud").classList.add("hidden");
        });

        // Form CRUD Submit
        document.getElementById("form-crud").addEventListener("submit", (e) => {
            e.preventDefault();
            this.saveCrudRecord();
        });

        // File Drag and Drop & Import
        const dropZone = document.getElementById("drop-zone");
        const fileInput = document.getElementById("file-input");

        dropZone.addEventListener("dragover", (e) => {
            e.preventDefault();
            dropZone.classList.add("dragover");
        });

        dropZone.addEventListener("dragleave", () => {
            dropZone.classList.remove("dragover");
        });

        dropZone.addEventListener("drop", (e) => {
            e.preventDefault();
            dropZone.classList.remove("dragover");
            if (e.dataTransfer.files.length) {
                this.handleFileUpload(e.dataTransfer.files[0]);
            }
        });

        fileInput.addEventListener("change", (e) => {
            if (e.target.files.length) {
                this.handleFileUpload(e.target.files[0]);
            }
        });

        document.getElementById("btn-confirm-ingest").addEventListener("click", () => {
            this.confirmIngestion();
        });

        // Model Fit Button
        document.getElementById("btn-fit-model").addEventListener("click", () => {
            this.fitModel();
        });
    },

    switchTab(tabId) {
        document.querySelectorAll(".nav-btn").forEach(b => b.classList.remove("active"));
        document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

        const activeNav = document.querySelector(`.nav-btn[data-tab="${tabId}"]`);
        if (activeNav) activeNav.classList.add("active");

        const activePane = document.getElementById(tabId);
        if (activePane) activePane.classList.add("active");

        this.currentTab = tabId;

        // Update titles
        const titles = {
            "tab-dashboard": "Executive Sales Forecast",
            "tab-whatif": "What-If Factor Sensitivity Engine",
            "tab-workbench": "Quotation & Backlog Data Workbench",
            "tab-directories": "Customer & Supplier Directories",
            "tab-ingest": "Data Ingestion & Column Mapping",
            "tab-settings": "Model Settings & Fallback Management",
            "tab-inspector": "Live SQLite Database Inspector"
        };
        document.getElementById("page-title").textContent = titles[tabId] || "Sales Forecast Engine";

        if (tabId === "tab-workbench") this.loadCrudTable();
        if (tabId === "tab-inspector") this.loadInspectorTables();
    },

    // =========================================================================
    // API CALLS & DATA LOADING
    // =========================================================================

    async loadForecast() {
        try {
            const res = await fetch("/api/forecast");
            const data = await res.json();
            if (data.error) return alert("Error: " + data.error);
            this.forecastData = data;
            this.renderDashboard();
            this.renderWhatIfCharts();
        } catch (e) {
            console.error(e);
        }
    },

    async loadSettings() {
        try {
            const res = await fetch("/api/settings");
            const data = await res.json();
            if (data.error) return;
            this.settingsData = data;
            this.renderWhatIfToggles();
            this.renderSettingsTables();
        } catch (e) {
            console.error(e);
        }
    },

    async loadDirectories() {
        try {
            const custRes = await fetch("/api/table/customers");
            const custData = await custRes.json();
            this.renderTableBody("tbl-cust-body", custData.data || [], ["customer_code", "customer_name", "payment_term", "sales_employee"]);

            const supRes = await fetch("/api/table/supplier_settings");
            const supData = await supRes.json();
            this.renderTableBody("tbl-sup-body", supData.data || [], ["supplier_code", "supplier_name", "lead_time_offset_days", "win_rate_modifier"]);
        } catch (e) {
            console.error(e);
        }
    },

    // =========================================================================
    // DASHBOARD RENDERING
    // =========================================================================

    renderDashboard() {
        if (!this.forecastData) return;
        const kpis = this.forecastData.kpis;

        document.getElementById("kpi-total").textContent = `$${kpis.total_projected.toLocaleString('en-US', {minimumFractionDigits:2})}`;
        document.getElementById("kpi-pipeline").textContent = `$${kpis.pipeline_revenue.toLocaleString('en-US', {minimumFractionDigits:2})}`;
        document.getElementById("kpi-backlog").textContent = `$${kpis.backlog_revenue.toLocaleString('en-US', {minimumFractionDigits:2})}`;
        document.getElementById("kpi-winrate").textContent = `${kpis.avg_win_rate}%`;

        document.getElementById("kpi-quotes-count").textContent = `${kpis.open_quotes_count} Open Quotes`;
        document.getElementById("kpi-orders-count").textContent = `${kpis.backlog_orders_count} Open Sales Orders`;

        // Render Stacked Forecast Chart
        const summary = this.forecastData.monthly_summary || [];
        const chartContainer = document.getElementById("chart-bars");
        chartContainer.innerHTML = "";

        const maxVal = Math.max(...summary.map(s => s.total), 1.0);

        summary.forEach(item => {
            const col = document.createElement("div");
            col.className = "bar-column";

            const pipePct = (item.pipeline / maxVal) * 100;
            const backPct = (item.backlog / maxVal) * 100;
            const totalPct = (item.total / maxVal) * 100;

            col.innerHTML = `
                <div class="bar-tooltip">$${item.total.toLocaleString()} (${item.month})</div>
                <div class="bar-stack" style="height: ${Math.max(totalPct, 5)}%;">
                    <div class="bar-segment bg-emerald" style="height: ${(item.backlog / (item.total || 1)) * 100}%;" title="Backlog: $${item.backlog}"></div>
                    <div class="bar-segment bg-amber" style="height: ${(item.pipeline / (item.total || 1)) * 100}%;" title="Pipeline: $${item.pipeline}"></div>
                </div>
                <span class="bar-label">${item.month}</span>
            `;
            chartContainer.appendChild(col);
        });

        // Render Breakdown Table
        const tbody = document.getElementById("tbl-monthly-body");
        tbody.innerHTML = "";
        summary.forEach(s => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td><strong>${s.month}</strong></td>
                <td class="text-amber">$${s.pipeline.toLocaleString()}</td>
                <td class="text-emerald">$${s.backlog.toLocaleString()}</td>
                <td><strong>$${s.total.toLocaleString()}</strong></td>
                <td class="text-dim">$${s.p10.toLocaleString()}</td>
                <td class="text-indigo">$${s.p90.toLocaleString()}</td>
            `;
            tbody.appendChild(tr);
        });

        // Render Queues
        const overdue = this.forecastData.queues.overdue_quotes || [];
        document.getElementById("cnt-overdue").textContent = overdue.length;
        const listOverdue = document.getElementById("list-overdue");
        listOverdue.innerHTML = overdue.length ? "" : '<li class="empty-item">No overdue follow-up quotes.</li>';
        overdue.slice(0, 5).forEach(q => {
            const li = document.createElement("li");
            li.className = "queue-item";
            li.innerHTML = `<span><strong>${q.quote_ref_no || q.quote_id}</strong> (${q.customer_name})</span> <span class="status-pill status-lost">${q.follow_up_status}</span>`;
            listOverdue.appendChild(li);
        });

        const unmatched = this.forecastData.queues.unmatched_po_backlog || [];
        document.getElementById("cnt-unmatched").textContent = unmatched.length;
        const listUnmatched = document.getElementById("list-unmatched");
        listUnmatched.innerHTML = unmatched.length ? "" : '<li class="empty-item">All sales orders matched to POs.</li>';
        unmatched.slice(0, 5).forEach(b => {
            const li = document.createElement("li");
            li.className = "queue-item";
            li.innerHTML = `<span><strong>${b.so_number || b.order_id}</strong> (${b.part_code})</span> <span class="status-pill status-open">No PO Match</span>`;
            listUnmatched.appendChild(li);
        });
    },

    // =========================================================================
    // WHAT-IF SENSITIVITY ENGINE
    // =========================================================================

    renderWhatIfToggles() {
        if (!this.settingsData) return;
        const grid = document.getElementById("whatif-toggles-grid");
        grid.innerHTML = "";

        const coefs = this.settingsData.coefficients || [];
        coefs.forEach(item => {
            const card = document.createElement("div");
            card.className = `toggle-card ${item.is_enabled ? '' : 'disabled'}`;
            card.innerHTML = `
                <div>
                    <strong>${item.key}</strong>
                    <div style="font-size:0.75rem; color:var(--text-dim);">${item.category} • W: ${item.value}</div>
                </div>
                <label class="switch">
                    <input type="checkbox" ${item.is_enabled ? 'checked' : ''} data-key="${item.key}">
                    <span class="slider"></span>
                </label>
            `;
            const chk = card.querySelector("input");
            chk.addEventListener("change", (e) => {
                this.toggleCoefficient(item.key, e.target.checked);
            });
            grid.appendChild(card);
        });
    },

    async toggleCoefficient(key, isEnabled) {
        const toggles = {};
        toggles[key] = isEnabled;
        try {
            const res = await fetch("/api/forecast/recalculate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ toggles })
            });
            const data = await res.json();
            this.forecastData = data;
            this.renderDashboard();
            this.renderWhatIfCharts();
            this.loadSettings();
        } catch (e) {
            console.error(e);
        }
    },

    renderWhatIfCharts() {
        if (!this.forecastData) return;
        const container = document.getElementById("whatif-chart-bars");
        container.innerHTML = "";

        const summary = this.forecastData.monthly_summary || [];
        const maxVal = Math.max(...summary.map(s => s.total), 1.0);

        summary.forEach(item => {
            const col = document.createElement("div");
            col.className = "bar-column";
            const totalPct = (item.total / maxVal) * 100;
            col.innerHTML = `
                <div class="bar-tooltip">$${item.total.toLocaleString()}</div>
                <div class="bar-stack" style="height: ${Math.max(totalPct, 5)}%;">
                    <div class="bar-segment bg-indigo-line" style="height: 100%;"></div>
                </div>
                <span class="bar-label">${item.month}</span>
            `;
            container.appendChild(col);
        });
    },

    // =========================================================================
    // CRUD WORKBENCH
    // =========================================================================

    async loadCrudTable() {
        try {
            const table = this.currentCrudEntity === "quotes" ? "quotes" : "backlog";
            const res = await fetch(`/api/table/${table}`);
            const data = await res.json();

            const thead = document.getElementById("tbl-crud-head");
            const tbody = document.getElementById("tbl-crud-body");

            if (this.currentCrudEntity === "quotes") {
                thead.innerHTML = `
                    <tr>
                        <th>Ref No</th><th>Customer</th><th>Value ($)</th><th>Quarter</th><th>Status</th><th>Confidence</th><th>Actions</th>
                    </tr>
                `;
                tbody.innerHTML = (data.data || []).map(r => `
                    <tr>
                        <td><strong>${r.quote_ref_no || r.quote_id}</strong></td>
                        <td>${r.customer_name}</td>
                        <td class="font-mono">$${(r.quote_value || 0).toLocaleString()}</td>
                        <td>${r.quarter || 'Q1/2025'}</td>
                        <td><span class="status-pill status-${(r.status || 'open').toLowerCase()}">${r.status || 'Open'}</span></td>
                        <td>${r.confidence_level || 'Medium'}</td>
                        <td>
                            <button class="btn btn-secondary" style="padding:2px 6px;" onclick="App.deleteRecord('quotes', '${r.quote_id}')">🗑️</button>
                        </td>
                    </tr>
                `).join("");
            } else {
                thead.innerHTML = `
                    <tr>
                        <th>SO Number</th><th>Part Code</th><th>Customer</th><th>Qty</th><th>Value ($)</th><th>Due Date</th><th>Actions</th>
                    </tr>
                `;
                tbody.innerHTML = (data.data || []).map(r => `
                    <tr>
                        <td><strong>${r.so_number || r.order_id}</strong></td>
                        <td>${r.part_code}</td>
                        <td>${r.customer_name}</td>
                        <td>${r.outstanding_qty}</td>
                        <td class="font-mono">$${(r.order_value || 0).toLocaleString()}</td>
                        <td>${r.due_date}</td>
                        <td>
                            <button class="btn btn-secondary" style="padding:2px 6px;" onclick="App.deleteRecord('backlog', '${r.order_id}')">🗑️</button>
                        </td>
                    </tr>
                `).join("");
            }
        } catch (e) {
            console.error(e);
        }
    },

    filterCrudTable(query) {
        const q = query.toLowerCase();
        document.querySelectorAll("#tbl-crud-body tr").forEach(tr => {
            tr.style.display = tr.textContent.toLowerCase().includes(q) ? "" : "none";
        });
    },

    async deleteRecord(table, pkVal) {
        if (!confirm(`Delete record '${pkVal}'?`)) return;
        try {
            const res = await fetch(`/api/crud/${table}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "delete", record: { quote_id: pkVal, order_id: pkVal } })
            });
            await res.json();
            this.loadCrudTable();
            this.loadForecast();
        } catch (e) {
            console.error(e);
        }
    },

    openCrudModal() {
        const fields = document.getElementById("form-crud-fields");
        if (this.currentCrudEntity === "quotes") {
            fields.innerHTML = `
                <div class="form-group"><label>Quote Ref No</label><input type="text" id="m-ref" class="input-search" value="QRN-${Date.now().toString().slice(-4)}"></div>
                <div class="form-group"><label>Customer Name</label><input type="text" id="m-cust" class="input-search" value="Acme Corp"></div>
                <div class="form-group"><label>Quote Value ($)</label><input type="number" id="m-val" class="input-search" value="15000"></div>
                <div class="form-group"><label>Status</label><select id="m-status" class="select-field"><option value="Open">Open</option><option value="Won">Won</option><option value="Lost">Lost</option></select></div>
                <div class="form-group"><label>Confidence Level</label><select id="m-conf" class="select-field"><option value="High">High</option><option value="Medium">Medium</option><option value="Low">Low</option></select></div>
            `;
        }
        document.getElementById("modal-crud").classList.remove("hidden");
    },

    async saveCrudRecord() {
        const record = {
            quote_id: `Q-${Date.now()}`,
            quote_ref_no: document.getElementById("m-ref").value,
            customer_name: document.getElementById("m-cust").value,
            quote_value: parseFloat(document.getElementById("m-val").value),
            status: document.getElementById("m-status").value,
            confidence_level: document.getElementById("m-conf").value,
            quote_date: new Date().toISOString().split("T")[0]
        };

        try {
            const res = await fetch("/api/crud/quotes", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ action: "create", record })
            });
            await res.json();
            document.getElementById("modal-crud").classList.add("hidden");
            this.loadCrudTable();
            this.loadForecast();
        } catch (e) {
            console.error(e);
        }
    },

    // =========================================================================
    // INGESTION & HEADER MAPPER
    // =========================================================================

    async handleFileUpload(file) {
        const formData = new FormData();
        formData.append("file", file);

        try {
            const res = await fetch("/api/upload", {
                method: "POST",
                body: formData
            });
            const data = await res.json();
            if (data.error) return alert("Upload error: " + data.error);

            this.uploadedColumns = data.columns || [];
            this.uploadedRawData = data.raw_data || [];

            this.renderMappingModal(data.columns, data.preview[0] || {});
        } catch (e) {
            console.error(e);
        }
    },

    renderMappingModal(columns, sampleRow) {
        const modal = document.getElementById("mapping-modal");
        modal.classList.remove("hidden");

        const targetFields = [
            "quote_ref_no", "quote_date", "customer_code", "customer_name",
            "account_manager", "confidence_level", "quote_value", "status"
        ];

        const tbody = document.getElementById("tbl-mapping-body");
        tbody.innerHTML = "";

        targetFields.forEach(field => {
            const tr = document.createElement("tr");
            
            // Auto match column name
            const bestMatch = columns.find(c => c.toLowerCase().replace(/ /g, "_") === field) || "";

            const options = ['<option value="">-- Ignore --</option>']
                .concat(columns.map(c => `<option value="${c}" ${c === bestMatch ? 'selected' : ''}>${c}</option>`));

            tr.innerHTML = `
                <td><strong>${field}</strong></td>
                <td><select class="select-field sel-map" data-target="${field}">${options.join("")}</select></td>
                <td class="text-muted">${sampleRow[bestMatch] || '-'}</td>
            `;
            tbody.appendChild(tr);
        });
    },

    async confirmIngestion() {
        const entityType = document.getElementById("sel-entity-type").value;
        const mapping = {};
        document.querySelectorAll(".sel-map").forEach(sel => {
            const target = sel.getAttribute("data-target");
            const source = sel.value;
            if (source) mapping[target] = source;
        });

        try {
            const res = await fetch("/api/ingest/confirm", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    entity_type: entityType,
                    mapping: mapping,
                    raw_data: this.uploadedRawData
                })
            });
            const data = await res.json();
            alert(data.message || "Ingestion complete!");
            document.getElementById("mapping-modal").classList.add("hidden");
            this.loadForecast();
        } catch (e) {
            console.error(e);
        }
    },

    // =========================================================================
    // MODEL FITTING & SETTINGS
    // =========================================================================

    async fitModel() {
        try {
            const res = await fetch("/api/model/fit", { method: "POST" });
            const data = await res.json();
            alert(data.message || "Model refitted successfully!");
            this.loadSettings();
            this.loadForecast();
        } catch (e) {
            console.error(e);
        }
    },

    renderSettingsTables() {
        if (!this.settingsData) return;
        this.renderTableBody("tbl-coef-body", this.settingsData.coefficients || [], ["key", "category", "value", "is_enabled"]);
        this.renderTableBody("tbl-quintile-body", this.settingsData.quote_bands || [], ["band_name", "min_val", "max_val", "is_derived"]);
    },

    // =========================================================================
    // LIVE DB INSPECTOR
    // =========================================================================

    async loadInspectorTables() {
        try {
            const res = await fetch("/api/tables");
            const data = await res.json();
            const container = document.getElementById("inspector-table-list");
            container.innerHTML = "";
            (data.tables || []).forEach(t => {
                const btn = document.createElement("button");
                btn.className = "btn btn-secondary";
                btn.textContent = t;
                btn.addEventListener("click", () => this.inspectTable(t));
                container.appendChild(btn);
            });
            if (data.tables && data.tables.length) this.inspectTable(data.tables[0]);
        } catch (e) {
            console.error(e);
        }
    },

    async inspectTable(tableName) {
        try {
            document.getElementById("active-table-title").textContent = `Table: ${tableName}`;
            const res = await fetch(`/api/table/${tableName}`);
            const data = await res.json();

            const cols = data.columns || [];
            const rows = data.data || [];

            const thead = document.getElementById("tbl-inspector-head");
            const tbody = document.getElementById("tbl-inspector-body");

            thead.innerHTML = `<tr>${cols.map(c => `<th>${c}</th>`).join("")}</tr>`;
            tbody.innerHTML = rows.map(r => `
                <tr>${cols.map(c => `<td>${r[c] !== null ? r[c] : ''}</td>`).join("")}</tr>
            `).join("");
        } catch (e) {
            console.error(e);
        }
    },

    // Utility Helper
    renderTableBody(elementId, data, keys) {
        const tbody = document.getElementById(elementId);
        if (!tbody) return;
        tbody.innerHTML = data.map(r => `
            <tr>${keys.map(k => `<td>${r[k] !== undefined ? r[k] : ''}</td>`).join("")}</tr>
        `).join("");
    }
};

window.App = App;
