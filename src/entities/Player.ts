import Phaser from 'phaser';

export type Direction = 'up' | 'down' | 'left' | 'right';

export class Player extends Phaser.Physics.Arcade.Sprite {
  private speed = 180;
  private facing: Direction = 'down';

  constructor(scene: Phaser.Scene, x: number, y: number, texture: string) {
    super(scene, x, y, texture);

    scene.add.existing(this);
    scene.physics.add.existing(this);

    this.setCollideWorldBounds(true);
    this.setDepth(this.y);
  }

  update(cursors: Phaser.Types.Input.Keyboard.CursorKeys, wasd: Record<Direction, Phaser.Input.Keyboard.Key>): void {
    let velocityX = 0;
    let velocityY = 0;

    if (cursors.left?.isDown || wasd.left.isDown) {
      velocityX = -this.speed;
      this.facing = 'left';
    } else if (cursors.right?.isDown || wasd.right.isDown) {
      velocityX = this.speed;
      this.facing = 'right';
    }

    if (cursors.up?.isDown || wasd.up.isDown) {
      velocityY = -this.speed;
      this.facing = 'up';
    } else if (cursors.down?.isDown || wasd.down.isDown) {
      velocityY = this.speed;
      this.facing = 'down';
    }

    this.setVelocity(velocityX, velocityY);

    // Simple bobbing animation while moving
    if (velocityX !== 0 || velocityY !== 0) {
      this.setScale(1 + Math.sin(this.scene.time.now / 100) * 0.03);
    } else {
      this.setScale(1);
    }

    // Depth sort based on Y position so the bear appears in front/behind tiles correctly
    this.setDepth(this.y);
  }
}
