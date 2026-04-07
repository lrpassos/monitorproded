import { useState, useEffect, useRef } from 'react';
import React from 'react';
import { Activity, PlusCircle, Signpost, RefreshCw, Trash2, AlertTriangle, Clock } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';

interface PingPoint {
  time: string;
  ms: number;
}

interface MonitorItem {
  id: number;
  ip: string;
  label: string;
  ping?: number | string;
  status: 'online' | 'offline' | 'checking';
  history: PingPoint[];
}

interface LossLog {
  id: string;
  ip: string;
  label: string;
  time: string;
  type: 'loss' | 'latency';
  value?: number;
}

export default function App() {
  const [items, setItems] = useState<MonitorItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [newIp, setNewIp] = useState({ ip: '', label: '' });
  const [traceroute, setTraceroute] = useState<{ host: string; output: string } | null>(null);
  const [lossHistory, setLossHistory] = useState<LossLog[]>([]);
  
  const itemsRef = useRef<MonitorItem[]>([]);

  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/status');
      const data = await res.json();
      
      const now = new Date().toLocaleTimeString();
      
      const updatedItems = data.map((newItem: any) => {
        const existingItem = itemsRef.current.find(i => i.id === newItem.id);
        const pingValue = typeof newItem.ping === 'number' ? newItem.ping : 0;
        
        // Track loss history
        if (newItem.status === 'offline' && (!existingItem || existingItem.status === 'online')) {
          setLossHistory(prev => [
            {
              id: Math.random().toString(36).substr(2, 9),
              ip: newItem.ip,
              label: newItem.label,
              time: new Date().toLocaleString(),
              type: 'loss'
            },
            ...prev
          ].slice(0, 50)); // Keep last 50 logs
        } else if (typeof newItem.ping === 'number' && newItem.ping > 100) {
          setLossHistory(prev => [
            {
              id: Math.random().toString(36).substr(2, 9),
              ip: newItem.ip,
              label: newItem.label,
              time: new Date().toLocaleString(),
              type: 'latency',
              value: newItem.ping as number
            },
            ...prev
          ].slice(0, 50));
        }

        const newHistory = existingItem 
          ? [...existingItem.history, { time: now, ms: pingValue }].slice(-20)
          : [{ time: now, ms: pingValue }];

        return { ...newItem, history: newHistory };
      });

      setItems(updatedItems);
      itemsRef.current = updatedItems;
    } catch (error) {
      console.error('Error fetching status:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 120000); // 2 minutes
    return () => clearInterval(interval);
  }, []);

  const addIp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newIp.ip) return;
    try {
      await fetch('/api/add_ip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newIp),
      });
      setNewIp({ ip: '', label: '' });
      fetchStatus();
    } catch (error) {
      console.error('Error adding IP:', error);
    }
  };

  const runTraceroute = async (host: string) => {
    setTraceroute({ host, output: 'Iniciando traceroute...' });
    try {
      const res = await fetch(`/api/traceroute/${host}`);
      const data = await res.json();
      let out = `Destino: ${data.host}\n\n`;
      data.hops.forEach((h: any) => {
        out += `Hop ${h.hop}: ${h.ip} - ${h.ms}ms\n`;
      });
      out += `\nNota: ${data.note}`;
      setTraceroute({ host, output: out });
    } catch (error) {
      setTraceroute({ host, output: 'Erro ao executar traceroute.' });
    }
  };

  const deleteIp = async (id: number) => {
    // Removed confirm() as it's blocked in iframes
    try {
      const res = await fetch(`/api/delete_ip/${id}`, { method: 'DELETE' });
      if (res.ok) {
        fetchStatus();
      }
    } catch (error) {
      console.error('Error deleting IP:', error);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 font-sans text-slate-900">
      {/* Navbar */}
      <nav className="bg-white text-slate-900 py-3 shadow-md border-b-4 border-sky-500">
        <div className="container mx-auto px-4 flex items-center justify-between">
          <div className="flex items-center">
            <div className="bg-sky-500 p-2 rounded-lg mr-3">
              <Activity className="text-white w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-black tracking-tighter text-slate-800 flex items-center">
                MONITOR <span className="text-sky-500 ml-1">PRODED</span>
              </h1>
              <p className="text-[10px] uppercase tracking-widest text-slate-400 font-bold -mt-1">Network Intelligence</p>
            </div>
          </div>
          <div className="hidden md:block">
            <div className="text-right">
              <p className="text-xs font-bold text-slate-500 uppercase">Status do Sistema</p>
              <div className="flex items-center justify-end">
                <div className="w-2 h-2 bg-green-500 rounded-full mr-2 animate-pulse"></div>
                <span className="text-[10px] font-bold text-green-600 uppercase">Operacional</span>
              </div>
            </div>
          </div>
        </div>
      </nav>

      <div className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 gap-8">
          
          {/* Main Dashboard */}
          <div className="w-full">
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
              <div className="p-6 border-b border-slate-50 flex justify-between items-center">
                <h2 className="text-lg font-semibold flex items-center">
                  <Activity className="w-5 h-5 mr-2 text-sky-500" />
                  Monitoramento de Hosts
                </h2>
                <button 
                  onClick={fetchStatus}
                  className="p-2 hover:bg-slate-100 rounded-full transition-colors"
                  title="Atualizar agora"
                >
                  <RefreshCw className={`w-4 h-4 text-slate-500 ${loading ? 'animate-spin' : ''}`} />
                </button>
              </div>
              
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead className="bg-slate-50 text-slate-500 text-xs uppercase tracking-wider">
                    <tr>
                      <th className="px-6 py-4 font-medium">Host / IP</th>
                      <th className="px-6 py-4 font-medium">Label</th>
                      <th className="px-6 py-4 font-medium">Status / Latência</th>
                      <th className="px-6 py-4 font-medium w-48">Gráfico (ms)</th>
                      <th className="px-6 py-4 font-medium">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {items.map((item) => (
                      <tr key={item.id} className="hover:bg-slate-50 transition-colors">
                        <td className="px-6 py-4">
                          <code className="bg-slate-100 px-2 py-1 rounded text-sm text-sky-700">{item.ip}</code>
                        </td>
                        <td className="px-6 py-4 text-sm text-slate-600">{item.label}</td>
                        <td className="px-6 py-4">
                          <div className="flex items-center">
                            <div className={`w-3 h-3 rounded-full mr-2 ${
                              item.status === 'online' ? 'bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]' : 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.6)]'
                            }`} />
                            <span className={`text-xs font-bold uppercase ${
                              item.status === 'online' ? 'text-green-600' : 'text-red-600'
                            }`}>
                              {item.status} {item.ping && item.status === 'online' ? `(${item.ping}ms)` : ''}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-4 min-w-[200px]">
                          <div className="h-10 w-40">
                            <LineChart width={160} height={40} data={item.history} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
                              <YAxis hide domain={[0, 'auto']} />
                              <Line 
                                type="monotone" 
                                dataKey="ms" 
                                stroke={item.status === 'online' ? "#0ea5e9" : "#ef4444"} 
                                strokeWidth={2} 
                                dot={(props: any) => {
                                  const { cx, cy, payload } = props;
                                  if (payload.ms > 100) {
                                    return <circle key={`dot-${cx}-${cy}`} cx={cx} cy={cy} r={3} fill="#ef4444" stroke="none" />;
                                  }
                                  return <></>;
                                }} 
                                isAnimationActive={false}
                              />
                            </LineChart>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center space-x-4">
                            <button 
                              onClick={() => runTraceroute(item.ip)}
                              className="text-sky-600 hover:text-sky-800 text-sm font-medium flex items-center"
                            >
                              <Signpost className="w-4 h-4 mr-1" />
                              Trace
                            </button>
                            <button 
                              onClick={() => deleteIp(item.id)}
                              className="text-red-400 hover:text-red-600 transition-colors"
                              title="Excluir IP"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Add IP Form */}
              <div className="p-6 bg-slate-50 border-t border-slate-100">
                <h3 className="text-sm font-semibold mb-4 flex items-center">
                  <PlusCircle className="w-4 h-4 mr-2 text-green-500" />
                  Adicionar Novo Host
                </h3>
                <form onSubmit={addIp} className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <input 
                    type="text" 
                    placeholder="IP ou Domínio"
                    className="bg-white border border-slate-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-sky-500 outline-none"
                    value={newIp.ip}
                    onChange={e => setNewIp({...newIp, ip: e.target.value})}
                  />
                  <input 
                    type="text" 
                    placeholder="Nome / Label"
                    className="bg-white border border-slate-200 rounded-lg px-4 py-2 text-sm focus:ring-2 focus:ring-sky-500 outline-none"
                    value={newIp.label}
                    onChange={e => setNewIp({...newIp, label: e.target.value})}
                  />
                  <button type="submit" className="bg-sky-600 text-white rounded-lg px-4 py-2 text-sm font-bold hover:bg-sky-700 transition-colors">
                    Incluir
                  </button>
                </form>
              </div>
            </div>
          </div>

          {/* History Log Section */}
          <div className="w-full">
            <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
              <div className="p-6 border-b border-slate-50 flex items-center">
                <Clock className="w-5 h-5 mr-2 text-orange-500" />
                <h2 className="text-lg font-semibold">Histórico de Perda de Ping</h2>
              </div>
              <div className="p-6">
                {lossHistory.length === 0 ? (
                  <p className="text-sm text-slate-400 italic">Nenhuma perda de ping registrada recentemente.</p>
                ) : (
                  <div className="space-y-3">
                    {lossHistory.map((log) => (
                      <div key={log.id} className={`flex items-center p-3 rounded-xl border ${
                        log.type === 'loss' ? 'bg-red-50 border-red-100' : 'bg-orange-50 border-orange-100'
                      }`}>
                        <AlertTriangle className={`w-4 h-4 mr-3 ${log.type === 'loss' ? 'text-red-500' : 'text-orange-500'}`} />
                        <div className="flex-1">
                          <span className={`text-sm font-bold ${log.type === 'loss' ? 'text-red-700' : 'text-orange-700'}`}>
                            {log.label} ({log.ip})
                          </span>
                          <span className={`text-xs ml-2 ${log.type === 'loss' ? 'text-red-500' : 'text-orange-500'}`}>
                            {log.type === 'loss' ? 'teve perda no ping' : `latência alta: ${log.value}ms`}
                          </span>
                        </div>
                        <div className="text-xs text-slate-500 font-mono">{log.time}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* Traceroute Modal */}
      {traceroute && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 text-green-400 w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden border border-slate-700">
            <div className="p-4 border-b border-slate-800 flex justify-between items-center">
              <h3 className="font-mono text-sm">traceroute {traceroute.host}</h3>
              <button onClick={() => setTraceroute(null)} className="text-slate-400 hover:text-white">✕</button>
            </div>
            <div className="p-6 font-mono text-sm h-64 overflow-y-auto">
              <pre className="whitespace-pre-wrap">{traceroute.output}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
