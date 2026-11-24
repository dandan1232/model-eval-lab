# Third-party notices

## three.js

This page vendors **three.js r170** (built from `three@0.170.0/build/three.module.min.js`)
directly inside `index.html` as a classic script, with the module's export table bound to
`window.THREE`. The copy is unmodified apart from that export binding and an added wrapper.

- Project: https://threejs.org
- Source: https://github.com/mrdoob/three.js
- Version: r170 (0.170.0)
- License: MIT

```
The MIT License

Copyright © 2010-2024 three.js authors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
```

The three.js license header is also preserved at the top of the vendored block inside
`index.html`.

## Everything else

The scene code, shaders, procedural canvas textures, geometry and audio synthesis are original
to this project. No image, model, font, audio or texture files are bundled or downloaded; all
visual and audio content is generated at runtime. Wang Wei's poem 《山居秋暝》 is in the public
domain.
