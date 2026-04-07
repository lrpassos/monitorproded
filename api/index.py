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
    """Realiza 5 tentativas para cada IP."""
    data = request.json
    hosts = data.get('hosts', [])
    results = []
    
    for host in hosts:
        ip = host.get('ip')
        online_count = 0
        # 5 tentativas (simulando pings)
        for _ in range(5):
            if check_tcp_status(ip):
                online_count += 1
                break # Se um funcionar, já está online
        
        results.append({
            "id": host.get('id'),
            "ip": ip,
            "status": "online" if online_count > 0 else "offline",
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
    <title>IP Monitor - Vercel</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    <style>
        body { background-color: #f4f7f6; font-family: 'Segoe UI', sans-serif; }
        .card { border: none; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
        .status-dot { height: 12px; width: 12px; border-radius: 50%; display: inline-block; margin-right: 8px; }
        .online { background-color: #28a745; box-shadow: 0 0 8px #28a745; }
        .offline { background-color: #dc3545; box-shadow: 0 0 8px #dc3545; }
        .navbar { background-color: #fff; border-bottom: 2px solid #eee; }
        .btn-primary { background-color: #0d6efd; border: none; border-radius: 8px; }
        .table th { border-top: none; color: #6c757d; font-size: 0.85rem; text-transform: uppercase; }
        .font-mono { font-family: 'Courier New', Courier, monospace; }
    </style>
</head>
<body>

<nav class="navbar py-3 mb-4">
    <div class="container">
        <span class="navbar-brand fw-bold text-dark"><i class="bi bi-shield-check text-primary me-2"></i>IP Monitor PRO</span>
        <div class="text-muted small d-none d-md-block">Monitoramento Automático (5 min)</div>
    </div>
</nav>

<div class="container">
    <div class="row justify-content-center">
        <div class="col-lg-10">
            
            <!-- Adicionar IP -->
            <div class="card p-4 mb-4">
                <div class="row g-3 align-items-end">
                    <div class="col-md-8">
                        <label class="form-label small fw-bold">Novo Endereço IP</label>
                        <input type="text" id="new-ip" class="form-control" placeholder="Ex: 1.1.1.1 ou google.com">
                    </div>
                    <div class="col-md-4">
                        <button onclick="addHost()" class="btn btn-primary w-100 py-2 fw-bold">Adicionar à Lista</button>
                    </div>
                </div>
            </div>

            <!-- Tabela de Status -->
            <div class="card overflow-hidden">
                <div class="table-responsive">
                    <table class="table table-hover mb-0 align-middle">
                        <thead class="bg-light">
                            <tr>
                                <th class="px-4 py-3">Endereço IP</th>
                                <th class="py-3">Status</th>
                                <th class="py-3">Última Verificação</th>
                                <th class="px-4 py-3 text-end">Ações</th>
                            </tr>
                        </thead>
                        <tbody id="host-list">
                            <!-- JS -->
                        </tbody>
                    </table>
                </div>
                <div id="empty-msg" class="p-5 text-center d-none">
                    <p class="text-muted mb-0">Nenhum IP cadastrado para monitoramento.</p>
                </div>
            </div>

            <!-- Traceroute Simples -->
            <div class="card p-4 mt-4">
                <h6 class="fw-bold mb-3"><i class="bi bi-signpost-split me-2"></i>Ferramenta Traceroute</h6>
                <div class="input-group">
                    <input type="text" id="trace-ip" class="form-control" placeholder="IP para rastrear">
                    <button onclick="runTrace()" class="btn btn-dark">Executar Trace</button>
                </div>
                <div id="trace-result" class="mt-3 d-none">
                    <pre class="bg-dark text-light p-3 rounded small font-mono mb-0" id="trace-output"></pre>
                </div>
            </div>

        </div>
    </div>
</div>

<script>
    let hosts = JSON.parse(localStorage.getItem('monitor_ips')) || [];

    function save() {
        localStorage.setItem('monitor_ips', JSON.stringify(hosts));
    }

    function render() {
        const list = document.getElementById('host-list');
        const empty = document.getElementById('empty-msg');
        
        if (hosts.length === 0) {
            list.innerHTML = '';
            empty.classList.remove('d-none');
            return;
        }
        
        empty.classList.add('d-none');
        list.innerHTML = hosts.map(h => `
            <tr>
                <td class="px-4 fw-bold font-mono">${h.ip}</td>
                <td>
                    <span class="status-dot ${h.status === 'online' ? 'online' : (h.status === 'offline' ? 'offline' : 'bg-secondary')}"></span>
                    <span class="small fw-bold text-uppercase">${h.status || 'Pendente'}</span>
                </td>
                <td class="text-muted small">${h.last_check || '--:--:--'}</td>
                <td class="px-4 text-end">
                    <button onclick="removeHost('${h.id}')" class="btn btn-sm btn-outline-danger border-0">
                        <i class="bi bi-trash3"></i>
                    </button>
                </td>
            </tr>
        `).join('');
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
            
            hosts = hosts.map(h => {
                const r = results.find(item => item.id === h.id);
                return r ? { ...h, status: r.status, last_check: r.last_check } : h;
            });
            
            save();
            render();
        } catch (e) { console.error(e); }
    }

    function addHost() {
        const ip = document.getElementById('new-ip').value.trim();
        if (!ip) return;
        
        hosts.push({
            id: Date.now().toString(),
            ip: ip,
            status: null,
            last_check: null
        });
        
        document.getElementById('new-ip').value = '';
        save();
        render();
        checkAll();
    }

    function removeHost(id) {
        hosts = hosts.filter(h => h.id !== id);
        save();
        render();
    }

    async function runTrace() {
        const ip = document.getElementById('trace-ip').value.trim();
        if (!ip) return;
        
        const output = document.getElementById('trace-output');
        const resultDiv = document.getElementById('trace-result');
        
        resultDiv.classList.remove('d-none');
        output.innerText = 'Processando traceroute...';
        
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

    // Inicialização
    render();
    checkAll();

    // Intervalo de 5 minutos (300.000 ms)
    setInterval(checkAll, 300000);
</script>

</body>
</html>
'''
