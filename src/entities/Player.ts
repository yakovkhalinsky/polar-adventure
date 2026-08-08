import Phaser from 'phaser';

export type Direction = 'up' | 'down' | 'left' | 'right';

export class Player extends Phaser.Physics.Arcade.Sprite {
  private speed = 180;
  private facing: Direction = 'down';
  private walkTimer = 0;
  private lastTime = 0;

  constructor(scene: Phaser.Scene, x: number, y: number) {
    super(scene, x, y, 'polar-bear');

    scene.add.existing(this);
    scene.physics.add.existing(this);

    this.setCollideWorldBounds(true);

    // Origin at the bottom center so the sprite stands on its feet.
    // Depth sorting then uses the feet position, which matches the tile plane.
    this.setOrigin(0.5, 1.0);

    // Animations: one row per cardinal direction, 4 frames per direction.
    const directionRows: Record<Direction, number> = {
      up: 0,    // north
      right: 1, // east
      down: 2,  // south
      left: 3,  // west
    };

    Object.entries(directionRows).forEach(([dir, row]) => {
      const key = `walk-${dir}`;
      if (!scene.anims.exists(key)) {
        scene.anims.create({
          key,
          frames: scene.anims.generateFrameNumbers('polar-bear', {
            start: row * 4,
            end: row * 4 + 3,
          }),
          frameRate: 10,
          repeat: -1,
        });
      }
    });

    this.play('walk-down');
    this.updateDepth();
  }

  update(cursors: Phaser.Types.Input.Keyboard.CursorKeys, wasd: Record<Direction, Phaser.Input.Keyboard.Key>): void {
    let velocityX = 0;
    let velocityY = 0;
    let moving = false;

    if (cursors.left?.isDown || wasd.left.isDown) {
      velocityX = -this.speed;
      this.facing = 'left';
      moving = true;
    } else if (cursors.right?.isDown || wasd.right.isDown) {
      velocityX = this.speed;
      this.facing = 'right';
      moving = true;
    }

    if (cursors.up?.isDown || wasd.up.isDown) {
      velocityY = -this.speed;
      this.facing = 'up';
      moving = true;
    } else if (cursors.down?.isDown || wasd.down.isDown) {
      velocityY = this.speed;
      this.facing = 'down';
      moving = true;
    }

    this.setVelocity(velocityX, velocityY);

    const now = this.scene.time.now;
    const dt = this.lastTime ? now - this.lastTime : 16;
    this.lastTime = now;

    const animKey = `walk-${this.facing}`;
    if (moving) {
      if (this.anims.currentAnim?.key !== animKey) {
        this.play(animKey, true);
      }
      this.walkTimer += dt / 1000;
      this.animateWalk();
    } else {
      this.stop();
      // Show the first frame of the current facing direction.
      const idleFrame = {
        up: 0,
        right: 4,
        down: 8,
        left: 12,
      }[this.facing];
      this.setFrame(idleFrame);
      this.resetPose();
    }

    this.updateDepth();
  }

  private animateWalk(): void {
    // Add a bobbing / breathing motion while walking without fighting physics.
    const squash = 1 + Math.sin(this.walkTimer * Math.PI * 6 + Math.PI) * 0.05;
    const tilt = Math.sin(this.walkTimer * Math.PI * 4) * 2;
    this.setScale(0.9 * squash, 0.9 * (2 - squash));
    this.setRotation(Phaser.Math.DegToRad(tilt));
  }

  private resetPose(): void {
    this.setScale(0.9);
    this.walkTimer = 0;
  }

  private updateDepth(): void {
    // With bottom-center origin, this.y is the feet position on the tile plane.
    this.setDepth(this.y);
  }
}
