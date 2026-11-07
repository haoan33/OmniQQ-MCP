function assignment(contents,entry) {
  let section='',found=[];let offset=0;
  const python=entry.format==='python';
  const parts=entry.key?.split('.')||[];
  if(python?!/^[A-Za-z_]\w*$/.test(entry.key||''):parts.length!==2||parts.some(p=>!/^[-\w]+$/.test(p)))throw new Error('无效版本字段');
  for(const line of contents.split(/(?<=\n)/)) {
    const header=line.match(/^\s*\[([^\]]+)\]\s*(?:#.*)?(?:\r?\n)?$/);
    if(header)section=header[1];
    if(python||section===parts[0]) {
      const key=python?entry.key:parts[1];
      const match=line.match(new RegExp(`^(\\s*${key}\\s*=\\s*["'])([^"']+)(["']\\s*(?:#.*)?(?:\\r?\\n)?)$`));
      if(match)found.push({start:offset+match[1].length,end:offset+match[1].length+match[2].length,value:match[2]});
    }
    offset+=line.length;
  }
  if(found.length!==1)throw new Error('版本字段必须存在且唯一');
  return found[0];
}
export function readVersion(contents,entry) {
  if(entry.format==='text')return contents.trim();
  if(entry.format==='json'){let value=JSON.parse(contents);for(const part of (entry.key||'version').split('.'))value=value[part];return value;}
  if(['toml','python'].includes(entry.format))return assignment(contents,entry).value;
  throw new Error('不支持的版本文件格式');
}
export function writeVersion(contents,entry,version) {
  if(entry.format==='text')return version+'\n';
  if(entry.format==='json'){
    const object=JSON.parse(contents),parts=(entry.key||'version').split('.');let parent=object;
    for(const part of parts.slice(0,-1)){if(!Object.hasOwn(parent,part)||!parent[part]||typeof parent[part]!=='object')throw new Error('JSON 版本路径不存在');parent=parent[part];}
    if(!Object.hasOwn(parent,parts.at(-1)))throw new Error('JSON 版本字段不存在');
    parent[parts.at(-1)]=version;return JSON.stringify(object,null,2)+'\n';
  }
  if(['toml','python'].includes(entry.format)){const field=assignment(contents,entry);return contents.slice(0,field.start)+version+contents.slice(field.end);}
  throw new Error('不支持的版本文件格式');
}
