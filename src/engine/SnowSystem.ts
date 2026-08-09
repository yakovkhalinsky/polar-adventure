import * as THREE from 'three';

export interface SnowSystemOptions {
  count?: number;
  areaWidth?: number;
  areaHeight?: number;
  fallSpeed?: number;
  windX?: number;
}

/**
 * Simple atmospheric snowfall using Three.js Points. Particles fall through
 * a box above the world and respawn at the top, giving the illusion of
 * continuous snow.
 */
export class SnowSystem {
  readonly points: THREE.Points;
  private geometry: THREE.BufferGeometry;
  private material: THREE.PointsMaterial;
  private positions: Float32Array;
  private velocities: Float32Array;
  private count: number;
  private areaWidth: number;
  private areaHeight: number;
  private areaDepth = 80;
  private windX: number;

  constructor(options: SnowSystemOptions = {}) {
    this.count = options.count ?? 400;
    this.areaWidth = options.areaWidth ?? 600;
    this.areaHeight = options.areaHeight ?? 600;
    this.windX = options.windX ?? 0.3;
    const fallSpeed = options.fallSpeed ?? 18;

    this.geometry = new THREE.BufferGeometry();
    this.positions = new Float32Array(this.count * 3);
    this.velocities = new Float32Array(this.count);

    for (let i = 0; i < this.count; i++) {
      this.positions[i * 3] = (Math.random() - 0.5) * this.areaWidth;
      this.positions[i * 3 + 1] = (Math.random() - 0.5) * this.areaHeight;
      this.positions[i * 3 + 2] = Math.random() * this.areaDepth;
      this.velocities[i] = fallSpeed * (0.7 + Math.random() * 0.6);
    }

    this.geometry.setAttribute('position', new THREE.BufferAttribute(this.positions, 3));

    const texture = this.createSnowflakeTexture();
    this.material = new THREE.PointsMaterial({
      color: '#ffffff',
      size: 3,
      map: texture,
      transparent: true,
      opacity: 0.7,
      depthWrite: false,
      blending: THREE.NormalBlending,
      sizeAttenuation: true,
    });

    this.points = new THREE.Points(this.geometry, this.material);
  }

  update(dt: number): void {
    const seconds = dt / 1000;

    for (let i = 0; i < this.count; i++) {
      const idx = i * 3;
      this.positions[idx + 2] -= this.velocities[i] * seconds;
      this.positions[idx] += this.windX * seconds;

      // Respawn when below the ground plane.
      if (this.positions[idx + 2] < 0) {
        this.positions[idx] = (Math.random() - 0.5) * this.areaWidth;
        this.positions[idx + 1] = (Math.random() - 0.5) * this.areaHeight;
        this.positions[idx + 2] = this.areaDepth;
      }
    }

    this.geometry.attributes.position.needsUpdate = true;
  }

  dispose(): void {
    this.geometry.dispose();
    this.material.dispose();
    this.material.map?.dispose();
  }

  private createSnowflakeTexture(): THREE.Texture {
    const size = 32;
    const canvas = document.createElement('canvas');
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d')!;

    const grad = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    grad.addColorStop(0, 'rgba(255,255,255,0.9)');
    grad.addColorStop(0.5, 'rgba(255,255,255,0.3)');
    grad.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, size, size);

    const texture = new THREE.CanvasTexture(canvas);
    texture.magFilter = THREE.LinearFilter;
    texture.minFilter = THREE.LinearFilter;
    return texture;
  }
}
