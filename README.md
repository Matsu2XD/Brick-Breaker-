# Quebrando Tijolos V 0.1 Beta

Um brick-breaker 2D feito em Python, onde cada tijolo destruído pode liberar uma cápsula que
**reescreve as regras da partida** — para melhor ou para pior.

O jogador não controla só a bandeja: ele negocia com o caos. Na maioria dos jogos do gênero o
modificador é sempre uma recompensa; aqui a recompensa e o risco caem do mesmo tijolo, com a
mesma aparência até o momento da captura. Isso transforma cada rebote numa decisão de
posicionamento, e não só de mira.

---

## O que tem no jogo

**Modificadores que mudam a partida.** Sete cápsulas, quatro boas e três ruins:

| Boa | O que faz |
| --- | --- |
| Multiplicador de Bolas | multiplica as bolas em jogo (2x, 4x, 6x ou 8x), até oito |
| Multiplicador de Pontos | dobra a pontuação e acumula até 8x |
| Bandeja Grande | aumenta a bandeja em 25%, empilhável |
| Armamento | instala um canhão na bandeja com munição limitada |

| Ruim | O que faz |
| --- | --- |
| Inversão dos Comandos | troca esquerda e direita por alguns segundos |
| Bolas Super Rápidas | acelera as bolas em 85% |
| Invasores | inimigos descem tentando acertar a bandeja — e custam uma vida |

**Eventos aleatórios.** A cada 15 a 25 segundos o jogo dispara uma regra global, sempre
anunciada por um letreiro: chuva de cápsulas, frenesi de bolas, tiro livre, rede de segurança,
invasão, apagão e bola louca. O mundo age sozinho em vez de esperar você quebrar tijolos.

**Sequência.** Tijolos destruídos sem perder a bola viram pontos extras (até +80%) e, a cada
oito seguidos, uma cápsula garantida. Toda recompensa do jogo tem uma parte que você pode
conquistar em vez de esperar do sorteio.

**Reta final.** Quando restam cinco tijolos, o jogo anuncia, sobe para três bolas e acelera.
O fim da fase é o clímax, não a parte em que você olha o relógio.

**Interface que explica o que está acontecendo.** Placar flutuante dourado quando algum
multiplicador está ativo, estrela e corações no lugar de texto, chips de efeito com contagem
regressiva, e cápsulas que **dizem o nome do efeito**.

**Tela inicial, placar de líderes e ajustes.** O jogo abre num menu com os recordes ao lado. A
pausa é um menu de verdade, com voltar, recomçar e abandonar. Ajustes de música, volume,
partículas e tremor ficam gravados entre sessões.

**Trilha sonora** em laço, com controle de volume separado dos efeitos.

---

## Como jogar

### Executável

Baixe o arquivo da sua plataforma em **Releases** (ou em *Actions*, se a build estiver
publicada como artefato):

| Plataforma | Arquivo |
| --- | --- |
| Windows | `QuebrandoTijolos.exe` |
| Linux | `QuebrandoTijolos` (`chmod +x` antes de rodar) |

Os ajustes e o placar são gravados numa pasta `save/` **ao lado do executável**. Se a pasta não
for gravável, o jogo usa o diretório de dados do usuário.

### Do código

```bash
pip install -r requirements.txt
python main.py
```

Precisa de Python 3.11 ou superior. O projeto usa `pygame-ce` (o fork mantido do `pygame`).

### Diagnóstico

```bash
QuebrandoTijolos --version      # mostra a versão
QuebrandoTijolos --selftest     # confere sprites, sons e trilha e escreve save/selftest.log
```

Um erro em jogo é gravado em `save/crash.log`.

---

## Controles

| Tecla | Ação |
| --- | --- |
| `A` / `←`  e  `D` / `→` | mover a bandeja |
| `S` / `↓` | modo precisão (movimento fino, para mirar) |
| `W` / `↑` / `Espaço` | lançar a bola · atirar com o canhão · avançar de fase |
| `P` ou `ESC` | pausar (abre o menu de pausa) |
| `R` | reiniciar a partida |
| `M` | ligar/desligar todo o som |

Nos menus, `W`/`S` (ou as setas) navegam, `A`/`D` mexem num valor e `ENTER` confirma.

**A tecla de lançar também atira.** Quando o canhão está ativo e a bola já está em jogo,
lançar não tem mais função, então a mesma tecla faz o trabalho que sobrou.

---

## Como construir os executáveis

```bash
pip install pyinstaller
python build.py
```

Gera um arquivo único por plataforma (com sprites e sons dentro) e em seguida **roda o
autoteste dentro do binário** — que é a única forma de saber que o pacote está completo.

O PyInstaller **não cross-compila**: o binário é sempre da plataforma onde o script roda. O
workflow em `.github/workflows/build.yml` empacota para Windows e Linux automaticamente (ação
manual ou tag `v*`).

---

## Testes

```bash
python run_tests.py
```

Seis suítes, 496 verificações, todas rodando sem janela e sem placa de som — não precisa de
pytest nem de display:

| Suíte | Cobre |
| --- | --- |
| `test_physics` | física da bola e controles |
| `test_layout` | sprites, HUD e enquadramento (pixel a pixel) |
| `test_powerups` | modificadores, debuffs, sorteio e áudio |
| `test_dynamics` | partículas, tremor, sequência, eventos e reta final |
| `test_ui` | telas, ajustes, placar e persistência |
| `test_design_doc` | consistência do documento com o código |

Os testes gravam num diretório temporário, nunca no `save/` de quem está jogando.

---

## Estrutura

```
src/
├── config.py     tabela de constantes e ajustes (sem lógica)
├── controls.py   teclado -> estado de entrada
├── physics.py    física e colisões (não conhece regras de jogo)
├── game.py       loop, estados, pontuação, desenho
├── level.py      construção da grade de tijolos
├── audio.py      efeitos, trilha, canais e mudo
├── events.py     eventos aleatórios
├── sprites.py    atlas do pack de arte, com fallback para primitivas
├── menu.py       navegação dos menus (sem pygame)
├── settings.py   ajustes do jogador, com validação
├── scores.py     placar de líderes
├── store.py      JSON à prova de arquivo ruim
├── modifiers/    catálogo, pilha de efeitos e cápsulas
└── entities/     bola, bandeja, tijolo, projétil, invasor, partícula, placar flutuante
```

Duas fronteiras sustentam o resto: `physics.py` move corpos e relata contatos, mas **não decide
nada sobre o jogo**; e nenhum modificador muta a bandeja ou a bola — eles declaram
multiplicadores, e o jogo consulta. É o que faz um efeito expirar sozinho, sem código de
desfazer.

---

## Documentação

O **[GAME_DESIGN.md](GAME_DESIGN.md)** é o documento completo do projeto: conceito, pilares,
arquitetura, a física da bola em detalhe, catálogo de modificadores com pesos e durações,
balanceamento, verificação e roadmap. Ele é conferido contra o código por uma suíte de testes -
se um número no documento divergir do `config.py`, o teste falha.

---

## Estado

Versão **0.1 Beta**. O jogo está completo e jogável do começo ao fim; o que falta está no
roadmap do documento de design. As próximas adições naturais são inimigos permanentes na grade
e mais modificadores.

Feito com Python e `pygame-ce`. Os sprites vêm do pack livre *Breakout Tile Set*.
