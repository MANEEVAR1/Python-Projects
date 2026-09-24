// Small helpers: $ finds one element, $$ finds all matching elements
const $ = s => document.querySelector(s), $$ = s => [...document.querySelectorAll(s)];

// ---- Word picking: no word repeats until every word of that length has been used ----
const seen = {};
function seenSet(n) {
  if (!seen[n]) {
    try {
      seen[n] = new Set(JSON.parse(localStorage.getItem('sb' + n) || '[]'));
    } catch (e) {
      seen[n] = new Set();
    }
  }
  return seen[n];
}
function pickWord(n) {
  const all = POOL[n].trim().split(/\s+/), s = seenSet(n);
  let c = all.filter(w => !s.has(w));
  if (!c.length) {
    s.clear();
    c = all;
  }
  const w = c[Math.random() * c.length | 0];
  s.add(w);
  try {
    localStorage.setItem('sb' + n, JSON.stringify([...s]));
  } catch (e) {
  }
  return w;
}

// ---- Audio: sound effects, haptics (vibration) and background music ----
let on = true, mOn = true, ac, mg, tempo = 1, step = 0, nt = 0, mt = null, scr = 's-intro';
const AC = window.AudioContext || window.webkitAudioContext;
function A() {
  try {
    if (!ac) {
      ac = new AC();
      mg = ac.createGain();
      mg.gain.value = mOn ? 1 : 0;
      mg.connect(ac.destination);
    }
    if (ac.state == 'suspended')
      ac.resume();
  } catch (e) {
  }
  return ac;
}
function tone(f, d = 0.12, ty = 'sine', v = 0.08, at = 0, to) {
  if (!on)
    return;
  try {
    A();
    const t = ac.currentTime + at, o = ac.createOscillator(), g = ac.createGain();
    o.type = ty;
    o.frequency.setValueAtTime(f, t);
    if (to)
      o.frequency.exponentialRampToValueAtTime(to, t + d);
    g.gain.setValueAtTime(v, t);
    g.gain.exponentialRampToValueAtTime(0.0001, t + d);
    o.connect(g);
    g.connect(ac.destination);
    o.start(t);
    o.stop(t + d);
  } catch (e) {
  }
}
const vib = p => {
  try {
    on && navigator.vibrate && navigator.vibrate(p);
  } catch (e) {
  }
};
const sfx = {
  tap: () => {
    tone(660, 0.05);
    vib(5);
  },
  key: () => {
    tone(500 + Math.random() * 90, 0.06, 'triangle');
    vib(6);
  },
  del: () => {
    tone(300, 0.07, 'triangle');
    vib(4);
  },
  clank: () => {
    tone(170, 0.14, 'square', 0.04);
    tone(1300, 0.05, 'triangle', 0.03);
  },
  snap: () => {
    tone(240, 0.4, 'sawtooth', 0.09, 0, 55);
    tone(90, 0.45, 'square', 0.06);
    vib([
      60,
      40,
      120
    ]);
  },
  short: () => {
    tone(200, 0.15, 'square', 0.05);
    vib(30);
  },
  win: () => {
    [
      523,
      659,
      784,
      1047
    ].forEach((f, i) => tone(f, 0.28, 'triangle', 0.09, i * 0.11));
    vib([
      40,
      30,
      40,
      30,
      120
    ]);
  },
  lose: () => {
    [
      392,
      330,
      262,
      196
    ].forEach((f, i) => tone(f, 0.42, 'sawtooth', 0.06, i * 0.2));
    vib([
      200,
      60,
      300
    ]);
  }
};

// Background music: a slow looping A minor chord progression, generated live
const CH = [
    [
      57,
      60,
      64
    ],
    [
      53,
      57,
      60
    ],
    [
      48,
      52,
      55
    ],
    [
      55,
      59,
      62
    ]
  ], mf = m => 440 * 2 ** ((m - 69) / 12);
