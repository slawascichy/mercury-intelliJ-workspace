import { compile } from 'file:///D:/workspace/git/scisoftware-webpage/docusaurus-hgdb/node_modules/@mdx-js/mdx/index.js';
import fs from 'fs';
let bad = 0;
for (const dir of process.argv.slice(2)) {
  for (const f of fs.readdirSync(dir)) {
    const p = dir + '/' + f;
    try { await compile(fs.readFileSync(p, 'utf8'), { format: 'mdx' }); console.log('OK  ', p); }
    catch (e) { bad++; console.log('BŁĄD', p, String(e.message).slice(0, 200)); }
  }
}
process.exit(bad ? 1 : 0);
