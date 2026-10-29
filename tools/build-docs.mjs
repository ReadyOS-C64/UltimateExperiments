// Build the static documentation without reading ignored Site checkouts or logs.
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {Marked} from 'marked';
import {execFileSync} from 'node:child_process';
import hljs from 'highlight.js/lib/core';
import sql from 'highlight.js/lib/languages/sql';
import delphi from 'highlight.js/lib/languages/delphi';
hljs.registerLanguage('sql',sql);
hljs.registerLanguage('pascal',delphi);
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const out=path.join(root,'DOCS');
const tracked=new Set(execFileSync('git',['ls-files','-z'],{cwd:root,encoding:'utf8'}).split('\0').filter(Boolean));
execFileSync(process.execPath,[path.join(root,'ReadyFS/build_support/build_readyfs_user_guide.mjs')],{stdio:'inherit'});
const sources=new Map();
const destinations=new Map();
const register=(src,dst)=>{
 const key=dst.toLowerCase();
 if(destinations.has(key) && destinations.get(key)!==src)throw new Error('Case-colliding documentation destination: '+dst);
 destinations.set(key,src);sources.set(path.join(root,src),path.join(out,dst));
};
function tree(src,dst,accept=()=>true){
 for(const entry of fs.readdirSync(path.join(root,src),{withFileTypes:true})){
  if(entry.name.startsWith('.') || entry.name==='__pycache__')continue;
  const a=path.posix.join(src,entry.name),b=path.posix.join(dst,entry.name);
  if(entry.isDirectory())tree(a,b,accept);
  else if(accept(a))register(a,b);
 }
}
register('ReadyFS/README.md','readyfs/index.md');
register('ReadyFS/PROJECT_INVENTORY.md','readyfs/PROJECT_INVENTORY.md');
register('ReadyFS/AGENTS.md','readyfs/AGENTS.md');
tree('ReadyFS/docs','readyfs',p=>!p.endsWith('.html'));
register('ReadyFS/docs/READYFS_USER_GUIDE.html','readyfs/portable-guide.html');
register('SuperEditor/README.md','supereditor/index.md');
tree('SuperEditor/docs','supereditor');
tree('SuperEditor/screenshots','supereditor/screenshots');
register('SuperEditor/releases/SuperEditor-preview.zip','downloads/SuperEditor-preview.zip');
register('8088DOS64ultimate/README.md','dos64/index.md');
tree('8088DOS64ultimate/docs','dos64',p=>!p.includes('/videos/') && !p.endsWith('.html'));
register('8088DOS64ultimate/examples/README.md','dos64/examples/index.md');
for(const name of ['README.TXT','RIPPLE.PAS','RIPPLE.EXE','HANGMAN.BAS'])register('8088DOS64ultimate/examples/'+name,'dos64/examples/'+name);
register('8088DOS64ultimate/downloads/DOS64-development.zip','downloads/DOS64-development.zip');
register('8088DOS64ultimate/examples/EXAMPLES.IMG','downloads/DOS64-examples.img');
register('ReuSQL64/README.md','reusql/index.md');
register('ReuSQL64/third_party/README.md','reusql/dependencies.md');
tree('ReuSQL64/docs','reusql');
register('C77Cyberpunk77/README.md','c77/index.md');
register('C77Cyberpunk77/C77CYBER.VPL','c77/C77CYBER.VPL');
tree('C77Cyberpunk77/assets','c77/assets');
tree('C77Cyberpunk77/screenshots','c77/screenshots');
const downloads=[
 ['ReadyFS/artifacts/readyfs/readyfs-overlay-lab.d81','downloads/readyfs-overlay-lab.d81'],
 ['ReadyFS/artifacts/readyfs/readyfs-lab.d81','downloads/readyfs-lab.d81'],
 ['ReuSQL64/build/rsql64_shell.d81','downloads/rsql64_shell.d81']
];
for(const [a,b] of downloads)register(a,b);
const relative=(from,to)=>path.relative(path.dirname(from),to).split(path.sep).join('/')||path.basename(to);
function localLink(url,src,dst){
 if(/^(?:[a-z][a-z0-9+.-]*:|#|\/\/)/i.test(url))return url;
 const [name,fragment]=url.split('#',2);
 const abs=path.resolve(path.dirname(src),decodeURIComponent(name));
 let mapped=sources.get(abs);
 if(abs===path.join(root,'README.md'))mapped=path.join(out,'index.md');
 if(abs.startsWith(out+path.sep))mapped=abs;
 if(!mapped){
  const repositoryPath=path.relative(root,abs).split(path.sep).join('/');
  if(abs.startsWith(root+path.sep) && tracked.has(repositoryPath))return 'https://github.com/ReadyOS-C64/UltimateExperiments/blob/main/'+repositoryPath.split('/').map(encodeURIComponent).join('/')+(fragment?'#'+fragment:'');
  return url;
 }
 return relative(dst,mapped)+(fragment?'#'+fragment:'');
}
for(const [src,dst] of sources){
 fs.mkdirSync(path.dirname(dst),{recursive:true});
 if(src.endsWith('.md')){
  let content=fs.readFileSync(src,'utf8');
  content=content.replace(/(\]\()([^\s)]+)([^)]*\))/g,(_,a,url,b)=>a+localLink(url,src,dst)+b);
  fs.writeFileSync(dst,content.trimEnd()+'\n');
 }else fs.copyFileSync(src,dst);
}
const escape=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const slug=s=>s.toLowerCase().replace(/<[^>]*>/g,'').replace(/[^a-z0-9\s-]/g,'').replace(/\s+/g,'-');
const experiments=[
 {label:'SuperEditor',directory:'supereditor',children:[
  ['Complete user guide','USER_GUIDE.html'],
  ['Screenshot gallery','SCREENSHOTS.html'],
  ['GEOS preview and settings','GEOS_PREVIEW.html'],
  ['Standalone keys','STANDALONE_KEYS.html'],
  ['Build and package','BUILD.html'],
  ['Capacity and limits','CAPACITY.html'],
  ['Performance','PERFORMANCE.html'],
  ['Optimization plan','OPTIMIZATION_PLAN.html'],
  ['Memory and adapters','MEMORY_AND_ADAPTERS.html']
 ]},
 {label:'ReadyFS',directory:'readyfs',children:[
  ['Illustrated user guide','READYFS_USER_GUIDE.html'],
  ['Editor and history','READYFS_INTERACTIVE_UI.html'],
  ['RUN / batch scripting','READYFS_RUN_GUIDE.html'],
  ['SoftwareIEC mappings','READYFS_SOFTWAREIEC_GUIDE.html'],
  ['SD2IEC walkthrough','READYFS_SD2IEC_TUTORIAL.html'],
  ['IEC configuration','READYFS_IEC_CONFIGURATION.html'],
  ['Native SD2IEC reference','SD2IEC_NATIVE.html'],
  ['Editor screenshot tour','tours/editor.html'],
  ['SD2IEC screenshot tour','tours/sd2iec.html'],
  ['Safety','READYFS_SAFETY.html'],
  ['Acceptance and limits','READYFS_ACCEPTANCE.html'],
  ['Design plan','READYFS_MASTER_PLAN.html'],
  ['Path research','READYFS_PATH_RESEARCH.html']
 ]},
 {label:'DOS64 Ultimate',directory:'dos64',children:[
  ['Install the prebuilt preview','INSTALL.html'],
  ['Build and tests','BUILD.html'],
  ['Current status and limits','STATUS.html'],
  ['Physical screenshots','SCREENSHOTS.html'],
  ['Example applications','examples/index.html'],
  ['Technical documentation','TECHNICAL.html'],
  ['Publication audit','AUDIT.html']
 ]},
 {label:'ReuSQL64',directory:'reusql',children:[
  ['Performance and staged queries','performance.html'],
  ['Interactive shell','shell.html'],
  ['SQL language','sql-language.html'],
  ['Tested SQL examples','tested-queries.html'],
  ['Architecture','architecture.html'],
  ['Memory map','memory-map.html'],
  ['Public API','public-api.html'],
  ['Storage format','storage-format.html'],
  ['Export format','export-format.html'],
  ['Build dependencies','dependencies.html']
 ]},
 {label:'C77 Cyberpunk 77',directory:'c77',children:[
  ['Clean character-ROM gallery','screenshots/c77-cyberpunk-77-charrom/README.html'],
  ['CRT gallery','screenshots/c77-cyberpunk-77-crt/README.html'],
  ['Earlier palette gallery','screenshots/c77-cyberpunk-77/README.html']
 ]}
];
function navigation(page){
 const link=(label,target)=>`<a href="${escape(relative(page,path.join(out,target)))}"${path.join(out,target)===page?' aria-current="page"':''}>${escape(label)}</a>`;
 const home=link('All experiments','index.html');
 return home+experiments.map(project=>{
  const current=page.startsWith(path.join(out,project.directory)+path.sep);
  const children=`<li>${link('Overview and downloads',project.directory+'/index.html')}</li>`+project.children.map(([label,target])=>`<li>${link(label,project.directory+'/'+target)}</li>`).join('');
  return `<details class="project-nav" data-project="${project.directory}"${current?' open':''}><summary aria-label="${escape(project.label)} guides">${escape(project.label)}<span class="nav-chevron" aria-hidden="true"></span></summary><ul>${children}</ul></details>`;
 }).join('');
}
function* files(dir){for(const e of fs.readdirSync(dir,{withFileTypes:true})){const p=path.join(dir,e.name);if(e.isDirectory())yield* files(p);else yield p;}}
let count=0;
for(const file of files(out)){
 if(!file.endsWith('.md'))continue;
 const source=fs.readFileSync(file,'utf8');
 const title=source.match(/^# (.+)$/m)?.[1]||path.basename(file,'.md');
 const page=file.slice(0,-3)+'.html',toc=[],seen=new Map();
 const renderer={
 code(token){
  const language=token.lang?.toLowerCase();
  if(!['sql','pascal'].includes(language))return false;
  const highlighted=hljs.highlight(token.text,{language,ignoreIllegals:true}).value;
  return `<pre class="${language}-code" aria-label="${language} example"><code class="language-${language} hljs">${highlighted}</code></pre>\n`;
 },
 blockquote(token){
  if(!token.text.startsWith('**Performance:'))return false;
  return `<blockquote class="performance-callout" aria-label="Query performance">${this.parser.parse(token.tokens)}</blockquote>\n`;
 },
 heading(token){
  const base=slug(token.text),n=seen.get(base)||0;seen.set(base,n+1);
  const id=base+(n?'-'+n:'');
  const label=this.parser.parseInline(token.tokens);
  if(token.depth===2)toc.push({id,label:token.text});
  return `<h${token.depth} id="${id}">${label}</h${token.depth}>\n`;
 }};
 let content=new Marked({renderer,gfm:true}).parse(source);
 content=content.replace(/(href=")([^"?#]+)\.md([#?][^"]*)?"/g,'$1$2.html$3"');
 // Reserve image space so a late-loading screenshot cannot move a section anchor.
 content=content.replace(/<img src="([^"]+)"([^>]*)>/g,(tag,src,rest)=>{
  let dimensions='';
  const imageFile=path.resolve(path.dirname(page),decodeURIComponent(src));
  if(imageFile.startsWith(out+path.sep) && fs.existsSync(imageFile)){
   const bytes=fs.readFileSync(imageFile);
   if(imageFile.toLowerCase().endsWith('.png') && bytes.length>=24){
    dimensions=` width="${bytes.readUInt32BE(16)}" height="${bytes.readUInt32BE(20)}"`;
   }else if(imageFile.toLowerCase().endsWith('.svg')){
    const svg=bytes.toString('utf8');
    const width=svg.match(/\bwidth="(\d+)"/)?.[1],height=svg.match(/\bheight="(\d+)"/)?.[1];
    if(width && height)dimensions=` width="${width}" height="${height}"`;
   }
  }
  return `<img loading="lazy" decoding="async"${dimensions} src="${src}"${rest}>`;
 });
 if(file.includes(path.join('tours', ''))){
  content=content.replace(/(<p><img [\s\S]*?<\/p>)\s*(<pre>[\s\S]*?<\/pre>)/g,'$1<details class="screen-text"><summary>Read the screen text</summary>$2</details>');
 }
 const links=navigation(page);
 const tocHtml=toc.length && page!==path.join(out,'index.html')?`<details class="contents" open><summary>On this page</summary><ul>${toc.map(h=>`<li><a href="#${h.id}">${escape(h.label)}</a></li>`).join('')}</ul></details>`:'';
 const home=relative(page,path.join(out,'index.html'));
 const html=`<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light dark"><title>${escape(title)} · Ultimate Experiments</title><meta name="description" content="Commodore 64 Ultimate experiments: ${escape(title)}"><link rel="stylesheet" href="${relative(page,path.join(out,'style.css'))}"></head>
<body><a class="skip" href="#content">Skip to content</a><header><a class="brand" href="${home}">ULTIMATE<span>EXPERIMENTS</span></a><span class="tag">Commodore 64 · Work in progress</span></header><div class="layout"><aside><nav aria-label="Documentation">${links}</nav>${tocHtml}</aside><main id="content"><div class="page-actions"><a href="${escape(path.basename(file))}" download>Markdown source ↓</a><button type="button" onclick="window.print()">Print</button></div>${content}</main></div><footer>Independent experiments for the Commodore 64 Ultimate. <a href="${relative(page,path.join(out,'README.html'))}">Build and publishing</a></footer></body></html>`;
 fs.writeFileSync(page,html);count++;
}
fs.writeFileSync(path.join(out,'.nojekyll'),'');
console.log(`Built ${count} Markdown/HTML pages; screenshots and experiment downloads copied.`);
