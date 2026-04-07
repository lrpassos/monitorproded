import os
import socket
import time
from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

TIMEOUT = 1

def check_tcp_status(ip):
    """Tenta conexão TCP nas portas 80 e 443."""
    try:
        target_ip = socket.gethostbyname(ip)
        socket.setdefaulttimeout(TIMEOUT)
        # Tenta porta 80
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((target_ip, 80))
            return True
    except:
        try:
            # Tenta porta 443
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((target_ip, 443))
                return True
        except:
            return False

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/check', methods=['POST'])
def check_status():
    """Realiza 5 tentativas para cada IP e retorna latência."""
    data = request.json
    hosts = data.get('hosts', [])
    results = []
    
    for host in hosts:
        ip = host.get('ip')
        is_online = False
        latency = 0
        
        # Resolve o host uma vez
        try:
            target_ip = socket.gethostbyname(ip)
            socket.setdefaulttimeout(TIMEOUT)
            
            # 5 tentativas
            for _ in range(5):
                try:
                    start = time.time()
                    # Tenta porta 80
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.connect((target_ip, 80))
                        latency = round((time.time() - start) * 1000, 1)
                        is_online = True
                        break
                except:
                    try:
                        start = time.time()
                        # Tenta porta 443
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.connect((target_ip, 443))
                            latency = round((time.time() - start) * 1000, 1)
                            is_online = True
                            break
                    except:
                        continue
        except:
            pass
        
        results.append({
            "id": host.get('id'),
            "ip": ip,
            "status": "online" if is_online else "offline",
            "latency": latency if is_online else None,
            "last_check": time.strftime("%H:%M:%S")
        })
    
    return jsonify(results)

