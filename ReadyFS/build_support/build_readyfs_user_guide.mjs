// Render the Markdown source as a portable, self-contained reading/print edition.
// Uses marked from an installed package, READYFS_MARKED_PATH, or the Codex runtime.
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {fileURLToPath, pathToFileURL} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const docs=path.join(root, 'docs');
let markedModule;
try { markedModule=await import('marked'); }
catch {
 const modulePath=process.env.READYFS_MARKED_PATH || path.join(os.homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/marked/lib/marked.esm.js');
 if (!fs.existsSync(modulePath)) throw new Error('Install marked or set READYFS_MARKED_PATH to its ESM entry.');
 markedModule=await import(pathToFileURL(modulePath).href);
}
const {Marked}=markedModule;
const source=fs.readFileSync(path.join(docs, 'READYFS_USER_GUIDE.md'), 'utf8');
const escape=s=>s.replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;').replaceAll('>','&gt;');
const slug=s=>s.toLowerCase().replace(/[^a-z0-9\s-]/g,'').replace(/\s+/g,'-');
const headings=[];
const renderer={heading(token) {
 const text=this.parser.parseInline(token.tokens);
 const id=slug(token.text);
 if(token.depth===2 && /^\d+\./.test(token.text)) headings.push({id,text:token.text});
 return `<h${token.depth} id="${id}">${text}</h${token.depth}>\n`;
}};
const parser=new Marked({renderer,gfm:true});
let content=parser.parse(source).replace(/^<h1[^>]*>.*?<\/h1>\s*/,'');
let imageCount=0;
content=content.replace(/<img src="([^"]+)"([^>]*)>/g,(_,src,rest)=>{
 const file=path.resolve(docs,src);
 if(!file.startsWith(docs+path.sep) || !fs.existsSync(file)) throw new Error(`Missing guide asset: ${src}`);
 const mime=file.endsWith('.svg')?'image/svg+xml':'image/png';
 imageCount++;
 return `<img src="data:${mime};base64,${fs.readFileSync(file).toString('base64')}"${rest}>`;
});
content=content.replace(/<p>(<img [\s\S]*?>)<\/p>\s*<p><em>([\s\S]*?)<\/em><\/p>/g,(_,img,caption)=>`<figure${img.includes('image/svg+xml')?' class="diagram"':''}>${img}<figcaption>${caption}</figcaption></figure>\n`);
// Retain useful source links without making the portable edition depend on siblings.
content=content.replace(/<a href="([^"#]+)"/g,(tag,href)=>{
 if(/^https?:|^data:/.test(href)) return tag;
 if(href==='READYFS_USER_GUIDE.html') return '<a href="#top"';
 const file=path.resolve(docs,href);
 if(!file.startsWith(docs+path.sep) || !fs.existsSync(file)) throw new Error(`Missing guide source link: ${href}`);
 const mime=href.endsWith('.json')?'application/json':'text/markdown';
 return `<a download="${escape(path.basename(file))}" href="data:${mime};base64,${fs.readFileSync(file).toString('base64')}"`;
});
// Chapters are independent print sections. The short contents remain on the opening page.
content=content.replace(/<h2 id="contents">([\s\S]*?)(?=<h2 id="1-start-here">)/, '<div class="contents-block"><h2 id="contents">$1</div>\n');
content=content.replace(/(<h2 id="\d+-)/g, '</section><section class="chapter">$1').replace('</section><section class="chapter">','<section class="chapter">')+'</section>';
const toc=headings.map(h=>`<li><a href="#${h.id}">${escape(h.text)}</a></li>`).join('');
const css=fs.readFileSync(path.join(docs,'guide-assets/guide.css'),'utf8');
const html=`<!doctype html>
<html lang="en" id="top"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ReadyFS user guide · Paths, commands & worked examples</title><meta name="description" content="An illustrated ReadyFS field guide: path concepts, options, editing, every command, and verified nested copy, move, what-if and delete on a real C64."><link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 40 40'%3E%3Crect width='40' height='40' rx='7' fill='%2340318d'/%3E%3Ctext x='6' y='28' font-size='25' fill='white' font-family='monospace'%3E%3E_%3C/text%3E%3C/svg%3E"><style>${css}</style></head>
<body><div class="topbar"><a class="brand" href="#top">READY<span>FS</span> <small>FIELD GUIDE</small></a><div class="actions"><a href="https://readyfs-editor-demo.klumsy.chatgpt.site/">Demo &amp; downloads</a><button class="primary" type="button" onclick="window.print()">Print / Save as PDF</button></div></div>
<header class="cover"><div class="eyebrow">A guide for the Commodore 64 filesystem laboratory</div><h1>Know the path.<br>Understand the command.</h1><p>From endpoints and aliases to nested SD2IEC folders and disk-image contents, with real C64 screenshots and a command reference.</p><div class="edition"><span>Current overlay build · Updated 13 October 2026</span><span>Offline, self-contained HTML</span><span>Letter / A4 print friendly</span></div></header>
<div class="layout"><nav class="rail" aria-label="Guide chapters"><strong>IN THIS GUIDE</strong><ol>${toc}</ol><div class="hint">Cyan in C64 captures: commands.<br>White: results.<br>Yellow: summaries and pager.<br>Red: errors.<br>Diagrams: concepts and workflow.</div></nav><main class="document">${content}<p class="print-origin no-screen">ReadyFS user guide · Updated 13 October 2026 · Companion video and updates: readyfs-editor-demo.klumsy.chatgpt.site<br>Print tip: choose Letter or A4, 100% scale, and disable browser headers/footers. Color aids scanning; labels remain meaningful in grayscale.</p></main></div>
<footer class="footer"><span>ReadyFS · Standalone filesystem laboratory</span><span>Real C64 evidence · One Markdown source · Portable print edition</span></footer></body></html>`;
const output=path.join(docs,'READYFS_USER_GUIDE.html');fs.writeFileSync(output,html);
const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);
for(const match of html.matchAll(/href="#([^"]+)"/g)) if(!ids.includes(match[1])) throw new Error(`Broken guide anchor: ${match[1]}`);
if(new Set(ids).size!==ids.length) throw new Error('Duplicate guide anchors');
if(imageCount!==26 || headings.length!==12 || html.includes('<img src="guide-assets/')) throw new Error('Incomplete illustrated guide');
console.log(JSON.stringify({output,chapters:headings.length,embedded_images:imageCount,words:source.split(/\s+/).length,bytes:Buffer.byteLength(html)}));