function mn(m, t, d, ty, v) {
  const o = ac.createOscillator(), g = ac.createGain();
  o.type = ty;
  o.frequency.value = mf(m);
  g.gain.setValueAtTime(0.0001, t);
  g.gain.linearRampToValueAtTime(v, t + 0.03);
  g.gain.exponentialRampToValueAtTime(0.0001, t + d);
  o.connect(g);
  g.connect(mg);
  o.start(t);
  o.stop(t + d + 0.05);
}
function tick() {
  if (!ac)
    return;
  while (nt < ac.currentTime + 0.4) {
    const c = CH[(step >> 3) % 4], s = step % 8, st = 0.32 / tempo;
    mn(c[[
      0,
      1,
      2,
      1,
      2,
      1,
      0,
      1
    ][s]] + 12, nt, 0.6, 'triangle', 0.05);
    if (s == 0) {
      mn(c[0] - 12, nt, st * 7, 'sine', 0.11);
      c.forEach(m => mn(m, nt, st * 7.5, 'sine', 0.02));
    }
    if (s == 4)
      mn(c[0] - 5, nt, st * 3, 'sine', 0.06);
    nt += st;
    step++;
  }
}
function musicOn() {
  if (!A() || mt)
    return;
  mg.gain.setTargetAtTime(1, ac.currentTime, 0.1);
  nt = ac.currentTime + 0.05;
  mt = setInterval(tick, 120);
}
function musicOff() {
  clearInterval(mt);
  mt = null;
  if (ac)
    mg.gain.setTargetAtTime(0, ac.currentTime, 0.05);
}
function duck(sec) {
  if (!ac || !mOn)
    return;
  mg.gain.setTargetAtTime(0, ac.currentTime, 0.15);
  setTimeout(() => {
    if (mOn)
      mg.gain.setTargetAtTime(1, ac.currentTime, 0.7);
  }, sec * 1000);
}
[
  'pointerdown',
  'keydown'
].forEach(ev => addEventListener(ev, () => {
  if (mOn)
    musicOn();
}));
function tg(sel, v, lab) {
  const e = $(sel);
  e.classList.toggle('off', !v);
  e.setAttribute('aria-pressed', v);
  e.setAttribute('aria-label', lab + (v ? ' on' : ' off'));
}
$('#mus').onclick = () => {
  mOn = !mOn;
  tg('#mus', mOn, 'Music');
  mOn ? musicOn() : musicOff();
};
$('#snd').onclick = () => {
  on = !on;
  tg('#snd', on, 'Sound effects and haptics');
  sfx.tap();
};

// ---- Screens: intro, word length, game and goodbye ----
function show(id) {
  scr = id;
  $$('.scr').forEach(e => e.classList.toggle('on', e.id === id));
  window.scrollTo(0, 0);
  if (id == 's-intro') {
    $('#ierr').textContent = '';
    tempo = 1;
    document.documentElement.style.setProperty('--w', 0);
  }
  const f = {
    's-intro': '#yes',
    's-bye': '#back'
  }[id];
  if (f)
    setTimeout(() => $(f).focus({ preventScroll: true }), 80);
}

