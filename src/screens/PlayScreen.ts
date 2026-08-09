import * as THREE from 'three';
import { IsometricScene } from '../engine/IsometricScene.ts';
import { TileMap, TileType } from '../engine/TileMap.ts';
import { DepthSorter } from '../engine/DepthSorter.ts';
import { CameraController } from '../engine/CameraController.ts';
import { WorldObject } from '../engine/WorldObject.ts';
import { PolarBear } from '../entities/PolarBear.ts';

const TILE_WIDTH = 64;
const TILE_HEIGHT = 32;
const GRID_SIZE = 24;

/**
 * The main gameplay screen. Sets up an isometric tile grid, spawns the polar
 * bear, places obstacles and decorations, drives the render loop, and keeps the
 * camera smoothly following the player.
 */
export class PlayScreen {
  private scene: IsometricScene;
  private worldRoot: THREE.Object3D;
  private tileMap: TileMap | null = null;
  private player: PolarBear | null = null;
  private camera: CameraController | null = null;
  private sorter: DepthSorter;
  private keys = new Set<string>();
  private running = true;
  private objects: WorldObject[] = [];

  private textures: {
    polarBear: THREE.Texture;
    tiles: Record<TileType, THREE.Texture>;
    objects: Record<string, THREE.Texture>;
  };

  constructor(textures: PlayScreen['textures']) {
    this.textures = textures;
    this.scene = new IsometricScene('game-container');
    this.worldRoot = new THREE.Object3D();
    this.scene.scene.add(this.worldRoot);
    this.sorter = new DepthSorter(this.worldRoot);
  }

  start(): void {
    this.tileMap = new TileMap({
      size: GRID_SIZE,
      tileWidth: TILE_WIDTH,
      tileHeight: TILE_HEIGHT,
      textures: this.textures.tiles,
    });
    this.tileMap.addTo(this.worldRoot);

    this.spawnObjects();

    this.player = new PolarBear(this.textures.polarBear);
    this.worldRoot.add(this.player.character.sprite);
    this.worldRoot.add(this.player.shadow.sprite);

    // Center player on the grid.
    const { x, y } = this.tileMap.cartesianToIsometric(0, 0);
    this.player.setPosition(x, y);
    this.player.setCollisionContext(this.tileMap, this.objects);

    // Initial zoom to frame the grid, then a smooth follow camera.
    this.fitCamera();
    this.camera = new CameraController(
      this.worldRoot,
      this.scene.designWidth,
      this.scene.designHeight,
      { bounds: this.tileMap.bounds }
    );
    this.camera.snapTo(x, y);

    // Input.
    window.addEventListener('keydown', this.handleKeyDown);
    window.addEventListener('keyup', this.handleKeyUp);

    this.running = true;
    this.loop(0);
  }

  stop(): void {
    this.running = false;
    window.removeEventListener('keydown', this.handleKeyDown);
    window.removeEventListener('keyup', this.handleKeyUp);
    this.scene.dispose();
  }

  private spawnObjects(): void {
    if (!this.tileMap) return;

    const half = Math.floor(GRID_SIZE / 2);
    const rng = seededRng(42);
    const objectTypes = [
      { key: 'rock', width: 48, height: 40, radius: 18 },
      { key: 'iceberg', width: 56, height: 72, radius: 20 },
      { key: 'tree', width: 48, height: 72, radius: 16 },
      { key: 'snowMound', width: 40, height: 24, radius: 12 },
    ];

    // Place a ring of water around the outer edges and scattered objects inside.
    for (const tile of this.tileMap.tiles) {
      // Skip the starting area around (0,0).
      if (Math.abs(tile.col - half) <= 2 && Math.abs(tile.row - half) <= 2) {
        continue;
      }

      // Border water.
      const distFromEdge = Math.min(
        tile.col,
        tile.row,
        GRID_SIZE - 1 - tile.col,
        GRID_SIZE - 1 - tile.row
      );
      if (distFromEdge <= 1) {
        if (rng() > 0.3) {
          tile.type = 'water';
          tile.blocked = true;
          // Swap texture.
          (tile.sprite.sprite.material as THREE.SpriteMaterial).map = this.textures.tiles.water;
        }
        continue;
      }

      // Random decorations on snow/ice tiles.
      if (tile.type === 'snow' || tile.type === 'ice') {
        if (rng() < 0.04) {
          const type = objectTypes[Math.floor(rng() * objectTypes.length)];
          const obj = new WorldObject({
            x: tile.x,
            y: tile.y,
            width: type.width,
            height: type.height,
            texture: this.textures.objects[type.key],
            blocked: type.key !== 'snowMound',
            blockRadius: type.radius,
          });
          this.objects.push(obj);
          this.worldRoot.add(obj.sprite.sprite);
        }
      }
    }
  }

  private loop = (_time: number): void => {
    if (!this.running) return;

    this.player?.update(16.67, this.keys); // fixed 60fps dt for stability

    if (this.player) {
      const pos = this.player.getPosition();
      this.camera?.setTarget(pos.x, pos.y);
    }
    this.camera?.update(16.67);

    if (this.player && this.tileMap) {
      this.sorter.sort([
        ...this.tileMap.tiles.map((t) => t.sprite),
        ...this.objects.map((o) => o.sprite),
        this.player.shadow,
        this.player.character,
      ]);
    }

    this.scene.render();
    requestAnimationFrame(this.loop);
  };

  private handleKeyDown = (e: KeyboardEvent): void => {
    this.mapKey(e, true);
  };

  private handleKeyUp = (e: KeyboardEvent): void => {
    this.mapKey(e, false);
  };

  private mapKey(e: KeyboardEvent, pressed: boolean): void {
    const map: Record<string, string> = {
      ArrowLeft: 'left',
      KeyA: 'left',
      ArrowRight: 'right',
      KeyD: 'right',
      ArrowUp: 'up',
      KeyW: 'up',
      ArrowDown: 'down',
      KeyS: 'down',
      Space: 'jump',
    };

    const action = map[e.code];
    if (!action) return;

    // Prevent page scroll on arrow keys and space.
    if (['left', 'right', 'up', 'down', 'jump'].includes(action)) {
      e.preventDefault();
    }

    if (pressed) {
      this.keys.add(action);
    } else {
      this.keys.delete(action);
    }
  }

  private fitCamera(): void {
    if (!this.tileMap) return;

    const worldWidth = this.tileMap.bounds.max.x - this.tileMap.bounds.min.x;
    const worldHeight = this.tileMap.bounds.max.y - this.tileMap.bounds.min.y;
    const zoom = Math.min(
      this.scene.designWidth / worldWidth,
      this.scene.designHeight / worldHeight
    ) * 0.85;
    this.scene.setZoom(zoom);
  }
}

function seededRng(seed: number): () => number {
  let s = seed;
  return () => {
    s = Math.sin(s * 12.9898 + 78.233) * 43758.5453;
    return s - Math.floor(s);
  };
}
