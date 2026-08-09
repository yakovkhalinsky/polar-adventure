import * as THREE from 'three';
import { IsometricSprite } from '../engine/IsometricSprite.ts';
import { SpriteAnimation } from '../engine/SpriteAnimation.ts';
import { TileMap } from '../engine/TileMap.ts';
import { WorldObject } from '../engine/WorldObject.ts';

export type Direction = 'up' | 'down' | 'left' | 'right';

const WALK_SPEED = 160;
const JUMP_VELOCITY = -260;
const GRAVITY_Y = 800;

const FRAME_SIZE = 128;
const SPRITE_SCALE = FRAME_SIZE * 1.25; // 160 world units.

/**
 * Player-controlled polar bear with an extended animation set:
 * 4-direction walk, swim, attack, push, and idle-breathe.
 * Respects tile and object collision.
 */
export class PolarBear {
  readonly character: IsometricSprite;
  readonly shadow: IsometricSprite;
  private animation: SpriteAnimation;

  private facing: Direction = 'down';
  private isJumping = false;
  private isPushing = false;
  private pushTimer = 0;
  private isAttacking = false;
  private attackTimer = 0;
  private jumpTime = 0;
  private groundY = 0;
  private pos = new THREE.Vector3();
  private vel = new THREE.Vector3();

  private tileMap: TileMap | null = null;
  private objects: WorldObject[] = [];

