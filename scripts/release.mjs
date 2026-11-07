import {writeVersion} from './version-files.mjs';
import {readFileSync,writeFileSync} from 'node:fs';
import {resolve,sep} from 'node:path';
import {execFileSync} from 'node:child_process';
const root=process.cwd();
function git(...args){return execFileSync('git',args,{cwd:root,encoding:'utf8',stdio:['ignore','pipe','pipe']}).trim();}
const version=process.argv[2];
if(!/^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.test(version||''))throw new Error('版本格式应为 1.2.3，不包含 v 前缀');
const dryRun=process.argv.includes('--dry-run');
const config=JSON.parse(readFileSync('.release.json','utf8'));
if(git('branch','--show-current')!=='main')throw new Error('请在 main 分支发布');
if(git('status','--porcelain','--untracked-files=all'))throw new Error('请先提交业务代码，并保持工作区干净；脚本不会提交其他本地文件');
if(git('tag','--list',`v${version}`))throw new Error('版本标签已存在；请重试原构建或使用新版本，不能覆盖标签');
git('remote','get-url','origin');
if(!Array.isArray(config.versionFiles)||!config.versionFiles.length)throw new Error('请声明需要更新的版本文件');
const updates=config.versionFiles.map(entry=>{
  const file=resolve(root,entry.path);
  if(!file.startsWith(root+sep)||/(^|[\\/])(\.git|node_modules|\.env[^\\/]*)($|[\\/])/.test(entry.path))throw new Error('版本文件必须位于仓库内，且不能是凭据或 Git 内部文件');
  const content=writeVersion(readFileSync(file,'utf8'),entry,version);
  return {path:entry.path,file,content};
});
if(dryRun){console.log(`预检查通过：仅更新 ${updates.map(x=>x.path).join(', ')}，创建 v${version} 并原子推送 main 与标签。未修改文件。`);process.exit(0);}
for(const update of updates)writeFileSync(update.file,update.content);
git('add','--',...updates.map(x=>x.path));
if(git('diff','--cached','--name-only'))git('commit','-m',`chore(release): ${version}`);
git('tag','-a',`v${version}`,'-m',`Release ${version}`);
try{git('push','--atomic','origin','HEAD:refs/heads/main',`refs/tags/v${version}`);console.log(`v${version} 已推送，GitHub Actions 开始构建。`);}
catch{console.error(`推送失败，已保留本地提交和标签。不要重建或强推标签；检查网络后重试：git push --atomic origin HEAD:refs/heads/main refs/tags/v${version}`);process.exit(1);}
