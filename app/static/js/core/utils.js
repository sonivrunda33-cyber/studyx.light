export const escapeHtml=(value='')=>String(value).replace(/[&<>"']/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
export const localDate=(value)=>{const d=value?new Date(value):new Date();return new Date(d.getFullYear(),d.getMonth(),d.getDate())};
export const isoDay=(date)=>{const y=date.getFullYear(),m=String(date.getMonth()+1).padStart(2,'0'),d=String(date.getDate()).padStart(2,'0');return `${y}-${m}-${d}`};
export const dateLabel=(value,options={weekday:'short',month:'short',day:'numeric'})=>value?new Date(value).toLocaleDateString(undefined,options):'No due date';
export const timeLabel=(value)=>value?new Date(value).toLocaleTimeString(undefined,{hour:'numeric',minute:'2-digit'}):'Any time';
export const dateTimeLabel=(value)=>value?`${dateLabel(value)} · ${timeLabel(value)}`:'No due date';
export const minutesLabel=(mins)=>{const n=Number(mins)||0;return n>=60?`${Math.floor(n/60)}h ${n%60?`${n%60}m`:''}`.trim():`${n} min`};
export const colorFor=(name='')=>{const text=String(name).toLowerCase();if(text.includes('stat'))return 'coral';if(text.includes('web'))return 'blue';if(text.includes('python'))return 'mint';if(text.includes('design'))return 'violet';if(text.includes('artificial')||text.includes('ai'))return 'gold';return 'mint'};
export const initials=(name='A')=>String(name).trim().split(/\s+/).slice(0,2).map(part=>part[0]||'').join('').toUpperCase()||'A';
export function setProfile(name){const safe=name||'Student';document.querySelectorAll('#profileName').forEach(el=>el.textContent=safe);document.querySelectorAll('#profileInitial,#topInitial').forEach(el=>el.textContent=initials(safe));}
export function taskDueSort(a,b){return (a.due_at||'9999').localeCompare(b.due_at||'9999')}
