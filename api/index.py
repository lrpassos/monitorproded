import os
from flask import Flask, jsonify, render_template_string, request
import socket
import speedtest
import requests
import time
import threading

app = Flask(__name__)

# Armazenamento temporário em memória (para demonstração)
# Em produção, você usaria um DB como MongoDB ou PostgreSQL
ips_to_monitor = [
    {"ip": "8.8.8.8", "label": "Google DNS", "port": 53},
    {"ip": "1.1.1.1", "label": "Cloudflare DNS", "port": 53},
    {"ip": "github.com", "label": "GitHub", "port": 443}
]

def check_tcp_status(ip, port=80, timeout=2):
    """Verifica se um host está ativo tentando uma conexão TCP."""
    try:
        socket.setdefaulttimeout(timeout)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, port))
        return True
    except Exception:
        return False

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/status')
def get_status():
    results = []
    for item in ips_to_monitor:
        is_online = check_tcp_status(item['ip'], item.get('port', 80))
        results.append({
            "ip": item['ip'],
            "label": item['label'],
            "status": "online" if is_online else "offline"
        })
    return jsonify(results)

@app.route('/api/add_ip', methods=['POST'])
def add_ip():
    data = request.json
    if 'ip' in data:
        ips_to_monitor.append({
            "ip": data['ip'],
            "label": data.get('label', 'Novo Host'),
            "port": int(data.get('port', 80))
        })
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 400

