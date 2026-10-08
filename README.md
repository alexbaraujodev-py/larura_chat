# Falar

Interface local de voz para executar tarefas pelo
[Hermes Agent](https://github.com/NousResearch/hermes-agent).

O projeto oferece:

- interface web local com reconhecimento de voz pelo navegador;
- execução de tarefas no Hermes Agent;
- acompanhamento do progresso no painel de logs;
- resumo falado ao final da tarefa;
- interface visual com olhos animados e bailarinas decorativas;
- interface desktop opcional com captura local, Whisper e TTS.

Para configurar o Hermes em outra máquina, consulte
[CONFIGURACAO-HERMES.md](./CONFIGURACAO-HERMES.md).

## Como funciona

### Interface web

1. Clique em **FALE COMIGO**.
2. O navegador captura a solicitação em português.
3. O texto reconhecido é enviado ao Hermes.
4. O progresso aparece no painel de logs.
5. Ao terminar, a interface fala um resumo curto do processo.

Os logs completos continuam disponíveis visualmente, mas não são lidos
integralmente pela voz.

### Interface desktop

A interface desktop usa:

1. `arecord` para capturar o áudio;
2. `faster-whisper` para transcrever localmente;
3. `hermes -z ... --cli` para executar a tarefa;
4. `pyttsx3` para narrar o andamento.

## Requisitos

- Linux;
- Python 3.10 ou superior;
- [uv](https://docs.astral.sh/uv/);
- Hermes Agent instalado e configurado;
- microfone;
- navegador com suporte a reconhecimento de voz para a interface web.

Para a interface desktop, instale também:

```bash
sudo apt update
sudo apt install python3-tk alsa-utils espeak-ng
```

O Hermes, o provedor, o modelo e as credenciais são configurados
separadamente pelo usuário. O Falar não armazena chaves de API.

## Instalação

Entre na pasta do projeto e sincronize as dependências:

```bash
cd /caminho/para/Falar
uv sync
```

Antes de usar o Falar, confirme que o Hermes funciona diretamente:

```bash
hermes --version
hermes -z "Responda apenas: OK" --cli --no-restore-cwd
```

## Iniciar a interface web

```bash
uv run falar-web
```

Depois abra:

<http://127.0.0.1:8765/>

Permita o acesso ao microfone quando o navegador solicitar. Mantenha o
terminal do serviço aberto enquanto estiver usando a interface.

Para parar o serviço, pressione `Ctrl+C` no terminal em que ele está rodando.

Se aparecer `Address already in use`, já existe uma instância na porta 8765:

```bash
ss -ltnp '( sport = :8765 )'
```

## Iniciar a interface desktop

```bash
uv run falar
```

Na primeira transcrição, o `faster-whisper` pode baixar o modelo local.
Para uma instalação mais leve:

```bash
WHISPER_MODEL=tiny uv run falar
```

## Configuração

As variáveis abaixo são opcionais:

| Variável | Padrão | Função |
|---|---|---|
| `HERMES_COMMAND` | `hermes` | Nome ou caminho do executável Hermes |
| `HERMES_WORKDIR` | diretório atual | Diretório de trabalho enviado ao Hermes |
| `WHISPER_MODEL` | `base` | Modelo local de transcrição |
| `SPEECH_LANGUAGE` | `pt` | Idioma da captura desktop |
| `RECORDINGS_DIR` | `~/.local/share/falar` | Diretório das gravações temporárias |

Exemplo:

```bash
export HERMES_COMMAND="$HOME/.local/bin/hermes"
export HERMES_WORKDIR="$HOME/Documentos/projetos"
export WHISPER_MODEL=base
export SPEECH_LANGUAGE=pt
uv run falar-web
```

Para tornar as variáveis permanentes no Bash, adicione-as ao `~/.bashrc`.
Nunca coloque chaves de API no projeto ou em arquivos versionados.

## Voz e interface visual

A voz web:

- seleciona automaticamente uma voz `pt-BR` disponível;
- usa velocidade `1.08`;
- respeita pausas entre frases;
- fala um resumo ao concluir a tarefa.

O front-end usa:

- [olhos_front.png](./falar/web/olhos_front.png), com animação de piscar;
- três instâncias de [bailarina_novo_teste.gif](./falar/web/bailarina_novo_teste.gif);
- posições aleatórias para as bailarinas;
- entrada e saída suaves;
- proteção contra sobreposição de olhos, botões, status e painel de logs.

## Estrutura principal

```text
falar/
├── app.py              # Interface desktop
├── audio.py            # Captura, transcrição e TTS
├── config.py           # Variáveis de configuração
├── hermes.py           # Execução do Hermes
├── web.py              # Servidor HTTP local
└── web/
    ├── app.js          # Voz e interação da interface web
    ├── index.html      # Estrutura da interface
    ├── styles.css      # Layout e animações
    ├── olhos_front.png
    └── bailarina_novo_teste.gif
```

## Limitações conhecidas

- Uma tarefa é executada por vez.
- O navegador precisa permitir acesso ao microfone.
- O reconhecimento de voz depende do suporte do navegador.
- A voz e a qualidade da transcrição dependem do navegador e do modelo
  local escolhido.
- O Hermes mantém suas próprias limitações de provedor, modelo, autenticação
  e cota.
