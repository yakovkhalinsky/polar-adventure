import Phaser from 'phaser';
import { Player, type Direction } from '../entities/Player.ts';

const TILE_WIDTH = 64;
const TILE_HEIGHT = 32;
const GRID_SIZE = 12;

export class GameScene extends Phaser.Scene {
  private player!: Player;
  private cursors!: Phaser.Types.Input.Keyboard.CursorKeys;
  private wasd!: Record<Direction, Phaser.Input.Keyboard.Key>;
  private tileGroup!: Phaser.GameObjects.Group;
  private worldBounds!: Phaser.Geom.Rectangle;

  constructor() {
    super({ key: 'GameScene' });
  }

  preload(): void {
    this.load.spritesheet('polar-bear', 'assets/characters/polar-bear.png', {
      frameWidth: 64,
      frameHeight: 64,
    });

    this.load.image('tile-snow', 'assets/tiles/snow.png');
    this.load.image('tile-ice', 'assets/tiles/ice.png');
    this.load.image('tile-ice-cracks', 'assets/tiles/ice-cracks.png');
  }

  create(): void {
    this.cameras.main.setBackgroundColor('#0b1d2e');
    this.tileGroup = this.add.group();

    this.drawIsometricGrid();

    const startIso = this.cartesianToIsometric(0, 0);
    this.player = new Player(this, startIso.x, startIso.y);

    this.cursors = this.input.keyboard!.createCursorKeys();
    this.wasd = this.input.keyboard!.addKeys({
      up: Phaser.Input.Keyboard.KeyCodes.W,
      down: Phaser.Input.Keyboard.KeyCodes.S,
      left: Phaser.Input.Keyboard.KeyCodes.A,
      right: Phaser.Input.Keyboard.KeyCodes.D,
    }) as Record<Direction, Phaser.Input.Keyboard.Key>;

    // Set up the camera so the map is centered and the player can roam it.
    this.configureCamera();
  }

  update(): void {
    this.player.update(this.cursors, this.wasd);

    // Depth-sort tiles each frame so the bear walks behind/in-front correctly.
    this.tileGroup.getChildren().forEach((child) => {
      const tile = child as Phaser.GameObjects.Image;
      tile.setDepth(tile.y);
    });
  }

  private drawIsometricGrid(): void {
    const centerX = this.cameras.main.width / 2;
    const centerY = this.cameras.main.height / 2;

    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;

    for (let row = 0; row < GRID_SIZE; row++) {
      for (let col = 0; col < GRID_SIZE; col++) {
        const { x, y } = this.cartesianToIsometric(col - GRID_SIZE / 2, row - GRID_SIZE / 2);
        const tileX = centerX + x;
        const tileY = centerY + y;

        const key = this.pickTileTexture(row, col);
        const tile = this.add.image(tileX, tileY, key);
        tile.setOrigin(0.5, 0.5);
        tile.setDepth(tileY);
        this.tileGroup.add(tile);

        minX = Math.min(minX, tileX - TILE_WIDTH / 2);
        minY = Math.min(minY, tileY - TILE_HEIGHT / 2);
        maxX = Math.max(maxX, tileX + TILE_WIDTH / 2);
        maxY = Math.max(maxY, tileY + TILE_HEIGHT / 2);
      }
    }

    // Pad bounds to keep tiles fully in view.
    const padding = 64;
    this.worldBounds = new Phaser.Geom.Rectangle(
      minX - padding,
      minY - padding,
      maxX - minX + padding * 2,
      maxY - minY + padding * 2,
    );
  }

  private configureCamera(): void {
    const cam = this.cameras.main;

    // Fit the whole grid into view at start.
    const zoomX = cam.width / this.worldBounds.width;
    const zoomY = cam.height / this.worldBounds.height;
    const fitZoom = Math.min(zoomX, zoomY) * 0.9; // 10% margin
    const zoom = Phaser.Math.Clamp(fitZoom, 0.5, 1.25);

    cam.setZoom(zoom);
    cam.centerOn(this.worldBounds.centerX, this.worldBounds.centerY);
    cam.setBounds(this.worldBounds.x, this.worldBounds.y, this.worldBounds.width, this.worldBounds.height);

    // Follow the player with a small deadzone so the map stays centered
    // until the player gets close to the edge.
    cam.startFollow(this.player, true, 0.08, 0.08);
    cam.setFollowOffset(0, -32); // account for player height
    cam.setDeadzone(cam.width * 0.2, cam.height * 0.2);
  }

  private pickTileTexture(row: number, col: number): string {
    const n = (row * 3 + col * 7) % 10;
    if (n === 0) return 'tile-ice-cracks';
    if (n < 4) return 'tile-ice';
    return 'tile-snow';
  }

  private cartesianToIsometric(cartX: number, cartY: number): { x: number; y: number } {
    return {
      x: (cartX - cartY) * (TILE_WIDTH / 2),
      y: (cartX + cartY) * (TILE_HEIGHT / 2),
    };
  }
}
