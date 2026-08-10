import * as THREE from 'three';
import { SideScrollScene } from '../engine/SideScrollScene.ts';
import { PlatformTileMap, TileType } from '../engine/PlatformTileMap.ts';
import { CameraController } from '../engine/CameraController.ts';
import { WorldObject } from '../engine/WorldObject.ts';
import { NPC, Collectible, Interactable } from '../engine/Interactables.ts';
import { DialogueBox } from '../ui/DialogueBox.ts';
import { PolarBear } from '../entities/PolarBear.ts';
import { SnowSystem } from '../engine/SnowSystem.ts';
import { DecalSystem } from '../engine/DecalSystem.ts';

const TILE_WIDTH = 64;
const TILE_HEIGHT = 32;
const GROUND_Y = 240;
const LEVEL_WIDTH = 2600;

/**
 * The main gameplay screen. Sets up a horizontal side-scrolling level,
 * spawns the polar bear, places obstacles and decorations, drives the
 * render loop, and keeps the camera smoothly following the player.
 */
export class PlayScreen {
  private scene: SideScrollScene;
  private worldRoot: THREE.Object3D;
  private tileMap: PlatformTileMap | null = null;
  private player: PolarBear | null = null;
  private camera: CameraController | null = null;
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
    this.scene = new SideScrollScene('game-container');
    this.worldRoot = new THREE.Object3D();
    this.scene.scene.add(this.worldRoot);
    this.dialogue = new DialogueBox();
    this.scoreHud = document.getElementById('score-hud') ?? document.createElement('div');
    this.updateScoreHud();
  }

  start(): void {
    this.tileMap = new PlatformTileMap({
      width: LEVEL_WIDTH,
      groundY: GROUND_Y,
      tileWidth: TILE_WIDTH,
      tileHeight: TILE_HEIGHT,
      textures: this.textures.tiles,
    });
    this.tileMap.addTo(this.worldRoot);

    this.spawnObjects();

    this.snow = new SnowSystem({ count: 500, areaWidth: 1200, areaHeight: 800, windX: -0.3 });
    this.scene.scene.add(this.snow.points);
    this.snow.points.position.z = 120;

    this.decals = new DecalSystem(this.worldRoot);

    this.player = new PolarBear(this.textures.polarBear);
    this.worldRoot.add(this.player.character.sprite);
    this.worldRoot.add(this.player.shadow.sprite);

    // Start on the ground at the left side.
    this.player.setPosition(80, GROUND_Y);
    this.player.setCollisionContext(this.tileMap, this.objects);
    this.player.setDecalSystem(this.decals);

    // Camera follows the player through the level.
    this.camera = new CameraController(
      this.worldRoot,
      this.scene.designWidth,
      this.scene.designHeight,
      { bounds: this.tileMap.bounds, deadzoneX: 64, deadzoneY: 9999, smoothness: 0.12 }
    );
    this.camera.snapTo(this.player.getPosition().x, this.player.getPosition().y);

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

    const rng = seededRng(42);
    const objectTypes = [
      { key: 'rock', width: 48, height: 40, radius: 18 },
      { key: 'tree', width: 48, height: 72, radius: 16 },
      { key: 'snowMound', width: 40, height: 24, radius: 12 },
      { key: 'iceberg', width: 56, height: 72, radius: 20 },
    ];

    this.spawnNPCs();
    this.spawnCollectibles(rng);
    this.spawnInteractables();

    // Scatter decorations across the level, avoiding the start area.
    for (let x = 300; x < LEVEL_WIDTH - 120; x += 140 + Math.floor(rng() * 160)) {
      if (rng() > 0.35) continue;

      const type = objectTypes[Math.floor(rng() * objectTypes.length)];
      const groundY = this.tileMap.groundHeightAt(x);
      if (groundY === null) continue;

      const obj = new WorldObject({
        x,
        y: groundY,
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

  private loop = (_time: number): void => {
    if (!this.running) return;

    this.player?.update(16.67, this.keys);

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
      Space: 'jump',
      KeyW: 'jump',
      ArrowUp: 'jump',
      KeyX: 'attack',
      ShiftLeft: 'attack',
      ShiftRight: 'attack',
    };

    const action = map[e.code];
    if (!action) return;

    if (['left', 'right', 'jump'].includes(action)) {
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

    const groundY = this.tileMap.groundHeightAt(620);
    const penguin = new NPC({
      x: 620,
      y: groundY ?? GROUND_Y,
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
    for (let x = 250; x < LEVEL_WIDTH - 100 && placed < 8; x += 220 + Math.floor(rng() * 180)) {
      const groundY = this.tileMap.groundHeightAt(x);
      if (groundY === null) continue;
      // Skip the NPC zone.
      if (Math.abs(x - 620) < 80) continue;

      const fish = new Collectible({
        x,
        y: groundY + 48,
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

  private spawnInteractables(): void {
    if (!this.tileMap) return;

    const iglooGround = this.tileMap.groundHeightAt(LEVEL_WIDTH - 180);
    const igloo = new Interactable({
      x: LEVEL_WIDTH - 180,
      y: iglooGround ?? GROUND_Y,
      width: 64,
      height: 48,
      texture: this.textures.objects.igloo,
      label: 'A cozy igloo. It smells like warm soup inside.',
    });
    this.interactables.push(igloo);
    this.worldRoot.add(igloo.sprite.sprite);

    const signGround = this.tileMap.groundHeightAt(160);
    const sign = new Interactable({
      x: 160,
      y: signGround ?? GROUND_Y,
      width: 32,
      height: 48,
      texture: this.textures.objects.sign,
      label: 'Welcome to Polar Adventures! Arrows/WASD to run, Space/W/Up to jump, E to talk.',
    });
    this.interactables.push(sign);
    this.worldRoot.add(sign.sprite.sprite);
  }

  private updateCollectibles(): void {
    if (!this.player) return;
    const pos = this.player.getPosition();

    for (let i = this.collectibles.length - 1; i >= 0; i--) {
      const item = this.collectibles[i];
      if (item.collected) continue;
      const dx = pos.x - item.position.x;
      const dy = pos.y - item.position.y;
      if (Math.sqrt(dx * dx + dy * dy) < 36) {
        this.score += item.collect();
        this.worldRoot.remove(item.sprite.sprite);
        this.updateScoreHud();
      }
    }
  }

  private handleInteract(): void {
    if (!this.player || this.dialogue.isOpen) return;
    const pos = this.player.getPosition();

    let nearestNpc: NPC | null = null;
    let nearestNpcDist = Infinity;
    for (const npc of this.npcs) {
      const dx = pos.x - npc.position.x;
      const dy = pos.y - npc.position.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 65 && dist < nearestNpcDist) {
        nearestNpc = npc;
        nearestNpcDist = dist;
      }
    }

    if (nearestNpc) {
      const line = nearestNpc.lines[Math.floor(Math.random() * nearestNpc.lines.length)];
      this.dialogue.show(`${nearestNpc.name}: ${line}`);
      return;
    }

    for (const obj of this.interactables) {
      const dx = pos.x - obj.position.x;
      const dy = pos.y - obj.position.y;
      if (Math.sqrt(dx * dx + dy * dy) < 60) {
        this.dialogue.show(obj.label, obj.action);
        return;
      }
    }
  }

  private updateScoreHud(): void {
    this.scoreHud.textContent = `Fish: ${this.score}/8  |  Arrows/WASD move  |  Space jump  |  E talk`;
  }
}

function seededRng(seed: number): () => number {
  let s = seed;
  return () => {
    s = Math.sin(s * 12.9898 + 78.233) * 43758.5453;
    return s - Math.floor(s);
  };
}
