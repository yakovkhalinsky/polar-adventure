import * as THREE from 'three';
import { GameSprite } from '../engine/GameSprite.ts';
import { SpriteAnimation } from '../engine/SpriteAnimation.ts';
import { PlatformTileMap } from '../engine/PlatformTileMap.ts';
import { WorldObject } from '../engine/WorldObject.ts';
import { DecalSystem } from '../engine/DecalSystem.ts';

export type Facing = 'left' | 'right';

const WALK_SPEED = 220;
const JUMP_VELOCITY = -520;
const GRAVITY = 1600;
const FALL_GRAVITY = 1800;

const FRAME_SIZE = 128;
const SPRITE_SCALE = FRAME_SIZE * 1.25; // 160 world units.

/**
 * Player-controlled polar bear for a 2D side-scrolling platformer.
 * Moves left/right, jumps on solid tiles, and respects object collision.
 */
export class PolarBear {
  readonly character: GameSprite;
  readonly shadow: GameSprite;
  private animation: SpriteAnimation;

  private facing: Facing = 'right';
  private isJumping = false;
  private isAttacking = false;
  private attackTimer = 0;
  private coyoteTimer = 0;
  private pos = new THREE.Vector3();
  private vel = new THREE.Vector3();

  private tileMap: PlatformTileMap | null = null;
  private objects: WorldObject[] = [];
  private decalSystem: DecalSystem | null = null;
  private footstepAccumulator = 0;

