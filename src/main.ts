import * as me from 'melonjs';
import { PlayScreen } from './screens/PlayScreen.ts';
import { PolarBearEntity } from './entities/PolarBearEntity.ts';

// Register the custom entity so Tiled object layers can spawn it if needed.
me.pool.register('PolarBear', PolarBearEntity);

// Bootstrap melonJS into the existing #game-container div.
me.device.onReady(() => {
  const app = new me.Application(1024, 768, {
    parent: 'game-container',
    renderer: me.video.AUTO,
    scale: 'auto',
    scaleMethod: 'fit',
    transparent: true,
  });

  if (!app.isInitialized) {
    console.error('Failed to initialize melonJS application.');
    return;
  }

  // Disable smoothing for crisp pixel-art-like sprites.
  app.renderer.setAntiAlias(false);

  // Audio is not required for this demo; initialise with no audio to avoid
  // the WebAudio unlock prompt on some platforms.
  me.audio.init('mp3,ogg,wav');

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

  // Register the play screen and switch to it.
  me.state.set(me.state.PLAY, new PlayScreen());
  me.state.change(me.state.PLAY);
});
