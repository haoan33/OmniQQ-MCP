import fs from 'node:fs';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
const config=JSON.parse(fs.readFileSync('.release.json','utf8'));
const version=process.env.GITHUB_REF_NAME?.replace(/^v/,'');
if(!/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(version||''))throw new Error('只发布正式版本标签');
const tag=`v${version}`,repo=config.releaseRepository;
const sourceCommit=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
function gh(args){return execFileSync('gh',args,{encoding:'utf8',stdio:['ignore','pipe','pipe']}).trim();}
const targets=config.targets.map(target=>{
  const folder=path.resolve('release-downloads',`${target.platform}-${target.arch}`);
  const metadata=JSON.parse(fs.readFileSync(path.join(folder,'target.json'),'utf8'));
  const asset=metadata.asset;
  if(metadata.version!==version||metadata.sourceCommit!==sourceCommit||asset.platform!==target.platform||asset.arch!==target.arch||path.basename(asset.name)!==asset.name)throw new Error('构建元数据与当前版本不一致');
  const file=path.join(folder,asset.name),body=fs.readFileSync(file);
  if(body.length!==asset.size||createHash('sha256').update(body).digest('hex')!==asset.sha256)throw new Error('下载的构建产物校验失败');
  return {asset,file};
});
if(new Set(targets.map(t=>t.asset.name)).size!==targets.length)throw new Error('各平台安装包需使用不同文件名');
let changelog='';
if(fs.existsSync('CHANGELOG.md')){
  const escaped=version.replaceAll('.','\\.');
  const lines=fs.readFileSync('CHANGELOG.md','utf8').split(/\r?\n/);
  const start=lines.findIndex(line=>new RegExp(`^##\\s+\\[?${escaped}\\]?(?:\\s|$)`).test(line));
  if(start>=0){let end=start+1;while(end<lines.length&&!/^##\s/.test(lines[end]))end++;changelog=lines.slice(start+1,end).join('\n').trim();}
}
if(!changelog)changelog=`版本 ${version} 已发布，安装说明见项目文档。`;
fs.writeFileSync('release-notes.md',changelog);
let existing;
try{existing=JSON.parse(gh(['release','view',tag,'--repo',repo,'--json','id,isDraft']));}catch{}
if(!existing){
  gh(['release','create',tag,'--repo',repo,'--draft','--title',`${config.product} ${version}`,'--notes-file','release-notes.md','--target',repo===process.env.GITHUB_REPOSITORY?sourceCommit:'main']);
  existing={isDraft:true};
}
if(!existing.isDraft){
  // Re-running a workflow can rebuild nondeterministic binaries. Reuse the original
  // immutable manifest for this exact source commit, rather than replacing packages.
  fs.mkdirSync('.release-original',{recursive:true});
  gh(['release','download',tag,'--repo',repo,'--pattern','release-manifest.json','--dir','.release-original','--clobber']);
  const original=JSON.parse(fs.readFileSync('.release-original/release-manifest.json','utf8'));
  if(original.product!==config.product||original.version!==version||original.sourceCommit!==sourceCommit)throw new Error('已发布版本来自不同的源提交，不能覆盖');
  for(const target of targets){const asset=original.assets.find(a=>a.platform===target.asset.platform&&a.arch===target.asset.arch);if(!asset)throw new Error('原正式版缺少必需平台');target.asset=asset;}
}
const checksum=targets.map(t=>`${t.asset.sha256}  ${t.asset.name}`).join('\n')+'\n';
fs.writeFileSync('SHA256SUMS',checksum);
fs.writeFileSync('release-manifest.json',JSON.stringify({product:config.product,version,sourceCommit,assets:targets.map(t=>t.asset)},null,2));
if(existing.isDraft){
  // Only drafts may replace an interrupted upload; published packages are immutable here.
  gh(['release','upload',tag,...targets.map(t=>t.file),'SHA256SUMS','release-manifest.json','--repo',repo,'--clobber']);
  let makeLatest=true;
  try{
    const latest=JSON.parse(gh(['release','view','--repo',repo,'--json','tagName'])).tagName.replace(/^v/,'');
    if(/^\d+\.\d+\.\d+$/.test(latest)){
      const a=latest.split('.').map(Number),b=version.split('.').map(Number);
      for(let i=0;i<3;i++){if(a[i]!==b[i]){makeLatest=a[i]<b[i];break;}}
    }
  }catch{}
  gh(['release','edit',tag,'--repo',repo,'--draft=false',`--latest=${makeLatest}`]);
}
const release=JSON.parse(gh(['api',`repos/${repo}/releases/tags/${tag}`]));
const assets=targets.map(({asset})=>{
  const remote=release.assets.find(item=>item.name===asset.name);
  if(!remote||remote.size!==asset.size||(remote.digest&&remote.digest!==`sha256:${asset.sha256}`))throw new Error('已发布安装包与当前构建不同，拒绝覆盖或同步');
  return {...asset,url:remote.browser_download_url};
});
const payload={product:config.product,version,sourceCommit,githubReleaseId:String(release.id),changelog,instructions:'',assets};
const site=config.siteUrl.replace(/\/$/,'');
const oidcUrl=new URL(process.env.ACTIONS_ID_TOKEN_REQUEST_URL);oidcUrl.searchParams.set('audience',site);
const tokenResponse=await fetch(oidcUrl,{headers:{Authorization:`Bearer ${process.env.ACTIONS_ID_TOKEN_REQUEST_TOKEN}`},signal:AbortSignal.timeout(15000)});
if(!tokenResponse.ok)throw new Error('无法取得 GitHub Actions 身份');
const identity=(await tokenResponse.json()).value;
let succeeded=false;
for(let attempt=0;attempt<3;attempt++){
  try{
    const response=await fetch(`${site}/api/v1/ci/releases`,{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${identity}`},body:JSON.stringify(payload),signal:AbortSignal.timeout(25000)});
    if(response.ok){succeeded=true;console.log('安装包已发布，网站正式版本已同步。');break;}
    console.error(`网站同步失败，HTTP ${response.status}。安装包保留在 GitHub，可重跑本工作流安全重试。`);
    if(response.status>=400&&response.status<500&&response.status!==429)break;
  }catch{console.error('网站暂不可达，准备重试。');}
  if(attempt<2)await new Promise(resolve=>setTimeout(resolve,2000*(attempt+1)));
}
if(!succeeded)process.exit(1);
