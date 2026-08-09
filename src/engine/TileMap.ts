import * as THREE from 'three';
import { IsometricSprite } from './IsometricSprite.ts';

export interface TileMapOptions {
  size: number;
  tileWidth: number;
  tileHeight: number;
  textures: {
    snow: THREE.Texture;
    ice: THREE.Texture;
    iceCracks: THREE.Texture;
  };
}

/**
 * Builds a runtime isometric diamond tile grid from a few repeating textures.
 * Each tile is a billboard Sprite so it always faces the camera and the diamond
 * artwork stays pixel-perfect.
 */
export class TileMap {
  readonly tiles: IsometricSprite[] = [];
  readonly bounds = new THREE.Box2();

  private tileWidth: number;
  private tileHeight: number;
  private textures: TileMapOptions['textures'];

  constructor(options: TileMapOptions) {
    this.tileWidth = options.tileWidth;
    this.tileHeight = options.tileHeight;
    this.textures = options.textures;

    const half = Math.floor(options.size / 2);

    for (let row = 0; row < options.size; row++) {
      for (let col = 0; col < options.size; col++) {
        const { x, y } = this.cartesianToIsometric(
          col - half,
          row - half
        );

        const texture = this.pickTexture(row, col);
        texture.magFilter = THREE.NearestFilter;
        texture.minFilter = THREE.NearestFilter;
        texture.wrapS = THREE.ClampToEdgeWrapping;
        texture.wrapT = THREE.ClampToEdgeWrapping;

        const material = new THREE.SpriteMaterial({
          map: texture,
          transparent: true,
          alphaTest: 0.5,
          depthWrite: false,
        });
        const tile = new IsometricSprite(
          material,
          options.tileWidth,
          options.tileHeight
        );
        tile.setPosition(x, y, 0);
        tile.sortMode = 'y';

        this.tiles.push(tile);

        this.bounds.expandByPoint(
          new THREE.Vector2(x - options.tileWidth / 2, y - options.tileHeight / 2)
        );
        this.bounds.expandByPoint(
          new THREE.Vector2(x + options.tileWidth / 2, y + options.tileHeight / 2)
        );
      }
    }
  }

  addTo(parent: THREE.Object3D): void {
    for (const tile of this.tiles) {
      parent.add(tile.sprite);
    }
  }

  removeFrom(parent: THREE.Object3D): void {
    for (const tile of this.tiles) {
      parent.remove(tile.sprite);
    }
  }

  cartesianToIsometric(cx: number, cy: number): { x: number; y: number } {
    return {
      x: (cx - cy) * (this.tileWidth / 2),
      y: (cx + cy) * (this.tileHeight / 2),
    };
  }

  private pickTexture(row: number, col: number): THREE.Texture {
    const n = (row * 3 + col * 7) % 10;
    if (n === 0) return this.textures.iceCracks;
    if (n < 4) return this.textures.ice;
    return this.textures.snow;
  }
}
