import {isoDay} from './utils.js';

export function toast(message,type='success'){
  const stack=document.querySelector('#toastStack');if(!stack)return;
  const node=document.createElement('div');node.className=`toast ${type==='error'?'error':''}`;
  node.innerHTML=`<span class="toast-mark">${type==='error'?'!':'✓'}</span><span></span>`;node.querySelector('span:last-child').textContent=message;
  stack.append(node);setTimeout(()=>node.remove(),3400);
}
export function openModal(id){const modal=document.getElementById(id);if(!modal)return;modal.classList.add('open');modal.setAttribute('aria-hidden','false');setTimeout(()=>modal.querySelector('input:not([type=hidden]),select,button')?.focus(),80)}
export function closeModal(id){const modal=document.getElementById(id);if(!modal)return;modal.classList.remove('open');modal.setAttribute('aria-hidden','true')}
export function emptyState(title,copy,mark='✳'){return `<div class="empty-state"><span class="empty-art">${mark}</span><h3>${title}</h3><p>${copy}</p></div>`}
export function renderChart(target,days){
  if(!target)return;const max=Math.max(60,...days.map(day=>Number(day.minutes)||0));
  target.innerHTML=`<div class="chart-bars">${days.map(day=>{const height=Math.max(2,Math.round((Number(day.minutes)||0)/max*100));const today=day.date===isoDay(new Date());return `<div class="chart-day ${today?'today':''}"><span class="chart-tip">${day.minutes||0} min · ${day.sessions||0} sessions</span><div class="chart-bar-wrap"><div class="chart-bar" style="height:${height}%"></div></div><span class="chart-label">${day.label||new Date(day.date+'T12:00:00').toLocaleDateString(undefined,{weekday:'short'})}</span></div>`}).join('')}</div>`;
}
