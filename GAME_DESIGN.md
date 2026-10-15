# Quebrando Tijolos V 0.1 Beta — Documento de Design

Documento único de referência do projeto: conceito, arquitetura, física, controles,
sistema de modificadores, balanceamento e roadmap.

Versão: 0.1 (Milestone 1 — física da bola e controles do jogador)

---

## 1. Visão geral

| Item | Definição |
| --- | --- |
| Título | Quebrando Tijolos V 0.1 Beta |
| Gênero | Arcade / brick-breaker 2D com modificadores |
| Plataforma | Desktop (Windows / Linux / macOS) |
| Stack | Python 3.11+ e `pygame-ce` |
| Modo | Um jogador, sessões curtas (3 a 8 minutos por partida) |
| Tela | 960 × 720 px, 60 FPS |
| Distribuição | Executável único por plataforma (§21) |
| Referências | Arkanoid, Breakout, Shatter, Wizorb |

### Pitch

Um brick-breaker clássico onde cada tijolo destruído pode liberar uma cápsula que
**reescreve temporariamente as regras da partida** — para melhor ou para pior. O
jogador não controla apenas a bandeja: ele negocia com o caos, decidindo quando vale
a pena arriscar uma cápsula na base da tela e quando é melhor deixá-la cair.

### Diferencial

Na maioria dos brick-breakers o modificador é sempre uma recompensa. Aqui **a
recompensa e o risco vêm da mesma fonte**: as cápsulas boas e as ruins caem do mesmo
tijolo, com a mesma aparência até o momento da captura. Isso transforma cada rebote
em uma decisão de posicionamento, e não só de mira.

---

## 2. Objetivo e condições de fim

**Objetivo principal:** destruir todos os tijolos da fase com a bola, usando a bandeja
para mantê-la em jogo.

**Como o jogador pontua:** acertar um tijolo dá pontos; destruí-lo dá o bônus de
destruição, multiplicado pela resistência do tijolo.

**Derrota:** perder todas as vidas (3 por padrão). Uma vida é perdida quando a
**última** bola em jogo cruza a linha de morte na base do campo — ou quando um invasor
toca a bandeja (§11.2). Enquanto houver mais de uma bola, perder uma não custa vida, o que
faz o Multiplicador de Bolas valer também como rede de segurança.

**Vitória:** campanha de 10 fases; ao limpar a 10ª o jogador vence. Depois disso é
liberado um modo infinito com velocidade crescente.

---

## 3. Core loop

```
observar a posição da bola  ->  mover a bandeja  ->  rebater  ->  destruir tijolo
        ^                                                              |
        |                                                              v
   modificador muda as regras  <-  capturar cápsula  <-  cápsula pode cair
```

Ciclo de decisão do jogador, em ordem de prioridade:

1. **Sobreviver** — onde a bola vai cair, não onde ela está.
2. **Mirar** — usar o ângulo de saída da bandeja para abrir caminho na grade.
3. **Coletar** — vale a pena abandonar a posição defensiva para pegar a cápsula?
4. **Capitalizar** — durante "Pontos em Dobro", limpar o máximo de tijolos possível.

A fase é dividida em quatro momentos de tensão crescente:

| Momento | Situação | Sensação desejada |
| --- | --- | --- |
| Abertura | Grade cheia, bola presa na bandeja | Controle, planejamento do saque |
| Meio | Túneis abertos, cápsulas caindo | Aceleração, risco calculado |
| Fim | Poucos tijolos, bola com trajetória longa | Paciência e precisão |
| Virada | Modificador ruim ativo | Improviso e resistência |

**Regra de ouro:** a bola nunca pode entrar em um estado onde o jogador não tenha
nada a fazer. É por isso que existem a guarda anti-horizontal e o ângulo de saque
alternado (§7).

---

## 4. Pilares de design

1. **A física é previsível, o conteúdo é caótico.** O jogador nunca deve suspeitar que
   a bola foi injusta; toda a imprevisibilidade vem dos modificadores.
2. **Todo modificador tem um custo.** Até os buffs. "Pontos em Dobro" empurra o
   jogador a se arriscar; "Ímã" tira o hábito de rebater no ritmo.
3. **Debuff é conteúdo, não punição.** Um debuff bem desenhado cria uma mini-fase
   dentro da fase — como sobreviver 8 segundos com os controles invertidos.
4. **Sessões curtas.** Uma partida completa deve caber em 3 a 8 minutos.
5. **Nada de aleatoriedade na física.** Sem `random` na trajetória da bola: o
   lançamento alterna o sinal de inclinação de forma determinística, o que mantém a
   simulação reproduzível e debugável.

---

## 5. Controles

Teclado, sem mouse. WASD e setas têm exatamente a mesma função, então o jogador usa o
conjunto que preferir. Nos menus, as mesmas teclas navegam (§17.2).

| Tecla | Ação |
| --- | --- |
| `A` / `←` | Mover a bandeja para a esquerda |
| `D` / `→` | Mover a bandeja para a direita |
| `S` / `↓` | Modo precisão (movimento fino, 42 % da velocidade) — usado para mirar |
| `W` / `↑` / `Espaço` | Lançar a bola (toque) · **atirar** (segurando, com o Canhão ativo) |
| `W` / `↑` / `Espaço` | Avançar de fase · jogar de novo depois do fim de jogo |
| `P` / `ESC` | Pausar (abre o menu de pausa, §17.1) |
| `R` | Reiniciar a partida do zero |
| `M` | Ligar / desligar todo o som, trilha inclusive |
| `ESC` | Sair, quando na tela inicial |

Teclas de teste, atrás do ajuste `Teclas de teste` (§17.3):

| Tecla | Ação |
| --- | --- |
| `1` a `7` | Solta na tela o modificador correspondente do catálogo (§11) |
| `E` | Dispara um evento aleatório agora (§14.3) |
| `0` | Limpa todos os efeitos, cápsulas, tiros, invasores e eventos |

### Por que `S`/`↓` é "precisão" e não "descer"?

A bandeja se move apenas na horizontal — um eixo vertical não tem função. Em vez de
deixar duas teclas mortas, `S`/`↓` virou o controle de precisão. Ele resolve um
problema real: a 680 px/s, a bandeja cruza o campo em ~1,4 s e o ajuste fino fica
impossível perto do fim da fase, quando só resta um tijolo e a bola faz trajetórias
longas. `W`/`↑` ficou redundante com `Espaço` de propósito: as duas formas de lançar
são igualmente válidas.

### Modelo de entrada

A entrada é separada em três canais, porque têm semânticas diferentes:

- **Estado contínuo** (`InputState.from_keyboard`): direção, precisão e a tecla de ação
  pressionada são lidos por polling a cada frame e valem para o frame inteiro.
- **Eventos discretos** (`KEYDOWN`): lançar, pausar e reiniciar são ações de borda. São
  registrados como *flag* pendente (`_launch_requested`) e consumidos dentro do passo
  fixo de simulação, nunca no meio de um frame de render. Isso evita que um toque de
  tecla caia entre dois subpassos de física e se perca.
- **Ação mantida** (`InputState.action`): atirar precisa ser contínuo, não de borda. A
  mesma tecla que lança (borda) também atira (contínuo), e o contexto decide qual dos
  dois vale — ver abaixo.

### Por que a mesma tecla lança e atira?

Porque quando o Canhão está ativo e a bola já está em jogo, lançar não tem mais função.
Em vez de inventar uma tecla nova, a tecla de ação fica com o trabalho que sobrou:

```python
if any(ball.attached for ball in self.balls):
    return          # ainda tem bola na bandeja: a tecla é de lançar
```

Há um detalhe que só aparece com o jogo rodando: se o jogador **segurar** a tecla para
lançar, o lançamento é um evento de borda e o estado contínuo continua verdadeiro — a
munição começaria a ser gasta no frame seguinte. Por isso existe `GUN_LAUNCH_GRACE`: o
saque arma um intervalo de 0,35 s em que o canhão não dispara. O toque que lançou nunca
custa munição.

---

## 6. Arquitetura do código

```
Project-01/
├── main.py                    # ponto de entrada (--version, --selftest)
├── build.py                   # empacota e verifica o executavel (§21)
├── quebrando_tijolos.spec     # receita do PyInstaller
├── run_tests.py               # roda as seis suítes de teste (§21)
├── requirements.txt           # pygame-ce>=2.5.8
├── GAME_DESIGN.md             # este documento
├── .github/workflows/build.yml  # empacota para Windows e Linux na CI
├── sounds/                    # efeitos e trilha (ver §15)
├── assets/                    # pack de sprites (ver §16)
├── save/                      # ajustes e placar gravados (ver §17.5)
├── dist/                      # executaveis gerados
├── tests/                     # verificação headless (ver §19)
└── src/
    ├── config.py              # tabela única de constantes e cores (sem lógica)
    ├── controls.py            # teclado -> InputState imutável
    ├── audio.py               # SoundBank: efeitos, trilha, canais, mudo
    ├── events.py              # eventos aleatórios: catálogo + director
    ├── sprites.py             # atlas do pack de arte, com fallback para primitivas
    ├── menu.py                # navegação e itens dos menus (sem pygame)
    ├── settings.py            # ajustes do jogador, com validação campo a campo
    ├── scores.py              # placar de líderes
    ├── store.py               # JSON à prova de arquivo ruim
    ├── physics.py             # física e resolução de colisões (sem regras de jogo)
    ├── level.py               # construção da grade de tijolos
    ├── game.py                # estados, loop, pontuação, vidas, desenho
    ├── modifiers/
    │   ├── specs.py           # catálogo de modificadores + Drop
    │   ├── manager.py         # pilha de efeitos, timers, sorteio
    │   └── capsule.py         # cápsula que cai do tijolo
    └── entities/
        ├── ball.py            # bola: estado, integração, lançamento, desenho
        ├── paddle.py          # bandeja: movimento, limites, english, canhão
        ├── brick.py           # tijolo: vida, valor de pontos, desenho
        ├── projectile.py      # projétil do modificador Armamento
        ├── invader.py         # inimigo do debuff Invasores
        ├── particle.py        # partículas de impacto (puramente cosmético)
        └── popup.py           # placar flutuante "+800" (puramente cosmético)
```

### Responsabilidades e fronteiras

| Módulo | Sabe sobre | **Não** sabe sobre |
| --- | --- | --- |
| `config.py` | nada — só números | tudo |
| `entities/` | `config` | física, colisões, pontuação, modificadores |
| `physics.py` | `config`, entidades | pontuação, vidas, fases, modificadores |
| `audio.py` | `config`, `sounds/` | jogo, entidades, estados |
| `events.py` | `config` | entidades, física, desenho |
| `modifiers/` | `config`, `specs` | física, entidades, desenho da bandeja |
| `sprites.py` | `config`, `assets/` | entidades, jogo, física |
| `menu.py` | `settings` | pygame, jogo, entidades |
| `settings.py` | `config`, `store` | jogo, áudio, pygame |
| `scores.py` | `config`, `store` | jogo, desenho |
| `store.py` | `config` | o que está sendo gravado |
| `level.py` | `config`, `Brick` | física, loop |
| `game.py` | tudo | — |

A fronteira mais importante é `physics.py`: ele **não decide nada sobre o jogo**. Ele
move a bola, resolve o contato e devolve um relatório:

```python
@dataclass
class CollisionReport:
    bricks_hit: list[Brick]   # tijolos tocados, sem aplicar dano
    paddle_hits: int
    walls_hit: list[str]      # "left" | "right" | "top"
    touched: bool
```

Quem decide que um tijolo perde vida, que o ponto entra no placar (e por qual
multiplicador) e que uma cápsula deve ser sorteada é o `game.py`. **Esse relatório é
exatamente o ponto de extensão do sistema de modificadores** (§13), por isso ele existe
desde a primeira versão.

A segunda fronteira é `modifiers/`: o gerenciador **não toca na bandeja nem na bola**.
Ele expõe multiplicadores; o `Game` consulta. É o que permite um efeito expirar sem
nenhum código de desfazer (§13.1).

