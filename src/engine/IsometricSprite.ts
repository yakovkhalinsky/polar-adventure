import * as THREE from 'three';

export type IsometricSortMode = 'y' | 'z' | 'manual';

/**
 * A billboard sprite that always faces the camera and supports isometric
 * depth sorting by world position. Three.js Sprites face the camera
 * automatically, which is ideal for characters.
 */
export class IsometricSprite {
  readonly sprite: THREE.Sprite;
  sortMode: IsometricSortMode = 'y';
  private sortValue = 0;

  constructor(material: THREE.SpriteMaterial, width = 64, height = 64) {
    this.sprite = new THREE.Sprite(material);
    this.sprite.scale.set(width, height, 1);
    this.sprite.center.set(0.5, 0);
  }

  setPosition(x: number, y: number, z = 0): void {
    this.sprite.position.set(x, y, z);
    this.updateSortValue();
  }

  setSize(width: number, height: number): void {
    this.sprite.scale.set(width, height, 1);
  }

  setOpacity(alpha: number): void {
    this.sprite.material.opacity = alpha;
    this.sprite.material.transparent = alpha < 1;
  }

  /**
   * Computes a scalar used to sort sprites/tiles so things draw in the
   * correct isometric order. Larger values draw later (on top).
   */
  updateSortValue(): void {
    const p = this.sprite.position;
    if (this.sortMode === 'y') {
      // In an isometric world with y as depth, sort by world y + z elevation.
      this.sortValue = p.y + p.z * 0.001;
    } else if (this.sortMode === 'z') {
      this.sortValue = p.z;
    }
  }

  getSortValue(): number {
    return this.sortValue;
  }
}
