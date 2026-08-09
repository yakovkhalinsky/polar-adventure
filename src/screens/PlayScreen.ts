import * as me from 'melonjs';
import { PolarBearEntity } from '../entities/PolarBearEntity.ts';

const TILE_WIDTH = 64;
const TILE_HEIGHT = 32;
const GRID_SIZE = 12;

/**
 * The main gameplay screen. We do not load a TMX map here because the project
 * intentionally generates simple diamond tile textures from ComfyUI. Instead,
 * we build an isometric grid at runtime and place a polar bear entity on it.
 */
export class PlayScreen extends me.Stage {
  private worldBounds = new me.Bounds();

  onResetEvent(): void {
    // Set the arctic background color on the renderer.
    me.game.renderer.backgroundColor.parseCSS('#0b1d2e');

    // Preload image assets. melonJS will queue them and continue once ready.
    me.loader.load([
      { name: 'polar-bear', type: 'image', src: 'assets/characters/polar-bear.png' },
      { name: 'tile-snow', type: 'image', src: 'assets/tiles/snow.png' },
      { name: 'tile-ice', type: 'image', src: 'assets/tiles/ice.png' },
      { name: 'tile-ice-cracks', type: 'image', src: 'assets/tiles/ice-cracks.png' },
    ]);

    this.drawIsometricGrid();

    // Spawn the player at the center of the grid.
    const start = this.cartesianToIsometric(0, 0);
    const centerX = me.game.viewport.width / 2;
    const centerY = me.game.viewport.height / 2;
    const player = new PolarBearEntity(centerX + start.x, centerY + start.y);
    me.game.world.addChild(player, 10);

    // Camera follows the player smoothly.
    me.game.viewport.follow(player, me.game.viewport.AXIS.BOTH, 0.08);
    me.game.viewport.setDeadzone(
      me.game.viewport.width * 0.2,
      me.game.viewport.height * 0.2
    );

    this.configureCamera();
  }

  private drawIsometricGrid(): void {
    const centerX = me.game.viewport.width / 2;
    const centerY = me.game.viewport.height / 2;

    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;

    for (let row = 0; row < GRID_SIZE; row++) {
      for (let col = 0; col < GRID_SIZE; col++) {
        const { x, y } = this.cartesianToIsometric(col - GRID_SIZE / 2, row - GRID_SIZE / 2);
        const tileX = centerX + x;
        const tileY = centerY + y;

        const texture = this.pickTileTexture(row, col);
        const tile = new me.Sprite(tileX, tileY, {
          image: texture,
          anchorPoint: new me.Vector2d(0.5, 0.5),
        });
        // Depth is the screen Y so that characters walk in front/behind tiles correctly.
        tile.depth = tileY;

        me.game.world.addChild(tile, 1);

        minX = Math.min(minX, tileX - TILE_WIDTH / 2);
        minY = Math.min(minY, tileY - TILE_HEIGHT / 2);
        maxX = Math.max(maxX, tileX + TILE_WIDTH / 2);
        maxY = Math.max(maxY, tileY + TILE_HEIGHT / 2);
      }
    }

    // Pad bounds to keep tiles fully in view.
    const padding = 64;
    this.worldBounds.setMinMax(
      minX - padding,
      minY - padding,
      maxX + padding,
      maxY + padding
    );
  }

  private configureCamera(): void {
    const viewport = me.game.viewport;
    const fitZoomX = viewport.width / this.worldBounds.width;
    const fitZoomY = viewport.height / this.worldBounds.height;
    const fitZoom = Math.min(fitZoomX, fitZoomY) * 0.9;

    viewport.zoom = Math.max(0.5, Math.min(fitZoom, 1.25));
    viewport.setBounds(
      this.worldBounds.x,
      this.worldBounds.y,
      this.worldBounds.width,
      this.worldBounds.height
    );
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

  onDestroyEvent(): void {
    // Clean up all dynamic children added by this screen.
    const world = me.game.world;
    const children = world.children ?? [];
    while (children.length > 0) {
      world.removeChild(children[0]);
    }
  }
}