### Direção das dependências

```
main.py ──> game.py ──┬──> physics.py    ──> entities/  ──> config.py
                      ├──> level.py      ──> entities/
                      ├──> controls.py
                      ├──> audio.py      ──> sounds/
                      ├──> events.py     ──> config.py
                      └──> modifiers/    ──> specs.py
```

Sem ciclos. `config.py` não importa nada do projeto, o que o torna seguro de importar
em qualquer lugar (inclusive em ferramentas de balanceamento futuras).

---

## 7. Loop de simulação e física da bola

### 7.1 Timestep fixo

O jogo separa **simulação** de **renderização**:

```
acumulador += min(tempo_do_frame, 0.25s)     # 0.25s evita "espiral da morte"
enquanto acumulador >= 1/120:
    passo_fixo(1/120, entrada)
    acumulador -= 1/120
desenha()                                     # uma vez por frame
```

A simulação roda travada em **120 Hz**, independente do FPS. Vantagens:

- Trajetória idêntica em máquinas de 60 Hz e 144 Hz.
- Um travamento de meio segundo não teleporta a bola.
- O teto de 0,25 s (`MAX_FRAME_TIME`) impede que uma pausa longa do sistema gere
  centenas de passos de uma vez.

### 7.2 Subpassos (anti-tunneling)

A 430 px/s e 120 Hz, a bola anda ~3,6 px por passo. Mas um "Bola Rápida" pode levar
isso a 600 px/s, e a 1/120 s isso vira 5 px — mais que o suficiente para atravessar a
quina de um tijolo se o alvo for fino.

A solução é dividir cada passo em subpassos de no máximo **meio raio**:

```python
distancia = velocidade.length() * dt
max_passo = raio * 0.5                       # 4,5 px
subpassos = ceil(distancia / max_passo)
for _ in range(subpassos):
    bola.advance(dt / subpassos)
    resolve_tijolos(); resolve_bandeja(); resolve_paredes()
```

A mesma técnica é o que permite uma verificação absurda como "bola a 60.000 px/s
continua colidindo" passar no teste (§19). O custo médio em jogo normal é de **2
subpassos por passo**.

### 7.3 Representação da bola

| Propriedade | Tipo | Observação |
| --- | --- | --- |
| `position` | `Vector2` (float) | **Centro** da bola, não o canto |
| `velocity` | `Vector2` (px/s) | Módulo constante; só a direção muda |
| `radius` | float | 9 px |
| `attached` | bool | Presa na bandeja, velocidade zero |

Tudo em ponto flutuante. `pygame.Rect` (inteiro) é usado só para broadphase e para
desenhar — nunca para a matemática de colisão, que perderia precisão.

**A velocidade é constante por decisão de design.** Acelerar a cada tijolo destruído
é um clássico do gênero, mas atrapalha o balanceamento dos modificadores: se a
velocidade base muda sozinha, o efeito de "Bola Lenta" fica impossível de comunicar ao
jogador. Aqui a velocidade só sobe por fase (§9).

### 7.4 Colisão círculo × retângulo

Base de toda a física. O teste é pelo ponto do retângulo mais próximo do centro:

```python
mais_proximo = clamp(centro, rect)
offset = centro - mais_proximo
if offset.length_squared() > raio²: return None
```

Duas leituras possíveis do resultado:

- **offset ≠ 0** → o centro está fora: a normal é `offset` normalizado e a penetração
  é `raio - |offset|`. É o caso comum (bola batendo na face ou na quina do tijolo).
- **offset = 0** → o centro está **dentro** do retângulo (bola engolida por um
  tijolo). Escolhe-se a face de menor penetração e empurra-se a bola para fora por
  ela. Sem esse caso a bola ficaria presa, vibrando dentro do tijolo.

Como a normal sai do cálculo geométrico e não de um `if eixo_x/eixo_y`, quinas geram
reflexões diagonais naturalmente — a bola sai "de lado" de uma quina, como deveria.

### 7.5 Depenetração e skin

Toda colisão segue a mesma ordem:

1. **Corrigir a posição primeiro** — `position += normal * (penetracao + skin)`
2. **Depois refletir a velocidade**

O `skin` (0,1 px) separa os corpos o suficiente para que o subpasso seguinte não
detecte o mesmo contato de novo. Além disso, se a bola já está se afastando
(`velocity · normal > 0`), o código **só corrige a posição e não reflete** — evita o
"duplo rebote" que faz a bola tremer entre dois tijolos.

### 7.6 Reflexão

```
v' = v − 2 (v · n) n
```

Reflexão vetorial pura sobre a normal. A magnitude é preservada por construção, então
o drift de velocidade medido em 6.000 frames de simulação é de `6.8e-13` px/s —
ruído de ponto flutuante.

### 7.7 Guarda anti-horizontal

O pior estado possível é uma bola correndo de parede em parede, paralela ao chão:
o jogo trava, o jogador não tem nada a fazer e a única saída é reiniciar.

`enforce_min_vertical()` garante que a componente vertical represente sempre pelo
menos **22 %** da velocidade:

```python
if abs(direcao.y) < 0.22:
    direcao.x = ±sqrt(1 − 0.22²)     # preserva o sinal do movimento horizontal
    direcao.y = ±0.22                # preserva o sinal do movimento vertical
```

Detalhes que importam:

- **O sinal é preservado.** Uma bola subindo continua subindo; só o módulo do ângulo
  muda. Corrigir uma bola a 3° da horizontal para 22° é imperceptível; virar o sinal
  dela seria um bug visível.
- **A velocidade é preservada.** A direção é reconstruída como vetor unitário e
  multiplicada pela velocidade original.
- **Roda depois de cada reflexão**, e o caso degenerado de velocidade zero é
  recuperado empurrando a bola para cima em vez de travar.

### 7.8 Rebote da bandeja (estilo Arkanoid)

A bandeja não reflete a velocidade: ela **define** o ângulo de saída a partir do ponto
de impacto.

```
offset    = (bola.x − centro_da_bandeja) / (largura / 2)   →   −1 .. +1
angulo    = 62° × offset                                    →   −62° .. +62°
direcao   = (sin(angulo), −cos(angulo))
direcao.x += (velocidade_da_bandeja / 680) × 0.35           →   english
```

| Ponto de impacto | Ângulo de saída |
| --- | --- |
| Extremidade esquerda | −62° (quase horizontal à esquerda) |
| Um quarto da esquerda | −31° |
| Centro | 0° (reto para cima) |
| Um quarto da direita | +31° |
| Extremidade direita | +62° |

O **english** é o ajuste fino: rebater enquanto a bandeja está em movimento desloca
levemente o ângulo, então quem se posiciona *antes* do impacto tem mais precisão do
que quem rebate em cima da hora. O impacto no centro é sempre a "zona de segurança" —
reto para cima.

A velocidade de saída usa `max(velocidade_da_bola, BALL_SPEED)`, então nenhum
modificador de lentidão pode empurrar a bola abaixo da velocidade base e transformar
o jogo em um alvo lento demais.

### 7.9 Paredes e linha de morte

O campo é fechado em três lados: esquerda, direita e teto. A base é **aberta** — é a
linha de morte, desenhada em vermelho para leitura instantânea.

- Paredes laterais: `position.x` é travado e `velocity.x` recebe `±abs(...)`. O sinal
  é forçado em vez de invertido, o que torna a resolução idempotente (chamar duas
  vezes não inverte a direção duas vezes).
- Teto: mesma lógica para `y`.
- Depois de qualquer parede, a guarda anti-horizontal roda — é exatamente no rebote
  lateral que a bola tende a ficar horizontal.
- Uma bola é perdida quando `position.y − raio > PLAYFIELD.bottom`, ou seja, quando ela
  sai **inteira** do campo. Isso dá ao jogador a leitura correta de "morreu".

### 7.10 Saque

A bola nasce presa na bandeja e acompanha o jogador até o lançamento, o que dá tempo
de se posicionar. O saque **não é aleatório**: o sinal da inclinação alterna a cada
lançamento (`+18°`, `−18°`, `+18°`, ...).

Motivo: um saque perfeitamente vertical faz a bola subir e descer para sempre pela
mesma coluna de tijolos, sem nunca abrir caminho. Alternar o sinal troca de coluna a
cada saque e mantém a simulação totalmente determinística — o que, de novo, é o que
permite testar a física sem sementes de aleatoriedade.

### 7.11 Resumo numérico

| Constante | Valor | Papel |
| --- | --- | --- |
| `FIXED_TIMESTEP` | 1/120 s | Frequência da simulação |
| `MAX_FRAME_TIME` | 0,25 s | Teto do acumulador (anti-espiral) |
| `MAX_SUBSTEP_RATIO` | 0,5 × raio | Tamanho máximo de um subpasso |
| `COLLISION_SKIN` | 0,1 px | Separação após depenetração |
| `BALL_RADIUS` | 9 px | Raio |
| `BALL_SPEED` | 430 px/s | Velocidade base (constante) |
| `BALL_MAX_BOUNCE_ANGLE_DEG` | 62° | Ângulo máximo de saída da bandeja |
| `BALL_MIN_VERTICAL_FRACTION` | 0,22 | Piso da componente vertical |
| `BALL_SERVE_ANGLE_DEG` | 18° | Inclinação do saque (sinal alternado) |
| `PADDLE_SPEED` | 680 px/s | Velocidade da bandeja |
| `PADDLE_PRECISION_FACTOR` | 0,42 | Multiplicador no modo precisão |
| `PADDLE_ENGLISH` | 0,35 | Influência do movimento da bandeja no ângulo |
| `LEVEL_SPEED_STEP` | +6 % | Aceleração da bola por fase |

---

## 8. Entidades

### Bola

Centro em ponto flutuante, velocidade vetorial, `attached`. Métodos: `launch()`,
`advance(dt)`, `snap_to_paddle()`, `is_lost()`. A lista `game.balls` é um **array** desde
o início, e é isso que faz o Multiplicador de Bolas ser uma linha de código em vez de uma
refatoração.

### Bandeja

Caixa alinhada aos eixos, movimento só na horizontal, travada dentro do campo por
`_clamp_to_playfield()`. Guarda `velocity_x` para que a bola herde o english.

A largura é **mutável** e existe `set_width_multiplier(m)`, que redimensiona pelo centro
(§13.1). Também desenha o cano do canhão quando o Armamento está ativo.

### Tijolo

`column`, `row`, `rect`, `hp` e `max_hp`. O valor de pontos é
`SCORE_PER_BRICK × max_hp`. A cor vem da linha (`BRICK_ROW_COLORS`), então a cor já
comunica a dureza: as **duas linhas do topo têm 2 de vida** e ficam visualmente
rachadas depois do primeiro acerto (`hp < max_hp` desenha um retângulo interno escuro).

### Cápsula, projétil e invasor

As três entidades do sistema de modificadores, todas em `modifiers/capsule.py` ou
`entities/`:

| Entidade | Movimento | Como morre |
| --- | --- | --- |
| `Capsule` | Reto para baixo a 165 px/s | Capturada pela bandeja, ou some ao passar do fundo |
| `Projectile` | Reto para cima a 980 px/s | Acerta um tijolo ou um invasor, ou sai pelo teto |
| `Invader` | Desce a 92 px/s ricocheteando nas paredes | Tiro, bola, ou acerta a bandeja (custa uma vida) |

Todas usam `pygame.Rect.colliderect` para colisão — são caixas contra caixas e contra a
bandeja, sem a matemática contínua que a bola precisa (§7.4). O invasor contra a bola é a
única exceção: usa `circle_rect_contact`, porque ali a bola precisa ricochetear de volta.

### Grade

7 linhas × 11 colunas = **77 tijolos**, distribuídos pela largura útil com `gap` de
6 px. O layout é calculado a partir de `PLAYFIELD`, então mudar o tamanho da janela
reflui a grade sozinho — foi o que aconteceu quando o HUD cresceu de 52 para 80 px: a
grade se ajustou sem uma linha de mudança.

