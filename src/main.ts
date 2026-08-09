import * as me from 'melonjs';
import { PlayScreen } from './screens/PlayScreen.ts';
import { PolarBearEntity } from './entities/PolarBearEntity.ts';

// Bootstrap melonJS into the existing #game-container div.
me.device.onReady(() => {
  // Create and initialize the game application.
  const app = new me.Application(1024, 768, {
    parent: 'game-container',
    renderer: me.video.AUTO,
    scale: 'auto',
    scaleMethod: 'fit',
    transparent: true,
  });

  // Disable smoothing for crisp pixel-art-like sprites.
  app.renderer.setAntiAlias(false);

  // Audio is not required for this demo; initialise with no audio to avoid
  // the WebAudio unlock prompt on some platforms.
  try {
    me.audio.init('mp3,ogg,wav');
  } catch {
    // Audio is optional; continue silently if it fails.
  }

  // Bind keyboard input before any screen loads.
  me.input.bindKey(me.input.KEY.LEFT, 'left');
  me.input.bindKey(me.input.KEY.A, 'left');
  me.input.bindKey(me.input.KEY.RIGHT, 'right');
  me.input.bindKey(me.input.KEY.D, 'right');
  me.input.bindKey(me.input.KEY.UP, 'up');
  me.input.bindKey(me.input.KEY.W, 'up');
  me.input.bindKey(me.input.KEY.DOWN, 'down');
  me.input.bindKey(me.input.KEY.S, 'down');
  me.input.bindKey(me.input.KEY.SPACE, 'jump', true);

  // Register the custom entity so Tiled object layers can spawn it if needed.
  me.pool.register('PolarBear', PolarBearEntity);

  // Preload all assets before starting the play screen.
  me.loader
    .preload(
      [
        { name: 'polar-bear', type: 'image', src: 'assets/characters/polar-bear.png' },
        { name: 'tile-snow', type: 'image', src: 'assets/tiles/snow.png' },
        { name: 'tile-ice', type: 'image', src: 'assets/tiles/ice.png' },
        { name: 'tile-ice-cracks', type: 'image', src: 'assets/tiles/ice-cracks.png' },
      ],
      () => {
        // Register the play screen and switch to it once assets are ready.
        me.state.set(me.state.PLAY, new PlayScreen());
        me.state.change(me.state.PLAY);
      }
    )
    .catch(() => {
      console.error('Failed to load game assets.');
    });
});
