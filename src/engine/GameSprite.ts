import * as THREE from 'three';

/**
 * A simple billboard sprite for a 2D side-scrolling game. Three.js Sprites
 * always face the camera, so they work perfectly for flat characters and
 * objects in a straight-on orthographic scene.
 */
export class GameSprite {
  readonly sprite: THREE.Sprite;

  constructor(material: THREE.SpriteMaterial, width = 64, height = 64) {
    this.sprite = new THREE.Sprite(material);
    this.sprite.scale.set(width, height, 1);
    // Anchor at the bottom center so characters stand on the ground.
    this.sprite.center.set(0.5, 0);
  }

  setPosition(x: number, y: number, z = 0): void {
    this.sprite.position.set(x, y, z);
  }

  setSize(width: number, height: number): void {
    this.sprite.scale.set(width, height, 1);
  }

  setOpacity(alpha: number): void {
    this.sprite.material.opacity = alpha;
    this.sprite.material.transparent = alpha < 1;
  }

  flipX(flip: boolean): void {
    const sy = this.sprite.scale.y;
    const sx = Math.abs(this.sprite.scale.x) * (flip ? -1 : 1);
    this.sprite.scale.set(sx, sy, 1);
  }
}
