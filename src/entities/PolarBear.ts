import * as THREE from 'three';
import { IsometricSprite } from '../engine/IsometricSprite.ts';
import { SpriteAnimation } from '../engine/SpriteAnimation.ts';

export type Direction = 'up' | 'down' | 'left' | 'right';

const WALK_SPEED = 160;
const JUMP_VELOCITY = -260;
const GRAVITY_Y = 800;

export class PolarBear {
  readonly character: IsometricSprite;
  readonly shadow: IsometricSprite;
  private animation: SpriteAnimation;

  private facing: Direction = 'down';
  private isJumping = false;
  private jumpTime = 0;
  private groundY = 0;
  private pos = new THREE.Vector3();
  private vel = new THREE.Vector3();

  constructor(texture: THREE.Texture) {
    const material = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      alphaTest: 0.5,
    });

    this.character = new IsometricSprite(material, 80, 80);
    this.character.sortMode = 'y';
    this.character.setPosition(0, 0, 0.5);

    this.animation = new SpriteAnimation(
      texture,
      [
        { name: 'idle-up', row: 0, frames: 1, fps: 1, loop: true },
        { name: 'idle-right', row: 1, frames: 1, fps: 1, loop: true },
        { name: 'idle-down', row: 2, frames: 1, fps: 1, loop: true },
        { name: 'idle-left', row: 3, frames: 1, fps: 1, loop: true },
        { name: 'walk-up', row: 0, frames: 4, fps: 8, loop: true },
        { name: 'walk-right', row: 1, frames: 4, fps: 8, loop: true },
        { name: 'walk-down', row: 2, frames: 4, fps: 8, loop: true },
        { name: 'walk-left', row: 3, frames: 4, fps: 8, loop: true },
      ],
      4,
      4
    );

    this.animation.play('idle-down');

    // Ground shadow using a tiny generated texture.
    const shadowTexture = this.createShadowTexture();
    const shadowMaterial = new THREE.SpriteMaterial({
      map: shadowTexture,
      transparent: true,
      opacity: 0.35,
      depthWrite: false,
    });
    this.shadow = new IsometricSprite(shadowMaterial, 36, 14);
    this.shadow.setPosition(0, 0, 0.1);
    this.shadow.sortMode = 'y';
  }

  setPosition(x: number, y: number): void {
    this.pos.set(x, y, 0);
    this.groundY = y;
    this.character.setPosition(x, y, 0.5);
    this.shadow.setPosition(x, this.groundY, 0.1);
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

    if (this.isJumping) {
      this.updateJump(seconds);
    }

    // Apply velocity.
    this.vel.x = vx;
    this.vel.y = this.isJumping ? this.vel.y : vy;
    this.pos.x += this.vel.x * seconds;
    this.pos.y += this.vel.y * seconds;

    if (!this.isJumping) {
      this.groundY = this.pos.y;
    }

    // Animation state.
    if (moving && !this.isJumping) {
      this.animation.play(`walk-${this.facing}`);
    } else if (!this.isJumping) {
      this.animation.play(`idle-${this.facing}`);
    }

    this.animation.update(dt);

    // Character floats upward during jump (z is screen height).
    this.character.setPosition(this.pos.x, this.groundY, 0.5 + (this.groundY - this.pos.y));
    this.updateShadow();
  }

  private startJump(): void {
    this.isJumping = true;
    this.jumpTime = 0;
    this.vel.y = JUMP_VELOCITY;
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
    this.shadow.setSize(36 * scale, 14 * scale);
    this.shadow.setOpacity(0.35 * scale);
  }

  private createShadowTexture(): THREE.Texture {
    const canvas = document.createElement('canvas');
    canvas.width = 64;
    canvas.height = 24;
    const ctx = canvas.getContext('2d')!;
    const grad = ctx.createRadialGradient(32, 12, 2, 32, 12, 30);
    grad.addColorStop(0, 'rgba(0,0,0,0.45)');
    grad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 64, 24);

    const texture = new THREE.CanvasTexture(canvas);
    texture.magFilter = THREE.NearestFilter;
    texture.minFilter = THREE.NearestFilter;
    return texture;
  }
}
