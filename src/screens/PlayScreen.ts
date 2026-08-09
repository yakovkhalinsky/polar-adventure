import * as THREE from 'three';
import { IsometricScene } from '../engine/IsometricScene.ts';
import { TileMap } from '../engine/TileMap.ts';
import { DepthSorter } from '../engine/DepthSorter.ts';
import { PolarBear } from '../entities/PolarBear.ts';

const TILE_WIDTH = 64;
const TILE_HEIGHT = 32;
const GRID_SIZE = 12;

/**
 * The main gameplay screen. Sets up an isometric tile grid, spawns the polar
 * bear, and drives the render loop.
 */
export class PlayScreen {
  private scene: IsometricScene;
  private worldRoot: THREE.Object3D;
  private tileMap: TileMap | null = null;
  private player: PolarBear | null = null;
  private sorter: DepthSorter;
  private keys = new Set<string>();
  private running = true;

  private textures: {
    polarBear: THREE.Texture;
    snow: THREE.Texture;
    ice: THREE.Texture;
    iceCracks: THREE.Texture;
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
      textures: {
        snow: this.textures.snow,
        ice: this.textures.ice,
        iceCracks: this.textures.iceCracks,
      },
    });
    this.tileMap.addTo(this.worldRoot);

    this.player = new PolarBear(this.textures.polarBear);
    this.worldRoot.add(this.player.character.sprite);
    this.worldRoot.add(this.player.shadow.sprite);

    // Center player on the grid.
    const { x, y } = this.tileMap.cartesianToIsometric(0, 0);
    this.player.setPosition(x, y);

    // Fit camera to the grid.
    this.fitCamera();

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

  private loop = (_time: number): void => {
    if (!this.running) return;

    this.player?.update(16.67, this.keys); // fixed 60fps dt for stability

    if (this.player && this.tileMap) {
      this.sorter.sort([
        ...this.tileMap.tiles,
        this.player.shadow,
        this.player.character,
      ]);

    }

    this.scene.render();
    requestAnimationFrame(this.loop);
  };

  private handleKeyDown = (e: KeyboardEvent): void => {
    this.mapKey(e.code, true);
  };

  private handleKeyUp = (e: KeyboardEvent): void => {
    this.mapKey(e.code, false);
  };

  private mapKey(code: string, pressed: boolean): void {
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

    const action = map[code];
    if (!action) return;

    // Prevent page scroll on arrow keys and space.
    if (action !== 'jump') {
      // handled by preventDefault below for arrows only
    }

    if (pressed) {
      this.keys.add(action);
    } else {
      this.keys.delete(action);
    }
  }

  private fitCamera(): void {
    if (!this.tileMap) return;

    const centerX = (this.tileMap.bounds.min.x + this.tileMap.bounds.max.x) / 2;
    const centerY = (this.tileMap.bounds.min.y + this.tileMap.bounds.max.y) / 2;
    this.worldRoot.position.set(-centerX, -centerY, 0);

    const worldWidth = this.tileMap.bounds.max.x - this.tileMap.bounds.min.x;
    const worldHeight = this.tileMap.bounds.max.y - this.tileMap.bounds.min.y;
    const zoom = Math.min(1024 / worldWidth, 768 / worldHeight) * 0.85;
    this.scene.setZoom(zoom);
  }
}
