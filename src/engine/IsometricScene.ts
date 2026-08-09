import * as THREE from 'three';

/**
 * Manages the Three.js renderer, orthographic isometric camera, lights,
 * and the root scene. Keeps the canvas filling its parent and a fixed
 * world-up vector for isometric sprites.
 */
export class IsometricScene {
  readonly scene: THREE.Scene;
  readonly camera: THREE.OrthographicCamera;
  readonly renderer: THREE.WebGLRenderer;

  private parent: HTMLElement;
  private designWidth = 1024;
  private designHeight = 768;
  private zoom = 1;

  constructor(parentId: string) {
    const parent = document.getElementById(parentId);
    if (!parent) {
      throw new Error(`Missing parent element #${parentId}`);
    }
    this.parent = parent;

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color('#0b1d2e');

    // Arctic lighting: cool ambient + directional moon/sun.
    const ambient = new THREE.AmbientLight('#a6d2ff', 0.6);
    this.scene.add(ambient);

    const dir = new THREE.DirectionalLight('#ffffff', 0.8);
    dir.position.set(20, 40, 30);
    this.scene.add(dir);

    this.camera = new THREE.OrthographicCamera(
      -this.designWidth / 2,
      this.designWidth / 2,
      this.designHeight / 2,
      -this.designHeight / 2,
      1,
      2000
    );

    // True 2:1 pixel-art isometric orientation.
    // Equal x/z with y at half the horizontal distance gives the classic
    // diamond ratio used by 64x32 tiles.
    const distance = 400;
    this.camera.position.set(distance, distance / 2, distance);
    this.camera.lookAt(0, 0, 0);

    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      alpha: false,
      powerPreference: 'high-performance',
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(parent.clientWidth, parent.clientHeight);
    this.renderer.shadowMap.enabled = false; // keep simple for now
    this.parent.appendChild(this.renderer.domElement);

    window.addEventListener('resize', this.handleResize);
    this.handleResize();
  }

  setZoom(zoom: number): void {
    this.zoom = zoom;
    this.updateCameraZoom();
  }

  render(): void {
    this.renderer.render(this.scene, this.camera);
  }

  dispose(): void {
    window.removeEventListener('resize', this.handleResize);
    this.renderer.dispose();
    this.parent.removeChild(this.renderer.domElement);
  }

  private handleResize = (): void => {
    const width = this.parent.clientWidth;
    const height = this.parent.clientHeight;

    this.renderer.setSize(width, height);
    this.updateCameraZoom(width, height);
  };

  private updateCameraZoom(width = this.parent.clientWidth, height = this.parent.clientHeight): void {
    const aspect = width / height;
    const designRatio = this.designWidth / this.designHeight;

    let viewWidth: number;
    let viewHeight: number;

    if (aspect < designRatio) {
      viewWidth = this.designWidth / this.zoom;
      viewHeight = viewWidth / aspect;
    } else {
      viewHeight = this.designHeight / this.zoom;
      viewWidth = viewHeight * aspect;
    }

    this.camera.left = -viewWidth / 2;
    this.camera.right = viewWidth / 2;
    this.camera.top = viewHeight / 2;
    this.camera.bottom = -viewHeight / 2;
    this.camera.updateProjectionMatrix();
  }
}
