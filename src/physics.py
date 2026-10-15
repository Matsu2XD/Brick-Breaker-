"""Fisica da bola: integracao em subpassos e resolucao de colisoes.

Este modulo nao conhece regras de jogo. Ele move a bola, resolve o contato
com tijolos, raquete e paredes e devolve um relatorio do que foi tocado.
Pontuacao, vidas e modificadores ficam em ``game.py``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pygame

from src import config
from src.entities.ball import Ball
from src.entities.brick import Brick
from src.entities.paddle import Paddle


@dataclass
class CollisionReport:
    """Tudo que a bola tocou durante um passo de simulacao."""

    bricks_hit: list[Brick] = field(default_factory=list)
    paddle_hits: int = 0
    walls_hit: list[str] = field(default_factory=list)
    touched: bool = False


def move_and_collide(
    ball: Ball,
    dt: float,
    paddle: Paddle,
    bricks: list[Brick],
    floor: bool = False,
) -> CollisionReport:
    """Integra a bola por ``dt`` e resolve tudo que ela encontrar no caminho.

    O passo e dividido em subpassos de no maximo meio raio. Sem isso uma bola
    rapida atravessaria tijolos inteiros sem colidir (tunneling).

    ``floor`` fecha a base do campo, para o evento Rede de Seguranca.
    """
    report = CollisionReport()
    distance = ball.velocity.length() * dt
    max_step = ball.radius * config.MAX_SUBSTEP_RATIO
    substeps = max(1, math.ceil(distance / max_step))
    sub_dt = dt / substeps

    for _ in range(substeps):
        ball.advance(sub_dt)
        _resolve_bricks(ball, bricks, report)
        _resolve_paddle(ball, paddle, report)
        _resolve_walls(ball, report, floor)

    return report


def circle_rect_contact(
    center: pygame.Vector2,
    radius: float,
    rect: pygame.Rect,
) -> tuple[pygame.Vector2, float] | None:
    """Retorna ``(normal, penetracao)`` para expulsar o circulo do retangulo.

    ``normal`` aponta do retangulo para fora. Se não houver sobreposicao,
    devolve ``None``.
    """
    closest = pygame.Vector2(
        min(max(center.x, rect.left), rect.right),
        min(max(center.y, rect.top), rect.bottom),
    )
    offset = center - closest
    distance_sq = offset.length_squared()

    if distance_sq > radius * radius:
        return None

    if distance_sq > 1e-12:
        distance = math.sqrt(distance_sq)
        return offset / distance, radius - distance

    # Centro dentro do retangulo: sai pela face mais proxima.
    to_left = center.x - rect.left
    to_right = rect.right - center.x
    to_top = center.y - rect.top
    to_bottom = rect.bottom - center.y
    smallest = min(to_left, to_right, to_top, to_bottom)
    if smallest == to_left:
        return pygame.Vector2(-1.0, 0.0), to_left + radius
    if smallest == to_right:
        return pygame.Vector2(1.0, 0.0), to_right + radius
    if smallest == to_top:
        return pygame.Vector2(0.0, -1.0), to_top + radius
    return pygame.Vector2(0.0, 1.0), to_bottom + radius


def enforce_min_vertical(velocity: pygame.Vector2) -> pygame.Vector2:
    """Impede que a bola entre em trajetoria quase horizontal.

    Uma bola presa correndo de parede em parede e o pior estado possivel: o
    jogo nao avanca e o jogador nao tem o que fazer.
    """
    speed = velocity.length()
    if speed < 1e-6:
        return pygame.Vector2(0.0, -config.BALL_SPEED)

    direction = velocity / speed
    minimum = config.BALL_MIN_VERTICAL_FRACTION
    if abs(direction.y) >= minimum:
        return velocity

    sign_x = 1.0 if direction.x >= 0 else -1.0
    sign_y = 1.0 if direction.y > 0 else -1.0
    horizontal = math.sqrt(1.0 - minimum * minimum) * sign_x
    return pygame.Vector2(horizontal, minimum * sign_y) * speed


def _resolve_bricks(ball: Ball, bricks: list[Brick], report: CollisionReport) -> None:
    bounds = ball.rect.inflate(4, 4)
    for brick in bricks:
        if not brick.alive or not bounds.colliderect(brick.rect):
            continue

        contact = circle_rect_contact(ball.position, ball.radius, brick.rect)
        if contact is None:
            continue

        normal, penetration = contact
        if ball.velocity.dot(normal) > 0.0:
            # Ja esta saindo: apenas separa, sem refletir.
            ball.position += normal * (penetration + config.COLLISION_SKIN)
            continue

        ball.position += normal * (penetration + config.COLLISION_SKIN)
        ball.velocity = enforce_min_vertical(ball.velocity.reflect(normal))
        report.bricks_hit.append(brick)
        report.touched = True
        bounds = ball.rect.inflate(4, 4)


def _resolve_paddle(ball: Ball, paddle: Paddle, report: CollisionReport) -> None:
    if ball.attached:
        return

    contact = circle_rect_contact(ball.position, ball.radius, paddle.rect)
    if contact is None:
        return

    normal, penetration = contact
    if ball.velocity.y <= 0.0:
        # Bateu de lado ou por baixo: apenas separa.
        ball.position += normal * (penetration + config.COLLISION_SKIN)
        return

    _bounce_off_paddle(ball, paddle)
    report.paddle_hits += 1
    report.touched = True


def _bounce_off_paddle(ball: Ball, paddle: Paddle) -> None:
    """Bounce estilo Arkanoid: o ponto de impacto define o angulo de saida."""
    half_width = paddle.width / 2.0
    offset = (ball.position.x - paddle.center_x) / half_width
    offset = max(-1.0, min(1.0, offset))

    max_angle = math.radians(config.BALL_MAX_BOUNCE_ANGLE_DEG)
    angle = max_angle * offset
    direction = pygame.Vector2(math.sin(angle), -math.cos(angle))
    direction.x += (paddle.velocity_x / config.PADDLE_SPEED) * config.PADDLE_ENGLISH

    length = direction.length()
    if length < 1e-9:
        direction.update(0.0, -1.0)
        length = 1.0

    speed = max(ball.speed, config.BALL_SPEED)
    ball.velocity = enforce_min_vertical(direction * (speed / length))
    ball.position.y = paddle.rect.top - ball.radius - config.COLLISION_SKIN


def _resolve_walls(ball: Ball, report: CollisionReport, floor: bool = False) -> None:
    field_rect = config.PLAYFIELD
    bounced = False

    if ball.position.x - ball.radius < field_rect.left:
        ball.position.x = field_rect.left + ball.radius
        ball.velocity.x = abs(ball.velocity.x)
        report.walls_hit.append("left")
        bounced = True
    elif ball.position.x + ball.radius > field_rect.right:
        ball.position.x = field_rect.right - ball.radius
        ball.velocity.x = -abs(ball.velocity.x)
        report.walls_hit.append("right")
        bounced = True

    if ball.position.y - ball.radius < field_rect.top:
        ball.position.y = field_rect.top + ball.radius
        ball.velocity.y = abs(ball.velocity.y)
        report.walls_hit.append("top")
        bounced = True

    if floor and ball.position.y + ball.radius > field_rect.bottom:
        ball.position.y = field_rect.bottom - ball.radius
        ball.velocity.y = -abs(ball.velocity.y)
        report.walls_hit.append("floor")
        bounced = True

    if bounced:
        ball.velocity = enforce_min_vertical(ball.velocity)
        report.touched = True
