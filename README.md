# Polar Adventures

A polar / arctic / ice-themed isometric adventure game. You play as a polar bear exploring a frozen tile-based world.

## Tech stack

- [Phaser 3](https://phaser.io/) — 2D/2.5D game framework
- [TypeScript](https://www.typescriptlang.org/) — typed JavaScript
- [Vite](https://vitejs.dev/) — fast build tool and dev server

## Getting started

### Prerequisites

- Node.js >= 20
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

- **Arrow keys** or **WASD** — move the polar bear around the isometric ice grid.

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
    ├── main.ts             # Phaser game bootstrap
    ├── scenes/
    │   └── GameScene.ts    # Initial isometric ice scene
    └── entities/
        └── Player.ts       # Polar bear player class
```

## Notes on the framework choice

Phaser 3 was selected because it is purpose-built for browser-based 2D/2.5D games, has first-class TypeScript support, and produces a plain static bundle that GitHub Pages can serve without extra headers or server configuration. Its built-in camera, input, physics, scene manager, and asset pipeline make it a strong fit for an adventure game with movement, dialogue, inventory, and quests.

## License

MIT
