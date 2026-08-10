import * as THREE from 'three';
import { GameSprite } from './GameSprite.ts';

export interface Decal {
  sprite: GameSprite;
  life: number;
  maxLife: number;
  grow: boolean;
  startScale: number;
  endScale: number;
  baseWidth: number;
  baseHeight: number;
}

/**
 * Manages short-lived billboard decals in the world: footprints that fade
 * behind the player, dust puffs on cracked ice, and landing bursts.
 */
export class DecalSystem {
  get sprites(): GameSprite[] {
    return this.decals.map((d) => d.sprite);
  }
  private decals: Decal[] = [];
  private parent: THREE.Object3D;
  private footprintTexture: THREE.Texture;
  private dustTexture: THREE.Texture;

  constructor(parent: THREE.Object3D) {
    this.parent = parent;
    this.footprintTexture = this.createFootprintTexture();
    this.dustTexture = this.createDustTexture();
  }

  spawnFootprint(x: number, y: number, direction: number): void {
    const material = new THREE.SpriteMaterial({
      map: this.footprintTexture,
      transparent: true,
      opacity: 0.5,
      depthWrite: false,
    });
    const sprite = new GameSprite(material, 20, 14);
    sprite.setPosition(x, y, 0.05);
    sprite.sprite.rotation.z = direction;

    this.parent.add(sprite.sprite);
    this.decals.push({
      sprite,
      life: 1.2,
      maxLife: 1.2,
      grow: false,
      startScale: 1,
      endScale: 0.7,
      baseWidth: 20,
      baseHeight: 14,
    });
  }

  spawnDust(x: number, y: number, count = 6): void {
    for (let i = 0; i < count; i++) {
      const material = new THREE.SpriteMaterial({
        map: this.dustTexture,
        transparent: true,
        opacity: 0.6,
        depthWrite: false,
      });
      const size = 12 + Math.random() * 16;
      const sprite = new GameSprite(material, size, size);
      const angle = Math.random() * Math.PI * 2;
      const dist = Math.random() * 12;
      sprite.setPosition(x + Math.cos(angle) * dist, y + Math.sin(angle) * dist, 0.2);

      this.parent.add(sprite.sprite);
      this.decals.push({
        sprite,
        life: 0.4 + Math.random() * 0.3,
        maxLife: 0.7,
        grow: true,
        startScale: 0.3,
        endScale: 1.5,
        baseWidth: size,
        baseHeight: size,
      });
    }
  }

  spawnLandingPuff(x: number, y: number): void {
    this.spawnDust(x, y, 12);
  }

  update(dt: number): void {
    const seconds = dt / 1000;

    for (let i = this.decals.length - 1; i >= 0; i--) {
      const decal = this.decals[i];
      decal.life -= seconds;

      const t = 1 - Math.max(0, decal.life / decal.maxLife);
      let scale: number;
      if (decal.grow) {
        scale = decal.startScale + (decal.endScale - decal.startScale) * t;
      } else {
        scale = decal.startScale;
      }
      const alpha = Math.max(0, decal.life / decal.maxLife);

      decal.sprite.setOpacity(alpha * 0.6);
      decal.sprite.setSize(decal.baseWidth * scale, decal.baseHeight * scale);

      if (decal.life <= 0) {
        this.parent.remove(decal.sprite.sprite);
        decal.sprite.sprite.material.dispose();
        this.decals.splice(i, 1);
      }
    }
  }

  private createFootprintTexture(): THREE.Texture {
    const canvas = document.createElement('canvas');
    canvas.width = 32;
    canvas.height = 24;
    const ctx = canvas.getContext('2d')!;

    ctx.fillStyle = 'rgba(255,255,255,0.6)';
    ctx.beginPath();
    ctx.ellipse(8, 6, 5, 3, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.beginPath();
    ctx.ellipse(24, 18, 5, 3, 0, 0, Math.PI * 2);
    ctx.fill();

    const texture = new THREE.CanvasTexture(canvas);
    texture.magFilter = THREE.NearestFilter;
    texture.minFilter = THREE.NearestFilter;
    return texture;
  }

  private createDustTexture(): THREE.Texture {
    const size = 32;
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d')!;

    const grad = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    grad.addColorStop(0, 'rgba(220,240,255,0.8)');
    grad.addColorStop(0.5, 'rgba(200,230,255,0.3)');
    grad.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, size, size);

    const texture = new THREE.CanvasTexture(canvas);
    texture.magFilter = THREE.LinearFilter;
    texture.minFilter = THREE.LinearFilter;
    return texture;
  }
}
