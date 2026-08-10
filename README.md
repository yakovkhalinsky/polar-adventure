# Polar Adventures

A polar / arctic / ice-themed 2D side-scrolling adventure game. You play as a polar bear running, jumping, and exploring a frozen platforming world.

## Tech stack

- [Three.js](https://threejs.org/) — WebGL renderer and sprite system
- [TypeScript](https://www.typescriptlang.org/) — typed JavaScript
- [Vite](https://vitejs.dev/) — fast build tool and dev server

## Getting started

### Prerequisites

- Node.js >= 22
- npm (bundled with Node.js)

### Install dependencies

```bash
npm install
```

### Run the development server

```bash
npm run dev
```

Vite will start a local server (usually http://localhost:5173) and open the game in your browser. The page reloads automatically when you edit source files.

### Type-check only

```bash
npm run typecheck
```

### Build for production

```bash
npm run build
```

This compiles TypeScript and bundles everything into the `dist/` directory. The output is a set of static files ready for any static host, including GitHub Pages.

### Preview the production build

```bash
npm run preview
```

## Controls

- **Arrow keys** or **A / D** — run left and right
- **Space**, **W**, or **Arrow Up** — jump
- **E** — talk to NPCs and read signs
- **X** or **Shift** — attack

## Deployment

The repository includes a GitHub Actions workflow at `.github/workflows/deploy.yml` that builds the project and publishes `dist/` to GitHub Pages on every push to the default branch (`main`).

To enable Pages deployment:

1. Push this repository to GitHub.
2. In the repository settings, set **Pages** → **Build and deployment** → **Source** to **GitHub Actions**.
3. Push to `main` (or merge a pull request). The workflow will build and deploy the site.

## Project structure

```
.
├── index.html              # Entry HTML page
├── package.json            # Dependencies and scripts
├── tsconfig.json           # TypeScript configuration
├── vite.config.ts          # Vite build configuration
├── README.md               # This file
├── .gitignore              # Ignored files
├── .github/workflows/      # CI/CD workflows
│   └── deploy.yml          # GitHub Pages deploy workflow
└── src/
    ├── main.ts             # Asset loading and game bootstrap
    ├── screens/
    │   └── PlayScreen.ts   # Main side-scrolling gameplay screen
    ├── entities/
    │   └── PolarBear.ts     # Player-controlled polar bear
    ├── engine/
    │   ├── SideScrollScene.ts   # Three.js renderer and camera
    │   ├── GameSprite.ts        # Billboard sprite helper
    │   ├── PlatformTileMap.ts   # Horizontal level tiles
    │   ├── SpriteAnimation.ts # Spritesheet animation
    │   ├── SnowSystem.ts        # Atmospheric snowfall
    │   ├── DecalSystem.ts       # Footprints and dust effects
    │   ├── CameraController.ts  # Smooth follow camera
    │   ├── WorldObject.ts       # Generic placed objects
    │   └── Interactables.ts     # NPCs, collectibles, signs
    └── ui/
        └── DialogueBox.ts   # In-game dialogue box
```

## License

MIT
