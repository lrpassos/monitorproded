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
            
            # Portas para tentar (Comuns em provedores e servidores)
            # 80/443 (Web), 22 (SSH), 8291 (Winbox/Mikrotik), 23 (Telnet)
            ports_to_try = [80, 443, 22, 8291, 23]
            
            for port in ports_to_try:
                try:
                    start = time.time()
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.connect((target_ip, port))
                        latency = round((time.time() - start) * 1000, 1)
                        is_online = True
                        break # Se conectou em qualquer porta, está online
                except:
                    continue
            
            # Se ainda não estiver online, faz mais 2 tentativas na porta 80 por garantia
            if not is_online:
                for _ in range(2):
                    try:
                        start = time.time()
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.connect((target_ip, 80))
                            latency = round((time.time() - start) * 1000, 1)
                            is_online = True
                            break
                    except:
                        time.sleep(0.1)
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
        body { background-color: #f8fafc; font-family: 'Inter', sans-serif; color: #1e293b; padding-top: 1rem; }
        .card { border: 1px solid #e2e8f0; border-radius: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); background: white; margin-bottom: 1.5rem; }
        .card-header { background: white; border-bottom: 1px solid #f1f5f9; padding: 1rem 1.5rem; display: flex; justify-content: space-between; align-items: center; }
        .card-header h5 { margin: 0; font-weight: 700; font-size: 1rem; display: flex; align-items: center; }
        .card-header h5 i { color: #0ea5e9; margin-right: 10px; }
        
        /* Header Branding */
        .branding { display: flex; align-items: center; margin-bottom: 1.5rem; padding: 0 0.5rem; }
        .branding-logo { background: #0ea5e9; color: white; padding: 8px; border-radius: 10px; margin-right: 12px; display: flex; align-items: center; justify-content: center; }
        .branding-text h1 { font-size: 1.25rem; font-weight: 800; margin: 0; line-height: 1; letter-spacing: -0.02em; }
        .branding-text h1 span { color: #0ea5e9; }
        .branding-text p { font-size: 0.65rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.1em; margin: 0; }

        .table { margin-bottom: 0; }
        .table th { background: #f8fafc; color: #64748b; font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; padding: 0.75rem 1rem; border-top: none; }
        .table td { padding: 0.75rem 1rem; vertical-align: middle; border-bottom: 1px solid #f1f5f9; }
        
        code { background: #f1f5f9; color: #0369a1; padding: 3px 6px; border-radius: 5px; font-weight: 500; font-size: 0.8rem; }
        .status-text { font-weight: 700; font-size: 0.7rem; text-transform: uppercase; }
        .status-online { color: #22c55e; }
        .status-offline { color: #ef4444; }
        .status-dot { height: 8px; width: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; }
        .dot-online { background: #22c55e; box-shadow: 0 0 6px rgba(34, 197, 94, 0.4); }
        .dot-offline { background: #ef4444; box-shadow: 0 0 6px rgba(239, 68, 68, 0.4); }
        
        .chart-container { width: 100px; height: 25px; }
        
        .btn-action { background: none; border: none; color: #0ea5e9; font-weight: 600; font-size: 0.8rem; padding: 4px; display: inline-flex; align-items: center; }
        .btn-action:hover { color: #0284c7; }
        .btn-delete { color: #fca5a5; }
        .btn-delete:hover { color: #ef4444; }
        
        .add-section { padding: 1.5rem; border-top: 1px solid #f1f5f9; }
        .add-title { color: #22c55e; font-weight: 600; font-size: 0.85rem; margin-bottom: 1rem; display: flex; align-items: center; }
        .add-title i { margin-right: 8px; }
        
        .form-control { border-radius: 8px; border: 1px solid #e2e8f0; padding: 0.6rem 1rem; font-size: 0.9rem; }
        .form-control:focus { box-shadow: 0 0 0 3px rgba(14, 165, 233, 0.1); border-color: #0ea5e9; }
        .btn-include { background: #0ea5e9; color: white; border: none; border-radius: 8px; font-weight: 700; padding: 0.6rem 2rem; width: 100%; transition: all 0.2s; }
        .btn-include:hover { background: #0284c7; transform: translateY(-1px); }
        
        .history-header { padding: 1rem 1.5rem; display: flex; align-items: center; font-weight: 700; font-size: 1rem; border-bottom: 1px solid #f1f5f9; }
        .history-header i { color: #f97316; margin-right: 12px; }
        .history-content { padding: 1rem 1.5rem; color: #94a3b8; font-size: 0.8rem; font-style: italic; }
        
        .log-item { padding: 8px 0; border-bottom: 1px solid #f1f5f9; color: #475569; font-style: normal; display: flex; flex-direction: column; }
        .log-time { color: #94a3b8; font-weight: 600; font-size: 0.7rem; margin-bottom: 2px; }
        .log-text { font-size: 0.8rem; }

        /* Mobile Specific */
        @media (max-width: 768px) {
            .table-desktop { display: none; }
            .mobile-cards { display: block; }
            .branding { justify-content: center; text-align: center; flex-direction: column; }
            .branding-logo { margin-right: 0; margin-bottom: 8px; }
        }
        @media (min-width: 769px) {
            .table-desktop { display: table; }
            .mobile-cards { display: none; }
            .log-item { flex-direction: row; justify-content: space-between; }
            .log-time { margin-bottom: 0; margin-right: 12px; }
        }

        .mobile-card { padding: 1rem 1.5rem; border-bottom: 1px solid #f1f5f9; }
        .mobile-card:last-child { border-bottom: none; }
        .mobile-card-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
        .mobile-card-info h6 { margin: 0; font-size: 0.9rem; font-weight: 700; }
        .mobile-card-info p { margin: 0; font-size: 0.75rem; color: #64748b; }
        .mobile-card-status { display: flex; align-items: center; justify-content: space-between; }
    </style>
</head>
<body>

<div class="container">
    <!-- Branding Header -->
    <div class="branding">
        <div class="branding-logo">
            <i class="bi bi-activity fs-4"></i>
        </div>
        <div class="branding-text">
            <h1>MONITOR <span>PRODED</span></h1>
            <p>Network Intelligence</p>
        </div>
    </div>

    <!-- Monitoramento de Hosts Card -->
    <div class="card">
        <div class="card-header">
            <h5><i class="bi bi-activity"></i> Monitoramento de Hosts</h5>
            <button class="btn btn-link p-0 text-muted" onclick="checkAll()"><i class="bi bi-arrow-clockwise fs-5"></i></button>
        </div>
        
        <!-- Desktop Table -->
        <div class="table-responsive table-desktop">
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
                <tbody id="host-list-desktop">
                    <!-- JS -->
                </tbody>
            </table>
        </div>

        <!-- Mobile Cards -->
        <div id="host-list-mobile" class="mobile-cards">
            <!-- JS -->
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
        const desktopList = document.getElementById('host-list-desktop');
        const mobileList = document.getElementById('host-list-mobile');
        
        // Render Desktop
        desktopList.innerHTML = hosts.map(h => {
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
                            <canvas id="chart-desktop-${h.id}"></canvas>
                        </div>
                    </td>
                    <td>
                        <button class="btn-action" onclick="runTrace('${h.ip}')"><i class="bi bi-signpost-split me-1"></i> Trace</button>
                        <button class="btn-action btn-delete" onclick="removeHost('${h.id}')"><i class="bi bi-trash"></i></button>
                    </td>
                </tr>
            `;
        }).join('');

        // Render Mobile
        mobileList.innerHTML = hosts.map(h => {
            const lastLatency = h.history && h.history.length > 0 ? h.history[h.history.length - 1] : null;
            const isOnline = h.status === 'online';
            return `
                <div class="mobile-card">
                    <div class="mobile-card-header">
                        <div class="mobile-card-info">
                            <h6><code>${h.ip}</code></h6>
                            <p>${h.label}</p>
                        </div>
                        <div class="btn-group">
                            <button class="btn-action" onclick="runTrace('${h.ip}')"><i class="bi bi-signpost-split"></i></button>
                            <button class="btn-action btn-delete" onclick="removeHost('${h.id}')"><i class="bi bi-trash"></i></button>
                        </div>
                    </div>
                    <div class="mobile-card-status">
                        <div class="d-flex align-items-center">
                            <span class="status-dot ${isOnline ? 'dot-online' : 'dot-offline'}"></span>
                            <span class="status-text ${isOnline ? 'status-online' : 'status-offline'}">
                                ${isOnline ? `ONLINE (${lastLatency}MS)` : 'OFFLINE'}
                            </span>
                        </div>
                        <div class="chart-container">
                            <canvas id="chart-mobile-${h.id}"></canvas>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        renderLogs();
        hosts.forEach(h => {
            initChart(h, 'desktop');
            initChart(h, 'mobile');
        });
    }

    function renderLogs() {
        const container = document.getElementById('loss-history');
        if (logs.length === 0) {
            container.innerHTML = 'Nenhuma perda de ping registrada recentemente.';
            return;
        }
        container.innerHTML = logs.map(l => `
            <div class="log-item">
                <div class="log-time">${l.time}</div>
                <div class="log-text">Host <strong>${l.label}</strong> (${l.ip}) ficou offline.</div>
            </div>
        `).join('');
    }

    function initChart(host, type) {
        const ctx = document.getElementById(`chart-${type}-${host.id}`);
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
                animation: false,
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
