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

  constructor() {
    super({ key: 'GameScene' });
  }

  preload(): void {
    // Polar bear walk-cycle spritesheet: 4 directions x 4 frames, each 64x64.
    this.load.spritesheet('polar-bear', '/assets/characters/polar-bear.png', {
      frameWidth: 64,
      frameHeight: 64,
    });

    // Isometric ground tiles.
    this.load.image('tile-snow', '/assets/tiles/snow.png');
    this.load.image('tile-ice', '/assets/tiles/ice.png');
    this.load.image('tile-ice-cracks', '/assets/tiles/ice-cracks.png');
  }

  create(): void {
    this.cameras.main.setBackgroundColor('#0b1d2e');
    this.tileGroup = this.add.group();

    this.drawIsometricGrid();

    const startIso = this.cartesianToIsometric(0, 0);
    this.player = new Player(this, startIso.x, startIso.y - TILE_HEIGHT * 2);
    this.player.setScale(0.9);

    this.cursors = this.input.keyboard!.createCursorKeys();
    this.wasd = this.input.keyboard!.addKeys({
      up: Phaser.Input.Keyboard.KeyCodes.W,
      down: Phaser.Input.Keyboard.KeyCodes.S,
      left: Phaser.Input.Keyboard.KeyCodes.A,
      right: Phaser.Input.Keyboard.KeyCodes.D,
    }) as Record<Direction, Phaser.Input.Keyboard.Key>;
  }

  update(): void {
    this.player.update(this.cursors, this.wasd);

    // Keep tiles depth-sorted relative to the player so walking behind/in-front works.
    this.tileGroup.getChildren().forEach((child) => {
      const tile = child as Phaser.GameObjects.Image;
      tile.setDepth(tile.y);
    });
  }

  private drawIsometricGrid(): void {
    const centerX = this.cameras.main.width / 2;
    const offsetY = this.cameras.main.height / 4;

    for (let row = 0; row < GRID_SIZE; row++) {
      for (let col = 0; col < GRID_SIZE; col++) {
        const { x, y } = this.cartesianToIsometric(col - GRID_SIZE / 2, row - GRID_SIZE / 2);
        const tileX = centerX + x;
        const tileY = offsetY + y;

        // Pick a tile texture based on a simple pattern.
        const key = this.pickTileTexture(row, col);
        const tile = this.add.image(tileX, tileY, key);
        tile.setOrigin(0.5, 0.5);
        tile.setDepth(tileY);
        this.tileGroup.add(tile);
      }
    }
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
