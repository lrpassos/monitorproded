# NetMonitor Pro - Vercel Edition

Esta é uma aplicação de monitoramento de rede desenvolvida com Flask e Bootstrap, projetada para ser implantada no Vercel.

## Funcionalidades
- **Dashboard:** Lista de IPs com monitoramento em tempo real.
- **Status Check:** Verifica a disponibilidade via TCP Socket (porta 80/443), já que ICMP é bloqueado no Vercel.
- **Traceroute Web:** Simulação de traceroute para diagnóstico básico.
- **Speedtest:** Teste de velocidade a partir do servidor do Vercel.
- **MikroTik Ready:** Campo para configuração futura de monitoramento via API MikroTik.

## Como Implantar no Vercel
1. Instale a CLI do Vercel: `npm i -g vercel`
2. Execute `vercel` na raiz do projeto.
3. O Vercel detectará automaticamente a configuração em `vercel.json` e instalará as dependências do `requirements.txt`.

## Desenvolvimento Local
1. Instale as dependências: `pip install -r requirements.txt`
2. Execute o app: `python api/index.py`
3. Acesse: `http://localhost:3000`
