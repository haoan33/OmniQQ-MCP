import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
const config=JSON.parse(fs.readFileSync('.release.json','utf8'));
const site=config.siteUrl.replace(/\/$/,'');
const url=new URL(process.env.ACTIONS_ID_TOKEN_REQUEST_URL);url.searchParams.set('audience',site);
const response=await fetch(url,{headers:{Authorization:`Bearer ${process.env.ACTIONS_ID_TOKEN_REQUEST_TOKEN}`},signal:AbortSignal.timeout(15000)});
if(!response.ok)throw new Error('无法获取构建身份');
const {value}=await response.json();
const payload={product:config.product,version:process.env.GITHUB_REF_NAME.replace(/^v/,''),sourceCommit:execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim(),message:'GitHub 构建或发布失败。请打开该次 Actions 记录查看详细原因。'};
const result=await fetch(`${site}/api/v1/ci/events`,{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${value}`},body:JSON.stringify(payload),signal:AbortSignal.timeout(20000)});
if(!result.ok){console.error(`记录失败状态时收到 HTTP ${result.status}，正式版本未因此切换。`);process.exit(1);}
