/**
 * A lightweight HTML dialogue box overlay. Shows NPC lines or sign text one
 * page at a time and can be dismissed with the interact key.
 */
export class DialogueBox {
  private container: HTMLElement;
  private text: HTMLElement;
  private onDismiss?: () => void;

  constructor(parentId = 'ui-layer') {
    const parent = document.getElementById(parentId);
    if (!parent) {
      throw new Error(`DialogueBox parent #${parentId} not found`);
    }

    this.container = document.createElement('div');
    this.container.className = 'dialogue-box';
    this.container.style.display = 'none';

    this.text = document.createElement('p');
    this.text.className = 'dialogue-text';
    this.container.appendChild(this.text);

    const hint = document.createElement('small');
    hint.className = 'dialogue-hint';
    hint.textContent = 'Press E or Space to continue';
    this.container.appendChild(hint);

    parent.appendChild(this.container);
  }

  show(message: string, onDismiss?: () => void): void {
    this.text.textContent = message;
    this.onDismiss = onDismiss;
    this.container.style.display = 'block';
  }

  dismiss(): boolean {
    if (this.container.style.display === 'none') return false;
    this.container.style.display = 'none';
    this.onDismiss?.();
    this.onDismiss = undefined;
    return true;
  }

  get isOpen(): boolean {
    return this.container.style.display !== 'none';
  }
}