// ---- Tiles (planks), the title and the word length picker ----
function tile(ch, cls, i, y = 0, r = 0) {
  const e = document.createElement('div');
  e.className = 'tile ' + cls;
  e.textContent = ch;
  e.style.cssText = `--i:${ i };--y:${ y }px;--r:${ r }deg`;
  return e;
}
[
  [
    'spell',
    0
  ],
  [
    'bridge',
    5
  ]
].forEach(([w, o]) => {
  const r = document.createElement('div');
  r.className = 'ttl';
  [...w].forEach((c, i) => {
    const e = tile(c, 'tt', o + i, Math.sin(i / (w.length - 1) * Math.PI) * -14, (i / (w.length - 1) - 0.5) * 8);
    e.style.setProperty('--t', 'clamp(46px,12vw,84px)');
    e.onmouseenter = () => {
      pop(e);
      sfx.clank();
    };
    r.appendChild(e);
  });
  $('#title').appendChild(r);
});
const go = (id, fn) => {
  $(id).onclick = () => {
    try {
      sfx.tap();
    } catch (e) {
    }
    fn();
  };
};
go('#yes', () => show('s-len'));
go('#no', () => show('s-bye'));
go('#back', () => show('s-intro'));
const modeOf = n => n <= 4 ? 'short' : n <= 6 ? 'arch' : n <= 8 ? 'sus' : 'zig';
const modeName = {
  short: 'Footbridge',
  arch: 'Arch bridge',
  sus: 'Suspension bridge',
  zig: 'Switchback bridge'
};
const yOf = (m, i, n) => {
  const t = n > 1 ? i / (n - 1) : 0;
  return m == 'arch' ? [
    -Math.sin(Math.PI * t) * 30,
    (t - 0.5) * 20
  ] : m == 'sus' ? [
    4 * t * (1 - t) * 42,
    -(t - 0.5) * 16
  ] : m == 'zig' ? [
    i % 2 ? 12 : -12,
    i % 2 ? 2.5 : -2.5
  ] : [
    0,
    0
  ];
};
for (let k = 3; k <= 10; k++) {
  const b = document.createElement('button');
  b.className = 'lb';
  const m = modeOf(k);
  b.innerHTML = `<b>${ k }</b><small>${ modeName[m] }</small><div class="mini">${ [...Array(k)].map((_, i) => `<i style="--i:${ i };--y:${ yOf(m, i, k)[0] / 3 + 8 }px"></i>`).join('') }</div>`;
  b.onclick = () => {
    sfx.tap();
    start(k);
  };
  $('#lens').appendChild(b);
}

// ---- The game: same rules as the Python version ----
let word, n, hint, hs, hl, miss, g = [], cur = 0, used = 0, over = false, mode;
const pyRound = x => {
  const f = Math.floor(x), d = x - f;
  return d < 0.5 ? f : d > 0.5 ? f + 1 : f % 2 ? f + 1 : f;
};
function start(len) {
  n = len;
  word = pickWord(n);
  hl = Math.max(1, pyRound(n * 0.6));
  hs = Math.floor(Math.random() * (n - hl + 1));
  hint = word.slice(hs, hs + hl);
  miss = [...Array(n).keys()].filter(i => i < hs || i >= hs + hl);
  g = miss.map(() => '');
  cur = 0;
  used = 0;
  over = false;
  mode = modeOf(n);
  tempo = 1;
  $('#res').classList.remove('on');
  $('#msg').textContent = '';
  $('#msg').className = '';
  $('#hist').innerHTML = '';
  document.documentElement.style.setProperty('--w', 0);
  $('#piers').innerHTML = '<div class="pier"></div>'.repeat(5);
  show('s-game');
  build();
  chance();
}
function chance() {
  $('#cap').textContent = `${ modeName[mode] }, ${ n } letters. Chance ${ Math.min(used + 1, 5) } of 5`;
}
function fit() {
  const per = n > 8 ? 5 : n, gap = 10, av = Math.min(innerWidth - 32, 760);
  const base = {
    short: 96,
    arch: 78,
    sus: 70,
    zig: 72
  }[mode];
  const t = Math.min(base, (av - gap * (per - 1) - 24) / per);
  const sp = $('.span');
  sp.style.setProperty('--t', t + 'px');
  sp.style.width = per * t + (per - 1) * gap + 'px';
}
function build() {
  const br = $('#bridge');
  br.className = 'bridge ' + mode;
  br.innerHTML = '';
  const sp = document.createElement('div');
  sp.className = 'span';
  if (mode == 'sus')
    sp.innerHTML = '<svg viewBox="0 0 100 84" preserveAspectRatio="none"><path d="M0 0Q50 84 100 0"/></svg><div class="tw" style="left:-22px"></div><div class="tw" style="right:-22px"></div>';
  const dk = document.createElement('div');
  dk.className = 'deck';
  if (mode == 'sus')
    dk.style.paddingTop = '4px';
  for (let i = 0; i < n; i++) {
    const [y, r] = yOf(mode, i, n), isH = i >= hs && i < hs + hl, e = tile(isH ? word[i] : '', isH ? 'h' : 'm', i, y, r);
    e.dataset.i = i;
    if (isH)
      setTimeout(sfx.clank, 350 + i * 70);
    else
      e.onclick = () => {
        if (over)
          return;
        cur = miss.indexOf(i);
        sfx.tap();
        paint();
      };
    dk.appendChild(e);
  }
  sp.appendChild(dk);
  br.appendChild(sp);
  fit();
  $('#hint').innerHTML = '<b>Hint Letters:</b> ' + hint;
  paint();
}
addEventListener('resize', () => {
  if (scr == 's-game' && $('.span'))
    fit();
});
const T = i => $(`.tile[data-i="${ i }"]`);
function paint() {
  if (over)
    return;
  miss.forEach((idx, k) => {
    const e = T(idx);
    e.textContent = g[k];
    e.classList.toggle('f', !!g[k]);
    e.classList.toggle('cur', k == cur);
  });
}
function pop(e) {
  e.classList.remove('pop');
  void e.offsetWidth;
  e.classList.add('pop');
}
function type(ch) {
  if (over || scr != 's-game')
    return;
  g[cur] = ch;
  pop(T(miss[cur]));
  sfx.key();
  if (cur < miss.length - 1)
    cur++;
  paint();
}
function del() {
  if (over || scr != 's-game')
    return;
  if (!g[cur] && cur > 0)
    cur--;
  g[cur] = '';
  sfx.del();
  paint();
}
function move(d) {
  if (over || scr != 's-game')
    return;
  cur = Math.max(0, Math.min(miss.length - 1, cur + d));
  sfx.tap();
  paint();
}
function say(t, bad) {
  const m = $('#msg');
  m.textContent = t;
  m.className = '';
  void m.offsetWidth;
  m.className = bad ? 'bad' : '';
}

