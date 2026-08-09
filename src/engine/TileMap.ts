import * as THREE from 'three';
import { IsometricSprite } from './IsometricSprite.ts';

export type TileType = 'snow' | 'ice' | 'iceCracks' | 'water';

export interface Tile {
  col: number;
  row: number;
  x: number;
  y: number;
  type: TileType;
  blocked: boolean;
  sprite: IsometricSprite;
}

export interface TileMapOptions {
  size: number;
  tileWidth: number;
  tileHeight: number;
  textures: Record<TileType, THREE.Texture>;
}

/**
 * Builds a runtime isometric diamond tile grid from a few repeating textures.
 * Each tile is a billboard Sprite so it always faces the camera. Tiles can be
 * marked as blocked (water, cliffs, objects) for collision.
 */
export class TileMap {
  readonly tiles: Tile[] = [];
  readonly grid: Tile[][] = [];
  readonly bounds = new THREE.Box2();

  private tileWidth: number;
  private tileHeight: number;
  private textures: Record<TileType, THREE.Texture>;

  constructor(options: TileMapOptions) {
    this.tileWidth = options.tileWidth;
    this.tileHeight = options.tileHeight;
    this.textures = options.textures;

    const half = Math.floor(options.size / 2);

    for (let row = 0; row < options.size; row++) {
      const gridRow: Tile[] = [];
      for (let col = 0; col < options.size; col++) {
        const { x, y } = this.cartesianToIsometric(col - half, row - half);
        const type = this.pickTileType(row, col);
        const texture = this.prepareTexture(type);

        const material = new THREE.SpriteMaterial({
          map: texture,
          transparent: true,
          alphaTest: 0.5,
          depthWrite: false,
        });
        const sprite = new IsometricSprite(
          material,
          options.tileWidth,
          options.tileHeight
        );
        sprite.setPosition(x, y, 0);
        sprite.sortMode = 'y';

        const tile: Tile = {
          col,
          row,
          x,
          y,
          type,
          blocked: type === 'water',
          sprite,
        };

        this.tiles.push(tile);
        gridRow.push(tile);

        this.bounds.expandByPoint(
          new THREE.Vector2(x - options.tileWidth / 2, y - options.tileHeight / 2)
        );
        this.bounds.expandByPoint(
          new THREE.Vector2(x + options.tileWidth / 2, y + options.tileHeight / 2)
        );
      }
      this.grid.push(gridRow);
    }
  }

  addTo(parent: THREE.Object3D): void {
    for (const tile of this.tiles) {
      parent.add(tile.sprite.sprite);
    }
  }

  removeFrom(parent: THREE.Object3D): void {
    for (const tile of this.tiles) {
      parent.remove(tile.sprite.sprite);
    }
  }

  /**
   * Return the tile under a world-space position, or null if outside the grid.
   */
  getTileAt(worldX: number, worldY: number): Tile | null {
    const half = Math.floor(this.grid.length / 2);
    // Inverse of cartesianToIsometric.
    const cx = (worldX / (this.tileWidth / 2) + worldY / (this.tileHeight / 2)) / 2;
    const cy = (worldY / (this.tileHeight / 2) - worldX / (this.tileWidth / 2)) / 2;
    const col = Math.round(cx + half);
    const row = Math.round(cy + half);

    if (row < 0 || row >= this.grid.length || col < 0 || col >= this.grid[0].length) {
      return null;
    }
    return this.grid[row][col];
  }

  /**
   * True if the world position is blocked by a tile (water, off-grid, etc.).
   */
  isBlocked(worldX: number, worldY: number): boolean {
    const tile = this.getTileAt(worldX, worldY);
    return !tile || tile.blocked;
  }

  cartesianToIsometric(cx: number, cy: number): { x: number; y: number } {
    return {
      x: (cx - cy) * (this.tileWidth / 2),
      y: (cx + cy) * (this.tileHeight / 2),
    };
  }

  private prepareTexture(type: TileType): THREE.Texture {
    const texture = this.textures[type];
    texture.magFilter = THREE.NearestFilter;
    texture.minFilter = THREE.NearestFilter;
    texture.wrapS = THREE.ClampToEdgeWrapping;
    texture.wrapT = THREE.ClampToEdgeWrapping;
    return texture;
  }

  private pickTileType(row: number, col: number): TileType {
    const n = (row * 3 + col * 7) % 10;
    if (n === 0) return 'iceCracks';
    if (n < 4) return 'ice';
    return 'snow';
  }
}
