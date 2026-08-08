import Phaser from 'phaser';

export type Direction = 'up' | 'down' | 'left' | 'right';

const WALK_SPEED = 180;
const JUMP_VELOCITY = -320;
const GRAVITY_Y = 800;

export class Player extends Phaser.Physics.Arcade.Sprite {
  private facing: Direction = 'down';
  private walkTimer = 0;
  private isJumping = false;
  private jumpTime = 0;
  private shadow!: Phaser.GameObjects.Ellipse;

  constructor(scene: Phaser.Scene, x: number, y: number) {
    super(scene, x, y, 'polar-bear');

    scene.add.existing(this);
    scene.physics.add.existing(this);

    // Feet origin so sorting and landing feel correct.
    this.setOrigin(0.5, 1.0);

    // Slightly dampen default gravity so the jump arc is readable.
    (this.body as Phaser.Physics.Arcade.Body).setGravityY(GRAVITY_Y);

    this.createAnimations(scene);
    this.createShadow(scene);

    this.play('walk-down');
    this.updateDepth();
  }

  private createAnimations(scene: Phaser.Scene): void {
    const directionRows: Record<Direction, number> = {
      up: 0,
      right: 1,
      down: 2,
      left: 3,
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
  }

  private createShadow(scene: Phaser.Scene): void {
    this.shadow = scene.add.ellipse(this.x, this.y, 32, 12, 0x000000, 0.25);
    this.shadow.setDepth(this.y - 1);
  }

  update(
    cursors: Phaser.Types.Input.Keyboard.CursorKeys,
    wasd: Record<Direction, Phaser.Input.Keyboard.Key>,
  ): void {
    const dt = this.scene.game.loop.delta / 1000;

    // Direction + horizontal movement.
    let vx = 0;
    let vy = 0;
    let moving = false;

    if (cursors.left?.isDown || wasd.left.isDown) {
      vx = -WALK_SPEED;
      this.facing = 'left';
      moving = true;
    } else if (cursors.right?.isDown || wasd.right.isDown) {
      vx = WALK_SPEED;
      this.facing = 'right';
      moving = true;
    }

    if (cursors.up?.isDown || wasd.up.isDown) {
      vy = -WALK_SPEED;
      this.facing = 'up';
      moving = true;
    } else if (cursors.down?.isDown || wasd.down.isDown) {
      vy = WALK_SPEED;
      this.facing = 'down';
      moving = true;
    }

    // Jump on spacebar.
    if (Phaser.Input.Keyboard.JustDown(cursors.space!) && !this.isJumping) {
      this.startJump();
    }

    if (this.isJumping) {
      this.updateJump(dt);
    }

    // Preserve velocity while jumping.
    if (this.isJumping) {
      this.setVelocity(vx, this.body?.velocity.y ?? 0);
    } else {
      this.setVelocity(vx, vy);
    }

    // Sprite animation + procedural walk bounce.
    const animKey = `walk-${this.facing}`;
    if (moving && !this.isJumping) {
      if (this.anims.currentAnim?.key !== animKey) {
        this.play(animKey, true);
      }
      this.walkTimer += dt;
      this.applyWalkMotion();
    } else if (!this.isJumping) {
      this.stop();
      const idleFrame = { up: 0, right: 4, down: 8, left: 12 }[this.facing];
      this.setFrame(idleFrame);
      this.resetPose();
    }

    this.updateShadow();
    this.updateDepth();
  }

  private startJump(): void {
    this.isJumping = true;
    this.jumpTime = 0;
    (this.body as Phaser.Physics.Arcade.Body).setVelocityY(JUMP_VELOCITY);
    this.setRotation(Phaser.Math.DegToRad(-15 * (this.facing === 'left' ? -1 : this.facing === 'right' ? 1 : 0)));
  }

  private updateJump(dt: number): void {
    this.jumpTime += dt;

    // Land when velocity turns positive and we are close to the floor plane.
    const groundY = (this.body as any).startY ?? this.y;
    if (this.body && this.body.velocity.y > 0 && this.y >= groundY) {
      this.land();
    }

    // Slight forward rotation during the jump arc.
    const rot = Math.sin(this.jumpTime * Math.PI * 2) * 10;
    this.setRotation(Phaser.Math.DegToRad(rot));
  }

  private land(): void {
    this.isJumping = false;
    this.setRotation(0);
    this.setScale(1.0, 0.7); // squash on landing
    this.scene.tweens.add({
      targets: this,
      scaleX: 0.9,
      scaleY: 0.9,
      duration: 150,
      ease: 'Back.out',
    });
  }

  private applyWalkMotion(): void {
    const t = this.walkTimer * Math.PI * 4; // two full step cycles per second

    // Strong vertical bounce per step.
    const bounce = Math.abs(Math.sin(t)) * 8;
    this.y -= bounce;

    // Side-to-side body rock.
    const rock = Math.sin(t) * 4;
    this.setRotation(Phaser.Math.DegToRad(rock));

    // Squash-stretch synced to the ground contact.
    const ground = Math.cos(t) > 0;
    const stretch = ground ? 1.08 : 0.95;
    const squish = ground ? 0.92 : 1.04;
    this.setScale(0.9 * stretch, 0.9 * squish);

    // Tiny forward lunge per step.
    const lunge = Math.sin(t) * 2;
    this.x += lunge * (this.facing === 'left' ? -1 : this.facing === 'right' ? 1 : 0);
  }

  private resetPose(): void {
    this.setScale(0.9);
    this.setRotation(0);
    this.walkTimer = 0;
  }

  private updateShadow(): void {
    // Shadow stays on the ground plane.
    this.shadow.setPosition(this.x, this.y);

    // Make shadow shrink/grow with jump height.
    const groundY = (this.body as any).startY ?? this.y;
    const height = Math.max(0, groundY - this.y);
    const scale = Phaser.Math.Clamp(1 - height / 120, 0.4, 1.0);
    this.shadow.setScale(scale, scale);
    this.shadow.setAlpha(0.25 * scale);
    this.shadow.setDepth(this.y - 1);
  }

  private updateDepth(): void {
    // Feet position determines render order.
    this.setDepth(this.y);
  }
}
