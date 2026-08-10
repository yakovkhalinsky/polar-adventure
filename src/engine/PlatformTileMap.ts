import * as THREE from 'three';
import { GameSprite } from './GameSprite.ts';

export type TileType = 'snow' | 'ice' | 'iceCracks';

export interface Tile {
  x: number;
  y: number;
  width: number;
  height: number;
  type: TileType;
  sprite: GameSprite;
}

export interface PlatformTileMapOptions {
  /** Total world width in pixels. */
  width: number;
  /** Ground elevation in pixels. */
  groundY: number;
  /** Size of each tile segment. */
  tileWidth: number;
  tileHeight: number;
  textures: Record<TileType, THREE.Texture>;
}

/**
 * Builds a horizontal side-scrolling level from repeating platform segments.
 * The ground runs across the full width, with a handful of raised platforms.
 */
export class PlatformTileMap {
  readonly tiles: Tile[] = [];
  readonly width: number;
  readonly groundY: number;
  readonly bounds = new THREE.Box2();

  private tileWidth: number;
  private tileHeight: number;
  private textures: Record<TileType, THREE.Texture>;

  constructor(options: PlatformTileMapOptions) {
    this.width = options.width;
    this.groundY = options.groundY;
    this.tileWidth = options.tileWidth;
    this.tileHeight = options.tileHeight;
    this.textures = options.textures;

    this.buildGround();
    this.buildPlatforms();

    this.bounds.min.set(-this.tileWidth / 2, this.groundY - 320);
    this.bounds.max.set(this.width + this.tileWidth / 2, this.groundY + 128);
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
   * Return the highest solid surface under the given x position, or null if
   * there is no ground there.
   */
  groundHeightAt(x: number): number | null {
    let top: number | null = null;
    for (const tile of this.tiles) {
      if (x >= tile.x - tile.width / 2 && x <= tile.x + tile.width / 2) {
        const tileTop = tile.y + tile.height / 2;
        if (top === null || tileTop > top) {
          top = tileTop;
        }
      }
    }
    return top;
  }

  /**
   * True if the world position is inside a solid tile (used for wall/ceiling
   * checks).
   */
  isSolidAt(x: number, y: number): boolean {
    for (const tile of this.tiles) {
      const left = tile.x - tile.width / 2;
      const right = tile.x + tile.width / 2;
      const bottom = tile.y - tile.height / 2;
      const top = tile.y + tile.height / 2;
      if (x >= left && x <= right && y >= bottom && y <= top) {
        return true;
      }
    }
    return false;
  }

  private buildGround(): void {
    const segments = Math.ceil(this.width / this.tileWidth);

    for (let i = 0; i < segments; i++) {
      const type: TileType = i % 7 === 0 ? 'iceCracks' : i % 3 === 0 ? 'ice' : 'snow';
      const surfaceX = i * this.tileWidth + this.tileWidth / 2;
      this.addTile(surfaceX, this.groundY - this.tileHeight / 2, this.tileWidth, this.tileHeight, type);
    }
  }

  private buildPlatforms(): void {
    const platformSpecs = [
      { x: 360, y: this.groundY - 120, w: 192, h: 32, type: 'snow' as TileType },
      { x: 720, y: this.groundY - 200, w: 160, h: 32, type: 'ice' as TileType },
      { x: 1180, y: this.groundY - 140, w: 224, h: 32, type: 'snow' as TileType },
      { x: 1680, y: this.groundY - 260, w: 192, h: 32, type: 'ice' as TileType },
      { x: 2120, y: this.groundY - 120, w: 160, h: 32, type: 'snow' as TileType },
    ];

    for (const spec of platformSpecs) {
      // spec.y is the top surface of the platform.
      this.addPlatform(spec.x, spec.y - spec.h / 2, spec.w, spec.h, spec.type);
    }
  }

  private addPlatform(x: number, centerY: number, width: number, height: number, type: TileType): void {
    const segments = Math.max(1, Math.floor(width / this.tileWidth));
    const startX = x - width / 2 + this.tileWidth / 2;

    for (let i = 0; i < segments; i++) {
      this.addTile(startX + i * this.tileWidth, centerY, this.tileWidth, height, type);
    }
  }

  private addTile(x: number, y: number, width: number, height: number, type: TileType): void {
    const texture = this.prepareTexture(type, width, height);

    const material = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      alphaTest: 0.5,
      depthWrite: false,
    });

    const sprite = new GameSprite(material, width, height);
    sprite.setPosition(x, y, 0);

    this.tiles.push({ x, y, width, height, type, sprite });
  }

  private prepareTexture(type: TileType, width: number, height: number): THREE.Texture {
    const texture = this.textures[type].clone();
    texture.magFilter = THREE.NearestFilter;
    texture.minFilter = THREE.NearestFilter;
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(width / this.tileWidth, height / this.tileHeight);
    texture.needsUpdate = true;
    texture.userData.isClone = true;
    return texture;
  }
}