  constructor(texture: THREE.Texture) {
    const material = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      alphaTest: 0.5,
    });

    this.character = new GameSprite(material, SPRITE_SCALE, SPRITE_SCALE);
    this.character.setPosition(0, 0, 0.5);

    // Current polar-bear.png is a 4x4 sheet:
    // row 0 = walk-up, row 1 = walk-right, row 2 = walk-down, row 3 = walk-left.
    // For the side-scrolling pivot we only need left/right rows plus an idle pose.
    this.animation = new SpriteAnimation(
      texture,
      [
        { name: 'idle', row: 2, frames: 4, fps: 4, loop: true, direction: 'pingpong' },
        { name: 'walk-right', row: 1, frames: 4, fps: 10, loop: true },
        { name: 'walk-left', row: 3, frames: 4, fps: 10, loop: true },
        { name: 'jump', row: 1, frames: 1, fps: 1, loop: true },
        { name: 'attack', row: 2, frames: 4, fps: 10, loop: false },
      ],
      4,
      4
    );

    this.animation.play('idle');

    const shadowTexture = this.createShadowTexture();
    const shadowMaterial = new THREE.SpriteMaterial({
      map: shadowTexture,
      transparent: true,
      opacity: 0.35,
      depthWrite: false,
    });
    this.shadow = new GameSprite(shadowMaterial, 72, 28);
    this.shadow.setPosition(0, 0, 0.1);
  }

  setCollisionContext(tileMap: PlatformTileMap, objects: WorldObject[]): void {
    this.tileMap = tileMap;
    this.objects = objects;
  }

  setDecalSystem(system: DecalSystem): void {
    this.decalSystem = system;
  }

  setPosition(x: number, y: number): void {
    this.pos.set(x, y, 0);
    this.character.setPosition(x, y, 0.5);
    this.shadow.setPosition(x, y, 0.1);
  }

  getPosition(): THREE.Vector3 {
    return this.pos.clone();
  }

  update(dt: number, keys: Set<string>): void {
    const seconds = dt / 1000;
    let vx = 0;
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

    if (keys.has('jump') && !this.isJumping) {
      if (this.coyoteTimer > 0 || this.onGround()) {
        this.startJump();
      }
    }

    if (keys.has('attack') && !this.isAttacking) {
      this.startAttack();
    }

    // Apply horizontal velocity and resolve wall collisions.
    this.vel.x = vx;
    const nextX = this.pos.x + this.vel.x * seconds;
    if (!this.isBlocked(nextX, this.pos.y)) {
      this.pos.x = nextX;
    } else {
      this.vel.x = 0;
    }

    // Apply gravity and vertical movement.
    const gravity = this.vel.y > 0 ? FALL_GRAVITY : GRAVITY;
    this.vel.y += gravity * seconds;
    const nextY = this.pos.y + this.vel.y * seconds;

    if (this.vel.y > 0 || this.vel.y < 0) {
      // Moving up or down: check for ceilings/floors.
      if (!this.isBlocked(this.pos.x, nextY)) {
        this.pos.y = nextY;
      } else {
        // Hit something. If falling, snap to ground.
        if (this.vel.y > 0) {
          const ground = this.tileMap?.groundHeightAt(this.pos.x) ?? null;
          if (ground != null && this.pos.y <= ground + 1) {
            this.land(ground);
          } else {
            this.vel.y = 0;
          }
        } else {
          // Bonked head on ceiling.
          this.vel.y = 0;
        }
      }
    }

    // Make sure we still land when gravity settles exactly on a surface.
    if (!this.isJumping && this.vel.y >= 0) {
      const ground = this.tileMap?.groundHeightAt(this.pos.x) ?? null;
      if (ground != null && this.pos.y >= ground - 1 && this.pos.y <= ground + 1) {
        this.land(ground);
      }
    }

    // Track coyote time for forgiving jumps.
    if (this.onGround()) {
      this.coyoteTimer = 0.08;
    } else {
      this.coyoteTimer = Math.max(0, this.coyoteTimer - seconds);
    }

    // Decrement one-shot timers.
    if (this.isAttacking) {
      this.attackTimer -= seconds;
      if (this.attackTimer <= 0) {
        this.isAttacking = false;
      }
    }

    // Footprints while walking on ground.
    if (moving && !this.isJumping) {
      const dist = Math.abs(this.vel.x) * seconds;
      this.footstepAccumulator += dist;
      if (this.footstepAccumulator >= 45) {
        this.footstepAccumulator -= 45;
        this.decalSystem?.spawnFootprint(this.pos.x, this.pos.y, this.facing === 'right' ? 0 : Math.PI);
      }

      const tile = this.tileMap?.tiles.find((t) => {
        const left = t.x - t.width / 2;
        const right = t.x + t.width / 2;
        return this.pos.x >= left && this.pos.x <= right && Math.abs(t.y - this.pos.y) < 2;
      });
      if (tile?.type === 'iceCracks' && Math.random() < 0.06) {
        this.decalSystem?.spawnDust(this.pos.x, this.pos.y, 2);
      }
    }

    // Animation state priority: attack > jump > walk > idle.
    if (this.isAttacking) {
      this.animation.play('attack');
    } else if (this.isJumping) {
      this.animation.play('jump');
    } else if (moving) {
      this.animation.play(`walk-${this.facing}`);
    } else {
      this.animation.play('idle');
    }

    this.animation.update(dt);

    // Visual flip so left/right rows face the correct way even if the sheet
    // orientation is inconsistent.
    this.character.flipX(this.facing === 'left');

    this.character.setPosition(this.pos.x, this.pos.y, 0.5);
    this.updateShadow();
  }

  private onGround(): boolean {
    const ground = this.tileMap?.groundHeightAt(this.pos.x);
    if (ground === null || ground === undefined) return false;
    return Math.abs(this.pos.y - ground) <= 1;
  }

  private isBlocked(x: number, y: number): boolean {
    if (this.tileMap?.isSolidAt(x, y)) {
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
    this.vel.y = JUMP_VELOCITY;
  }

  private startAttack(): void {
    this.isAttacking = true;
    this.attackTimer = 0.4;
  }

  private land(groundY: number): void {
    this.isJumping = false;
    this.pos.y = groundY;
    this.vel.y = 0;
  }

  private updateShadow(): void {
    const ground = this.tileMap?.groundHeightAt(this.pos.x);
    const height = ground !== null && ground !== undefined ? Math.max(0, this.pos.y - ground) : 0;
    const scale = Math.max(0.4, Math.min(1, 1 - height / 160));
    this.shadow.setPosition(this.pos.x, this.pos.y, 0.1);
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
