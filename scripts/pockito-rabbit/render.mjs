import { mkdir, writeFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { build } from 'esbuild';
import puppeteer from 'puppeteer-core';

const [source, chrome, output] = process.argv.slice(2);
if (!source || !chrome || !output) {
  throw new Error('Usage: node render.mjs POCKITO_CHECKOUT CHROMIUM OUTPUT_DIRECTORY');
}
const clips = {
  boot: 2.4, idle: 7, walk: 0.8, happy: 3, sad: 4.5, sleepy: 5.5,
  sleep: 5.2, wake: 3.2, sit: 3, curious: 4, surprised: 1.6,
  excited: 3.5, wave: 2.8, hover: 3, pet: 1.9, carried: 1,
  settle: 1.2, drop: 1.8, grumpy: 3.8, dance: 6, think: 3.2, oops: 2.5,
};
const fps = 24;
const bodySize = 200;
const leftPad = 40;
const topPad = 144;
const width = bodySize + 2 * leftPad;
const height = bodySize + topPad;
const unitsPerPixel = 1.76 / bodySize;
const columns = 8;
const bundle = await build({
  stdin: {
    resolveDir: resolve(source),
    contents: `
      import * as THREE from 'three';
      import { Bunny } from './src/bunny/Bunny.js';
      import { Character } from './src/character/Character.js';
      import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
      let seed = 1234567;
      Math.random = () => ((seed = (1664525 * seed + 1013904223) >>> 0) / 4294967296);
      const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true, preserveDrawingBuffer: true });
      renderer.setClearColor(0, 0);
      renderer.setSize(${width}, ${height});
      renderer.toneMapping = THREE.NeutralToneMapping;
      const camera = new THREE.OrthographicCamera(
        ${-0.88 - leftPad * unitsPerPixel}, ${0.88 + leftPad * unitsPerPixel},
        ${0.88 + topPad * unitsPerPixel}, -0.88, 0.1, 20,
      );
      camera.position.set(-3.1, 1.6, 7);
      camera.lookAt(0, 0.70, 0);
      const pmrem = new THREE.PMREMGenerator(renderer);
      const room = new RoomEnvironment();
      const lightEnvironment = pmrem.fromScene(room, 0.04).texture;
      room.dispose();
      pmrem.dispose();
      function makeScene() {
        const s = new THREE.Scene();
        s.environment = lightEnvironment;
        s.environmentIntensity = 0.5;
        for (const [color, intensity, x, y, z] of [
          [0xffffff, 2.2, -3.5, 6, 6], [0xdfe9ff, 0.4, 5, 2, 4],
          [0x9fe8ff, 1.6, -5, 3, -5], [0x9fe8ff, 1.3, 5, 4, -5],
        ]) {
          const light = new THREE.DirectionalLight(color, intensity);
          light.position.set(x, y, z);
          s.add(light);
        }
        s.add(new THREE.AmbientLight(0xffffff, 0.45));
        return s;
      }
      window.renderClip = async (name, frames) => {
        const scene = makeScene();
        const bunny = new Bunny();
        await bunny.parts.ready;
        scene.add(bunny.root);
        const actor = new Character({mob: bunny, scene, settings: {walkSpeed: 1.1}});
        actor.setPlacement({scale: 1, floorY: 0, minX: -15, maxX: 15, halfHeight: 3});
        actor.allowAutoWake = false;
        const dt = 1 / ${fps};
        const canvas = document.createElement('canvas');
        canvas.width = ${columns * width};
        canvas.height = Math.ceil(frames / ${columns}) * ${height};
        const context = canvas.getContext('2d', {willReadFrequently: true});
        actor.trigger('idle', {duration: 100}, true);
        for (let k = 0; k < 12; k++) actor.update(dt, k * dt);
        if (name === 'drop') actor.lift = 0.48;
        actor.trigger(name, {duration: 100, x: 12, vx: 1.2, vy: -2}, true);
        if (name === 'pet') bunny.triggerPetReaction();
        if (name === 'hover') bunny.isHovered = true;
        for (let i = 0; i < frames; i++) {
          actor.update(dt, i * dt);
          if (name === 'walk') {
            bunny.walkAmount = 1;
            bunny.walkPhase = i * Math.PI * 2 / frames;
            bunny.applyPose(actor.final, 0);
            bunny.root.rotation.y = 0.95;
          }
          bunny.root.position.x = 0;
          for (const item of actor.emotes.active ?? []) {
            if (item.sprite) item.sprite.position.x -= actor.loco.x;
          }
          renderer.render(scene, camera);
          context.drawImage(renderer.domElement, (i % ${columns}) * ${width}, Math.floor(i / ${columns}) * ${height});
        }
        bunny.root.traverse(node => {
          node.geometry?.dispose();
          if (node.material?.map) node.material.map.dispose();
          node.material?.dispose?.();
        });
        const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
        const w = ${width}, h = ${height}, cols = ${columns};
        let left = w, top = h, right = 0, bottom = 0;
        for (let i = 0; i < frames; i++) {
          const x0 = (i % cols) * w;
          const y0 = Math.floor(i / cols) * h;
          for (let y = 0; y < h; y++) {
            const row = ((y0 + y) * canvas.width + x0) * 4 + 3;
            for (let x = 0; x < w; x++) {
              if (pixels[row + x * 4] >= 2) {
                left = Math.min(left, x);
                top = Math.min(top, y);
                right = Math.max(right, x + 1);
                bottom = Math.max(bottom, y + 1);
              }
            }
          }
        }
        const guard = 6;
        if (Math.min(left, top, w - right, h - bottom) < guard) {
          throw new Error(name + ' is clipped or too close to the frame edge: ' + [left, top, right, bottom]);
        }
        const rect = [left - guard, top - guard, right - left + 2 * guard, bottom - top + 2 * guard];
        const [x, y, cw, ch] = rect;
        const packed = document.createElement('canvas');
        packed.width = cw * cols;
        packed.height = Math.ceil(frames / cols) * ch;
        const packedContext = packed.getContext('2d');
        for (let i = 0; i < frames; i++) {
          const col = i % cols;
          const row = Math.floor(i / cols);
          packedContext.drawImage(canvas, col * w + x, row * h + y, cw, ch, col * cw, row * ch, cw, ch);
        }
        return { rect, png: packed.toDataURL('image/png').split(',')[1] };
      };
    `,
  },
  bundle: true,
  write: false,
  nodePaths: [join(dirname(fileURLToPath(import.meta.url)), 'node_modules')],
  loader: {'.glb': 'dataurl'},
  plugins: [{
    name: 'inline-glb',
    setup(build) {
      build.onResolve({filter: /\.glb\?inline$/}, args => ({
        path: resolve(args.resolveDir, args.path.slice(0, -7)),
      }));
    },
  }],
});
const browser = await puppeteer.launch({
  executablePath: chrome,
  headless: true,
  args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'],
});
try {
  await mkdir(output, {recursive: true});
  const page = await browser.newPage();
  page.on('pageerror', error => process.stderr.write(String(error) + '\n'));
  await page.addScriptTag({content: bundle.outputFiles[0].text});
  const manifest = {fps, bodySize, width, height, leftPad, topPad, columns, clips: {}, rects: {}};
  for (const [name, seconds] of Object.entries(clips)) {
    const frames = Math.round(seconds * fps);
    const data = await page.evaluate((name, frames) => window.renderClip(name, frames), name, frames);
    await writeFile(join(output, name + '.png'), Buffer.from(data.png, 'base64'));
    manifest.clips[name] = frames;
    manifest.rects[name] = data.rect;
    process.stdout.write(name + ' ' + frames + '\n');
  }
  await writeFile(join(output, 'animations.json'), JSON.stringify(manifest, null, 2) + '\n');
} finally {
  await browser.close();
}
