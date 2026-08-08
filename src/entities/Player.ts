import Phaser from 'phaser';

export type Direction = 'up' | 'down' | 'left' | 'right';

export class Player extends Phaser.Physics.Arcade.Sprite {
  private speed = 180;
  private facing: Direction = 'down';

  constructor(scene: Phaser.Scene, x: number, y: number) {
    super(scene, x, y, 'polar-bear');

    scene.add.existing(this);
    scene.physics.add.existing(this);

    this.setCollideWorldBounds(true);

    // Animations: one row per cardinal direction, 4 duplicate frames for a bobbing walk cycle.
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
          frameRate: 8,
          repeat: -1,
        });
      }
    });

    this.play('walk-down');
    this.setDepth(this.y);
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

    const animKey = `walk-${this.facing}`;
    if (moving) {
      if (this.anims.currentAnim?.key !== animKey) {
        this.play(animKey, true);
      }
    } else {
      this.stop();
      this.setFrame(this.facing === 'up' ? 0 : this.facing === 'right' ? 4 : this.facing === 'down' ? 8 : 12);
    }

    // Depth sort based on Y position so the bear appears in front/behind tiles correctly.
    this.setDepth(this.y);
  }
}