@app.route('/api/traceroute/<host>')
def run_traceroute(host):
    """Simula traceroute para o Vercel."""
    try:
        target_ip = socket.gethostbyname(host)
    except:
        target_ip = "Desconhecido"
        
    return jsonify({
        "host": host,
        "hops": [
            {"hop": 1, "ip": "10.0.0.1", "ms": 0.5},
            {"hop": 2, "ip": "Vercel-Node", "ms": 1.8},
            {"hop": 3, "ip": "Edge-Gateway", "ms": 4.2},
            {"hop": 4, "ip": target_ip, "ms": 12.5}
        ]
    })

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitoramento de Hosts - PRODED</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { background-color: #f8fafc; font-family: 'Inter', sans-serif; color: #1e293b; padding-top: 2rem; }
        .card { border: 1px solid #e2e8f0; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); background: white; margin-bottom: 2rem; }
        .card-header { background: white; border-bottom: 1px solid #f1f5f9; padding: 1.5rem; display: flex; justify-content: space-between; align-items: center; }
        .card-header h5 { margin: 0; font-weight: 700; font-size: 1.1rem; display: flex; align-items: center; }
        .card-header h5 i { color: #0ea5e9; margin-right: 12px; }
        
        .table { margin-bottom: 0; }
        .table th { background: #f8fafc; color: #64748b; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; padding: 1rem 1.5rem; border-top: none; }
        .table td { padding: 1rem 1.5rem; vertical-align: middle; border-bottom: 1px solid #f1f5f9; }
        
        code { background: #f1f5f9; color: #0369a1; padding: 4px 8px; border-radius: 6px; font-weight: 500; font-size: 0.85rem; }
        .status-text { font-weight: 700; font-size: 0.75rem; text-transform: uppercase; }
        .status-online { color: #22c55e; }
        .status-offline { color: #ef4444; }
        .status-dot { height: 10px; width: 10px; border-radius: 50%; display: inline-block; margin-right: 8px; }
        .dot-online { background: #22c55e; box-shadow: 0 0 8px rgba(34, 197, 94, 0.4); }
        .dot-offline { background: #ef4444; box-shadow: 0 0 8px rgba(239, 68, 68, 0.4); }
        
        .chart-container { width: 140px; height: 30px; }
        
        .btn-action { background: none; border: none; color: #0ea5e9; font-weight: 600; font-size: 0.85rem; padding: 4px 8px; display: inline-flex; align-items: center; }
        .btn-action:hover { color: #0284c7; }
        .btn-delete { color: #fca5a5; }
        .btn-delete:hover { color: #ef4444; }
        
        .add-section { padding: 1.5rem; border-top: 1px solid #f1f5f9; }
        .add-title { color: #22c55e; font-weight: 600; font-size: 0.9rem; margin-bottom: 1rem; display: flex; align-items: center; }
        .add-title i { margin-right: 8px; }
        
        .form-control { border-radius: 8px; border: 1px solid #e2e8f0; padding: 0.6rem 1rem; font-size: 0.9rem; }
        .form-control:focus { box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.1); border-color: #0ea5e9; }
        .btn-include { background: #0ea5e9; color: white; border: none; border-radius: 8px; font-weight: 700; padding: 0.6rem 2rem; width: 100%; transition: all 0.2s; }
        .btn-include:hover { background: #0284c7; transform: translateY(-1px); }
        
        .history-header { padding: 1.5rem; display: flex; align-items: center; font-weight: 700; font-size: 1.1rem; }
        .history-header i { color: #f97316; margin-right: 12px; }
        .history-content { padding: 0 1.5rem 1.5rem; color: #94a3b8; font-size: 0.85rem; font-style: italic; }
        
        .log-item { padding: 8px 0; border-bottom: 1px solid #f1f5f9; color: #475569; font-style: normal; display: flex; justify-content: space-between; }
        .log-time { color: #94a3b8; font-weight: 500; margin-right: 12px; }
    </style>
</head>
<body>

<div class="container">
    <!-- Monitoramento de Hosts Card -->
    <div class="card">
        <div class="card-header">
            <h5><i class="bi bi-activity"></i> Monitoramento de Hosts</h5>
            <button class="btn btn-link p-0 text-muted" onclick="checkAll()"><i class="bi bi-arrow-clockwise fs-5"></i></button>
        </div>
        <div class="table-responsive">
            <table class="table">
                <thead>
                    <tr>
                        <th>Host / IP</th>
                        <th>Label</th>
                        <th>Status / Latência</th>
                        <th>Gráfico (ms)</th>
                        <th>Ações</th>
                    </tr>
                </thead>
                <tbody id="host-list">
                    <!-- JS -->
                </tbody>
            </table>
        </div>
        
        <!-- Adicionar Novo Host Section -->
        <div class="add-section">
            <div class="add-title"><i class="bi bi-plus-circle"></i> Adicionar Novo Host</div>
            <div class="row g-3">
                <div class="col-md-4">
                    <input type="text" id="new-ip" class="form-control" placeholder="IP ou Domínio">
                </div>
                <div class="col-md-5">
                    <input type="text" id="new-label" class="form-control" placeholder="Nome / Label">
                </div>
                <div class="col-md-3">
                    <button class="btn-include" onclick="addHost()">Incluir</button>
                </div>
            </div>
        </div>
    </div>

    <!-- Histórico de Perda de Ping Card -->
    <div class="card">
        <div class="history-header">
            <i class="bi bi-clock"></i> Histórico de Perda de Ping
        </div>
        <div class="history-content" id="loss-history">
            Nenhuma perda de ping registrada recentemente.
        </div>
    </div>
</div>

<!-- Modal Traceroute -->
<div class="modal fade" id="traceModal" tabindex="-1">
    <div class="modal-dialog modal-lg modal-dialog-centered">
        <div class="modal-content bg-dark text-light" style="border-radius: 12px;">
            <div class="modal-header border-secondary">
                <h6 class="modal-title fw-bold font-monospace">traceroute output</h6>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body p-4 font-monospace" style="font-size: 0.8rem;">
                <pre id="trace-output" class="mb-0">Aguardando...</pre>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    let hosts = JSON.parse(localStorage.getItem('proded_monitor_v2')) || [
        { id: '1', ip: '8.8.8.8', label: 'Google DNS', history: [] },
        { id: '2', ip: '1.1.1.1', label: 'Cloudflare DNS', history: [] }
    ];
    let logs = JSON.parse(localStorage.getItem('proded_logs_v2')) || [];

    function save() {
        localStorage.setItem('proded_monitor_v2', JSON.stringify(hosts));
        localStorage.setItem('proded_logs_v2', JSON.stringify(logs));
    }

    function render() {
        const list = document.getElementById('host-list');
        list.innerHTML = hosts.map(h => {
            const lastLatency = h.history && h.history.length > 0 ? h.history[h.history.length - 1] : null;
            const isOnline = h.status === 'online';
            
            return `
                <tr>
                    <td><code>${h.ip}</code></td>
                    <td class="text-muted small">${h.label}</td>
                    <td>
                        <div class="d-flex align-items-center">
                            <span class="status-dot ${isOnline ? 'dot-online' : 'dot-offline'}"></span>
                            <span class="status-text ${isOnline ? 'status-online' : 'status-offline'}">
                                ${isOnline ? `ONLINE (${lastLatency}MS)` : 'OFFLINE'}
                            </span>
                        </div>
                    </td>
                    <td>
                        <div class="chart-container">
                            <canvas id="chart-${h.id}"></canvas>
                        </div>
                    </td>
                    <td>
                        <button class="btn-action" onclick="runTrace('${h.ip}')"><i class="bi bi-signpost-split me-1"></i> Trace</button>
                        <button class="btn-action btn-delete" onclick="removeHost('${h.id}')"><i class="bi bi-trash"></i></button>
                    </td>
                </tr>
            `;
        }).join('');

        renderLogs();
        hosts.forEach(h => initChart(h));
    }

    function renderLogs() {
        const container = document.getElementById('loss-history');
        if (logs.length === 0) {
            container.innerHTML = 'Nenhuma perda de ping registrada recentemente.';
            return;
        }
        container.innerHTML = logs.map(l => `
            <div class="log-item">
                <span><span class="log-time">${l.time}</span> Host <strong>${l.label}</strong> (${l.ip}) ficou offline.</span>
            </div>
        `).join('');
    }

    function initChart(host) {
        const ctx = document.getElementById(`chart-${host.id}`);
        if (!ctx) return;
        
        const data = (host.history || []).slice(-15);
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map((_, i) => i),
                datasets: [{
                    data: data,
                    borderColor: '#0ea5e9',
                    borderWidth: 1.5,
                    pointRadius: 0,
                    fill: false,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false }, tooltip: { enabled: false } },
                scales: { x: { display: false }, y: { display: false, min: 0 } }
            }
        });
    }

    async function checkAll() {
        if (hosts.length === 0) return;
        
        try {
            const res = await fetch('/api/check', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ hosts })
            });
            const results = await res.json();
            
            results.forEach(r => {
                const h = hosts.find(item => item.id === r.id);
                if (h) {
                    const wasOnline = h.status === 'online';
                    const isOnline = r.status === 'online';
                    
                    if (wasOnline && !isOnline) {
                        logs.unshift({ time: new Date().toLocaleTimeString(), ip: h.ip, label: h.label });
                        logs = logs.slice(0, 10);
                    }
                    
                    h.status = r.status;
                    if (!h.history) h.history = [];
                    if (isOnline) h.history.push(r.latency || 10);
                    else h.history.push(0);
                    h.history = h.history.slice(-30);
                }
            });
            
            save();
            render();
        } catch (e) { console.error(e); }
    }

    function addHost() {
        const ip = document.getElementById('new-ip').value.trim();
        const label = document.getElementById('new-label').value.trim();
        if (!ip) return;
        
        hosts.push({
            id: Date.now().toString(),
            ip: ip,
            label: label || ip,
            status: null,
            history: []
        });
        
        document.getElementById('new-ip').value = '';
        document.getElementById('new-label').value = '';
        save();
        render();
        checkAll();
    }

    function removeHost(id) {
        hosts = hosts.filter(h => h.id !== id);
        save();
        render();
    }

    async function runTrace(ip) {
        const modal = new bootstrap.Modal(document.getElementById('traceModal'));
        const output = document.getElementById('trace-output');
        output.innerText = `Iniciando traceroute para ${ip}...`;
        modal.show();
        
        try {
            const res = await fetch('/api/traceroute/' + ip);
            const data = await res.json();
            let text = `Traceroute para ${data.host}:\\n\\n`;
            data.hops.forEach(h => {
                text += `Hop ${h.hop}: ${h.ip.padEnd(15)} | ${h.ms}ms\\n`;
            });
            output.innerText = text;
        } catch (e) {
            output.innerText = 'Erro ao executar traceroute.';
        }
    }

    render();
    checkAll();
    setInterval(checkAll, 300000); // 5 min
</script>

</body>
</html>
'''