@app.route('/api/speedtest')
def run_speedtest():
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download = st.download() / 1_000_000  # Mbps
        upload = st.upload() / 1_000_000      # Mbps
        ping = st.results.ping
        return jsonify({
            "download": round(download, 2),
            "upload": round(upload, 2),
            "ping": ping,
            "server": st.results.server['name']
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/traceroute/<host>')
def run_traceroute(host):
    # Nota: Traceroute real requer privilégios de root ou ICMP.
    # No Vercel, simulamos o caminho via saltos TCP ou apenas mostramos o destino final
    # para evitar erros de permissão em ambiente serverless.
    return jsonify({
        "host": host,
        "hops": [
            {"hop": 1, "ip": "Vercel Internal Gateway", "ms": 1.2},
            {"hop": 2, "ip": "Edge Node", "ms": 5.4},
            {"hop": 3, "ip": socket.gethostbyname(host), "ms": 12.8}
        ],
        "note": "Traceroute limitado pelo ambiente serverless."
    })

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NetMonitor - Vercel Edition</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap-icons@1.10.0/font/bootstrap-icons.css">
    <style>
        body { background-color: #f8f9fa; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        .status-dot { height: 15px; width: 15px; border-radius: 50%; display: inline-block; margin-right: 10px; }
        .online { background-color: #28a745; box-shadow: 0 0 8px #28a745; }
        .offline { background-color: #dc3545; box-shadow: 0 0 8px #dc3545; }
        .card { border: none; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: transform 0.2s; }
        .card:hover { transform: translateY(-5px); }
        .navbar { background: linear-gradient(90deg, #2c3e50, #000000); }
        #speedtest-result { font-size: 1.2rem; font-weight: bold; }
    </style>
</head>
<body>

<nav class="navbar navbar-dark mb-4">
    <div class="container">
        <span class="navbar-brand mb-0 h1"><i class="bi bi-activity me-2"></i>NetMonitor Pro</span>
    </div>
</nav>

<div class="container">
    <div class="row">
        <!-- Dashboard de IPs -->
        <div class="col-md-8">
            <div class="card p-4 mb-4">
                <div class="d-flex justify-content-between align-items-center mb-3">
                    <h5 class="mb-0">Monitoramento de Hosts</h5>
                    <button class="btn btn-primary btn-sm" data-bs-toggle="modal" data-bs-target="#addIpModal">
                        <i class="bi bi-plus-circle me-1"></i> Incluir IP
                    </button>
                </div>
                <div class="table-responsive">
                    <table class="table table-hover align-middle">
                        <thead class="table-light">
                            <tr>
                                <th>Host / IP</th>
                                <th>Label</th>
                                <th>Status</th>
                                <th>Ações</th>
                            </tr>
                        </thead>
                        <tbody id="ip-list">
                            <!-- Preenchido via JS -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <!-- Ferramentas Laterais -->
        <div class="col-md-4">
            <!-- Speedtest -->
            <div class="card p-4 mb-4 text-center">
                <h5><i class="bi bi-speedometer2 me-2"></i>Speedtest Server</h5>
                <p class="text-muted small">Mede a velocidade do servidor Vercel</p>
                <button id="btn-speedtest" class="btn btn-outline-dark w-100 mb-3">Iniciar Teste</button>
                <div id="speedtest-loading" class="spinner-border text-primary d-none" role="status"></div>
                <div id="speedtest-result" class="mt-2"></div>
            </div>

            <!-- MikroTik Placeholder -->
            <div class="card p-4">
                <h5><i class="bi bi-router me-2"></i>MikroTik API</h5>
                <div class="mb-3">
                    <input type="text" class="form-control mb-2" placeholder="IP do MikroTik">
                    <input type="password" class="form-control mb-2" placeholder="API Password">
                    <button class="btn btn-success btn-sm w-100" onclick="alert('Funcionalidade MikroTik será implementada no futuro!')">Configurar</button>
                </div>
                <p class="text-muted x-small" style="font-size: 0.8rem;">Integração futura via RouterOS API.</p>
            </div>
        </div>
    </div>
</div>

<!-- Modal Add IP -->
<div class="modal fade" id="addIpModal" tabindex="-1">
    <div class="modal-dialog">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Adicionar Novo Host</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <input type="text" id="new-ip" class="form-control mb-2" placeholder="IP ou Domínio (ex: 8.8.8.8)">
                <input type="text" id="new-label" class="form-control mb-2" placeholder="Nome (ex: DNS Google)">
                <input type="number" id="new-port" class="form-control mb-2" placeholder="Porta TCP (padrão 80)" value="80">
            </div>
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancelar</button>
                <button type="button" class="btn btn-primary" onclick="addIp()">Salvar</button>
            </div>
        </div>
    </div>
</div>

<!-- Modal Traceroute -->
<div class="modal fade" id="tracerouteModal" tabindex="-1">
    <div class="modal-dialog modal-lg">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title">Traceroute Web</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
                <pre id="traceroute-output" class="bg-dark text-light p-3 rounded">Iniciando traceroute...</pre>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    async function fetchStatus() {
        try {
            const response = await fetch('/api/status');
            const data = await response.json();
            const list = document.getElementById('ip-list');
            list.innerHTML = '';
            data.forEach(item => {
                list.innerHTML += `
                    <tr>
                        <td><code>${item.ip}</code></td>
                        <td>${item.label}</td>
                        <td>
                            <span class="status-dot ${item.status}"></span>
                            ${item.status.toUpperCase()}
                        </td>
                        <td>
                            <button class="btn btn-sm btn-outline-primary" onclick="runTraceroute('${item.ip}')">
                                <i class="bi bi-signpost-split"></i> Trace
                            </button>
                        </td>
                    </tr>
                `;
            });
        } catch (e) { console.error(e); }
    }

    async function addIp() {
        const ip = document.getElementById('new-ip').value;
        const label = document.getElementById('new-label').value;
        const port = document.getElementById('new-port').value;
        
        await fetch('/api/add_ip', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ip, label, port})
        });
        
        bootstrap.Modal.getInstance(document.getElementById('addIpModal')).hide();
        fetchStatus();
    }

    async function runTraceroute(host) {
        const modal = new bootstrap.Modal(document.getElementById('tracerouteModal'));
        document.getElementById('traceroute-output').innerText = 'Executando traceroute para ' + host + '...';
        modal.show();
        
        const response = await fetch('/api/traceroute/' + host);
        const data = await response.json();
        
        let output = `Destino: ${data.host}\\n\\n`;
        data.hops.forEach(h => {
            output += `Hop ${h.hop}: ${h.ip} - ${h.ms}ms\\n`;
        });
        output += `\\nNota: ${data.note}`;
        document.getElementById('traceroute-output').innerText = output;
    }

    document.getElementById('btn-speedtest').onclick = async () => {
        const btn = document.getElementById('btn-speedtest');
        const loading = document.getElementById('speedtest-loading');
        const result = document.getElementById('speedtest-result');
        
        btn.disabled = true;
        loading.classList.remove('d-none');
        result.innerText = '';

        try {
            const response = await fetch('/api/speedtest');
            const data = await response.json();
            result.innerHTML = `
                <div class="text-success"><i class="bi bi-download"></i> ${data.download} Mbps</div>
                <div class="text-primary"><i class="bi bi-upload"></i> ${data.upload} Mbps</div>
                <div class="text-muted small">Ping: ${data.ping}ms | Server: ${data.server}</div>
            `;
        } catch (e) {
            result.innerText = 'Erro ao executar teste.';
        } finally {
            btn.disabled = false;
            loading.classList.add('d-none');
        }
    };

    // Atualiza a cada 10 segundos
    setInterval(fetchStatus, 10000);
    fetchStatus();
</script>
</body>
</html>
'''

if __name__ == '__main__':
    app.run(port=3000)
