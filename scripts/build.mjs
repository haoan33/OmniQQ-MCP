import {readVersion} from './version-files.mjs';
import {readFileSync,mkdirSync,copyFileSync,writeFileSync,statSync} from 'node:fs';
import {resolve,basename,sep} from 'node:path';
import {execFileSync} from 'node:child_process';
import {createHash} from 'node:crypto';
const config=JSON.parse(readFileSync('.release.json','utf8'));
const [platform,arch]=process.argv.slice(2);
const target=config.targets.find(t=>t.platform===platform&&t.arch===arch);
if(!target)throw new Error('未声明此构建平台');
const version=process.env.RELEASE_VERSION||readFileSync('VERSION','utf8').trim();
if(!/^\d+\.\d+\.\d+$/.test(version))throw new Error('无效版本');
for(const entry of config.versionFiles){
  const declared=readVersion(readFileSync(entry.path,'utf8'),entry);
  if(declared!==version)throw new Error('源文件版本与标签不同，请通过 release.ps1 发布');
}
for(const command of target.commands){
  if(!Array.isArray(command)||!command.length)throw new Error('构建命令须为参数数组');
  execFileSync(command[0],command.slice(1),{stdio:'inherit',env:{...process.env,RELEASE_VERSION:version}});
}
const file=resolve(target.artifact.replaceAll('{version}',version)),root=resolve('.');
if(!file.startsWith(root+sep)||!statSync(file).isFile())throw new Error('构建产物必须是仓库内的文件');
const body=readFileSync(file);
if(!body.length||body.length>2147483648)throw new Error('安装包为空或超过 2 GB');
const output=resolve('.release-artifacts',`${platform}-${arch}`);mkdirSync(output,{recursive:true});
copyFileSync(file,resolve(output,basename(file)));
const sourceCommit=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
const asset={name:basename(file),platform,arch,sha256:createHash('sha256').update(body).digest('hex'),size:body.length};
writeFileSync(resolve(output,'target.json'),JSON.stringify({version,sourceCommit,asset},null,2));
console.log(`构建完成：${asset.name} (${platform}/${arch})，已计算 SHA-256。`);