  constructor(texture: THREE.Texture) {
    const material = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      alphaTest: 0.5,
    });

    this.character = new IsometricSprite(material, SPRITE_SCALE, SPRITE_SCALE);
    this.character.sortMode = 'y';
    this.character.setPosition(0, 0, 0.5);

    this.animation = new SpriteAnimation(
      texture,
      [
        { name: 'walk-up', row: 0, frames: 4, fps: 8, loop: true },
        { name: 'walk-right', row: 1, frames: 4, fps: 8, loop: true },
        { name: 'walk-down', row: 2, frames: 4, fps: 8, loop: true },
        { name: 'walk-left', row: 3, frames: 4, fps: 8, loop: true },
        { name: 'swim', row: 4, frames: 4, fps: 6, loop: true },
        { name: 'attack', row: 5, frames: 4, fps: 10, loop: false },
        { name: 'push', row: 6, frames: 4, fps: 8, loop: true },
        { name: 'idle-breathe', row: 7, frames: 4, fps: 4, loop: true },
      ],
      4,
      8
    );

    this.animation.play('idle-breathe');

    // Ground shadow using a tiny generated texture.
    const shadowTexture = this.createShadowTexture();
    const shadowMaterial = new THREE.SpriteMaterial({
      map: shadowTexture,
      transparent: true,
      opacity: 0.35,
      depthWrite: false,
    });
    this.shadow = new IsometricSprite(shadowMaterial, 72, 28);
    this.shadow.setPosition(0, 0, 0.1);
    this.shadow.sortMode = 'y';
  }

  setCollisionContext(tileMap: TileMap, objects: WorldObject[]): void {
    this.tileMap = tileMap;
    this.objects = objects;
  }

  setPosition(x: number, y: number): void {
    this.pos.set(x, y, 0);
    this.groundY = y;
    this.character.setPosition(x, y, 0.5);
    this.shadow.setPosition(x, this.groundY, 0.1);
  }

  getPosition(): THREE.Vector3 {
    return this.pos.clone();
  }

  update(dt: number, keys: Set<string>): void {
    const seconds = dt / 1000;
    let vx = 0;
    let vy = 0;
    let moving = false;

    if (keys.has('left')) {
      vx = -WALK_SPEED;
      this.facing = 'left';
      moving = true;
    } else if (keys.has('right')) {
      vx = WALK_SPEED;
      this.facing = 'right';
      moving = true;
    }

    if (keys.has('up')) {
      vy = -WALK_SPEED;
      this.facing = 'up';
      moving = true;
    } else if (keys.has('down')) {
      vy = WALK_SPEED;
      this.facing = 'down';
      moving = true;
    }

    if (keys.has('jump') && !this.isJumping) {
      this.startJump();
    }

    if (keys.has('attack') && !this.isAttacking) {
      this.startAttack();
    }

    if (this.isJumping) {
      this.updateJump(seconds);
    }

    // Decrement one-shot timers.
    if (this.isAttacking) {
      this.attackTimer -= seconds;
      if (this.attackTimer <= 0) {
        this.isAttacking = false;
      }
    }

    if (this.isPushing) {
      this.pushTimer -= seconds;
      if (this.pushTimer <= 0) {
        this.isPushing = false;
      }
    }

    // Try to move; collision prevents entering blocked tiles/objects.
    this.vel.x = vx;
    this.vel.y = this.isJumping ? this.vel.y : vy;

    const nextX = this.pos.x + this.vel.x * seconds;
    const nextY = this.pos.y + this.vel.y * seconds;

    let movedX = false;
    let movedY = false;

    if (!this.isBlocked(nextX, this.pos.y)) {
      this.pos.x = nextX;
      movedX = true;
    } else {
      this.vel.x = 0;
    }

    if (!this.isBlocked(this.pos.x, nextY)) {
      this.pos.y = nextY;
      movedY = true;
    } else {
      this.vel.y = 0;
    }

    // If the player tried to move but got blocked, show a push animation.
    if (moving && !this.isJumping && !this.isAttacking && (!movedX || !movedY)) {
      this.isPushing = true;
      this.pushTimer = 0.25;
    }

    if (!this.isJumping) {
      this.groundY = this.pos.y;
    }

    // Animation state priority: attack > push > walk > idle.
    if (this.isAttacking) {
      this.animation.play('attack');
    } else if (this.isPushing) {
      this.animation.play('push');
    } else if (moving && !this.isJumping) {
      this.animation.play(`walk-${this.facing}`);
    } else if (!this.isJumping) {
      this.animation.play('idle-breathe');
    }

    this.animation.update(dt);

    // Character floats upward during jump (z is screen height).
    this.character.setPosition(this.pos.x, this.groundY, 0.5 + (this.groundY - this.pos.y));
    this.updateShadow();
  }

  private isBlocked(x: number, y: number): boolean {
    if (this.tileMap && this.tileMap.isBlocked(x, y)) {
      return true;
    }
    for (const obj of this.objects) {
      if (obj.blocksPoint(x, y)) {
        return true;
      }
    }
    return false;
  }

  private startJump(): void {
    this.isJumping = true;
    this.jumpTime = 0;
    this.vel.y = JUMP_VELOCITY;
  }

  private startAttack(): void {
    this.isAttacking = true;
    this.attackTimer = 0.4;
  }

  private updateJump(dt: number): void {
    this.jumpTime += dt;
    this.vel.y += GRAVITY_Y * dt;

    if (this.vel.y > 0 && this.pos.y >= this.groundY) {
      this.land();
    }
  }

  private land(): void {
    this.isJumping = false;
    this.pos.y = this.groundY;
    this.vel.y = 0;
  }

  private updateShadow(): void {
    const height = Math.max(0, this.groundY - this.pos.y);
    const scale = Math.max(0.4, Math.min(1, 1 - height / 120));
    this.shadow.setPosition(this.pos.x, this.groundY, 0.1);
    this.shadow.setSize(72 * scale, 28 * scale);
    this.shadow.setOpacity(0.35 * scale);
  }

  private createShadowTexture(): THREE.Texture {
    const canvas = document.createElement('canvas');
    canvas.width = 128;
    canvas.height = 48;
    const ctx = canvas.getContext('2d')!;
    const grad = ctx.createRadialGradient(64, 24, 4, 64, 24, 60);
    grad.addColorStop(0, 'rgba(0,0,0,0.45)');
    grad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 128, 48);

    const texture = new THREE.CanvasTexture(canvas);
    texture.magFilter = THREE.NearestFilter;
    texture.minFilter = THREE.NearestFilter;
    return texture;
  }
}