---

## 9. Pontuação, vidas e fases

| Evento | Pontos |
| --- | --- |
| Acertar um tijolo sem destruir | 10 |
| Destruir um tijolo de 1 de vida | 100 |
| Destruir um tijolo de 2 de vida | 200 (10 no primeiro acerto + 200 no segundo) |

- **Vidas:** 3 por padrão. Perder a última bola em jogo custa uma vida; com múltiplas
  bolas em jogo, perder uma não custa nada.
- **Fase:** limpa quando todos os 77 tijolos morrem. A bola congela, o estado muda para
  `LEVEL_CLEAR` e o jogador avança quando quiser.
- **Escalada:** a cada fase a velocidade da bola sobe 6 %
  (`BALL_SPEED × (1 + 0.06 × (fase − 1))`). Na fase 10 é +54 % — a dificuldade vem do
  ritmo, não de mais vida nos tijolos.
- **Estados:** `PLAYING`, `PAUSED`, `LEVEL_CLEAR`, `GAME_OVER`. A física só roda em
  `PLAYING`; nos outros o acumulador é zerado, então nada "anda escondido" durante uma
  pausa.

Ideia futura de pontuação (não implementada): multiplicador de combo por destruir
tijolos consecutivos sem tocar na bandeja, que também alimentaria a chance de cápsula.

---

## 10. Sistema de modificadores — conceito

### 10.1 O ciclo da cápsula

1. **Sorteio.** Ao destruir um tijolo, o jogo sorteia se uma cápsula cai (§12).
2. **Queda.** A cápsula desce a 165 px/s a partir do ponto exato do tijolo destruído.
3. **Decisão.** O jogador escolhe entre rebater e coletar. A cor revela a polaridade
   (verde = buff, vermelho = debuff) e o rótulo revela o efeito por extenso: `2 BOLAS`,
   `PONTOS x2`, `BANDEJA`, `CANHAO`, `INVERTE`, `RAPIDAS`, `INVASORES`.
4. **Captura.** Se tocar a bandeja, o efeito entra na pilha de efeitos ativos.
5. **Expiração.** Efeitos com duração saem sozinhos; o HUD mostra o tempo restante.

### 10.2 Identidade da cápsula: uma decisão revertida

A primeira versão deste documento propunha cápsulas **anônimas** — mesma cor para buff e
debuff, revelando o efeito só na captura, com a leitura de risco vindo de som e padrão de
queda.

**Isso foi revertido na implementação.** Os motivos:

1. Com 7 modificadores e apenas 4 arquivos de som, o anonimato viraria sorteio puro: o
   jogador não teria como decidir nada, só reagir.
2. A decisão interessante não é "pego ou não pego o que não sei o que é", e sim "vale a
   pena abandonar a posição defensiva para pegar esta `BANDEJA` que está caindo a três
   colunas daqui?".
3. Um debuff que o jogador não tem como evitar não gera tensão, gera injustiça.

A polaridade continua vindo da cor: verde e vermelho se distinguem no canto do olho durante
um rebate. O **ícone** (§16) diz qual efeito é, para quem tem tempo de olhar, e o **nome sobe
da bandeja** no momento da captura (§16.4), que é quando o jogador está de fato olhando para
lá.

Se um dia o anonimato voltar, o lugar de implementá-lo é uma única linha em
`Capsule.color` — o resto do sistema não precisa saber.

---

## 11. Catálogo de modificadores

**Estado: implementado.** O catálogo vive em `src/modifiers/specs.py`, o arquivo de
*conteúdo* do jogo. `peso` é o peso relativo dentro da própria polaridade (§12). Cada
cápsula carrega um `Drop` = (spec + magnitude), onde a magnitude só é usada pelo
Multiplicador de Bolas.

### 11.1 Buffs

| ID | Nome | Na cápsula | Efeito | Duração | Peso |
| --- | --- | --- | --- | --- | --- |
| `ball_multiplier` | Multiplicador de Bolas | `2 BOLAS` … `8 BOLAS` | Multiplica as bolas em jogo por 2, 4, 6 ou 8, até o teto de 8 | instantâneo | 22 |
| `score_multiplier` | Multiplicador de Pontos | `PONTOS x2` | Dobra a pontuação. Acumula até 8x | instantâneo, acumula | 20 |
| `paddle_grow` | Bandeja Grande | `BANDEJA` | Largura da bandeja ×1,25. Acumula até 3 vezes | 20 s | 20 |
| `gun` | Armamento | `CANHAO` | Canhão na bandeja com 8 disparos. Acumula munição até 40 | instantâneo | 18 |

**Notas de design**

- **`ball_multiplier`** — os quatro fatores caem com pesos diferentes (50 / 28 / 14 / 8),
  então o 2x é o caso comum e o 8x é o prêmio. Cada clone nasce com a direção da bola de
  origem girada em 26°, para as bolas se separarem em vez de voarem coladas; clones
  sucessivos abrem mais o leque. O teto de **8 bolas** é o que impede a tela de virar uma
  sopa ilegível — e como o teto é checado antes do sorteio, o modificador para de cair
  quando não serve mais para nada.
- **`score_multiplier`** — é o único efeito que **persiste pela partida inteira** e
  sobrevive à troca de fase e à perda de vida. É de propósito: perder o acúmulo ao morrer
  transformaria o buff em mais uma coisa a proteger, e o jogador já tem 8 bolas para
  proteger. Teto de 8x porque além disso o número deixa de significar algo.
- **`paddle_grow`** — redimensiona **pelo centro**, não pela borda. Assim a bandeja não
  escorrega para fora da mão do jogador quando o efeito começa nem quando ele termina.
- **`gun`** — a cadência é de 4,5 tiros/s (`GUN_COOLDOWN = 0,22 s`) e o projétil voa a
  980 px/s, mais rápido que qualquer bola. A tecla é a mesma de lançar (§5).

### 11.2 Debuffs

| ID | Nome | Na cápsula | Efeito | Duração | Peso |
| --- | --- | --- | --- | --- | --- |
| `inverted_controls` | Inversão dos Comandos | `INVERTE` | Esquerda e direita trocadas | 8 s | 34 |
| `fast_balls` | Bolas Super Rápidas | `RAPIDAS` | Velocidade da bola ×1,85. Acumula até 2 vezes | 8 s | 33 |
| `invaders` | Invasores | `INVASORES` | Inimigos descem em direção à bandeja, um a cada 2,4 s | 12 s | 33 |

**Notas de design**

- **`inverted_controls`** — o debuff mais caro em frustração e o mais interessante, porque
  converte reflexo em decisão consciente: por 8 segundos o jogador precisa pensar antes de
  mover a mão. Curto de propósito.
- **`fast_balls`** — a ×1,85 a bola fica em ~795 px/s e cruza o campo em pouco mais de um
  segundo, o que tira a margem de erro do jogador. O ponto técnico está em §13.2: a
  velocidade é **reaplicada a cada passo**, então o efeito pega imediatamente todas as
  bolas em jogo e desaparece na hora quando expira.
- **`invaders`** — o único debuff que cria uma **ameaça nova** em vez de distorcer um
  número existente. Os invasores descem a 92 px/s com deriva lateral, ricocheteiam nas
  paredes e podem ser destruídos pelo canhão ou pela bola. Tocar na bandeja custa uma
  vida. Se chegarem ao fundo sem acertar, somem: o debuff é pressão, não sentença de
  morte.

### 11.3 Regras de acúmulo

- O **mesmo** efeito com duração coletado de novo **acumula** e reinicia o cronômetro, até
  o teto específico daquele efeito.
- `score_multiplier` dobra a cada coleta: 2x → 4x → 8x, e para.
- Buffs e debuffs **não se cancelam** — não existe antídoto. Como só há um modificador de
  velocidade (e ele é debuff), a composição de multiplicadores é hoje teórica, mas o
  código já multiplica em vez de somar, então "Bola Lenta" no futuro se cancelaria com
  "Bolas Super Rápidas" por aritmética, sem lógica especial.
- Um efeito que já está **ativo** ou já está no **teto** não é sorteado de novo: o sorteio
  tira outro do bolo. Isso evita gastar cápsulas em efeitos que não fariam nada.

### 11.4 Como a morte interage com os efeitos

Perder uma vida limpa os **buffs** e a munição, mas os **debuffs continuam correndo**.

A primeira versão limpava tudo — e isso abria um buraco. Bastava deixar a bola cair de
propósito para se livrar de "Bolas Super Rápidas" ou de uma invasão, trocando **uma vida
por um efeito ruim**. Como o jogador tem 3 vidas, era um preço perfeitamente pagável.

Agora `_lose_life()` chama `ModifierManager.on_life_lost()`, que remove apenas os efeitos
de polaridade `BUFF`. A punição tem que doer até o cronômetro zerar. Trocar de fase
(`on_level_start`) limpa tudo — ali a fase realmente acabou.

Esse bug só apareceu porque um teste automatizado verificou que os invasores apareciam
depois de 2,4 s e eles nunca apareciam: a bola caía antes, e a vida perdida apagava o
efeito (§19).

---

## 12. Sorteio de cápsulas

Três camadas, nesta ordem, todas em `ModifierManager`.

**1. Vai cair?** (`roll_drop`)

| Regra | Valor |
| --- | --- |
| Chance base por tijolo destruído | 18 % |
| Piedade: ao chegar em 12 tijolos sem queda | força uma queda |
| Buffer anti-frustração | no máximo 4 cápsulas na tela |

O contador de piedade avança **mesmo quando a tela está cheia** de cápsulas: o sorteio
acontece antes da checagem de espaço. Se fosse ao contrário, uma sequência longa com a
tela cheia zeraria o contador sem nunca ter dado nada ao jogador.

**2. Qual polaridade?**

62 % buff / 38 % debuff (`CAPSULE_BUFF_BIAS`), com uma trava:
**nenhum debuff cai nos primeiros 8 tijolos destruídos da partida**
(`CAPSULE_MIN_BRICKS_BEFORE_DEBUFF`). O jogador precisa aprender a rebater antes de ser
punido por rebater mal.

Na medição real (4.000 sorteios), a taxa efetiva de queda ficou em **20 %** — os 18 %
mais o empurrão da piedade — e a proporção de buffs entre as escolhas, em **61 %**.

**3. Qual modificador?**

Sorteio ponderado pelo `peso` dentro da polaridade, descartando o que já está ativo ou já
está no teto (§11.3). Para o Multiplicador de Bolas, um segundo sorteio escolhe o fator
entre 2, 4, 6 e 8 com pesos 50 / 28 / 14 / 8.

Todos os sorteios usam um `random.Random(semente)` próprio do `ModifierManager` —
**separado da física, que não tem aleatoriedade nenhuma**. O `Game` aceita uma semente no
construtor, então uma partida inteira é reproduzível, com modificadores ligados.

---

## 13. Arquitetura do sistema de modificadores

**Estado: implementado.** O que segue descreve o código, não um plano.

### 13.1 Princípio: efeitos declaram, o jogo consulta

O erro clássico é o efeito **mutar** o estado dos objetos (`bandeja.width *= 0.7`) e
depois ter que desfazer. Isso quebra com dois efeitos simultâneos, com pausa e com troca
de fase.

A abordagem implementada: cada efeito ativo é um **declarante de dados**, e o `Game`
deriva o valor efetivo a cada quadro a partir de `config` (código real, abreviado):

