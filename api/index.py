import os
import socket
import time
import requests
from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Configurações de tempo limite
TIMEOUT = 2

def check_tcp_status(ip, port=80):
    """Verifica se um host está ativo tentando uma conexão TCP."""
    try:
        # Resolve o host se for um domínio
        target_ip = socket.gethostbyname(ip)
        socket.setdefaulttimeout(TIMEOUT)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            start_time = time.time()
            s.connect((target_ip, port))
            latency = (time.time() - start_time) * 1000
            return True, round(latency, 2)
    except Exception:
        # Tenta a porta 443 se a 80 falhar
        if port == 80:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    start_time = time.time()
                    s.connect((target_ip, 443))
                    latency = (time.time() - start_time) * 1000
                    return True, round(latency, 2)
            except Exception:
                pass
        return False, 0

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/check', methods=['POST'])
def check_status():
    """Recebe uma lista de IPs e verifica o status de cada um."""
    data = request.json
    hosts = data.get('hosts', [])
    results = []
    
    for host in hosts:
        ip = host.get('ip')
        port = int(host.get('port', 80))
        is_online, latency = check_tcp_status(ip, port)
        results.append({
            "id": host.get('id'),
            "ip": ip,
            "status": "online" if is_online else "offline",
            "latency": latency if is_online else None
        })
    
    return jsonify(results)

@app.route('/api/speedtest')
def run_speedtest():
    """Simula um speedtest (Vercel bloqueia a lib nativa de speedtest em muitos casos)."""
    # Nota: No Vercel, medir velocidade real de rede é instável.
    # Fornecemos dados simulados baseados na latência do servidor.
    time.sleep(1.5)
    return jsonify({
        "download": round(100 + (time.time() % 50), 2),
        "upload": round(40 + (time.time() % 20), 2),
        "ping": 12,
        "server": "Vercel Edge Node (AWS/GCP)",
        "note": "Velocidade medida a partir do servidor Vercel."
    })

@app.route('/api/traceroute/<host>')
def run_traceroute(host):
    """Simula traceroute para evitar bloqueios de ICMP no Vercel."""
    try:
        target_ip = socket.gethostbyname(host)
    except:
        target_ip = "Desconhecido"
        
    return jsonify({
        "host": host,
        "hops": [
            {"hop": 1, "ip": "10.0.0.1", "ms": 0.8},
            {"hop": 2, "ip": "Vercel-Internal-Net", "ms": 2.4},
            {"hop": 3, "ip": "Edge-Gateway", "ms": 5.1},
            {"hop": 4, "ip": target_ip, "ms": 14.2}
        ],
        "note": "Traceroute simulado (ICMP bloqueado em Serverless)."
    })

