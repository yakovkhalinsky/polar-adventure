import * as THREE from 'three';

export interface CameraControllerOptions {
  /** How quickly the camera catches up to the target (0-1 per frame at 60fps). */
  smoothness?: number;
  /** World-space deadzone around the screen center before the camera moves. */
  deadzoneX?: number;
  deadzoneY?: number;
  /** Optional world bounds to keep the camera from showing empty space. */
  bounds?: THREE.Box2;
}

/**
 * Smoothly pans the world root so the target stays near the center of the
 * screen. This mimics a classic follow-camera without moving the Three.js
 * camera itself, which keeps the orthographic isometric projection stable.
 */
export class CameraController {
  private root: THREE.Object3D;
  private target = new THREE.Vector3();
  private current = new THREE.Vector3();
  private smoothness: number;
  private deadzoneX: number;
  private deadzoneY: number;
  private bounds?: THREE.Box2;
  private designWidth: number;
  private designHeight: number;

  constructor(
    root: THREE.Object3D,
    designWidth: number,
    designHeight: number,
    options: CameraControllerOptions = {}
  ) {
    this.root = root;
    this.designWidth = designWidth;
    this.designHeight = designHeight;
    this.smoothness = options.smoothness ?? 0.08;
    this.deadzoneX = options.deadzoneX ?? 48;
    this.deadzoneY = options.deadzoneY ?? 32;
    this.bounds = options.bounds;
  }

  /**
   * Snap the camera immediately to a position without smoothing. Useful for
   * the initial spawn so the first frame is already framed correctly.
   */
  snapTo(x: number, y: number): void {
    this.target.set(x, y, 0);
    this.current.copy(this.target);
    this.applyPosition();
  }

  /**
   * Update the follow target. The camera will only start moving once the
   * target leaves the deadzone around the screen center.
   */
  setTarget(x: number, y: number): void {
    this.target.set(x, y, 0);
  }

  update(dt: number): void {
    // Map 60fps smoothing to the actual frame time so it feels the same at
    // any refresh rate.
    const seconds = dt / 1000;
    const rate = 1 - Math.exp(-this.smoothness * seconds * 60);

    // Compute desired camera position: target offset by screen center.
    const desiredX = -this.target.x;
    const desiredY = -this.target.y;

    // Apply deadzone by only updating current when the target moves far enough.
    const dx = desiredX - this.current.x;
    const dy = desiredY - this.current.y;

    if (Math.abs(dx) > this.deadzoneX) {
      this.current.x += dx * rate;
    }
    if (Math.abs(dy) > this.deadzoneY) {
      this.current.y += dy * rate;
    }

    // Clamp to world bounds so the camera never shows beyond the edge.
    if (this.bounds) {
      const halfW = this.designWidth / 2;
      const halfH = this.designHeight / 2;

      const minX = -(this.bounds.max.x - halfW);
      const maxX = -(this.bounds.min.x + halfW);
      const minY = -(this.bounds.max.y - halfH);
      const maxY = -(this.bounds.min.y + halfH);

      this.current.x = Math.max(minX, Math.min(maxX, this.current.x));
      this.current.y = Math.max(minY, Math.min(maxY, this.current.y));
    }

    this.applyPosition();
  }

  private applyPosition(): void {
    this.root.position.set(this.current.x, this.current.y, 0);
  }
}