```python
@dataclass(frozen=True)
class ModifierSpec:
    id: str
    name: str
    short: str          # texto da capsula: "BANDEJA", "RAPIDAS", "2 BOLAS"
    hud: str            # nome no chip do HUD: "BANDEJA", "BOLAS RAPIDAS"
    polarity: Polarity  # BUFF | DEBUFF
    weight: int
    duration: float     # 0.0 -> instantâneo
    summary: str

@dataclass
class ActiveEffect:
    spec: ModifierSpec
    remaining: float
    stacks: int = 1

class ModifierManager:
    def update(self, dt: float) -> list[ModifierSpec]: ...   # expira e devolve
    def roll_drop(self, at_ball_cap: bool) -> Drop | None: ...
    def activate(self, drop: Drop) -> None: ...
    def on_level_start(self) -> None: ...                    # limpa tudo
    def on_life_lost(self) -> None: ...                      # limpa só os buffs
    @property
    def score_multiplier(self) -> float: ...
    @property
    def paddle_width_multiplier(self) -> float: ...
    @property
    def ball_speed_multiplier(self) -> float: ...
    @property
    def controls_inverted(self) -> bool: ...
    @property
    def invaders_active(self) -> bool: ...
```

O `Game` consome isso em duas linhas:

```python
@property
def ball_speed(self) -> float:
    base = config.BALL_SPEED * (1.0 + config.LEVEL_SPEED_STEP * (self.level - 1))
    return base * self.modifiers.ball_speed_multiplier

self.score += int(brick.score_value * self.modifiers.score_multiplier)
```

**Nenhum efeito muta a bandeja ou a bola.** A bandeja não "fica larga": ela *lê* um
multiplicador e se redimensiona. Quando o efeito expira, a informação some sozinha e a
bandeja volta ao tamanho base no quadro seguinte, sem nenhum código de desfazer. É por
isso que pausar, morrer ou trocar de fase não deixam efeito colado.

### 13.2 Velocidade é reaplicada, não guardada

`Bolas Super Rápidas` é o caso mais delicado, porque a velocidade tem três fontes: o valor
base, a escala da fase (×1,06 por fase) e o modificador.

Em vez de calcular a velocidade uma vez no lançamento e guardá-la, `Game._enforce_ball_speed()`
**reaplica o valor alvo a toda bola a cada passo fixo**:

```python
target = self.ball_speed
for ball in self.balls:
    if ball.attached:
        continue
    ball.velocity = ball.velocity * (target / ball.speed)
```

Isso resolve os dois sentidos de uma vez: o debuff pega imediatamente as bolas que **já
estão em jogo**, e quando ele expira todas voltam à velocidade normal sem nenhum evento de
"fim de efeito". A invariante é verificável — num teste de 60 segundos, toda bola está
sempre exatamente na velocidade efetiva do quadro.

O custo é um `Vector2` novo por bola por passo. Com 8 bolas a 120 Hz isso é ~960
multiplicações de vetor por segundo, o que é irrelevante perto do resto.

### 13.3 Pontos de gancho

| Gancho | Onde | Uso |
| --- | --- | --- |
| `CollisionReport.bricks_hit` | `physics.py` | Dano, pontos, sorteio de cápsula, som |
| `CollisionReport.paddle_hits` | `physics.py` | Som, english |
| `CollisionReport.walls_hit` | `physics.py` | Som |
| `Brick.damage()` | `entities/brick.py` | Devolve `True` na morte — o sinal exato do sorteio |
| `Game._damage_brick` | `game.py` | Ponto único onde o multiplicador de pontos entra |
| `Game._enforce_ball_speed` | `game.py` | Multiplicador de velocidade |
| `Paddle.set_width_multiplier` | `entities/paddle.py` | Bandeja Grande, redimensionando pelo centro |
| `Game._update_gun` | `game.py` | Consumo de munição e cadência |

### 13.4 Módulos criados

```
src/
├── audio.py                # SoundBank: carga, eventos, canais, mudo (§15)
├── modifiers/
│   ├── specs.py            # catálogo (tabelas §11) + Drop
│   ├── manager.py          # pilha, timers, acúmulos, sorteio
│   └── capsule.py          # entidade que cai
└── entities/
    ├── projectile.py       # projétil do Canhão
    └── invader.py          # inimigo do debuff Invasores
```

### 13.5 HUD de efeitos

A barra do HUD passou de 52 px para 80 px para caber duas linhas:

- **Linha 1:** pontuação, vidas, fase, bolas em jogo e o lembrete de controles.
- **Linha 2:** um *chip* por efeito com duração — rótulo, acúmulos e segundos restantes.
  Verde para buff, vermelho para debuff, o que deixa a leitura instantânea. À direita da
  mesma linha ficam o multiplicador de pontos acumulado, a munição do canhão e, quando for
  o caso, `MUDO`.

As duas linhas foram medidas: com um buff e um debuff ativos ao mesmo tempo, os chips
terminam por volta de x = 209 px e o resumo da direita começa em x = 821 px.

---

## 14. Dinâmica de partida

Esta seção existe por um motivo específico: a primeira versão jogável estava **correta e
sem graça**. A física funcionava, os modificadores funcionavam, os testes passavam — e
ainda assim a partida era uma espera. Aqui está o diagnóstico e o que foi feito.

### 14.1 O diagnóstico

| Sintoma | Causa | Efeito no jogador |
| --- | --- | --- |
| Nada acontecia sem quebrar tijolos | O jogo só reagia ao jogador | Passividade: esperar a bola |
| A fase ficava pior no fim | Menos tijolos = viagens mais longas e vazias | Tédio justo na hora do fecho |
| Nenhuma resposta ao impacto | Um tijolo sumia sem deixar rastro | Ação sem peso |
| Recompensa 100 % aleatória | Nada que o jogador fizesse mudava a sorte | Falta de agência |
| Uma única ameaça, e só como debuff | Sem pressão constante | Nenhuma urgência |

Cinco problemas, cinco correções. Nenhuma delas é grande sozinha; juntas, mudam o ritmo
de uma partida inteira.

### 14.2 Sequência — agência sobre a própria sorte

A **sequência** conta tijolos destruídos **desde a última bola perdida**. Cada tijolo vale
`1 + min(sequência, 40) × 0,02` a mais — até **+80 %** — e a cada **8 tijolos seguidos** o
jogador ganha uma cápsula **garantida**, aplicada na hora, sem chance de errar a coleta.

Isso ataca o problema da agência. Antes, toda cápsula vinha de um sorteio de 18 % e o
jogador não tinha **nenhum** botão para apertar em busca de recompensa. Agora tem: não
deixar a bola cair.

O número fica no HUD e muda de cor em 12 (âmbar) e 24 (vermelho), então a escalada é
visível sem precisar ler. Só uma coisa zera a sequência, e é perder a bola.

**Por que não zerar ao tocar na bandeja?** Porque a bola toca na bandeja a cada 2 ou 3
segundos, e a sequência nunca passaria de 2 ou 3. Métrica que não sobe não motiva ninguém.
Zerar só na perda de bola faz da sequência uma medida honesta de "esta vida está indo bem".

### 14.3 Eventos aleatórios — o mundo age sozinho

A cada **15 a 25 segundos** o jogo dispara um **evento**: uma regra global que muda por
alguns segundos, anunciada por um letreiro grande. O primeiro chega aos 9 s, para o
jogador ver um acontecendo antes de entender o resto.

| Evento | Tipo | Efeito | Duração |
| --- | --- | --- | --- |
| `capsule_rain` | bom | 5 cápsulas caem de uma vez pela largura do campo | instantâneo |
| `ball_frenzy` | bom | o campo vai a 4 bolas de uma vez | instantâneo |
| `free_gun` | bom | canhão sem limite de munição | 9 s |
| `safety_net` | bom | a base do campo fecha e devolve a bola | 12 s |
| `invasion` | ameaça | 3 invasores aparecem de uma vez | instantâneo |
| `blackout` | ameaça | o campo escurece; só a bandeja e as bolas iluminam | 8 s |
| `wild_ball` | ameaça | a bola acelera sem parar, até ×1,9 | 8 s |

Três decisões fazem o sistema funcionar:

1. **Tudo é anunciado.** Metade da graça de um apagão é vê-lo chegar. O letreiro aparece
   com fade de entrada e saída, e a cor diz a intenção antes de qualquer leitura.
2. **Os que têm duração viram chip no HUD**, com o tempo restante e a borda na cor do
   tipo. O estado do mundo é sempre legível.
3. **O sorteio nunca repete o evento anterior**, e um evento já em andamento não é
   sorteado de novo — evita desperdício e evita monotonia.

**Evento não é modificador.** O modificador é coletado pelo jogador e altera o estado
**dele**; o evento acontece com ou sem permissão e altera o **mundo**. Os dois convivem
porque resolvem problemas diferentes: o modificador premia, o evento surpreende.

### 14.4 Reta final — o fecho deixa de ser o pior pedaço

Dois ajustes atacam o mesmo problema por lados opostos:

- **Rampa de limpeza:** a velocidade da bola sobe até **+12 %** conforme a grade esvazia
  (`clear_ramp`). Menos tijolos significam viagens mais longas, e a rampa encurta as
  viagens — exatamente onde o jogo estava mais lento.
- **RETA FINAL:** quando restam **5 tijolos**, o jogo dispara um letreiro, sobe a contagem
  para **3 bolas** e acelera mais **15 %**. Uma vez por fase.

O resultado é que o fim da fase vira o clímax em vez de virar a parte em que o jogador
olha o relógio. Das cinco correções, esta é a que mais muda a sensação de uma partida
inteira.

### 14.5 Impacto — o que faz a ação pesar

Quatro camadas, todas **puramente cosméticas**: nenhuma delas tem efeito sobre a
jogabilidade, e nenhuma é lida por qualquer outro sistema. Os sprites (§16) são a base
sobre a qual as outras três trabalham.

**Partículas.** Todo tijolo destruído solta 8 fragmentos na cor do próprio tijolo, com
gravidade e encolhimento até sumir. Um tijolo que apenas pisca e desaparece não parece ter
quebrado. O sistema tem teto de **420 partículas** e descarta o excedente em vez de crescer
sem limite — um teto que só é atingido em situações extremas, mas que existe para que uma
sequência longa não degrade o quadro.

**Placar flutuante.** Um `+800` sobe do ponto exato do tijolo destruído. Existe por
clareza, não por enfeite: o jogo tem multiplicador de pontos, bônus de sequência e eventos
que mexem no placar, e sem ver o número subir o jogador não tem como perceber que essas
coisas estão funcionando. O texto sai **dourado quando algum multiplicador está ativo** e
branco quando não está, então a própria cor ensina que o valor mudou de patamar. O teto é
de 18 números na tela, e o mais antigo sai para dar lugar ao novo.

**Tremor de tela.** Quebrar um tijolo treme 1,5 px; rebater na bandeja, 2,4; perder uma
vida, 9. O tremor decai a 26 px/s e nunca passa de 14 px.

O deslocamento é gerado por **duas senoides de frequências diferentes**, não por `random`.
Isso importa: um tremor aleatório consumiria o gerador de números do jogo e deslocaria a
sequência de cápsulas, quebrando a reprodutibilidade por semente.

**Mundo em superfície própria.** Para o tremor poder deslocar tudo de uma vez, o campo
inteiro é desenhado numa `Surface` e depois copiada com o deslocamento. Partículas e placar
flutuante vivem nessa camada, então tremem junto com o mundo. O HUD e os letreiros ficam de
fora, porque texto tremendo é ilegível.

### 14.6 O que ficou de fora, e por quê

- **Inimigos permanentes no cenário.** Hoje o inimigo é sempre um evento ou um debuff. Uma
  torre fixa na grade, que atira na bandeja enquanto estiver viva, daria um alvo
  prioritário constante e uma razão para o canhão existir além de acelerar a limpeza. Foi
  deixada de fora porque o jogo ainda não tinha ritmo: adicionar uma ameaça permanente a um
  jogo parado só o deixaria irritante. Com a sequência e os eventos no lugar, é a próxima
  adição natural.
- **Escolha de evento pelo jogador.** Seria mais agência, mas tiraria o susto, que é
  justamente o ponto do sistema.
- **Dois eventos ao mesmo tempo.** O director já suporta, mas a leitura fica confusa com
  mais de dois chips de evento na mesma linha, então o sorteio evita.

---

## 15. Áudio

### 15.1 Os arquivos

