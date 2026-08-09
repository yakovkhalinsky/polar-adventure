import * as THREE from 'three';
import { IsometricSprite } from './IsometricSprite.ts';

type Sortable = IsometricSprite | THREE.Mesh;

/**
 * Re-orders children of a parent Object3D so sprites/meshes draw from back to
 * front in isometric order. Call once per frame after all positions are updated.
 */
export class DepthSorter {
  private parent: THREE.Object3D;

  constructor(parent: THREE.Object3D) {
    this.parent = parent;
  }

  sort(items: Sortable[]): void {
    for (const item of items) {
      if ('updateSortValue' in item) {
        item.updateSortValue();
      }
    }

    // Three.js renders children in array order. Lower sort value = further back.
    const ordered = items.slice().sort((a, b) => this.getValue(a) - this.getValue(b));

    for (let i = 0; i < ordered.length; i++) {
      const object = this.getObject(ordered[i]);
      if (this.parent.children[i] !== object) {
        this.parent.add(object);
      }
    }
  }

  private getValue(item: Sortable): number {
    if (item instanceof IsometricSprite) {
      return item.getSortValue();
    }
    return (item.userData as { sortValue?: number }).sortValue ?? item.position.y;
  }

  private getObject(item: Sortable): THREE.Object3D {
    if (item instanceof IsometricSprite) {
      return item.sprite;
    }
    return item;
  }
}
