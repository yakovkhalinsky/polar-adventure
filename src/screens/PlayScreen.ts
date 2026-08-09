import * as THREE from 'three';
import { IsometricScene } from '../engine/IsometricScene.ts';
import { TileMap, TileType } from '../engine/TileMap.ts';
import { DepthSorter } from '../engine/DepthSorter.ts';
import { CameraController } from '../engine/CameraController.ts';
import { WorldObject } from '../engine/WorldObject.ts';
import { NPC, Collectible, Interactable } from '../engine/Interactables.ts';
import { DialogueBox } from '../ui/DialogueBox.ts';
import { PolarBear } from '../entities/PolarBear.ts';
import { SnowSystem } from '../engine/SnowSystem.ts';
import { DecalSystem } from '../engine/DecalSystem.ts';

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
  private npcs: NPC[] = [];
  private collectibles: Collectible[] = [];
  private interactables: Interactable[] = [];
  private snow: SnowSystem | null = null;
  private decals: DecalSystem | null = null;
  private dialogue: DialogueBox;
  private score = 0;
  private scoreHud: HTMLElement;

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
    this.dialogue = new DialogueBox();
    this.scoreHud = document.getElementById('score-hud') ?? document.createElement('div');
    this.updateScoreHud();
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

    this.snow = new SnowSystem({ count: 500, areaWidth: 900, areaHeight: 700, windX: 0.5 });
    this.scene.scene.add(this.snow.points);
    this.snow.points.position.z = 120;

    this.decals = new DecalSystem(this.worldRoot);

    this.player = new PolarBear(this.textures.polarBear);
    this.worldRoot.add(this.player.character.sprite);
    this.worldRoot.add(this.player.shadow.sprite);

    // Center player on the grid.
    const { x, y } = this.tileMap.cartesianToIsometric(0, 0);
    this.player.setPosition(x, y);
    this.player.setCollisionContext(this.tileMap, this.objects);
    this.player.setDecalSystem(this.decals);

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
    this.snow?.dispose();
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

    // Spawn persistent NPCs, collectibles, and interactables at fixed tiles.
    this.spawnNPCs();
    this.spawnCollectibles(rng);
    this.spawnInteractables();

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
      if (this.snow) {
        this.snow.points.position.x = pos.x;
        this.snow.points.position.y = pos.y;
      }
    }
    this.camera?.update(16.67);
    this.snow?.update(16.67);
    this.decals?.update(16.67);
    this.updateCollectibles();
    for (const npc of this.npcs) npc.update(16.67);
    for (const item of this.collectibles) item.update(16.67);
    for (const obj of this.interactables) obj.update(16.67);

    if (this.player && this.tileMap) {
      this.sorter.sort([
        ...this.tileMap.tiles.map((t) => t.sprite),
        ...this.objects.map((o) => o.sprite),
        ...this.npcs.map((n) => n.sprite),
        ...this.collectibles.map((c) => c.sprite),
        ...this.interactables.map((i) => i.sprite),
        ...(this.decals?.sprites ?? []),
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
    // Dialogue consumes E and Space so the player does not jump/talk at the same time.
    if (this.dialogue.isOpen) {
      if (e.code === 'Space' || e.code === 'KeyE') {
        e.preventDefault();
        if (pressed) this.dialogue.dismiss();
        return;
      }
    }

    if (pressed && e.code === 'KeyE') {
      e.preventDefault();
      this.handleInteract();
      return;
    }

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
      KeyX: 'attack',
      ShiftLeft: 'attack',
      ShiftRight: 'attack',
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

  private spawnNPCs(): void {
    if (!this.tileMap) return;

    const penguin = new NPC({
      x: this.tileMap.grid[6][8].x,
      y: this.tileMap.grid[6][8].y,
      width: 48,
      height: 64,
      texture: this.textures.objects.penguin,
      name: 'Pip the Penguin',
      lines: [
        'Brrr! It is chilly today. Have you seen any fish around?',
        'If you find three fish, I will tell you the secret of the ice cave.',
      ],
    });
    this.npcs.push(penguin);
    this.worldRoot.add(penguin.sprite.sprite);
  }

  private spawnCollectibles(rng: () => number): void {
    if (!this.tileMap) return;

    let placed = 0;
    for (const tile of this.tileMap.tiles) {
      if (placed >= 6) break;
      if (tile.type === 'water' || tile.blocked) continue;
      // Skip start area and NPC zone.
      if (Math.abs(tile.col - 12) <= 2 && Math.abs(tile.row - 12) <= 2) continue;
      if (Math.abs(tile.col - 8) <= 2 && Math.abs(tile.row - 6) <= 2) continue;
      if (rng() < 0.04) {
        const fish = new Collectible({
          x: tile.x,
          y: tile.y,
          width: 36,
          height: 24,
          texture: this.textures.objects.fish,
          value: 1,
        });
        this.collectibles.push(fish);
        this.worldRoot.add(fish.sprite.sprite);
        placed++;
      }
    }
  }

  private spawnInteractables(): void {
    if (!this.tileMap) return;

    const igloo = new Interactable({
      x: this.tileMap.grid[10][14].x,
      y: this.tileMap.grid[10][14].y,
      width: 64,
      height: 48,
      texture: this.textures.objects.igloo,
      label: 'A cozy igloo. It smells like warm soup inside.',
    });
    this.interactables.push(igloo);
    this.worldRoot.add(igloo.sprite.sprite);

    const sign = new Interactable({
      x: this.tileMap.grid[14][6].x,
      y: this.tileMap.grid[14][6].y,
      width: 32,
      height: 48,
      texture: this.textures.objects.sign,
      label: 'Welcome to Polar Adventures! Press Space to jump and E to talk.',
    });
    this.interactables.push(sign);
    this.worldRoot.add(sign.sprite.sprite);
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

  private updateCollectibles(): void {
    if (!this.player) return;
    const pos = this.player.getPosition();

    for (let i = this.collectibles.length - 1; i >= 0; i--) {
      const item = this.collectibles[i];
      if (item.collected) continue;
      const dx = pos.x - item.position.x;
      const dy = pos.y - item.position.y;
      if (Math.sqrt(dx * dx + dy * dy) < 28) {
        this.score += item.collect();
        this.worldRoot.remove(item.sprite.sprite);
        this.updateScoreHud();
      }
    }
  }

  private handleInteract(): void {
    if (!this.player || this.dialogue.isOpen) return;
    const pos = this.player.getPosition();

    // Find the nearest NPC.
    let nearestNpc: NPC | null = null;
    let nearestNpcDist = Infinity;
    for (const npc of this.npcs) {
      const dx = pos.x - npc.position.x;
      const dy = pos.y - npc.position.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 55 && dist < nearestNpcDist) {
        nearestNpc = npc;
        nearestNpcDist = dist;
      }
    }

    if (nearestNpc) {
      const line = nearestNpc.lines[Math.floor(Math.random() * nearestNpc.lines.length)];
      this.dialogue.show(`${nearestNpc.name}: ${line}`);
      return;
    }

    // Otherwise check structures / signs.
    for (const obj of this.interactables) {
      const dx = pos.x - obj.position.x;
      const dy = pos.y - obj.position.y;
      if (Math.sqrt(dx * dx + dy * dy) < 55) {
        this.dialogue.show(obj.label, obj.action);
        return;
      }
    }
  }

  private updateScoreHud(): void {
    this.scoreHud.textContent = `Fish: ${this.score}/6  |  Arrows/WASD move  |  Space jump  |  E talk`;
  }
}

function seededRng(seed: number): () => number {
  let s = seed;
  return () => {
    s = Math.sin(s * 12.9898 + 78.233) * 43758.5453;
    return s - Math.floor(s);
  };
}