`sounds/` tem quatro arquivos WAV, todos 44,1 kHz, estéreo, 16 bits:

| Arquivo | Duração | Eventos |
| --- | --- | --- |
| `ball_sound.wav` | 0,29 s | Parede, bandeja, tijolo, tiro, invasor destruído |
| `power_up_sound.wav` | 4,25 s | Coleta de um buff |
| `lose_ball_sound.wav` | 3,00 s | Bola perdida e fim de jogo |
| `level_complete_sound.wav` | 2,99 s | Fase limpa |

### 15.2 O banco de sons

`SoundBank` (`src/audio.py`) varre `sounds/` na inicialização e liga **nomes de arquivo a
eventos de jogo**, e não o contrário:

```python
EVENT_SOURCES = {
    "wall":           ("wall_sound", "ball_sound"),
    "paddle":         ("paddle_sound", "ball_sound"),
    "brick":          ("brick_sound", "ball_sound"),
    "shoot":          ("shoot_sound", "ball_sound"),
    "power_up":       ("power_up_sound",),
    "debuff":         ("debuff_sound", "power_up_sound"),
    "lose_ball":      ("lose_ball_sound",),
    "level_complete": ("level_complete_sound",),
    "game_over":      ("game_over_sound", "lose_ball_sound"),
    "invader":        ("invader_sound", "ball_sound"),
    "menu":           ("menu_sound", "ball_sound"),
}
```

Cada evento tenta os candidatos em ordem e usa o primeiro arquivo que existir. Duas
consequências práticas:

1. **Adicionar som não exige mexer em código.** Basta largar um `shoot_sound.wav` em
   `sounds/` e o tiro passa a ter som próprio na próxima execução. Se ninguém largar
   nada, ele cai no `ball_sound` e o jogo continua com som.
2. **Um sample cobre vários eventos.** Os quatro arquivos renderiam dez eventos com o
   mesmo som, então o **volume** é o que os diferencia: parede a 0,35, tijolo a 0,50,
   tiro a 0,40, bandeja a 0,80. É a mesma amostra, mas a parede soa como um toque e a
   bandeja como um rebate.

### 15.3 Três decisões de robustez

**Canal dedicado por evento.** O mixer é configurado com 16 canais e cada evento recebe um
canal fixo. Repetir um som interrompe a si mesmo e nunca os outros — então um rebate rápido
não corta o jingle de fim de fase, e vice-versa. Com um `find_channel` genérico, o mixer
encheria e o som mais importante sumiria justo no momento mais importante.

**Cooldown por evento.** Sem ele, uma bola acertando quatro tijolos dentro do mesmo
subpasso dispara quatro cópias do mesmo sample no mesmo quadro, e o resultado é um estalo
distorcido em vez de som. Os cooldowns vão de 30 ms (parede, tijolo) a 500 ms (fim de
jogo), e são o motivo de o som de tijolo poder tocar em rajada sem virar ruído.

**Silêncio em vez de erro.** Se o mixer não inicializar, se a pasta não existir ou se um
arquivo estiver corrompido, o banco fica com `available = False` e todo `play()` vira uma
operação sem efeito. O jogo nunca quebra por causa de áudio, e é isso que permite os testes
rodarem em modo headless com `SDL_AUDIODRIVER=dummy` — as dez ligações de evento são
verificadas sem placa de som nenhuma.

### 15.4 Controle

`M` liga e desliga o som. O estado mudo aparece no HUD como `MUDO`, porque um jogo em
silêncio sem indicação visual é indistinguível de um jogo quebrado.

### 15.5 Pendência

Nenhum dos quatro arquivos foi feito para um evento específico de impacto: não há som de
rebate na bandeja, de tiro nem de coleta de debuff. O mapeamento acima extrai o máximo dos
quatro, mas três arquivos novos resolveriam isso sem tocar em código — só largando os
arquivos com os nomes que `EVENT_SOURCES` já procura: `paddle_sound.wav`, `shoot_sound.wav`
e `debuff_sound.wav`.

### 15.6 Trilha sonora

`sounds/background_music_01.mp3` (102 s) toca em laço, do início do jogo até sair, e usa
`pygame.mixer.music` em vez de `Sound`.

A escolha não é detalhe. `Sound` decodifica o arquivo inteiro na memória, e 102 s de áudio são
dezenas de MB de PCM; `music` faz streaming do disco e reserva um canal próprio, então a
trilha nunca rouba um canal de efeito. A descoberta é por nome: **qualquer** arquivo em
`sounds/` que comece com `background_music`, `music`, `theme`, `trilha` ou `bgm` é tratado
como trilha e sai da biblioteca de efeitos — assim ninguém acaba com o mp3 carregado duas
vezes, uma como trilha e outra como um "efeito" de 102 segundos.

`start_music()` é **idempotente**: os ajustes chamam a função a cada mudança, e reiniciar a
faixa do zero toda vez soaria como um disco pulando. Se já está tocando, só o volume muda.

O mudo rápido (`M`) pausa a trilha junto com os efeitos, sem mexer nos ajustes salvos: é um
silêncio temporário, não uma preferência.

---

## 16. Sprites e interface

### 16.1 O que o pack entrega

`assets/` traz 61 sprites num atlas do TexturePacker: `assets/Sprite Sheet/Breakout_Tile_Free.png`
é a folha e `Breakout_Tile_Free.xml` traz o retângulo de cada sprite. `assets/PNG/` tem os
mesmos 61 sprites soltos e `assets/Vector/` tem as versões vetoriais, que servem para
reescalar sem perda se um dia a grade mudar de tamanho.

A análise revelou uma estrutura bem mais útil do que parecia:

| Sprites | Tamanho | Conteúdo |
| --- | --- | --- |
| 01–20 | 384 × 128 | **10 cores de tijolo, cada uma em dois estados**: ímpar inteiro, par rachado |
| 21–30 | *(não usados — ver 16.3)* | 10 ícones quadrados glossy, mesma forma, cores diferentes |
| 31–56 | 243 × 64 | Pílulas de HUD com valores de pontos gravados (`+50`, `+250`) |
| 57 | 115 × 64 | Medidor segmentado |
| 58 | 64 × 64 | **Bola** — esfera azul com brilho |
| 59 | 64 × 61 | **Estrela** dourada |
| 60 | 64 × 58 | **Coração** vermelho |
| 61 | 10 × 21 | Fragmento pequeno (partícula) |

A descoberta que destravou tudo foi o par ímpar/par dos tijolos. Os arquivos ímpares têm
~1,8 KB e os pares ~13 KB — a diferença de compressão entre uma superfície lisa e uma
rachada. Comparando as cores dominantes, os pares têm sistematicamente mais pixels escuros
que os ímpares. **São 10 cores × 2 estados de dano**, exatamente o que um tijolo com
`hp`/`max_hp` precisa. A suíte de testes confere isso para as 7 linhas usadas: o sprite
rachado tem que ser mais escuro que o inteiro (§19).

### 16.2 Como o pack entra no jogo

| Sprite | Onde entra | Por quê |
| --- | --- | --- |
| Tijolos 01–20 | `Brick.sprites` | Uma cor por linha; o rachado aparece quando `hp < max_hp` |
| 58 (bola) | `Ball.draw` | Substitui o círculo desenhado |
| 60 (coração) | HUD | **Um coração por vida**, no lugar de "VIDAS 3" |
| 59 (estrela) | HUD | Ícone do placar, no lugar da palavra "PONTOS" |

Cada modificador tem um `short` (o texto que aparece na cápsula) e um `hud` (o nome do
chip), ambos em português e dizendo o efeito: `BANDEJA`, `CANHAO`, `INVERTE`, `RAPIDAS`,
`INVASORES`, `2 BOLAS`, `PONTOS x2`.

**Os tijolos são a maior vitória.** A grade já usava 78 × 26 — proporção 3:1, exatamente a
do sprite (384 × 128) — então o downscale não distorce nada. O resultado é uma grade com
bisel, brilho no topo e sombra embaixo, em vez de retângulos planos.

### 16.3 O que ficou de fora, e por quê

- **21–30 (os ícones quadrados).** Chegaram a ser usados como cápsulas e **foram removidos**:
  os dez são o mesmo quadrado arredondado mudando só de cor, então não dizem nada sobre o
  efeito. O jogador via uma cápsula verde caindo e não sabia se era bandeja, canhão ou
  pontos. Uma cápsula precisa **dizer o nome**, não apenas marcar a polaridade — ver 16.4.
- **31–57 (as pílulas de HUD).** Elas têm valores gravados na imagem (`+50`, `+250`), e o
  placar do jogo é dinâmico: 10 × multiplicadores × bônus de sequência, de 10 a ~1.600. Usar
  a pílula errada seria pior que não usar nenhuma — mostraria `+50` num acerto de 800. O
  placar flutuante (§14.5) é desenhado com texto próprio.
- **Não existe sprite de bandeja.** 56 e 57 são barras de HUD, não uma bandeja. Ela segue
  desenhada por primitiva, e isso não é uma perda: é a peça que precisa ser lida de relance,
  e uma barra chapada com brilho faz isso melhor que uma textura.
- **Não existe sprite de invasor nem de projétil.** Seguem desenhados.

### 16.4 Interface: o que mudou para ficar mais claro

O pedido era que o jogador entendesse o que está acontecendo. Estas mudanças atacam isso:

**Ícones no lugar de palavras — mas só onde o ícone é óbvio.** Uma estrela e N corações
comunicam "pontos" e "vidas" mais rápido que "PONTOS 000558 · VIDAS 3", e liberam ~120 px de
HUD. Numa cápsula, o mesmo raciocínio não vale: os ícones do pack não têm significado (16.3),
então lá voltou o **texto**.

**Cada modificador tem dois nomes.** `short` é o que aparece na cápsula, que cai rápido no
meio de um rebate: curto, mas **em português e dizendo o efeito** — `BANDEJA`, `CANHAO`,
`INVERTE`, `RAPIDAS`, `INVASORES`, `2 BOLAS`, `PONTOS x2`. `hud` é o que aparece no chip,
onde há espaço e tempo de leitura. Antes a cápsula mostrava siglas em inglês e depois um
ícone mudo; agora diz o nome.

**A cápsula é uma pílula com três informações.** Fundo escuro, borda e faixa na cor da
polaridade (verde pega, vermelho evita) e o **nome do efeito** no centro. A cor responde
"pego ou não pego" em um relance; o texto responde "o que exatamente é isso".

**A coleta se anuncia.** Quando a cápsula é pega, o nome sobe da bandeja em texto grande na
cor da polaridade: `BANDEJA`, `INVERTIDO`, `4 BOLAS`. É o momento em que o jogador está
olhando para a bandeja, então é onde a informação tem que aparecer.

**A barra de efeitos tem teto medido.** Modificadores e eventos dividem a linha 2 do HUD, e
o pior caso (4 modificadores + 2 eventos + o resumo da direita) foi medido num teste: 802 px
de chips não cabiam em 729 px disponíveis. Os nomes dos chips de evento foram encurtados para
`CAPSULAS` e `REDE`, o que trouxe o pior caso para dentro do limite — e existe uma guarda
que para de desenhar chips em vez de empilhá-los sobre o resumo. O nome completo continua
sendo anunciado pelo letreiro quando o evento começa.

### 16.5 A regra: sem assets, o jogo roda

Nenhuma entidade **exige** um sprite. `SpriteSheet.available` é falso quando o atlas não
existe ou não carrega, e nesse caso cada `draw` cai de volta no desenho por primitiva. Isso
mantém os testes headless rodando sem assets, torna a integração reversível e transforma um
arquivo corrompido em "menos bonito" em vez de "quebrado".

Os sprites são buscados **uma vez por linha de tijolo**, não por tijolo, e ficam em cache
por (índice, largura, altura): a grade inteira compartilha 14 superfícies em vez de 154.

---

## 17. Menus, ajustes e placar

### 17.1 As telas

