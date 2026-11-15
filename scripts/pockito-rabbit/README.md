# Render the rabbit assets

Check out [the pinned Pockito commit](https://github.com/AkkhileshCod3s/Pockito/tree/a101aacce1e8de49d508cad677813d2677bd77c4), then run these commands from this directory with Node.js and Chromium or Chrome installed.

```sh
npm ci
node render.mjs /path/to/Pockito /path/to/chromium ../../desktop/assets/pockito-rabbit
```

The renderer uses the upstream model, rabbit rig, facial expressions, and state machine. Node.js and Chromium are only needed to regenerate the frame sheets.
