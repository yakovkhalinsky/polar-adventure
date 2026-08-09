import * as THREE from 'three';

export interface AnimationClip {
  name: string;
  row: number;
  frames: number;
  fps: number;
  loop: boolean;
}

/**
 * Drives spritesheet animation on a Three.js texture by updating `repeat` and
 * `offset`. Assumes a uniform grid of frames.
 */
export class SpriteAnimation {
  private texture: THREE.Texture;
  private clips: Map<string, AnimationClip>;
  private current: AnimationClip | null = null;
  private timer = 0;
  private frame = 0;
  private cols: number;
  private rows: number;

  constructor(texture: THREE.Texture, clips: AnimationClip[], cols: number, rows: number) {
    this.texture = texture;
    this.cols = cols;
    this.rows = rows;
    this.clips = new Map(clips.map((c) => [c.name, c]));

    texture.magFilter = THREE.NearestFilter;
    texture.minFilter = THREE.NearestFilter;
    texture.repeat.set(1 / cols, 1 / rows);
    texture.offset.set(0, 1 - 1 / rows);
    texture.needsUpdate = true;
  }

  play(name: string, reset = true): void {
    const clip = this.clips.get(name);
    if (!clip) return;

    if (this.current?.name === name && !reset) return;

    this.current = clip;
    this.timer = 0;
    this.frame = 0;
    this.updateFrame();
  }

  update(dt: number): void {
    if (!this.current || this.current.frames <= 1) return;

    this.timer += dt;
    const duration = 1 / this.current.fps;

    if (this.timer >= duration) {
      this.timer -= duration;
      this.frame++;

      if (this.frame >= this.current.frames) {
        if (this.current.loop) {
          this.frame = 0;
        } else {
          this.frame = this.current.frames - 1;
        }
      }

      this.updateFrame();
    }
  }

  get currentClip(): string | null {
    return this.current?.name ?? null;
  }

  private updateFrame(): void {
    const col = this.frame % this.cols;
    const row = (this.current?.row ?? 0) % this.rows;

    this.texture.repeat.set(1 / this.cols, 1 / this.rows);
    this.texture.offset.set(col / this.cols, 1 - (row + 1) / this.rows);
    this.texture.needsUpdate = true;
  }
}
