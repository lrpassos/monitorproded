import os
import socket
import time
import json
import threading
from datetime import datetime, timezone, timedelta
from flask import Flask, jsonify, render_template_string, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

TIMEOUT = 1
PERSISTENT_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'proded_state.json')
TMP_STATE_FILE = '/tmp/proded_state.json'

STATE_FILE = PERSISTENT_STATE_FILE
STATE_LOCK = threading.RLock()

DEFAULT_HOSTS = [
    { 'id': '1', 'ip': '8.8.8.8', 'label': 'Google DNS', 'history': [], 'status': 'unknown' },
    { 'id': '2', 'ip': '1.1.1.1', 'label': 'Cloudflare DNS', 'history': [], 'status': 'unknown' }
]

GLOBAL_STATE = {
    "hosts": DEFAULT_HOSTS,
    "logs": []
}

def load_state():
    global GLOBAL_STATE
    with STATE_LOCK:
        # 1. Tenta carregar do arquivo de dados persistente (Base de dados em arquivo JSON no projeto)
        if os.path.exists(PERSISTENT_STATE_FILE):
            try:
                with open(PERSISTENT_STATE_FILE, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and 'hosts' in data and 'logs' in data:
                        GLOBAL_STATE = data
                        return
            except Exception as e:
                print("Erro ao carregar estado persistente:", e)
        
        # 2. Se não existir, tenta migrar do temporário para manter o histórico e IPs sem limpar os registros do usuario!
        if os.path.exists(TMP_STATE_FILE):
            try:
                with open(TMP_STATE_FILE, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and 'hosts' in data and 'logs' in data:
                        GLOBAL_STATE = data
                        # Salva imediatamente no persistente
                        try:
                            with open(PERSISTENT_STATE_FILE, 'w') as out_f:
                                json.dump(GLOBAL_STATE, out_f)
                            print("Estado migrado de temporário para persistente com sucesso!")
                        except Exception as save_err:
                            print("Erro ao gravar estado migrado:", save_err)
                        return
            except Exception as e:
                print("Erro ao tentar ler estado temporário para migração:", e)

        # 3. Se nenhum existir, inicializa com o estado padrão
        GLOBAL_STATE = {
            "hosts": DEFAULT_HOSTS,
            "logs": []
        }

def save_state():
    with STATE_LOCK:
        try:
            with open(STATE_FILE, 'w') as f:
                json.dump(GLOBAL_STATE, f)
        except Exception as e:
            print("Erro ao salvar estado no arquivo:", e)

# Inicializa o estado
load_state()

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/state', methods=['GET'])
def get_state():
    load_state()
    return jsonify(GLOBAL_STATE)

@app.route('/api/hosts/add', methods=['POST'])
def add_host():
    load_state()
    data = request.json or {}
    ip = data.get('ip', '').strip()
    label = data.get('label', '').strip()
    if not ip:
        return jsonify({"error": "IP ou Domínio inválido."}), 400
    
    new_host = {
        "id": str(int(time.time() * 1000)),
        "ip": ip,
        "label": label or ip,
        "status": "unknown",
        "history": []
    }
    GLOBAL_STATE["hosts"].append(new_host)
    save_state()
    return jsonify(GLOBAL_STATE)

@app.route('/api/hosts/delete/<host_id>', methods=['POST', 'DELETE'])
def delete_host(host_id):
    load_state()
    GLOBAL_STATE["hosts"] = [h for h in GLOBAL_STATE["hosts"] if str(h.get('id')) != str(host_id)]
    save_state()
    return jsonify(GLOBAL_STATE)

def check_status_internal():
    """Realiza verificação de latência de todos os hosts e registra logs de queda no backend com thread safety."""
    with STATE_LOCK:
        load_state()
        hosts = GLOBAL_STATE.get('hosts', [])
        logs = GLOBAL_STATE.get('logs', [])
        
        # Horário de Brasília (UTC-3)
        gmt_3 = timezone(timedelta(hours=-3))
        dt_now = datetime.now(gmt_3)
        now_ms = int(dt_now.timestamp() * 1000)
        
        # Limites para logs
        thirty_days_ms = 30 * 24 * 60 * 60 * 1000
        
        for host in hosts:
            ip = host.get('ip')
            was_online = host.get('status') == 'online'
            is_online = False
            latency = 0
            
            try:
                target_ip = socket.gethostbyname(ip)
                socket.setdefaulttimeout(TIMEOUT)
                
                # Portas para tentar conexão TCP
                ports_to_try = [80, 443, 22, 8291, 23]
                for port in ports_to_try:
                    try:
                        start_time = time.time()
                        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                            s.connect((target_ip, port))
                            latency = round((time.time() - start_time) * 1000, 1)
                            is_online = True
                            break
                    except:
                        continue
                
                # Segunda tentativa de contingência na porta 80 por garantia
                if not is_online:
                    for _ in range(2):
                        try:
                            start_time = time.time()
                            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                                s.connect((target_ip, 80))
                                latency = round((time.time() - start_time) * 1000, 1)
                                is_online = True
                                break
                        except:
                            time.sleep(0.1)
            except:
                pass
            
            status = "online" if is_online else "offline"
            host["status"] = status
            
            if "history" not in host or not isinstance(host["history"], list):
                host["history"] = []
                
            if is_online:
                host["history"].append(latency if latency > 0 else 10)
            else:
                host["history"].append(0)
                
            host["history"] = host["history"][-30:] # Guarda últimos 30 pings no gráfico
            
            # Lógica de queda de ping (Muda de online para offline)
            if was_online and not is_online:
                new_log = {
                    "timestamp": now_ms,
                    "time": dt_now.strftime("%d/%m/%Y %H:%M:%S"),
                    "ip": ip,
                    "label": host.get('label', ip),
                    "type": "offline"
                }
                logs.insert(0, new_log)
            # Lógica de latência alta (Online com ping acima de 300ms)
            elif is_online and latency > 300:
                new_log = {
                    "timestamp": now_ms,
                    "time": dt_now.strftime("%d/%m/%Y %H:%M:%S"),
                    "ip": ip,
                    "label": host.get('label', ip),
                    "type": "high_latency",
                    "latency": latency
                }
                logs.insert(0, new_log)
                
        # Remove logs com mais de 30 dias de registro
        logs = [l for l in logs if (now_ms - l.get('timestamp', 0)) <= thirty_days_ms]
        
        GLOBAL_STATE['hosts'] = hosts
        GLOBAL_STATE['logs'] = logs
        save_state()

def background_monitor():
    """Loop continuo que executa o monitoramento a cada 5 minutos em segundo plano."""
    time.sleep(10) # Aguarda inicialização inicial do servidor
    while True:
        try:
            check_status_internal()
        except Exception as e:
            print("Erro no monitoramento automático:", e)
        time.sleep(300) # 5 minutos (300 segundos)

def start_background_thread():
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or os.environ.get("WERKZEUG_RUN_MAIN") is None:
        monitor_thread = threading.Thread(target=background_monitor, daemon=True)
        monitor_thread.start()
        print("Monitoramento em segundo plano ativado com sucesso!")

# Inicializa o monitor automático em segundo plano
start_background_thread()

@app.route('/api/check', methods=['POST', 'GET'])
def check_status():
    """Realiza verificação de latência de todos os hosts e registra logs de queda no backend."""
    check_status_internal()
    return jsonify(GLOBAL_STATE)

@app.route('/api/ping-single/<host>')
def ping_single(host):
    """Realiza um único teste de conexão para o modo 'Ping -t'."""
    is_online = False
    latency = 0
    try:
        target_ip = socket.gethostbyname(host)
        socket.setdefaulttimeout(TIMEOUT)
        
        for port in [80, 443, 22, 8291]:
            try:
                start = time.time()
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((target_ip, port))
                    latency = round((time.time() - start) * 1000, 1)
                    is_online = True
                    break
            except:
                continue
    except:
        pass
        
    gmt_3 = timezone(timedelta(hours=-3))
    time_str = datetime.now(gmt_3).strftime("%H:%M:%S")
    return jsonify({
        "status": "online" if is_online else "offline",
        "latency": latency if is_online else None,
        "time": time_str
    })

@app.route('/api/traceroute/<host>')
def run_traceroute(host):
    """Simula traceroute para o host."""
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
        .branding { display: flex; flex-direction: column; align-items: center; justify-content: center; margin-bottom: 2rem; padding: 1rem 0; text-align: center; }
        .branding-logo { background: #0ea5e9; color: white; padding: 12px; border-radius: 14px; margin-bottom: 12px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(14, 165, 233, 0.2); }
        .branding-text h1 { font-size: 1.5rem; font-weight: 800; margin: 0; line-height: 1.2; letter-spacing: -0.02em; color: #1e293b; }
        .branding-text h1 span { color: #0ea5e9; }
        .branding-text p { font-size: 0.75rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.15em; margin-top: 4px; }

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

        /* Terminal Style for Ping */
        .terminal-output {
            background: #000;
            color: #0f0;
            padding: 1rem;
            border-radius: 8px;
            font-family: 'JetBrains Mono', 'Courier New', monospace;
            font-size: 0.8rem;
            height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
        }
    </style>
</head>
<body>

<div class="container">
    <!-- Branding Header -->
    <div class="branding">
        <div class="branding-logo">
            <i class="bi bi-activity fs-2"></i>
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
            <div class="d-flex align-items-center">
                <button class="btn btn-outline-secondary btn-sm me-2 d-flex align-items-center" onclick="openHistoryModal()" style="font-size: 0.8rem; border-radius: 6px; padding: 4px 8px;">
                    <i class="bi bi-journal-text me-1"></i> Histórico
                </button>
                <button class="btn btn-link p-0 text-muted" onclick="checkAll()"><i class="bi bi-arrow-clockwise fs-5"></i></button>
            </div>
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

    <!-- Histórico de Perda de Ping Card (Até 7 Dias) -->
    <div class="card">
        <div class="history-header">
            <i class="bi bi-clock"></i> Histórico de Perda de Ping (Últimos 7 dias)
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

<!-- Modal Ping -t -->
<div class="modal fade" id="pingModal" tabindex="-1" data-bs-backdrop="static">
    <div class="modal-dialog modal-lg modal-dialog-centered">
        <div class="modal-content bg-dark text-light" style="border-radius: 12px;">
            <div class="modal-header border-secondary">
                <h6 class="modal-title fw-bold font-monospace">ping -t output</h6>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" onclick="stopPing()"></button>
            </div>
            <div class="modal-body p-3">
                <div id="ping-output" class="terminal-output"></div>
            </div>
            <div class="modal-footer border-secondary">
                <button type="button" class="btn btn-outline-light btn-sm" onclick="stopPing()" data-bs-dismiss="modal">Fechar</button>
            </div>
        </div>
    </div>
</div>

<!-- Modal Histórico Completo (30 Dias) -->
<div class="modal fade" id="historyModal" tabindex="-1">
    <div class="modal-dialog modal-lg modal-dialog-centered">
        <div class="modal-content bg-light text-dark" style="border-radius: 12px;">
            <div class="modal-header border-bottom">
                <h6 class="modal-title fw-bold text-dark d-flex align-items-center">
                    <i class="bi bi-clock-history me-2 text-primary fs-5"></i> Histórico Completo de Perdas (Até 30 Dias)
                </h6>
                <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body p-4" style="max-height: 400px; overflow-y: auto;">
                <div id="full-history-content">
                    <!-- JS -->
                </div>
            </div>
            <div class="modal-footer border-top">
                <button type="button" class="btn btn-secondary btn-sm" data-bs-dismiss="modal">Fechar</button>
            </div>
        </div>
    </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    let hosts = [];
    let logs = [];
    let pingInterval = null;

    function maskIp(val) {
        if (!val) return "";
        const parts = val.split('.');
        if (parts.length === 4) {
            const isNumericIp = parts.every(part => /^\d+$/.test(part));
            if (isNumericIp) {
                return `***.***.${parts[2]}.${parts[3]}`;
            }
        }
        return val;
    }

    async function loadStateFromServer() {
        try {
            const res = await fetch('/api/state');
            const data = await res.json();
            hosts = data.hosts || [];
            logs = data.logs || [];
        } catch (e) {
            console.error("Erro ao carregar estado do servidor:", e);
        }
    }

    function render() {
        const desktopList = document.getElementById('host-list-desktop');
        const mobileList = document.getElementById('host-list-mobile');
        
        // Render Desktop
        desktopList.innerHTML = hosts.map(h => {
            const lastLatency = h.history && h.history.length > 0 ? h.history[h.history.length - 1] : null;
            const isOnline = h.status === 'online';
            const isHigh = isOnline && lastLatency && lastLatency > 300;
            
            const dotClass = isOnline ? (isHigh ? 'bg-warning' : 'dot-online') : 'dot-offline';
            const dotStyle = isHigh ? 'box-shadow: 0 0 6px rgba(245, 158, 11, 0.4);' : '';
            const statusClass = isOnline ? (isHigh ? 'text-warning' : 'status-online') : 'status-offline';
            const statusStyle = isHigh ? 'color: #d97706 !important;' : '';
            const statusText = isOnline ? `ONLINE (${lastLatency}MS)${isHigh ? ' - ALTA LATÊNCIA' : ''}` : 'OFFLINE';
            return `
                <tr>
                    <td><code>${maskIp(h.ip)}</code></td>
                    <td class="text-muted small">${maskIp(h.label)}</td>
                    <td>
                        <div class="d-flex align-items-center">
                            <span class="status-dot ${dotClass}" style="${dotStyle}"></span>
                            <span class="status-text ${statusClass}" style="${statusStyle}">
                                ${statusText}
                            </span>
                        </div>
                    </td>
                    <td>
                        <div class="chart-container">
                            <canvas id="chart-desktop-${h.id}"></canvas>
                        </div>
                    </td>
                    <td>
                        <button class="btn-action" onclick="startPing('${h.ip}')"><i class="bi bi-broadcast me-1"></i> Ping</button>
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
            const isHigh = isOnline && lastLatency && lastLatency > 300;
            
            const dotClass = isOnline ? (isHigh ? 'bg-warning' : 'dot-online') : 'dot-offline';
            const dotStyle = isHigh ? 'box-shadow: 0 0 6px rgba(245, 158, 11, 0.4);' : '';
            const statusClass = isOnline ? (isHigh ? 'text-warning' : 'status-online') : 'status-offline';
            const statusStyle = isHigh ? 'color: #d97706 !important;' : '';
            const statusText = isOnline ? `ONLINE (${lastLatency}MS)${isHigh ? ' - ALTA LATÊNCIA' : ''}` : 'OFFLINE';
            return `
                <div class="mobile-card">
                    <div class="mobile-card-header">
                        <div class="mobile-card-info">
                            <h6><code>${maskIp(h.ip)}</code></h6>
                            <p>${maskIp(h.label)}</p>
                        </div>
                        <div class="btn-group">
                            <button class="btn-action" onclick="startPing('${h.ip}')"><i class="bi bi-broadcast"></i></button>
                            <button class="btn-action" onclick="runTrace('${h.ip}')"><i class="bi bi-signpost-split"></i></button>
                            <button class="btn-action btn-delete" onclick="removeHost('${h.id}')"><i class="bi bi-trash"></i></button>
                        </div>
                    </div>
                    <div class="mobile-card-status">
                        <div class="d-flex align-items-center">
                            <span class="status-dot ${dotClass}" style="${dotStyle}"></span>
                            <span class="status-text ${statusClass}" style="${statusStyle}">
                                ${statusText}
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
        const now = Date.now();
        const sevenDaysMs = 7 * 24 * 60 * 60 * 1000;
        
        const filteredLogs = logs.filter(l => {
            return (now - (l.timestamp || now)) <= sevenDaysMs;
        });
        
        if (filteredLogs.length === 0) {
            container.innerHTML = 'Nenhuma perda de ping registrada nos últimos 7 dias.';
            return;
        }
        container.innerHTML = filteredLogs.map(l => {
            let msg = `Host <strong>${maskIp(l.label)}</strong> (${maskIp(l.ip)}) ficou offline.`;
            if (l.type === 'high_latency') {
                msg = `Host <strong>${maskIp(l.label)}</strong> (${maskIp(l.ip)}) registrou latência alta (${l.latency}ms).`;
            }
            return `
                <div class="log-item">
                    <div class="log-time">${l.time}</div>
                    <div class="log-text">${msg}</div>
                </div>
            `;
        }).join('');
    }

    function openHistoryModal() {
        const modal = new bootstrap.Modal(document.getElementById('historyModal'));
        const container = document.getElementById('full-history-content');
        const now = Date.now();
        const thirtyDaysMs = 30 * 24 * 60 * 60 * 1000;
        
        const filteredLogs = logs.filter(l => {
            return (now - (l.timestamp || now)) <= thirtyDaysMs;
        });
        
        if (filteredLogs.length === 0) {
            container.innerHTML = `<div class="text-center py-4 text-muted italic">Nenhum registro de perda de ping nos últimos 30 dias.</div>`;
        } else {
            container.innerHTML = `
                <div class="table-responsive">
                    <table class="table table-hover align-middle">
                        <thead class="table-light">
                            <tr>
                                <th style="font-size: 0.75rem;">Data/Hora</th>
                                <th style="font-size: 0.75rem;">Host / IP</th>
                                <th style="font-size: 0.75rem;">Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${filteredLogs.map(l => {
                                const isHighLatency = l.type === 'high_latency';
                                const badgeClass = isHighLatency ? 'bg-warning-subtle text-warning' : 'bg-danger-subtle text-danger';
                                const badgeStyle = isHighLatency ? 'font-size: 0.7rem; color: #b45309 !important;' : 'font-size: 0.7rem;';
                                const badgeText = isHighLatency ? `LATÊNCIA ALTA (${l.latency}ms)` : 'OFFLINE';
                                return `
                                    <tr>
                                        <td class="font-monospace small text-muted">${l.time}</td>
                                        <td><strong>${maskIp(l.label)}</strong> <code class="small text-secondary">(${maskIp(l.ip)})</code></td>
                                        <td><span class="badge ${badgeClass}" style="${badgeStyle}">${badgeText}</span></td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            `;
        }
        modal.show();
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
        try {
            const res = await fetch('/api/check', {
                method: 'POST'
            });
            const data = await res.json();
            hosts = data.hosts || [];
            logs = data.logs || [];
            render();
        } catch (e) {
            console.error("Erro ao executar checkAll:", e);
        }
    }

    async function addHost() {
        const ip = document.getElementById('new-ip').value.trim();
        const label = document.getElementById('new-label').value.trim();
        if (!ip) return;
        
        try {
            const res = await fetch('/api/hosts/add', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ ip, label })
            });
            const data = await res.json();
            hosts = data.hosts || [];
            logs = data.logs || [];
            render();
            
            document.getElementById('new-ip').value = '';
            document.getElementById('new-label').value = '';
            checkAll();
        } catch (e) {
            console.error("Erro ao adicionar host:", e);
        }
    }

    async function removeHost(id) {
        if (!confirm('Deseja realmente remover este host?')) return;
        try {
            const res = await fetch('/api/hosts/delete/' + id, {
                method: 'POST'
            });
            const data = await res.json();
            hosts = data.hosts || [];
            logs = data.logs || [];
            render();
        } catch (e) {
            console.error("Erro ao remover host:", e);
        }
    }

    async function runTrace(ip) {
        const modal = new bootstrap.Modal(document.getElementById('traceModal'));
        const output = document.getElementById('trace-output');
        const masked = maskIp(ip);
        output.innerText = `Iniciando traceroute para ${masked}...`;
        modal.show();
        
        try {
            const res = await fetch('/api/traceroute/' + ip);
            const data = await res.json();
            let text = `Traceroute para ${masked}:\\n\\n`;
            data.hops.forEach(h => {
                const hopIp = h.ip === ip ? masked : h.ip;
                text += `Hop ${h.hop}: ${hopIp.padEnd(15)} | ${h.ms}ms\\n`;
            });
            output.innerText = text;
        } catch (e) {
            output.innerText = 'Erro ao executar traceroute.';
        }
    }

    function startPing(ip) {
        const modal = new bootstrap.Modal(document.getElementById('pingModal'));
        const output = document.getElementById('ping-output');
        const masked = maskIp(ip);
        output.innerHTML = `Disparando contra ${masked} com 32 bytes de dados:\\n`;
        modal.show();
        
        if (pingInterval) clearInterval(pingInterval);
        
        pingInterval = setInterval(async () => {
            try {
                const res = await fetch('/api/ping-single/' + ip);
                const data = await res.json();
                
                let line = '';
                if (data.status === 'online') {
                    line = `Resposta de ${masked}: bytes=32 tempo=${data.latency}ms TTL=54\\n`;
                } else {
                    line = `Esgotado o tempo de limite do pedido.\\n`;
                }
                
                output.innerHTML += line;
                output.scrollTop = output.scrollHeight;
            } catch (e) {
                output.innerHTML += `Erro na requisição...\\n`;
            }
        }, 1000);
    }

    function stopPing() {
        if (pingInterval) {
            clearInterval(pingInterval);
            pingInterval = null;
        }
    }

    async function bootstrapApp() {
        await loadStateFromServer();
        render();
        // Agenda primeira verificação imediatamente
        checkAll();
        // Repete verificação a cada 5 minutos (300000ms)
        setInterval(checkAll, 300000);
    }

    bootstrapApp();
</script>

</body>
</html>
'''
