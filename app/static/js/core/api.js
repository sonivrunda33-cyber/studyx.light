export async function api(path,options={}){
  const response=await fetch(`/api${path}`,{...options,headers:{'Content-Type':'application/json',...(options.headers||{})}});
  const type=response.headers.get('content-type')||'';
  const data=type.includes('application/json')?await response.json():await response.text();
  if(!response.ok)throw new Error(data?.error||'Could not save this change.');
  return data;
}
export const get=(path)=>api(path);
export const post=(path,body)=>api(path,{method:'POST',body:JSON.stringify(body)});
export const patch=(path,body)=>api(path,{method:'PATCH',body:JSON.stringify(body)});
export const remove=(path)=>api(path,{method:'DELETE'});
export function track(name,detail={},durationMs=null){return fetch('/api/events',{method:'POST',keepalive:true,headers:{'Content-Type':'application/json'},body:JSON.stringify({name,detail,duration_ms:durationMs})}).catch(()=>{});}