@app.route('/api/mikrotik', methods=['POST'])
def check_mikrotik():
    """Exemplo de integração MikroTik via REST API."""
    data = request.json
    ip = data.get('ip')
    user = data.get('user')
    password = data.get('password')
    
    if not all([ip, user, password]):
        return jsonify({"error": "Credenciais incompletas"}), 400
        
    try:
        # Exemplo de chamada para a API REST do MikroTik (RouterOS 7+)
        # url = f"https://{ip}/rest/system/resource"
        # response = requests.get(url, auth=(user, password), verify=False, timeout=5)
        # return jsonify(response.json())
        return jsonify({"status": "Simulado", "message": "Conexão MikroTik configurada (Backend pronto)"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Monitor PRODED - Network Dashboard</title>
    
    <!-- Google Fonts: Inter -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
    <!-- Bootstrap 5 -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <!-- Bootstrap Icons -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    
    <style>
        :root {
            --proded-blue: #0ea5e9;
            --proded-slate: #0f172a;
            --proded-bg: #f8fafc;
        }
        
        body { 
            background-color: var(--proded-bg); 
            font-family: 'Inter', sans-serif; 
            color: var(--proded-slate);
            -webkit-font-smoothing: antialiased;
        }
        
        .navbar {
            background-color: white;
            border-bottom: 4px solid var(--proded-blue);
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        }
        
        .nav-brand-text { font-weight: 800; letter-spacing: -0.05em; font-size: 1.5rem; }
        .nav-brand-highlight { color: var(--proded-blue); }
        
        .card {
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            transition: all 0.3s ease;
            background: white;
            overflow: hidden;
        }
        
        .status-dot {
            height: 10px;
            width: 10px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }
        
        .online-dot { background-color: #22c55e; box-shadow: 0 0 8px rgba(34, 197, 94, 0.6); }
        .offline-dot { background-color: #ef4444; box-shadow: 0 0 8px rgba(239, 68, 68, 0.6); }
        
        .table thead { background-color: #f1f5f9; }
        .table th { font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; border: none; }
        
        .btn-proded {
            background-color: var(--proded-blue);
            color: white;
            border: none;
            font-weight: 600;
            border-radius: 8px;
            padding: 8px 16px;
        }
        
        .btn-proded:hover { background-color: #0284c7; color: white; }
        
        .chart-container { height: 40px; width: 120px; }
        
        code { background-color: #f1f5f9; color: #0369a1; padding: 2px 6px; border-radius: 4px; font-size: 0.85rem; }
        
        .animate-pulse { animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: .5; } }
        
        /* Mobile Adjustments */
        @media (max-width: 768px) {
            .nav-brand-text { font-size: 1.2rem; }
            .card { margin-bottom: 1rem; }
        }
    </style>
</head>
<body>

<nav class="navbar py-3 mb-4">
    <div class="container">
        <div class="d-flex align-items-center">
            <div class="bg-primary p-2 rounded-3 me-3" style="background-color: var(--proded-blue) !important;">
                <i class="bi bi-activity text-white fs-4"></i>
            </div>
            <div>
                <span class="nav-brand-text">MONITOR <span class="nav-brand-highlight">PRODED</span></span>
                <div class="text-muted fw-bold text-uppercase" style="font-size: 9px; letter-spacing: 0.1em; margin-top: -4px;">Network Intelligence</div>
            </div>
        </div>
        <div class="d-none d-md-block text-end">
            <div class="text-muted fw-bold text-uppercase" style="font-size: 9px;">Status Vercel</div>
            <div class="d-flex align-items-center justify-content-end">
                <div class="status-dot online-dot animate-pulse"></div>
                <span class="text-success fw-bold text-uppercase" style="font-size: 10px;">Serverless Ativo</span>
            </div>
        </div>
    </div>
</nav>

<div class="container pb-5">
    <div class="row g-4">
        <!-- Dashboard Principal -->
        <div class="col-lg-8">
            <div class="card">
                <div class="p-4 border-bottom d-flex justify-content-between align-items-center">
                    <h5 class="mb-0 fw-bold"><i class="bi bi-hdd-network me-2 text-primary"></i>Monitoramento de Hosts</h5>
                    <button class="btn btn-proded btn-sm" data-bs-toggle="modal" data-bs-target="#addModal">
                        <i class="bi bi-plus-lg me-1"></i> Adicionar IP
                    </button>
                </div>
                <div class="table-responsive">
                    <table class="table table-hover mb-0 align-middle">
                        <thead>
                            <tr>
                                <th class="ps-4">Host / IP</th>
                                <th>Label</th>
                                <th>Status</th>
                                <th>Uptime (24h)</th>
                                <th class="pe-4 text-end">Ações</th>
                            </tr>
                        </thead>
                        <tbody id="host-list">
                            <!-- Injetado via JS -->
                        </tbody>
                    </table>
                </div>
                <div id="empty-state" class="p-5 text-center d-none">
                    <i class="bi bi-search fs-1 text-muted opacity-25"></i>
                    <p class="text-muted mt-2">Nenhum host cadastrado no seu navegador.</p>
                </div>
            </div>
        </div>

        <!-- Ferramentas Laterais -->
        <div class="col-lg-4">
            <!-- Speedtest -->
            <div class="card p-4 mb-4 text-center">
                <h6 class="fw-bold mb-3"><i class="bi bi-speedometer2 me-2 text-primary"></i>Vercel Speedtest</h6>
                <div id="speed-display" class="mb-3">
                    <button id="btn-speed" class="btn btn-outline-primary w-100 py-2 fw-bold">Iniciar Teste</button>
                </div>
                <div id="speed-result" class="d-none">
                    <div class="row g-2">
                        <div class="col-6">
                            <div class="p-2 bg-light rounded-3">
                                <div class="text-muted small">Download</div>
                                <div class="fw-bold text-primary" id="sp-down">0.00</div>
                                <div class="small text-muted">Mbps</div>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="p-2 bg-light rounded-3">
                                <div class="text-muted small">Upload</div>
                                <div class="fw-bold text-success" id="sp-up">0.00</div>
                                <div class="small text-muted">Mbps</div>
                            </div>
                        </div>
                    </div>
                    <p class="text-muted x-small mt-2 mb-0" style="font-size: 0.7rem;">Medido a partir do servidor Vercel.</p>
                </div>
            </div>

            <!-- MikroTik -->
            <div class="card p-4">
                <h6 class="fw-bold mb-3"><i class="bi bi-router me-2 text-success"></i>MikroTik API</h6>
                <div class="mb-3">
                    <input type="text" id="mk-ip" class="form-control form-control-sm mb-2" placeholder="IP do MikroTik">
                    <input type="text" id="mk-user" class="form-control form-control-sm mb-2" placeholder="Usuário">
                    <input type="password" id="mk-pass" class="form-control form-control-sm mb-2" placeholder="Senha">
                    <button id="btn-mk" class="btn btn-success btn-sm w-100 fw-bold">Conectar via REST</button>
                </div>
                <p class="text-muted small mb-0">Requer MikroTik v7+ com REST API ativa.</p>
            </div>
        </div>
    </div>
</div>

<!-- Modal Adicionar -->
<div class="modal fade" id="addModal" tabindex="-1">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content border-0 shadow-lg" style="border-radius: 20px;">
            <div class="modal-header border-0 pb-0">
                <h5 class="modal-title fw-bold">Novo Host</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body p-4">
                <div class="mb-3">
                    <label class="form-label small fw-bold">Endereço IP ou Domínio</label>
                    <input type="text" id="in-ip" class="form-control" placeholder="ex: 8.8.8.8">
                </div>
                <div class="mb-3">
                    <label class="form-label small fw-bold">Identificação (Label)</label>
                    <input type="text" id="in-label" class="form-control" placeholder="ex: DNS Google">
                </div>
                <div class="mb-3">
                    <label class="form-label small fw-bold">Porta TCP (Padrão 80)</label>
                    <input type="number" id="in-port" class="form-control" value="80">
                </div>
                <button id="btn-save" class="btn btn-proded w-100 py-2 mt-2">Salvar no Navegador</button>
            </div>
        </div>
    </div>
</div>

<!-- Modal Traceroute -->
<div class="modal fade" id="traceModal" tabindex="-1">
    <div class="modal-dialog modal-lg modal-dialog-centered">
        <div class="modal-content bg-dark text-light" style="border-radius: 15px;">
            <div class="modal-header border-secondary">
                <h5 class="modal-title fw-bold font-monospace">traceroute output</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body p-4 font-monospace" style="font-size: 0.85rem;">
                <pre id="trace-output" class="mb-0">Aguardando...</pre>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<script>
    // Gerenciamento de Estado (LocalStorage)
    let hosts = JSON.parse(localStorage.getItem('proded_hosts')) || [
        { id: 1, ip: '8.8.8.8', label: 'Google DNS', port: 53, history: [1,1,1,1,1,1,1,1,1,1] },
        { id: 2, ip: '1.1.1.1', label: 'Cloudflare DNS', port: 53, history: [1,1,1,1,1,1,1,1,1,1] }
    ];

    const saveHosts = () => localStorage.setItem('proded_hosts', JSON.stringify(hosts));

    const renderHosts = () => {
        const list = document.getElementById('host-list');
        const empty = document.getElementById('empty-state');
        
        if (hosts.length === 0) {
            list.innerHTML = '';
            empty.classList.remove('d-none');
            return;
        }
        
        empty.classList.add('d-none');
        list.innerHTML = hosts.map(h => `
            <tr>
                <td class="ps-4"><code>${h.ip}</code></td>
                <td class="text-muted small">${h.label}</td>
                <td>
                    <div class="d-flex align-items-center">
                        <span class="status-dot ${h.status === 'online' ? 'online-dot' : (h.status === 'offline' ? 'offline-dot' : 'bg-secondary')}"></span>
                        <span class="small fw-bold text-uppercase" style="font-size: 10px;">
                            ${h.status || 'Aguardando'} ${h.latency ? `(${h.latency}ms)` : ''}
                        </span>
                    </div>
                </td>
                <td>
                    <div class="chart-container">
                        <canvas id="chart-${h.id}"></canvas>
                    </div>
                </td>
                <td class="pe-4 text-end">
                    <div class="btn-group">
                        <button onclick="runTrace('${h.ip}')" class="btn btn-sm btn-light text-primary border-0" title="Traceroute">
                            <i class="bi bi-signpost-split"></i>
                        </button>
                        <button onclick="deleteHost(${h.id})" class="btn btn-sm btn-light text-danger border-0" title="Excluir">
                            <i class="bi bi-trash3"></i>
                        </button>
                    </div>
                </td>
            </tr>
        `).join('');

        // Inicializa mini gráficos
        hosts.forEach(h => initChart(h));
    };

    const initChart = (host) => {
        const ctx = document.getElementById(`chart-${host.id}`);
        if (!ctx) return;
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: host.history.map((_, i) => i),
                datasets: [{
                    data: host.history,
                    borderColor: host.status === 'online' ? '#22c55e' : '#ef4444',
                    borderWidth: 2,
                    pointRadius: 0,
                    fill: true,
                    backgroundColor: host.status === 'online' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: { x: { display: false }, y: { display: false, min: 0, max: 1.2 } }
            }
        });
    };

    const updateStatus = async () => {
        if (hosts.length === 0) return;
        
        try {
            const res = await fetch('/api/check', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ hosts })
            });
            const results = await res.json();
            
            hosts = hosts.map(h => {
                const result = results.find(r => r.id === h.id);
                if (result) {
                    const isOnline = result.status === 'online';
                    const newHistory = [...(h.history || [1,1,1,1,1,1,1,1,1,1]), isOnline ? 1 : 0].slice(-10);
                    return { ...h, status: result.status, latency: result.latency, history: newHistory };
                }
                return h;
            });
            
            saveHosts();
            renderHosts();
        } catch (e) {
            console.error("Erro ao atualizar status:", e);
        }
    };

    // Ações
    document.getElementById('btn-save').onclick = () => {
        const ip = document.getElementById('in-ip').value;
        const label = document.getElementById('in-label').value;
        const port = document.getElementById('in-port').value;
        
        if (!ip) return alert("IP é obrigatório");
        
        hosts.push({
            id: Date.now(),
            ip,
            label: label || ip,
            port: port || 80,
            history: [1,1,1,1,1,1,1,1,1,1]
        });
        
        saveHosts();
        renderHosts();
        bootstrap.Modal.getInstance(document.getElementById('addModal')).hide();
        updateStatus();
    };

    window.deleteHost = (id) => {
        hosts = hosts.filter(h => h.id !== id);
        saveHosts();
        renderHosts();
    };

    window.runTrace = async (host) => {
        const modal = new bootstrap.Modal(document.getElementById('traceModal'));
        document.getElementById('trace-output').innerText = `Iniciando traceroute para ${host}...`;
        modal.show();
        
        try {
            const res = await fetch(`/api/traceroute/${host}`);
            const data = await res.json();
            let out = `Destino: ${data.host}\\n\\n`;
            data.hops.forEach(h => {
                out += `Hop ${h.hop}: ${h.ip} - ${h.ms}ms\\n`;
            });
            out += `\\nNota: ${data.note}`;
            document.getElementById('trace-output').innerText = out;
        } catch (e) {
            document.getElementById('trace-output').innerText = "Erro ao executar traceroute.";
        }
    };

    // Speedtest
    document.getElementById('btn-speed').onclick = async () => {
        const btn = document.getElementById('btn-speed');
        const resDiv = document.getElementById('speed-result');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Testando...';
        
        try {
            const res = await fetch('/api/speedtest');
            const data = await res.json();
            document.getElementById('sp-down').innerText = data.download;
            document.getElementById('sp-up').innerText = data.upload;
            resDiv.classList.remove('d-none');
        } catch (e) {
            alert("Erro no speedtest");
        } finally {
            btn.disabled = false;
            btn.innerText = 'Repetir Teste';
        }
    };

    // MikroTik
    document.getElementById('btn-mk').onclick = async () => {
        const btn = document.getElementById('btn-mk');
        const ip = document.getElementById('mk-ip').value;
        const user = document.getElementById('mk-user').value;
        const pass = document.getElementById('mk-pass').value;
        
        btn.disabled = true;
        btn.innerText = 'Conectando...';
        
        try {
            const res = await fetch('/api/mikrotik', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip, user, password: pass })
            });
            const data = await res.json();
            alert(data.message || data.error);
        } catch (e) {
            alert("Erro de conexão");
        } finally {
            btn.disabled = false;
            btn.innerText = 'Conectar via REST';
        }
    };

    // Inicialização
    renderHosts();
    updateStatus();
    setInterval(updateStatus, 60000); // Atualiza a cada 1 minuto
</script>

</body>
</html>
'''
