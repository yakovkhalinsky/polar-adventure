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
    const [polarBear, snow, ice, iceCracks] = await Promise.all([
      loadTexture('assets/characters/polar-bear.png'),
      loadTexture('assets/tiles/snow.png'),
      loadTexture('assets/tiles/ice.png'),
      loadTexture('assets/tiles/ice-cracks.png'),
    ]);

    const game = new PlayScreen({
      polarBear,
      snow,
      ice,
      iceCracks,
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
  }
}

main();