O jogo abre na **tela inicial**, não numa partida. Ela mostra o título, quatro itens
navegáveis e os cinco melhores resultados ao lado — o placar só importa se estiver onde o
jogador esbarra nele.

| Tela | Onde aparece | Itens |
| --- | --- | --- |
| `MAIN` | ao abrir e depois de abandonar | JOGAR, PLACAR, AJUSTES, SAIR |
| `PAUSED` | ESC ou P durante a partida | CONTINUAR, AJUSTES, RECOMECAR, ABANDONAR |
| `SETTINGS` | a partir de qualquer uma das duas | 7 ajustes + Voltar |
| `SCORES` | a partir das duas | o placar completo |

**A pausa é um menu, não um aviso.** A versão anterior desenhava "PAUSA" por cima do jogo e
escondia os controles numa lista de texto. Agora ela tem itens de verdade, e o ESC dentro do
jogo **pausa** em vez de sair: a única forma de abandonar uma partida é escolhendo ABANDONAR,
então não se perde progresso por apertar ESC sem querer.

**Voltar lembra de onde veio.** `Menu.return_to` guarda a tela de origem, então abrir AJUSTES
no meio de uma partida devolve para a pausa, e não para a tela inicial.

### 17.2 Navegação

A mesma linguagem do jogo, para não criar dois teclados mentais:

| Tecla | Ação |
| --- | --- |
| `W` / `↑` e `S` / `↓` | andar pela lista |
| `A` / `←` e `D` / `→` | mexer no valor do item atual |
| `ENTER` / `ESPAÇO` | confirmar; num interruptor, alterna |
| `ESC` | voltar uma tela; na tela inicial, sair |

O `menu.py` **não importa pygame**. Ele decide o que está na tela e o que cada tecla faz;
quem desenha é o `game.py`. A separação existe para que a navegação (andar, envolver no fim
da lista, ajustar um valor com limite, voltar para a origem) possa ser testada sem abrir
janela — e ela é testada em detalhe (§19).

`Menu.activate()` devolve a **intenção** e não executa a troca de tela. Quem troca é o `Game`,
porque só ele sabe quais efeitos colaterais acompanham a troca — gravar os ajustes ao sair
deles, por exemplo. A primeira versão chamava `back()` por dentro e saía da tela de ajustes
**sem gravar**, o que só apareceu quando um teste conferiu o arquivo em disco.

### 17.3 Ajustes

| Ajuste | Padrão | Efeito |
| --- | --- | --- |
| Musica | ligada | toca a trilha em laço |
| Volume da musica | 45 % | volume só da trilha |
| Efeitos | ligados | liga/desliga todos os sons |
| Volume dos efeitos | 70 % | master dos efeitos |
| Particulas | ligadas | se desligado, nada solta fragmento |
| Tremor de tela | ligado | se desligado, nada treme |
| Teclas de teste | ligadas | as teclas `1` a `7`, `E` e `0` |

**Volume tem dois níveis, e isso não é capricho.** O master vai no `Sound`; o balanço de cada
evento vai no **canal**. Cinco eventos (parede, tijolo, tiro, bandeja, invasor) caem no mesmo
`ball_sound`, e `Sound.set_volume` é propriedade do objeto: escrever o balanço de um apagaria
o dos outros, e o último a escrever venceria para todos. Como cada evento tem canal próprio,
o canal é o lugar certo — o mixer multiplica os dois, então o resultado é master × balanço.

Esse bug existia desde que o áudio foi escrito e só apareceu quando um teste conferiu o volume
de dois eventos que compartilham arquivo (§19).

Partículas, tremor e teclas de teste **não precisam ser propagados**: são consultados no
momento do uso, então mudar o ajuste já vale no próximo quadro. Só áudio precisa ser
empurrado, porque volume é propriedade de objeto de mixer.

### 17.4 Placar de líderes

Oito posições, gravadas em `save/highscores.json`. Cada entrada guarda **pontuação e fase**,
porque sozinhos os pontos não dizem se a partida foi boa: 4.000 pontos na fase 2 é melhor que
4.000 na fase 5.

Ao terminar uma partida a pontuação entra automaticamente se couber, e a tela de fim de jogo
diz em que lugar ficou — `NOVO RECORDE — 3o lugar` — com as cinco melhores logo abaixo para
comparação imediata. Abandonar uma partida **não** registra nada: só o fim de jogo real conta.

### 17.5 Persistência: falhar para o padrão, nunca para o erro

`store.py` lê e grava JSON com a mesma regra do áudio e dos sprites: **um arquivo ruim não
pode derrubar o jogo**.

- Arquivo ausente, ilegível, corrompido ou que não seja um objeto: devolve o padrão.
- Campo com tipo errado: aquele campo volta ao padrão, o resto é preservado.
- Entrada de placar malformada: é descartada, as outras ficam.
- A gravação é atômica (arquivo temporário + `os.replace`), então um desligamento no meio do
  salvamento não deixa um JSON pela metade.

Um jogador não tem como consertar um arquivo que ele nunca viu, então a única resposta útil é
ignorar o problema e continuar.

### 17.6 Os testes não encostam no save do jogador

`tests/harness.py` aponta `config.SAVE_DIR` para um diretório temporário antes de qualquer
teste rodar. Sem isso, uma suíte que simula um fim de jogo gravaria a pontuação do teste no
placar de quem está jogando — o que **aconteceu de verdade**: o placar ficou com oito entradas
idênticas de 9.035 pontos antes desta linha existir.

---

## 18. Balanceamento

### Estado atual (Milestones 1 a 7)

| Constante | Valor |
| --- | --- |
| Janela | 960 × 720 px · 60 FPS |
| HUD | 80 px de altura (duas linhas) |
| Parede | 12 px de espessura |
| Campo de jogo | 936 × 616 px (base aberta) |
| Bandeja | 116 × 16 px, 680 px/s, 46 px do fundo |
| Bola | raio 9 px, 430 px/s, ângulo de saque ±18° |
| Grade | 7 × 11 = 77 tijolos, 26 px de altura, vão de 6 px |
| Tijolos resistentes | 2 linhas do topo, 2 de vida |
| Vidas | 3 |
| Pontos | 10 por acerto · 100 por tijolo × resistência |

### Modificadores

| Constante | Valor |
| --- | --- |
| Teto de bolas em jogo | 8 |
| Fatores do Multiplicador de Bolas | 2 / 4 / 6 / 8, pesos 50 / 28 / 14 / 8 |
| Abertura do leque por clone | 26° |
| Multiplicador de Pontos | ×2 por coleta, teto 8x (3 acúmulos) |
| Bandeja Grande | ×1,25 por acúmulo, teto 3 acúmulos (×1,75), 20 s |
| Canhão | 8 tiros por coleta, teto 40, cadência 0,22 s, projétil a 980 px/s |
| Bolas Super Rápidas | ×1,85, teto 2 acúmulos (×3,42), 8 s |
| Inversão dos Comandos | 8 s |
| Invasores | 12 s, um a cada 2,4 s, no máximo 4 vivos, 92 px/s |
| Chance de cápsula | 18 %, piedade em 12 tijolos, no máximo 4 na tela |
| Velocidade da cápsula | 165 px/s |
| Volume do mixer | 0,70 global, por evento de 0,35 a 0,95 |

### Dinâmica de partida

| Constante | Valor |
| --- | --- |
| Recompensa de sequência | 1 cápsula garantida a cada 8 tijolos |
| Bônus da sequência | +2 % por tijolo, teto +80 % (40 tijolos) |
| Cores da sequência | normal, âmbar em 12, vermelho em 24 |
| Intervalo entre eventos | 15 a 25 s (o primeiro em 9 s) |
| Duração do letreiro | 2,6 s |
| Eventos no catálogo | 7 (4 bons, 3 ameaças) |
| Rampa de limpeza | +12 % de velocidade com a grade vazia |
| Reta final | dispara com 5 tijolos, 3 bolas, +15 % de velocidade |
| Partículas por tijolo | 8, teto de 420 na tela |
| Tremor | 1,5 (tijolo) / 2,4 (bandeja) / 9 (vida) / decai a 26 px/s, teto 14 |
| Luz do apagão | raio 158 na bandeja, 116 em cada bola, 6 bandas |

### Apresentação

| Constante | Valor |
| --- | --- |
| Tijolos | 7 linhas, cada uma com um sprite próprio em 2 estados de dano |
| Bola | sprite 58, desenhado 4 px maior que o diâmetro lógico |
| Coração | sprite 60 a 20 px, um por vida |
| Estrela | sprite 59 a 22 px, ao lado do placar |
| Placar flutuante | 0,9 s de vida, sobe 54 px/s, no máximo 18 na tela |
| Escurecimento do apagão | fora da luz é (0, 0, 0) literal, sem vazamento |

### Menus e persistência

| Constante | Valor |
| --- | --- |
| Posições no placar | 8 |
| Volume da música | 45 % (padrão) |
| Volume dos efeitos | 70 % (padrão) |
| Cápsula | 88 × 26 px, texto na cor da polaridade |
| Arquivos gravados | `save/settings.json`, `save/highscores.json` |
| Escrita | atômica (temporário + `os.replace`) |

### Metas de dificuldade

| Métrica | Alvo |
| --- | --- |
| Duração da fase 1 (jogador iniciante) | 45 a 70 s |
| Duração da fase 1 (jogador experiente) | 25 a 35 s |
| Fase 10 | 60 a 90 s |
| Vidas perdidas por fase (fases 1-3) | 0,3 em média |
| Vidas perdidas por fase (fases 8-10) | 1,2 em média |
| Cápsulas por fase | 8 a 14 |
| Proporção buff/debuff sentida | levemente a favor do jogador (55/45) |

### Como ajustar

Os números de motor vivem em `src/config.py`; o conteúdo dos modificadores (efeito,
duração, peso) vive em `src/modifiers/specs.py`. A ordem de ajuste recomendada é:

1. `BALL_SPEED` — controla a dificuldade global e o ritmo; mexer aqui primeiro.
2. `PADDLE_SPEED` e `PADDLE_PRECISION_FACTOR` — controlam a sensação de domínio.
3. `BALL_MAX_BOUNCE_ANGLE_DEG` — controla o quanto a mira importa.
4. `LEVEL_SPEED_STEP` — controla a curva de 10 fases.
5. `CAPSULE_DROP_CHANCE` e `CAPSULE_BUFF_BIAS` — controlam o quanto a partida é sobre
   modificadores.
6. Só então durações e pesos individuais em `specs.py`.

Nunca ajustar duas categorias na mesma sessão de teste: o efeito fica indistinguível.

### Como testar sem depender do sorteio

Quase tudo neste jogo é sorteado, e esperar o sorteio é um péssimo jeito de testar. Com
`config.DEBUG_KEYS_ENABLED = True`:

1. `python main.py` e lance a bola.
2. Aperte **`1` a `7`** — cada tecla solta a cápsula correspondente logo acima da bandeja,
   capturada em menos de meio segundo. A ordem é a ordem de `specs.MODIFIERS`:
   `1` Bolas ×2, `2` Pontos, `3` Bandeja Grande, `4` Canhão, `5` Inversão, `6` Bolas
   Rápidas, `7` Invasores.
3. A tecla do Multiplicador de Bolas **cicla** pelos fatores: a primeira vez dá 2x, a
   segunda 4x, depois 6x e 8x. É assim que se testa o teto de 8 bolas sem depender de
   sorte.
4. Aperte **`E`** para disparar um evento aleatório na hora. Repetir a tecla passa por
   todos os sete.
5. Aperte **`0`** para limpar tudo e voltar ao estado normal.
6. **`ESC`** pausa — a pausa é um menu de verdade (§17.1), com CONTINUAR, AJUSTES,
   RECOMECAR e ABANDONAR.

Se as teclas de teste não responderem, veja o ajuste `Teclas de teste` em AJUSTES: ele pode
ter sido desligado e ficou gravado. `config.DEBUG_KEYS_ENABLED` é apenas o padrão de fábrica.

