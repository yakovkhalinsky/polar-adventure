import * as me from 'melonjs';

export type Direction = 'up' | 'down' | 'left' | 'right';

const WALK_SPEED = 180;
const JUMP_VELOCITY = -320;
const GRAVITY_Y = 800;

const DIRECTION_ROWS: Record<Direction, number> = {
  up: 0,
  right: 1,
  down: 2,
  left: 3,
};

/**
 * Player-controlled polar bear entity for melonJS.
 *
 * It uses the existing 256x256 spritesheet (4 directions x 4 frames). The
 * spritesheet is loaded as an atlas; we pick the correct starting frame per
 * direction and update it manually for the walk cycle. Jump is implemented as
 * a vertical arc while keeping the shadow on the ground plane.
 */
export class PolarBearEntity extends me.Entity {
  private facing: Direction = 'down';
  private walkTimer = 0;
  private isJumping = false;
  private jumpTime = 0;
  private groundY = 0;
  private shadow!: me.Sprite;
  private sprite!: me.Sprite;

  constructor(x: number, y: number) {
    super(x, y, {
      width: 32,
      height: 32,
    });

    // Feet anchor so sorting and collision feel correct.
    this.anchorPoint.set(0.5, 1.0);

    // Use the existing spritesheet as a single sprite whose frame we change.
    this.sprite = new me.Sprite(0, 0, {
      image: 'polar-bear',
      framewidth: 64,
      frameheight: 64,
      anchorPoint: new me.Vector2d(0.5, 1.0),
    });
    this.renderable = this.sprite;
    this.sprite.setAnimationFrame(8); // idle down

    // Disable default gravity; we handle jump arc manually in update().
    this.body.setMaxVelocity(WALK_SPEED, WALK_SPEED * 2);
    this.body.setFriction(0, 0);
    this.body.gravity = 0;

    // Ground-level shadow sprite.
    this.shadow = new me.Sprite(0, 0, {
      image: this.createShadowTexture(),
      anchorPoint: new me.Vector2d(0.5, 0.5),
    });
    this.shadow.depth = 0;
    me.game.world.addChild(this.shadow, 0);

    this.groundY = y;
  }

  private createShadowTexture(): HTMLCanvasElement {
    // Build a small radial shadow texture on the fly and pass it directly to
    // the sprite. Avoids the asynchronous loader path, which can throw before
    // the generated image is registered.
    const canvas = document.createElement('canvas');
    canvas.width = 32;
    canvas.height = 12;
    const ctx = canvas.getContext('2d')!;
    const grad = ctx.createRadialGradient(16, 6, 2, 16, 6, 14);
    grad.addColorStop(0, 'rgba(0,0,0,0.35)');
    grad.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 32, 12);
    return canvas;
  }

  update(dt: number): boolean {
    const seconds = dt / 1000;
    let vx = 0;
    let vy = 0;
    let moving = false;

    if (me.input.isKeyPressed('left')) {
      vx = -WALK_SPEED;
      this.facing = 'left';
      moving = true;
    } else if (me.input.isKeyPressed('right')) {
      vx = WALK_SPEED;
      this.facing = 'right';
      moving = true;
    }

    if (me.input.isKeyPressed('up')) {
      vy = -WALK_SPEED;
      this.facing = 'up';
      moving = true;
    } else if (me.input.isKeyPressed('down')) {
      vy = WALK_SPEED;
      this.facing = 'down';
      moving = true;
    }

    // Jump on spacebar.
    if (me.input.isKeyPressed('jump') && !this.isJumping) {
      this.startJump();
    }

    if (this.isJumping) {
      this.updateJump(seconds);
    }

    // Apply horizontal velocity while preserving jump vertical state.
    this.body.vel.set(vx, this.isJumping ? this.body.vel.y : vy);

    // Procedural walk animation.
    if (moving && !this.isJumping) {
      this.walkTimer += seconds;
      this.applyWalkMotion(seconds);
    } else if (!this.isJumping) {
      this.resetPose();
      this.sprite.setAnimationFrame(DIRECTION_ROWS[this.facing] * 4);
    }

    // Sync shadow position and scale it with jump height.
    this.updateShadow();

    // Depth sort by feet position.
    this.depth = this.pos.y;

    return super.update(dt);
  }

  private startJump(): void {
    this.isJumping = true;
    this.jumpTime = 0;
    this.body.vel.y = JUMP_VELOCITY;
    this.sprite.currentTransform.rotate(
      me.Math.degToRad(-15 * (this.facing === 'left' ? -1 : this.facing === 'right' ? 1 : 0))
    );
  }

  private updateJump(dt: number): void {
    this.jumpTime += dt;
    // Simple gravity arc.
    this.body.vel.y += GRAVITY_Y * dt;
    this.pos.y += this.body.vel.y * dt;

    // Land when we return to ground level and are moving downward.
    if (this.body.vel.y > 0 && this.pos.y >= this.groundY) {
      this.land();
    }

    const rot = Math.sin(this.jumpTime * Math.PI * 2) * 10;
    this.sprite.currentTransform.identity();
    this.sprite.currentTransform.rotate(me.Math.degToRad(rot));
  }

  private land(): void {
    this.isJumping = false;
    this.pos.y = this.groundY;
    this.body.vel.y = 0;
    this.sprite.currentTransform.identity();
    this.sprite.currentTransform.scale(1.0, 0.7);

    // Restore scale after landing.
    me.timer.setTimeout(() => {
      this.sprite.currentTransform.identity();
      this.sprite.currentTransform.scale(0.9, 0.9);
    }, 150);
  }

  private applyWalkMotion(_dt: number): void {
    const t = this.walkTimer * Math.PI * 4;

    // Advance the walk frame based on time.
    const frameIndex = Math.floor(this.walkTimer * 10) % 4;
    this.sprite.setAnimationFrame(DIRECTION_ROWS[this.facing] * 4 + frameIndex);

    // Strong vertical bounce per step.
    const bounce = Math.abs(Math.sin(t)) * 8;
    this.pos.y -= bounce;

    // Side-to-side body rock.
    const rock = Math.sin(t) * 4;
    this.sprite.currentTransform.rotate(me.Math.degToRad(rock));

    // Squash-stretch synced to ground contact.
    const ground = Math.cos(t) > 0;
    const stretch = ground ? 1.08 : 0.95;
    const squish = ground ? 0.92 : 1.04;
    this.sprite.currentTransform.scale(0.9 * stretch, 0.9 * squish);

    // Tiny forward lunge per step.
    const lunge = Math.sin(t) * 2;
    this.pos.x +=
      lunge * (this.facing === 'left' ? -1 : this.facing === 'right' ? 1 : 0);
  }

  private resetPose(): void {
    this.sprite.currentTransform.identity();
    this.sprite.currentTransform.scale(0.9, 0.9);
    this.walkTimer = 0;
  }

  private updateShadow(): void {
    this.shadow.pos.set(this.pos.x, this.groundY);
    const height = Math.max(0, this.groundY - this.pos.y);
    const scale = Math.max(0.4, Math.min(1.0, 1 - height / 120));
    this.shadow.currentTransform.identity();
    this.shadow.currentTransform.scale(scale, scale);
    this.shadow.alpha = 0.25 * scale;
    this.shadow.depth = this.groundY - 1;
  }

  onDestroyEvent(): void {
    me.game.world.removeChild(this.shadow);
    super.onDestroyEvent();
  }
}
