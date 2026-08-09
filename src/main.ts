import * as THREE from 'three';
import { PlayScreen } from './screens/PlayScreen.ts';

/**
 * Bootstrap the Three.js isometric game after textures have loaded.
 */
function loadTexture(url: string): Promise<THREE.Texture> {
  return new Promise((resolve, reject) => {
    new THREE.TextureLoader().load(url, resolve, undefined, reject);
  });
}

async function main(): Promise<void> {
  try {
    const [
      polarBear,
      snow,
      ice,
      iceCracks,
      water,
      rock,
      iceberg,
      tree,
      snowMound,
      penguin,
      fish,
      igloo,
      sign,
    ] = await Promise.all([
      loadTexture('assets/characters/polar-bear.png'),
      loadTexture('assets/tiles/snow.png'),
      loadTexture('assets/tiles/ice.png'),
      loadTexture('assets/tiles/ice-cracks.png'),
      loadTexture('assets/tiles/water.png'),
      loadTexture('assets/objects/rock.png'),
      loadTexture('assets/objects/iceberg.png'),
      loadTexture('assets/objects/tree.png'),
      loadTexture('assets/objects/snow-mound.png'),
      loadTexture('assets/characters/penguin.png'),
      loadTexture('assets/objects/fish.png'),
      loadTexture('assets/objects/igloo.png'),
      loadTexture('assets/objects/sign.png'),
    ]);

    const game = new PlayScreen({
      polarBear,
      tiles: { snow, ice, iceCracks, water },
      objects: { rock, iceberg, tree, snowMound, penguin, fish, igloo, sign },
    });

    game.start();

    // Clean up on hot reload (Vite dev).
    if (import.meta.hot) {
      import.meta.hot.dispose(() => {
        game.stop();
      });
    }
  } catch (err) {
    console.error('Failed to load game assets:', err);
    const overlay = document.getElementById('error-overlay');
    if (overlay) {
      overlay.style.display = 'block';
      const message = err instanceof Error ? `${err.name}: ${err.message}\n${err.stack || ''}` : String(err);
      overlay.textContent = `CAUGHT ERROR:\n${message}`;
    }
  }
}

main();