Para medir a dinâmica sem jogar, `python run_tests.py` cobre 364 comportamentos,
incluindo "todo evento do catálogo pode ser sorteado", "a sequência paga uma cápsula a cada
8 tijolos" e "o placar de líderes sobrevive a um arquivo corrompido" (§19).

---

## 19. Verificação

O jogo é validado por seis conjuntos de checagem automatizados, todos rodando em modo
headless (`SDL_VIDEODRIVER=dummy` e `SDL_AUDIODRIVER=dummy`), sem depender de olhar para a
tela nem de placa de som. **496 verificações** no total — 364 de comportamento e 132 de
documento e consistência — todas passando. Rode com `python run_tests.py` (§21).

### Física e controles — 19 verificações

Bola nasce presa; `W` lança a 430,00 px/s; `D`/`→` move a bandeja (422 → 762 px); trava
nas duas paredes (12 / 948 px); modo precisão desacelera (4,76 < 11,33 px por quadro);
38 dos 77 tijolos destruídos numa partida simulada de 6.000 quadros, com a pontuação
creditada e as vidas dentro do intervalo; drift de velocidade abaixo de 1e-10 px/s; e uma
bola a 60.000 px/s (140× a nominal) **ainda colide** em vez de atravessar.

### Renderização e layout — 36 verificações

Entidades pintadas nas coordenadas corretas (verificação pixel a pixel, não por inspeção
visual), incluindo bandeja larga, cano do canhão, projétil e as superfícies dos sprites.
Três paredes e a linha de morte visíveis, grade dentro do campo, as seis colunas do HUD sem
sobreposição e os estados de tela renderizando.

Sobre os sprites, o que se verifica: o atlas carrega com os 61 sprites, cada linha de tijolo
tem a sua própria superfície, **o sprite rachado é mais escuro que o inteiro nas 7 linhas**,
a bola e o tijolo aparecem no pixel onde dizem estar, e os ícones de HUD e de cápsula
existem. E o caminho sem assets: com um pacote vazio, o jogo desenha tudo por primitiva sem
quebrar.

### Power-ups, debuffs e áudio — 113 verificações

As que mais valem:

| Verificação | Resultado observado |
| --- | --- |
| Os 4 WAV carregam e os 10 eventos ficam ligados | nenhum evento órfão |
| Cada evento tem canal próprio | 10 canais dedicados |
| O banco degrada para silêncio sem mixer | sem exceção |
| 2x dobra as bolas e mantém a velocidade efetiva | 1 → 2 bolas, 430,0 px/s |
| Os clones abrem leque em vez de voar colados | ângulos 0° e −26° |
| Os quatro fatores (2/4/6/8) multiplicam de verdade | teto de 8 respeitado |
| O teto de 8 bolas não é ultrapassado | 8, mesmo com coletas repetidas |
| O Multiplicador de Pontos acumula 2x → 4x → 8x e para | 8x no teto |
| Um tijolo destruído paga o multiplicador | 100 × 8 = 800 |
| Um tijolo que sobrevive paga o multiplicador também | 10 × 8 = 80 |
| Bandeja Grande cresce pelo centro, não pela borda | centro fixo em 480,0 px |
| Bandeja Grande acumula e para no teto | 116 → 203 px, teto ×1,75 |
| Bandeja Grande volta ao normal quando expira | 203 → 116 px |
| Uma bandeja larga não vaza pelas paredes | travada em 12 / 948 px |
| O canhão gasta 1 munição por tiro | 5 tiros em 1,0 s |
| O canhão respeita a cadência | ~4,5 tiros/s |
| O toque que lança não gasta munição | 8 de 8 após o saque |
| Uma arma vazia não atira | 0 tiros |
| Projéteis destroem tijolos | 77 → 74 tijolos |
| Inversão troca esquerda e direita | 422 → 410,7 px apertando `D` |
| Inversão volta ao normal quando expira | direção correta de novo |
| Bolas Super Rápidas pegam as bolas já em jogo | 430,0 → 795,5 px/s |
| E devolvem a velocidade normal quando expiram | 795,5 → 430,0 px/s |
| O acúmulo de Bolas Rápidas tem teto | ×3,42 |
| Os invasores nascem no intervalo configurado | 1 após 2,4 s |
| Os invasores descem e ficam entre as paredes | 92 px/s, presos no campo |
| Um invasor na bandeja custa uma vida | 3 → 2 |
| O invasor some depois de acertar | lista limpa |
| Projéteis e bola destroem invasores | 1 → 0 |
| Um invasor que passa do fundo é limpo | lista limpa |
| Perder uma vida **não** limpa os debuffs | `fast_balls` sobrevive |
| Perder uma vida limpa os buffs e a munição | `paddle_grow` e `GUN` saem |
| O acúmulo de pontos sobrevive à morte e à fase | 4x mantido |
| A taxa de queda bate com o configurado | 20 % em 4.000 sorteios |
| Nenhuma seca passa do limite da piedade | maior seca = 12 |
| Nenhum debuff nos 8 primeiros tijolos | 400 sorteios, 0 debuffs |
| A proporção buff/debuff se mantém | 61 % de buffs |
| Um efeito já ativo não é sorteado de novo | 300 sorteios |
| Um efeito no teto não é sorteado de novo | bolas e pontos |
| Uma cápsula perdida sai de cena sozinha | ninguém fica órfão |
| 60 s de partida com modificadores não quebra | velocidade sempre exata |
| As chaves de efeito sempre batem com os specs | 60 s de partida |

### Dinâmica — 85 verificações

| Verificação | Resultado observado |
| --- | --- |
| A velocidade da bola é sempre exatamente a efetiva | 90 s com tudo ligado |
| Partículas nascem na posição do impacto | 1 partícula, 1 pixel conferido |
| A gravidade puxa as partículas para baixo | velocidade vertical cresce |
| Partículas mortas são removidas | 0 restantes após o tempo de vida |
| O número de partículas respeita o teto | 420, mesmo com 200 rajadas |
| O tremor não existe em repouso | deslocamento (0, 0) |
| O tremor desloca o mundo de verdade | 3+ posições distintas em 40 quadros |
| O tremor decai até sumir | 0,0 após 2 s |
| Quebrar um tijolo treme a tela | 1,5 px |
| Perder uma vida treme mais forte | 9,0 px |
| O tremor é limitado pelo teto | 14,0 px |
| Destruir um tijolo sobe a sequência | 0 → 1 → 6 |
| O bônus da sequência cresce e tem teto | ×1,80 no teto |
| A cor da sequência escala em 12 e 24 | âmbar e vermelho |
| A cada 8 tijolos vem uma cápsula garantida | 1 recompensa no 8º |
| Perder a bola zera a sequência | 9 → 0 |
| O catálogo tem eventos bons e ameaças | 4 bons + 3 ameaças |
| O primeiro evento chega aos 9 s | letreiro com nome do catálogo |
| O mesmo evento nunca repete em sequência | 200 sorteios |
| Todo evento do catálogo pode sair | os 7 aparecem |
| CHUVA DE CAPSULAS solta 5 de uma vez | 5 cápsulas |
| FRENESI DE BOLAS enche o campo | 4 bolas |
| INVASAO traz uma leva | 3 invasores |
| TIRO LIVRE arma sem munição e não gasta | 0 munição, tiros no ar |
| BOLA LOUCA acelera e tem teto | ×1,90 |
| BOLA LOUCA termina e a bola volta ao normal | efeito sai |
| A REDE DE SEGURANCA devolve a bola | velocidade vertical negativa |
| A rede custa uma vida a menos | vidas intactas |
| Sem a rede, a mesma bola é perdida | 3 → 2 vidas |
| Forçar eventos não desloca o sorteio de cápsulas | sequências idênticas |
| A rampa de limpeza sobe com a grade vazia | ×1,000 → ×1,120 |
| A RETA FINAL dispara com 5 tijolos | 3 bolas e letreiro |
| A RETA FINAL dispara uma única vez | 3 bolas mantidas |
| O APAGAO escurece o canto do campo | mais de 40 % mais escuro |
| O APAGAO deixa a bandeja e a bola iluminadas | cores originais |
| A rede é desenhada na base do campo | pixel conferido |
| O HUD tem as seis colunas sem sobreposição | medidas reais de texto |

### Interface, ajustes, placar e trilha — 109 verificações

| Verificação | Resultado observado |
| --- | --- |
| Um arquivo ausente cai no padrão | campos preenchidos |
| Um arquivo corrompido não derruba o jogo | devolve o padrão |
| Um JSON que não é objeto é recusado | devolve o padrão |
| Um campo com tipo errado volta ao padrão, o resto fica | `"sim"` → padrão, 99 → 1,0 |
| Os ajustes sobrevivem a um ciclo de gravação | todos os 7 campos |
| O placar lista do melhor para o pior | 900, 500, 100 |
| O placar é limitado a 8 posições | 8, mesmo inserindo 10 |
| Uma entrada malformada é descartada, as outras ficam | 3 entradas → 1 sobrevive |
| O jogador começa a partida no menu, não jogando | `MENU` |
| O nível já está pronto atrás do menu | 77 tijolos |
| W/S e as setas andam na lista, com volta no fim | 0 → 1 → 3 → 0 |
| Voltar lembra de onde veio | ajustes na pausa voltam para a pausa |
| Um interruptor alterna no ENTER e na seta | ligado ↔ desligado |
| Um volume tem degraus de 10 % e trava em 0 % e 100 % | 20 passos, sem passar |
| `activate()` só devolve a intenção, sem trocar de tela | `"back"` sem navegar |
| JOGAR começa uma partida | `PLAYING` |
| ESC durante a partida pausa em vez de sair | `PAUSED` |
| CONTINUAR, RECOMECAR e ABANDONAR funcionam | estado conferido |
| PLACAR e AJUSTES abrem e fecham com ESC | volta para o menu |
| Mudar um ajuste vale no mesmo quadro | volume e trilha aplicados |
| Sair dos ajustes grava em disco | arquivo conferido |
| Desligar partículas realmente para as partículas | 0 partículas |
| Desligar o tremor realmente para o tremor | deslocamento 0 |
| Religar as duas coisas as traz de volta | 8 partículas, 1,5 px |
| O fim de jogo registra a pontuação e a posição | 4.321 no 1º lugar |
| O recorde está no arquivo, não só na memória | relido do disco |
| A trilha é encontrada e não é carregada como efeito | `music_available`, fora de `library` |
| Sem trilha, o banco não finge que tem | `start_music()` devolve False |
| Começar a trilha duas vezes não reinicia a faixa | idempotente |
| O mudo rápido pausa a trilha e volta | `muted` conferido |
| O balanço por evento mora no canal, não no som | 0,50 no tijolo, 0,35 na parede |
| Dois eventos que dividem arquivo mantêm balanços diferentes | 0,500 vs 0,350 |
| Um banco desligado recusa tocar | `play()` devolve False |
| Os testes gravam num diretório descartável, não no save do jogador | `brickbreaker-test-` |
| Cada tela nova renderiza | 4 telas |
| O texto das telas cabe onde foi posto | medidas reais |

### Empacotamento

O `build.py` roda o autoteste **dentro do binário**, nas duas plataformas:

| Verificação | Resultado observado |
| --- | --- |
| O documento tem o nome e a versão do jogo | `# Quebrando Tijolos V 0.1 Beta` |
| O autoteste do binário Windows passa | 17 conferências, saída 0 |
| O autoteste do binário Linux passa | 17 conferências, saída 0 |
| Os sprites chegam ao binário | 61 recortados, 77 tijolos montados |
| Os sons chegam ao binário | 11 eventos, nenhum órfão |
| A trilha chega ao binário | `background_music_01.mp3` |
| O `save/` fica ao lado do executável | pasta gravável criada |
| As 364 verificações de comportamento passam no Linux | idênticas às do Windows |

### Documento — 132 verificações

Cada número citado neste arquivo é conferido contra `config.py` (48 constantes), as 23
seções precisam estar numeradas sem buraco, toda referência de seção precisa apontar para
uma seção que existe — a checagem pegou uma referência que na verdade era um intervalo de
sprites — e o catálogo precisa ter exatamente os 7 modificadores esperados.

