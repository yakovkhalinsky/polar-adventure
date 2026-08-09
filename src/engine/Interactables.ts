import * as THREE from 'three';
import { WorldObject, WorldObjectOptions } from './WorldObject.ts';
import { SpriteAnimation } from './SpriteAnimation.ts';

export interface NPCOptions extends Omit<WorldObjectOptions, 'blocked' | 'blockRadius'> {
  name: string;
  lines: string[];
}

/**
 * Friendly NPC that the player can talk to. Does not block movement.
 * Supports a subtle idle spritesheet animation.
 */
export class NPC extends WorldObject {
  readonly name: string;
  readonly lines: string[];
  private animation: SpriteAnimation;
  private baseY = 0;
  private bobTime = 0;

  constructor(options: NPCOptions) {
    super({ ...options, blocked: false });
    this.name = options.name;
    this.lines = options.lines;
    this.sprite.sortMode = 'y';
    this.baseY = options.y;

    // Default 4-frame idle row at the bottom of the texture if not specified.
    this.animation = new SpriteAnimation(
      (this.sprite.sprite.material as THREE.SpriteMaterial).map as THREE.Texture,
      [
        { name: 'idle', row: 0, frames: 4, fps: 4, loop: true, direction: 'pingpong' },
      ],
      4,
      1
    );
    this.animation.play('idle');
  }

  update(dt: number): void {
    this.animation.update(dt);
    // Gentle bob for liveliness even on a single-frame sprite.
    this.bobTime += dt / 1000;
    const bob = Math.sin(this.bobTime * 2.5) * 2;
    this.sprite.setPosition(this.position.x, this.baseY + bob, 0.5 + bob * 0.01);
  }
}

export interface CollectibleOptions extends Omit<WorldObjectOptions, 'blocked' | 'blockRadius'> {
  value?: number;
}

/**
 * Pick-up item that disappears when the player touches it.
 * Slowly bobs and spins for visual interest.
 */
export class Collectible extends WorldObject {
  value: number;
  collected = false;
  private baseY = 0;
  private time = 0;

  constructor(options: CollectibleOptions) {
    super({ ...options, blocked: false });
    this.value = options.value ?? 1;
    this.sprite.sortMode = 'y';
    this.baseY = options.y;
  }

  collect(): number {
    this.collected = true;
    return this.value;
  }

  update(dt: number): void {
    this.time += dt / 1000;
    const bob = Math.sin(this.time * 2.2) * 4;
    const wobble = Math.cos(this.time * 1.7) * 3;
    this.sprite.setPosition(this.position.x + wobble, this.baseY + bob, 0.5 + bob * 0.01);
  }
}

export interface InteractableOptions extends Omit<WorldObjectOptions, 'blocked' | 'blockRadius'> {
  label: string;
  action?: () => void;
}

/**
 * Decorative structure or sign that shows a message when the player
 * interacts with it. Supports a subtle idle sparkle/sway.
 */
export class Interactable extends WorldObject {
  readonly label: string;
  readonly action?: () => void;
  private baseY = 0;
  private time = 0;

  constructor(options: InteractableOptions) {
    super({ ...options, blocked: true, blockRadius: Math.max(options.width, options.height) * 0.3 });
    this.label = options.label;
    this.action = options.action;
    this.sprite.sortMode = 'y';
    this.baseY = options.y;
  }

  update(dt: number): void {
    this.time += dt / 1000;
    const sway = Math.sin(this.time * 1.2) * 1.5;
    this.sprite.setPosition(this.position.x + sway, this.baseY, 0.5);
  }
}