// Submit a guess: it is compared with the secret word, ignoring upper/lower case
function submit() {
  if (over || scr != 's-game')
    return;
  const guess = [...word].map((c, i) => i >= hs && i < hs + hl ? c : g[miss.indexOf(i)]).join('');
  used++;
  if (guess.toLowerCase() == word.toLowerCase())
    return win();
  $$('.pier')[used - 1].classList.add('snap');
  sfx.snap();
  tempo = 1 + used * 0.07;
  const br = $('#bridge');
  br.classList.remove('shake');
  void br.offsetWidth;
  br.classList.add('shake');
  document.documentElement.style.setProperty('--w', used);
  const h = document.createElement('span');
  h.textContent = [...word].map((c, i) => i >= hs && i < hs + hl ? c : g[miss.indexOf(i)] || '_').join('');
  $('#hist').appendChild(h);
  g = miss.map(() => '');
  cur = 0;
  paint();
  if (used == 5)
    return lose();
  say('Wrong guess. Try again.', 1);
  chance();
}
function end(t, s, x) {
  setTimeout(() => {
    $('#rt').textContent = t;
    $('#rs').textContent = s;
    $('#rx').textContent = x;
    $('#res').classList.add('on');
  }, 1900);
}

// Correct guess
function win() {
  over = true;
  say('Correct! You did it');
  sfx.win();
  duck(2.4);
  $$('.tile[data-i]').forEach(e => {
    e.textContent = word[e.dataset.i];
    e.classList.remove('cur', 'm', 'f');
    e.classList.add('win');
  });
  const c = [
    '#fff',
    '#D3D3D3',
    '#8c8cff',
    '#b5b5ff'
  ];
  for (let i = 0; i < 48; i++) {
    const e = document.createElement('i');
    e.className = 'conf';
    e.style.background = c[i % 4];
    document.body.appendChild(e);
    const a = Math.random() * Math.PI * 2, d = 120 + Math.random() * 320;
    e.animate([
      {
        transform: 'translate(0,0) rotate(0)',
        opacity: 1
      },
      {
        transform: `translate(${ Math.cos(a) * d }px,${ Math.sin(a) * d + 220 }px) rotate(${ Math.random() * 720 }deg)`,
        opacity: 0
      }
    ], {
      duration: 1400 + Math.random() * 900,
      easing: 'cubic-bezier(.2,.7,.4,1)'
    }).onfinish = () => e.remove();
  }
  end('Correct! You did it', `The word was ${ word }.`, '');
}

