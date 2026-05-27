# 🚀 MONITOR PRODED

Sistema inteligente de monitoramento de IPs desenvolvido em Python para acompanhamento de disponibilidade de ativos de rede em tempo real.

![Python](https://img.shields.io/badge/Python-3.x-blue?style=for-the-badge\&logo=python)
![SQLite](https://img.shields.io/badge/Database-SQLite-green?style=for-the-badge\&logo=sqlite)
![Status](https://img.shields.io/badge/Status-Em%20Desenvolvimento-orange?style=for-the-badge)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey?style=for-the-badge)

---

# 📌 Sobre o Projeto

O **MONITOR PRODED** foi criado para realizar monitoramento contínuo de dispositivos e serviços através de ping automático, permitindo identificar falhas de conexão rapidamente.

O sistema possui interface amigável, armazenamento local via SQLite, alertas visuais e possibilidade de integração com notificações externas.

---

# ✨ Funcionalidades

✅ Cadastro de IPs
✅ Monitoramento automático via Ping
✅ Status online/offline em tempo real
✅ Histórico de monitoramento
✅ Alertas visuais
✅ Registro de logs
✅ Pesquisa por IP ou descrição
✅ Interface moderna
✅ Banco de dados SQLite
✅ Compartilhamento de relatórios
✅ Compatível com desktop

---

# 🖥️ Interface do Sistema

## Tela Principal
<img width="698" height="489" alt="image" src="https://github.com/user-attachments/assets/daaa4dde-0e29-4e09-ac09-14e2e7240a69" />

<img width="100%" src="https://via.placeholder.com/1200x600.png?text=MONITOR+PRODED" />

---

# ⚙️ Tecnologias Utilizadas

| Tecnologia   | Descrição             |
| ------------ | --------------------- |
| Python       | Linguagem principal   |
| SQLite       | Banco de dados local  |
| Kivy         | Interface gráfica     |
| Ping         | Monitoramento de rede |
| Telegram API | Alertas externos      |
| SMTP         | Envio de e-mails      |

---

# 📂 Estrutura do Projeto

```bash
monitorproded/
│
├── database/
├── logs/
├── assets/
├── src/
├── main.py
├── requirements.txt
└── README.md
```

# 🚀 Instalação

## 1️⃣ Clonar o repositório

```bash
git clone https://github.com/lrpassos/monitorproded.git
```

## 2️⃣ Acessar pasta

```bash
cd monitorproded
```

## 3️⃣ Instalar dependências

```bash
pip install -r requirements.txt
```

## 4️⃣ Executar sistema

```bash
python main.py
```

---

# 🔍 Funcionamento

O sistema executa verificações periódicas utilizando ping nos IPs cadastrados.

Caso algum dispositivo fique indisponível:

* O status muda automaticamente
* O evento é registrado em log
* Um alerta pode ser enviado
* O histórico fica salvo no banco

---

# 📊 Histórico e Compartilhamento

O sistema possui:

* Histórico dos últimos 30 dias
* Compartilhamento via:

  * WhatsApp
  * Telegram
  * E-mail

Os registros antigos permanecem preservados mesmo após atualizações da aplicação.

---

# 🔐 Segurança

* Dados armazenados localmente
* Controle de integridade dos registros
* Preservação automática do histórico
* Estrutura preparada para futuras melhorias

---

# 🛣️ Roadmap

* [ ] Dashboard Web
* [ ] Integração com API
* [ ] Relatórios em PDF
* [ ] Tema Dark Mode
* [ ] Exportação Excel
* [ ] Monitoramento SNMP
* [ ] Docker Support

---

# 🤝 Contribuição

Contribuições são bem-vindas.

1. Faça um Fork
2. Crie uma Branch
3. Commit suas alterações
4. Abra um Pull Request

---

# 📄 Licença

Este projeto está sob licença MIT.

---

# 👨‍💻 Autor

Desenvolvido por **Rogério Passos**

🔗 GitHub:
https://github.com/lrpassos

---

# ⭐ Apoie o Projeto

Se este projeto foi útil para você:

⭐ Deixe uma estrela no repositório
🍴 Faça um fork
📢 Compartilhe com outras pessoas


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
