let currentTable = null;
let autoRefresh = true;
let refreshInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

function initApp() {
    fetchTables();

    document.getElementById('refresh-btn').addEventListener('click', () => {
        fetchTables();
        if (currentTable) fetchTableData(currentTable);
    });

    const toggleBtn = document.getElementById('auto-refresh-toggle');
    toggleBtn.addEventListener('click', () => {
        autoRefresh = !autoRefresh;
        toggleBtn.innerText = `Auto Refresh: ${autoRefresh ? 'ON' : 'OFF'}`;
        toggleBtn.classList.toggle('btn-secondary', autoRefresh);
        if (autoRefresh) {
            startAutoRefresh();
        } else {
            stopAutoRefresh();
        }
    });

    startAutoRefresh();
}

function startAutoRefresh() {
    stopAutoRefresh();
    refreshInterval = setInterval(() => {
        if (autoRefresh) {
            fetchTables(false);
            if (currentTable) fetchTableData(currentTable, false);
        }
    }, 3000);
}

function stopAutoRefresh() {
    if (refreshInterval) clearInterval(refreshInterval);
}

async function fetchTables(showLoading = true) {
    const listEl = document.getElementById('tables-list');
    if (showLoading && listEl.children.length === 1 && listEl.children[0].classList.contains('loading')) {
        // Keep loading state
    }

    try {
        const res = await fetch('/api/tables');
        const data = await res.json();
        
        if (data.tables) {
            renderTablesList(data.tables);
            // Select first table by default if none selected
            if (!currentTable && data.tables.length > 0) {
                selectTable(data.tables[0]);
            }
        }
    } catch (err) {
        console.error('Failed to fetch tables:', err);
    }
}

function renderTablesList(tables) {
    const listEl = document.getElementById('tables-list');
    listEl.innerHTML = '';

    tables.forEach(tableName => {
        const li = document.createElement('li');
        li.innerText = `📋 ${tableName}`;
        if (tableName === currentTable) {
            li.classList.add('active');
        }
        li.addEventListener('click', () => selectTable(tableName));
        listEl.appendChild(li);
    });
}

function selectTable(tableName) {
    currentTable = tableName;
    renderTablesList(Array.from(document.querySelectorAll('#tables-list li')).map(el => el.innerText.replace('📋 ', '')));
    
    document.getElementById('active-table-title').innerText = `Table: ${tableName}`;
    document.getElementById('table-subtitle').innerText = `Viewing records inside SQLite table '${tableName}'`;
    
    fetchTableData(tableName);
}

async function fetchTableData(tableName, showSpinner = true) {
    const container = document.getElementById('table-container');
    if (showSpinner && container.querySelector('.empty-state')) {
        container.innerHTML = '<div class="empty-state"><h3>Loading data...</h3></div>';
    }

    try {
        const res = await fetch(`/api/table/${tableName}`);
        const data = await res.json();

        if (data.error) {
            container.innerHTML = `<div class="empty-state"><h3>Error</h3><p>${data.error}</p></div>`;
            return;
        }

        renderTableGrid(data);
    } catch (err) {
        console.error(`Failed to fetch data for ${tableName}:`, err);
    }
}

function renderTableGrid(tableData) {
    const container = document.getElementById('table-container');
    const badge = document.getElementById('row-count-badge');

    badge.innerText = `${tableData.row_count} rows`;
    badge.classList.remove('hidden');

    if (!tableData.data || tableData.data.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="icon">📭</div>
                <h3>Table is Empty</h3>
                <p>No rows found inside '${tableData.table_name}'. Run a workbench step to populate it!</p>
            </div>`;
        return;
    }

    let html = '<table><thead><tr>';
    tableData.columns.forEach(col => {
        html += `<th>${escapeHtml(col)}</th>`;
    });
    html += '</tr></thead><tbody>';

    tableData.data.forEach(row => {
        html += '<tr>';
        tableData.columns.forEach(col => {
            const val = row[col];
            if (val === null || val === undefined) {
                html += `<td class="null-value">NULL</td>`;
            } else if (typeof val === 'number') {
                html += `<td class="num-cell">${val}</td>`;
            } else {
                html += `<td>${escapeHtml(String(val))}</td>`;
            }
        });
        html += '</tr>';
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

function escapeHtml(str) {
    return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