### O bug que os testes pegaram

Vale registrar porque é o tipo de coisa que não aparece jogando por cinco minutos.

O teste dos invasores verificava que eles nasciam depois de 2,4 s — e eles **nunca**
nasciam. A causa não estava no spawner: a bola caía antes disso, `_lose_life()` limpava
**todos** os efeitos e a invasão era cancelada antes de começar.

Isso não era só um teste mal escrito. Era um furo no design: dava para se livrar de
qualquer debuff **de propósito**, deixando a bola cair e trocando uma vida por um efeito
ruim — e com 3 vidas isso é barato. A correção está em §11.4.

---

## 20. Roadmap

| # | Milestone | Escopo | Estado |
| --- | --- | --- | --- |
| 1 | **Física e controles** | Loop com timestep fixo, física da bola, bandeja WASD/setas, grade de tijolos, pontos, vidas, fases, HUD, overlays | **Concluído** |
| 2 | **Cápsulas** | Entidade da cápsula, queda, captura, sorteio com pesos e piedade, HUD de efeitos | **Concluído** |
| 3 | **Modificadores** | `ModifierManager`, agregação de multiplicadores, 4 buffs e 3 debuffs (§11) | **Concluído** |
| 4 | **Canhão e invasores** | Projétil, munição, cadência, invasores que ameaçam a bandeja | **Concluído** |
| 5 | **Áudio** | `SoundBank`, 10 eventos ligados aos 4 WAV, canais dedicados, cooldown, mudo (§15) | **Concluído** |
| 6 | **Dinâmica** | Sequência com recompensa garantida, 7 eventos aleatórios, partículas, tremor de tela, rampa de limpeza, reta final (§14) | **Concluído** |
| 7 | **Sprites e interface** | Atlas do pack, 7 linhas de tijolo com estado de dano, bola, estrela, coração, placar flutuante (§16) | **Concluído** |
| 8 | **Menus, ajustes e trilha** | Tela inicial, pausa como menu, placar de líderes, ajustes com persistência, música em laço (§17) | **Concluído** |
| 9 | Meta | Seleção de dificuldade, semente visível, mais estatísticas na tela inicial | Planejado |
| 10 | Polimento | Transições entre fases, som próprio para tiro e coleta, curva de 10 fases, telemetria, modo infinito | Planejado |

### Fora de escopo (por decisão)

- **Multijogador** — a física determinística permitiria, mas o sistema de modificadores
  foi desenhado em torno de uma única bandeja.
- **Editor de fases** — a grade é gerada por código; um editor exigiria um formato de
  arquivo antes de o balanceamento estabilizar.
- **Controle por mouse** — o ângulo de saída por ponto de impacto é o coração da mira;
  o mouse tiraria o english e o modo precisão do jogo.

### Próximas decisões em aberto

1. **Inimigos permanentes no cenário.** É a lacuna mais visível (§14.6). Uma torre fixa na
   grade, que atira na bandeja enquanto estiver viva, daria um alvo prioritário constante e
   uma razão para o canhão existir além de acelerar a limpeza. Agora que o jogo tem ritmo, a
   ameaça constante tem onde se apoiar.
2. **Segunda fonte de cápsula.** Hoje as cápsulas vêm de tijolo destruído e da recompensa de
   sequência. Uma cápsula garantida ao limpar uma linha daria ao jogador mais um objetivo
   tático.
3. **Mais modificadores ou mais profundidade nos 7?** O catálogo cobre as mecânicas pedidas,
   mas só há um modificador de velocidade. Um "Bola Lenta" (buff) fecharia o par e testaria a
   composição de multiplicadores que já está implementada.
4. **Som próprio para tiro e coleta de debuff.** Ver §15.5: basta largar os arquivos.

---

## 21. Como executar

```bash
# 1. Ambiente virtual (opcional, recomendado)
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # Linux / macOS

# 2. Dependência
pip install -r requirements.txt

# 3. Jogar
python main.py
```

Requisito: Python 3.11 ou superior. O projeto usa `pygame-ce` (fork mantido do
`pygame`, com pacotes prontos para Python 3.14) — a API é compatível.

### Gerar os executáveis

```bash
pip install pyinstaller
python build.py
```

Gera `dist/QuebrandoTijolos.exe` no Windows ou `dist/QuebrandoTijolos` no Linux — **um
arquivo só**, com sprites e sons dentro — e em seguida **roda o autoteste dentro do
binário**, que é a única forma de saber que o pacote está completo.

**O PyInstaller não cross-compila.** O binário é sempre da plataforma onde o script roda,
então para ter os dois é preciso rodar em cada sistema. O `.github/workflows/build.yml` faz
isso automaticamente: ele roda os testes e empacota em `windows-latest` e `ubuntu-latest`,
publicando os dois artefatos (ação manual ou tag `v*`).

### Como o pacote se comporta

| | Rodando do código | Executável |
| --- | --- | --- |
| Sprites e sons | pasta do projeto | extraídos para uma pasta temporária |
| Ajustes e placar | `save/` na pasta do projeto | `save/` **ao lado do executável** |

Ao lado do executável é o que um jogador espera — dá para levar num pendrive e o save vai
junto. Se a pasta não for gravável (instalado em `/usr/bin`, por exemplo), o jogo cai para o
diretório de dados do usuário (`%APPDATA%\QuebrandoTijolos` ou `~/.local/share/QuebrandoTijolos`).
A gravabilidade é conferida na inicialização: o pior resultado possível seria o jogo rodar a
sessão inteira sem gravar nada, e o jogador perder ajustes e recordes sem aviso.

### Autoteste

```bash
dist/QuebrandoTijolos.exe --selftest      # Windows
./dist/QuebrandoTijolos --selftest        # Linux
./dist/QuebrandoTijolos --version
```

Existe porque um executável **sem console não mostra erro nenhum**: se um sprite ou o mp3
ficar de fora do pacote, o jogo simplesmente não abre e o jogador não tem o que reportar. O
autoteste carrega atlas, sons e trilha, monta uma partida, simula 120 quadros, escreve um
relatório em `save/selftest.log` e devolve um código de saída — então dá para verificar o
pacote automaticamente.

Um erro não tratado em jogo também é gravado, em `save/crash.log`.

### Armadilha conhecida ao empacotar no Linux

O PyInstaller embute o pacote numa seção ELF própria usando o `objcopy`. Se o `objcopy` do
`PATH` for mais antigo que a `libbfd` instalada, ele não inicia — ou pior, inicia e falha no
meio. Aconteceu neste projeto dentro do WSL, onde um `~/bin/objcopy` de 2024 sombreava o
binutils 2.46 do sistema. A verificação é simples:

```bash
objcopy --version                                  # precisa responder
objcopy --add-section pydata=/etc/hostname /bin/true   # precisa não falhar
```

Se falhar, ponha `/usr/bin` na frente no `PATH` antes de empacotar.

### Testes automatizados

```bash
python run_tests.py
```

Seis suítes independentes, cada uma em seu próprio processo:

| Arquivo | Cobre |
| --- | --- |
| `tests/test_physics.py` | Física da bola e controles do jogador |
| `tests/test_layout.py` | Renderização, sprites, layout do HUD e enquadramento |
| `tests/test_powerups.py` | Modificadores, debuffs, sorteio de cápsulas e áudio |
| `tests/test_dynamics.py` | Partículas, tremor, sequência, eventos e reta final |
| `tests/test_ui.py` | Telas, ajustes, placar de líderes, persistência e trilha |
| `tests/test_design_doc.py` | Consistência deste documento com o código |

Todas rodam em modo headless (`SDL_VIDEODRIVER=dummy` e `SDL_AUDIODRIVER=dummy`), então
não abrem janela, não fazem barulho e não precisam de pytest nem de placa de som. O
`tests/harness.py` ainda aponta `SAVE_DIR` para um diretório temporário, para que os testes
nunca escrevam no save de quem está jogando (§17.6). Saída típica:

```
--- Física e controles ------------------------------------------
    19 verificações, 0 falhas -> ok

--- Renderização e layout ---------------------------------------
    38 verificações, 0 falhas -> ok

--- Power-ups, debuffs e áudio ----------------------------------
    113 verificações, 0 falhas -> ok

--- Dinâmica: partículas, sequência e eventos -------------------
    85 verificações, 0 falhas -> ok

--- Interface, ajustes, placar e trilha ------------------------
    109 verificações, 0 falhas -> ok

--- Documento de design -----------------------------------------
    132 verificações, 0 falhas -> ok

Todas as suítes passaram.
```

Também dá para rodar uma suíte sozinha, útil enquanto se mexe em uma área:

```bash
python tests/test_ui.py
```

### Solução de problemas

| Sintoma | Causa provável |
| --- | --- |
| `ModuleNotFoundError: No module named 'pygame'` | `pip install -r requirements.txt` |
| `ModuleNotFoundError: No module named 'src'` | Rodar de dentro de `src/`. Execute `python main.py` na raiz |
| Janela abre e fecha sozinha | `ESC` pressionado, ou exceção no console |

---

## 22. Convenções de código

- **Idioma:** identificadores em inglês, documentação e texto de UI em português.
- **Sem comentários explicativos:** o *porquê* vive em docstring e neste documento;
  o código diz o *quê*.
- **Duas tabelas de números, com papéis diferentes:** `config.py` é o **motor**
  (velocidades, tamanhos, taxas) e `specs.py` é o **conteúdo** (o que cada modificador faz,
  quanto dura, qual o peso). Um número de balanceamento novo tem que caber em uma das duas.
- **Sem `random` na física:** a simulação precisa ser reproduzível. A aleatoriedade dos
  modificadores vive num `Random` com semente própria, injetado no `ModifierManager`.
- **`physics.py` não conhece regras de jogo:** ele move corpos e relata contatos.
- **Modificadores declaram, o jogo consulta:** nenhum efeito muta a bandeja, a bola ou o
  estado da partida. Se um modificador novo precisar mutar algo, a arquitetura está errada,
  não o modificador.
- **Áudio nunca derruba o jogo:** todo caminho de som é opcional e falha para silêncio.
- **O cosmético não toca no jogo:** partículas e tremor não são lidos por nenhum outro
  sistema. Se um efeito visual mudar a jogabilidade, ele deixou de ser cosmético e virou
  modificador.
- **Nada de `random` no cosmético:** o tremor usa senoides justamente para não consumir o
  gerador de números do jogo e não deslocar a sequência de sorteios.
- **Separar simulação de render:** a lógica roda no passo fixo; o desenho roda no FPS.
- **Um arquivo, uma responsabilidade:** se um módulo precisa explicar duas coisas no
  docstring, provavelmente são dois módulos.

---

## 23. Glossário

| Termo | Significado |
| --- | --- |
| **Skin** | Folga de 0,1 px aplicada após separar dois corpos, para o contato não repetir |
| **Subpasso** | Fatia de um passo fixo, pequena o bastante para impedir atravessamento |
| **Tunneling** | Bola atravessar um tijolo sem colidir, por velocidade alta |
| **English** | Desvio no ângulo de saída causado pelo movimento da bandeja no impacto |
| **Zona de segurança** | O centro da bandeja, que sempre devolve a bola reto para cima |
| **Buffer anti-frustração** | Regras que impedem sequências de eventos injustas |
| **Piedade** | Queda de cápsula forçada após um período sem nenhuma |
| **Sequência** | Tijolos destruídos desde a última bola perdida; dá bônus de pontos e cápsula garantida |
| **Evento** | Regra global sorteada que muda o mundo por alguns segundos, sempre anunciada (§14.3) |
| **Letreiro** | O aviso grande que anuncia um evento ou a reta final |
| **Rampa de limpeza** | Aceleração gradual da bola conforme a grade esvazia |
| **Reta final** | Disparo único nos últimos 5 tijolos: mais bolas e mais velocidade |
