# Configuração do Hermes Agent

Este guia explica como outra pessoa pode instalar o projeto **Falar** e
integrá-lo ao próprio Hermes Agent.

O Falar não possui um provedor de IA próprio. Ele apenas captura a voz,
converte a fala em texto e executa o comando `hermes` instalado na máquina.
Portanto, cada usuário deve configurar o próprio Hermes, incluindo provedor,
modelo e credenciais.

## 1. Requisitos

No Linux, instale os componentes usados pela aplicação:

```bash
sudo apt update
sudo apt install python3-tk alsa-utils espeak-ng
```

Também são necessários:

- Python 3.10 ou superior;
- [uv](https://docs.astral.sh/uv/);
- Hermes Agent instalado;
- um microfone;
- um navegador com suporte a reconhecimento de voz, para a interface web.

## 2. Instalar e autenticar o Hermes

Instale o Hermes Agent seguindo a documentação oficial do projeto:

<https://github.com/NousResearch/hermes-agent>

Depois confirme que o comando está disponível no terminal:

```bash
hermes --version
command -v hermes
```

Execute a configuração/autenticação do Hermes conforme o provedor escolhido.
Por exemplo:

```bash
hermes setup
```

O comando pode variar conforme a versão instalada. Também é possível
selecionar ou trocar o modelo com:

```bash
hermes model
```

Não coloque chaves de API neste projeto, no `README` ou em arquivos
versionados. As credenciais devem permanecer na configuração segura do
Hermes, normalmente dentro de `~/.hermes/`.

Antes de iniciar o Falar, teste o Hermes diretamente:

```bash
hermes -z "Responda apenas: OK" --cli --no-restore-cwd
```

Se esse comando não funcionar, o Falar também não conseguirá executar tarefas.

## 3. Instalar o Falar

Clone ou copie este projeto e entre na pasta:

```bash
cd /caminho/para/Falar
uv sync
```

Na primeira execução, o `faster-whisper` pode baixar o modelo local de
transcrição. Para usar um modelo menor:

```bash
WHISPER_MODEL=tiny uv run falar
```

## 4. Configurar a integração

Por padrão, o Falar procura o executável chamado `hermes` no `PATH` e executa
as tarefas no diretório atual:

```text
HERMES_COMMAND=hermes
HERMES_WORKDIR=diretório atual
```

As variáveis opcionais são:

| Variável | Padrão | Função |
|---|---|---|
| `HERMES_COMMAND` | `hermes` | Nome ou caminho completo do executável Hermes |
| `HERMES_WORKDIR` | diretório atual | Diretório no qual o Hermes executará a tarefa |
| `WHISPER_MODEL` | `base` | Modelo local usado para transcrição |
| `SPEECH_LANGUAGE` | `pt` | Idioma da transcrição desktop |
| `RECORDINGS_DIR` | `~/.local/share/falar` | Diretório temporário das gravações |

Exemplo usando um Hermes instalado em um caminho específico e permitindo que
ele trabalhe em uma pasta de projetos:

```bash
export HERMES_COMMAND="$HOME/.local/bin/hermes"
export HERMES_WORKDIR="$HOME/Documentos/projetos"
export WHISPER_MODEL=base
export SPEECH_LANGUAGE=pt
```

Para tornar essas variáveis permanentes no Bash, adicione-as ao `~/.bashrc`
e abra um novo terminal. Não inclua credenciais nessas linhas.

## 5. Como o Falar chama o Hermes

O Falar executa, para cada solicitação reconhecida:

```bash
hermes -z "texto reconhecido da solicitação" --cli --no-restore-cwd
```

O texto é enviado ao Hermes como uma tarefa normal. A saída do processo é
exibida no painel de logs e, ao final, a interface web fala um resumo curto
do resultado.

## 6. Iniciar a interface web

Execute:

```bash
uv run falar-web
```

Abra no navegador:

<http://127.0.0.1:8765/>

Conceda permissão de acesso ao microfone quando o navegador solicitar.
Mantenha o terminal do serviço aberto enquanto estiver usando a interface.

O endpoint que inicia tarefas é protegido por um token aleatório gerado a cada
execução do serviço. A interface recebe esse token automaticamente; não é
necessário copiar ou configurar nenhum token manualmente. Por segurança, o
endpoint aceita apenas requisições JSON originadas da própria interface local.

Para parar o serviço, pressione `Ctrl+C` no terminal em que ele está rodando.

Se aparecer `Address already in use`, já existe uma instância usando a porta
8765. Verifique com:

```bash
ss -ltnp '( sport = :8765 )'
```

## 7. Teste completo

Faça as verificações nesta ordem:

```bash
hermes -z "Responda apenas: HERMES_OK" --cli --no-restore-cwd
curl http://127.0.0.1:8765/api/status
```

Depois abra a interface, clique em **FALE COMIGO** e diga uma tarefa simples,
como:

> Liste os arquivos da pasta atual e explique resumidamente o que encontrou.

Se o Hermes funcionar no terminal, o navegador tiver acesso ao microfone e o
diretório de trabalho estiver correto, a integração estará pronta.

## Problemas comuns

### `Failed to spawn: falar-web`

Use o entry point pelo `uv` dentro da pasta do projeto:

```bash
uv run falar-web
```

### `Hermes não encontrado`

Confira o caminho:

```bash
command -v hermes
```

Se necessário, defina `HERMES_COMMAND` com o caminho absoluto do executável.

### O Hermes funciona, mas acessa a pasta errada

Defina explicitamente o diretório:

```bash
export HERMES_WORKDIR="$HOME/caminho/do/projeto"
uv run falar-web
```

### O microfone não funciona

- confirme a permissão do navegador;
- teste o microfone no sistema;
- use um navegador compatível com `SpeechRecognition`;
- confira se outro aplicativo não está usando o microfone.

### O modelo ou a cota do Hermes falha

Teste o Hermes diretamente e verifique o provedor/modelo configurado:

```bash
hermes status
hermes model
```

O Falar não substitui limites de cota, autenticação ou disponibilidade do
provedor configurado no Hermes.
