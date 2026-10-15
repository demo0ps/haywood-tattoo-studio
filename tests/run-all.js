#!/usr/bin/env node
/* Runs every suite against the real page. Usage: cd tests && npm i jsdom && node run-all.js */
const { execFileSync } = require('child_process');
const suites = ['specials', 'ui', 'assistant', 'studio', 'commerce'];
let failed = 0;
for (const s of suites) {
  try {
    const out = execFileSync('node', [`${__dirname}/${s}.test.js`], { encoding: 'utf8' });
    const line = out.split('\n').filter(l => /passed,/.test(l)).pop() || '(no summary)';
    console.log(`${s.padEnd(11)} ${line.trim()}`);
  } catch (e) {
    failed++;
    const detail = [e.stdout, e.stderr].filter(Boolean).join('\n')
      .split('\n').filter(l => /FAIL|passed,|Error/.test(l)).slice(0, 8).join('\n    ');
    console.log(`${s.padEnd(11)} FAILED\n    ${detail}`);
  }
}
console.log(failed ? `\n${failed} suite(s) failed` : '\nall suites green');
process.exit(failed ? 1 : 0);