// Fifth wrong guess: reveal the word and let the bridge fall
function lose() {
  over = true;
  say('The bridge is down.', 1);
  $$('.tile[data-i]').forEach(e => {
    e.textContent = word[e.dataset.i];
    if (e.classList.contains('m'))
      e.classList.add('rev', 'f');
    e.classList.remove('cur');
  });
  setTimeout(() => {
    sfx.lose();
    duck(5);
    $$('.tile[data-i]').forEach(e => {
      e.style.setProperty('--fr', Math.random() * 90 - 45 + 'deg');
      e.style.setProperty('--d', Math.random() * 500 | 0);
      e.classList.add('fall');
    });
  }, 1000);
  end('Oh no! You couldn\'t guess the word.', `It was ${ word }.`, 'Told ya\' only 0.001% are able to guess the secret word.');
}

// Play again opens the word length page
go('#again', () => show('s-len'));
go('#quit', () => {
  $('#res').classList.remove('on');
  show('s-bye');
});

// On-screen keyboard
[
  'qwertyuiop',
  'asdfghjkl',
  'zxcvbnm'
].forEach((r, ri) => {
  const d = document.createElement('div');
  d.className = 'kr';
  if (ri == 2) {
    const b = document.createElement('button');
    b.className = 'k w go';
    b.textContent = 'Enter';
    b.onclick = submit;
    d.appendChild(b);
  }
  [...r].forEach(c => {
    const b = document.createElement('button');
    b.className = 'k';
    b.textContent = c;
    b.dataset.k = c;
    b.onmousedown = e => e.preventDefault();
    b.onclick = () => type(c);
    d.appendChild(b);
  });
  if (ri == 2) {
    const b = document.createElement('button');
    b.className = 'k w';
    b.textContent = 'Delete';
    b.onclick = del;
    d.appendChild(b);
  }
  $('#kb').appendChild(d);
});

// Physical keyboard
addEventListener('keydown', e => {
  if (e.ctrlKey || e.metaKey || e.altKey)
    return;
  const k = e.key.toLowerCase();
  if ($('#res').classList.contains('on')) {
    if (k == 'y')
      $('#again').click();
    else if (k == 'n')
      $('#quit').click();
    return;
  }
  if (scr == 's-intro' && /^\S$/.test(k)) {
    if (k == 'y')
      $('#yes').click();
    else if (k == 'n')
      $('#no').click();
    else {
      const m = $('#ierr');
      m.textContent = 'Invalid input. Please select \'y\' or \'n\'';
      m.classList.remove('b');
      void m.offsetWidth;
      m.classList.add('b');
      sfx.short();
    }
    return;
  }
  if (scr == 's-game' && !over) {
    if (k == 'enter') {
      e.preventDefault();
      submit();
    } else if (k == 'backspace') {
      e.preventDefault();
      del();
    } else if (k == 'arrowleft') {
      e.preventDefault();
      move(-1);
    } else if (k == 'arrowright') {
      e.preventDefault();
      move(1);
    } else if (/^[a-z]$/.test(k)) {
      const b = $(`.k[data-k="${ k }"]`);
      if (b) {
        b.classList.add('dn');
        setTimeout(() => b.classList.remove('dn'), 110);
      }
      type(k);
    }
  }
});