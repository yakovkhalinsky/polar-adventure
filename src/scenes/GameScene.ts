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
    // Create a runtime texture from an inline SVG so the project has zero external asset dependencies.
    const svg = `
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
        <rect width="64" height="64" fill="#8ecae6" opacity="0"/>
        <ellipse cx="32" cy="34" rx="18" ry="14" fill="#f8fbff"/>
        <circle cx="32" cy="24" r="12" fill="#f8fbff"/>
        <circle cx="28" cy="22" r="1.5" fill="#1a2b3c"/>
        <circle cx="36" cy="22" r="1.5" fill="#1a2b3c"/>
        <ellipse cx="32" cy="27" rx="3" ry="2" fill="#1a2b3c"/>
        <ellipse cx="18" cy="34" rx="5" ry="8" fill="#f8fbff" transform="rotate(-20 18 34)"/>
        <ellipse cx="46" cy="34" rx="5" ry="8" fill="#f8fbff" transform="rotate(20 46 34)"/>
        <ellipse cx="24" cy="46" rx="4" ry="7" fill="#f8fbff" transform="rotate(-10 24 46)"/>
        <ellipse cx="40" cy="46" rx="4" ry="7" fill="#f8fbff" transform="rotate(10 40 46)"/>
        <circle cx="16" cy="20" r="5" fill="#f8fbff"/>
        <circle cx="48" cy="20" r="5" fill="#f8fbff"/>
      </svg>
    `;
    const url = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
    this.load.svg('polar-bear', url, { width: 64, height: 64 });
  }

  create(): void {
    this.cameras.main.setBackgroundColor('#0b1d2e');
    this.tileGroup = this.add.group();

    this.drawIsometricGrid();

    const startIso = this.cartesianToIsometric(0, 0);
    this.player = new Player(this, startIso.x, startIso.y - TILE_HEIGHT * 2, 'polar-bear');
    this.player.setScale(0.8);

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
      const tile = child as Phaser.GameObjects.Rectangle;
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

        const color = (row + col) % 2 === 0 ? 0xa8dadc : 0x457b9d;
        const tile = this.add.rectangle(tileX, tileY, TILE_WIDTH, TILE_HEIGHT, color);
        tile.setStrokeStyle(1, 0x1d3557);
        tile.setOrigin(0.5, 0.5);
        tile.setDepth(tileY);
        this.tileGroup.add(tile);
      }
    }
  }

  private cartesianToIsometric(cartX: number, cartY: number): { x: number; y: number } {
    return {
      x: (cartX - cartY) * (TILE_WIDTH / 2),
      y: (cartX + cartY) * (TILE_HEIGHT / 2),
    };
  }
}
