import * as THREE from 'three';
import { GameSprite } from './GameSprite.ts';

export interface WorldObjectOptions {
  x: number;
  y: number;
  z?: number;
  width: number;
  height: number;
  texture: THREE.Texture;
  blocked?: boolean;
  /** Grid radius this object blocks around its center. */
  blockRadius?: number;
}

/**
 * A generic billboard object placed in the side-scrolling world: rocks,
 * trees, signs, NPCs, collectibles. Can block movement.
 */
export class WorldObject {
  readonly sprite: GameSprite;
  readonly position: THREE.Vector3;
  readonly blocked: boolean;
  readonly blockRadius: number;
  readonly width: number;
  readonly height: number;

  constructor(options: WorldObjectOptions) {
    this.position = new THREE.Vector3(options.x, options.y, options.z ?? 0);
    this.width = options.width;
    this.height = options.height;
    this.blocked = options.blocked ?? true;
    this.blockRadius = options.blockRadius ?? Math.max(options.width, options.height) * 0.25;

    const material = new THREE.SpriteMaterial({
      map: options.texture,
      transparent: true,
      alphaTest: 0.5,
      depthWrite: false,
    });
    this.sprite = new GameSprite(material, options.width, options.height);
    this.sprite.setPosition(options.x, options.y, options.z ?? 0.5);
  }

  /**
   * True if a point is inside this object's blocking footprint.
   */
  blocksPoint(x: number, y: number): boolean {
    if (!this.blocked) return false;
    const dx = x - this.position.x;
    const dy = y - this.position.y;
    return Math.sqrt(dx * dx + dy * dy) <= this.blockRadius;
  }
}
