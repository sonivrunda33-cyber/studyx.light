import {get,patch,track} from '../core/api.js';
import {emptyState,toast} from '../core/ui.js';
import {isoDay,dateLabel,timeLabel,colorFor,escapeHtml} from '../core/utils.js';
import {taskRow} from '../core/renderers.js';

let tasks=[],weekStart=mondayOf(new Date()),selectedDate=isoDay(new Date());
function mondayOf(date){const start=new Date(date.getFullYear(),date.getMonth(),date.getDate());start.setDate(start.getDate()-((start.getDay()+6)%7));return start}
export async function init(){
  tasks=await get('/tasks');render();
  document.querySelector('#weekPrev')?.addEventListener('click',()=>moveWeek(-7));
  document.querySelector('#weekNext')?.addEventListener('click',()=>moveWeek(7));
  document.querySelector('#plannerToday')?.addEventListener('click',()=>{weekStart=mondayOf(new Date());selectedDate=isoDay(new Date());render()});
  const calendar=document.querySelector('#weekCalendar');
  calendar?.addEventListener('click',event=>{const dateButton=event.target.closest('[data-select-day]');if(dateButton){selectedDate=dateButton.dataset.selectDay;renderDay();document.querySelectorAll('.week-head').forEach(node=>node.classList.toggle('selected',node===dateButton))}});
  calendar?.addEventListener('dragstart',event=>{const taskButton=event.target.closest('[data-week-task]');if(!taskButton)return;event.dataTransfer.setData('text/plain',taskButton.dataset.weekTask);event.dataTransfer.effectAllowed='move'});
  calendar?.addEventListener('dragover',event=>{const slot=event.target.closest('[data-calendar-slot]');if(slot){event.preventDefault();slot.classList.add('drag-over')}});
  calendar?.addEventListener('dragleave',event=>event.target.closest('[data-calendar-slot]')?.classList.remove('drag-over'));
  calendar?.addEventListener('drop',async event=>{const slot=event.target.closest('[data-calendar-slot]');if(!slot)return;event.preventDefault();slot.classList.remove('drag-over');const task=tasks.find(item=>item.id===Number(event.dataTransfer.getData('text/plain')));if(!task)return;try{await patch(`/tasks/${task.id}`,{due_at:slot.dataset.calendarSlot});await track('task_rescheduled',{task_id:task.id});tasks=await get('/tasks');toast('Task moved to a new time');render()}catch(error){toast(error.message,'error')}});
}
function moveWeek(days){weekStart.setDate(weekStart.getDate()+days);selectedDate=isoDay(weekStart);render()}
function render(){
  const holder=document.querySelector('#weekCalendar');const days=Array.from({length:7},(_,i)=>{const date=new Date(weekStart);date.setDate(weekStart.getDate()+i);return date});
  const weekEnd=days[6];document.querySelector('#weekLabel').textContent=`${days[0].toLocaleDateString(undefined,{month:'short',day:'numeric'})} — ${weekEnd.toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'})}`;
  const head=`<div class="week-grid"><div class="week-cell week-head">TIME</div>${days.map(date=>`<button class="week-cell week-head ${isoDay(date)===isoDay(new Date())?'today':''} ${isoDay(date)===selectedDate?'selected':''}" data-select-day="${isoDay(date)}"><span>${date.toLocaleDateString(undefined,{weekday:'short'}).toUpperCase()}</span><strong>${date.getDate()}</strong></button>`).join('')}`;
  let rows='';
  for(let hour=8;hour<=20;hour++){
    rows+=`<div class="week-cell week-time">${String(hour%12||12)} ${hour<12?'AM':'PM'}</div>`;
    for(const day of days){const key=isoDay(day);const matching=tasks.filter(task=>task.due_at?.slice(0,10)===key&&new Date(task.due_at).getHours()===hour);rows+=`<div class="week-cell" data-calendar-slot="${key}T${String(hour).padStart(2,'0')}:00">${matching.map(task=>`<button draggable="${task.status!=='done'}" class="week-event ${task.priority==='high'?'high':''} ${task.status==='done'?'done':''}" data-week-task="${task.id}" title="${escapeHtml(task.title)} · drag to reschedule">${escapeHtml(task.title)}</button>`).join('')}</div>`}
  }
  const flexible=tasks.filter(task=>!task.due_at&&task.status==='todo');
  holder.innerHTML=head+rows+'</div>';
  const flexibleStrip=flexible.length?`<div class="flexible-tasks"><span>FLEXIBLE</span>${flexible.slice(0,4).map(task=>`<span class="flexible-task">${escapeHtml(task.title)}</span>`).join('')}</div>`:'';
  holder.insertAdjacentHTML('beforeend',flexibleStrip);
  holder.querySelectorAll('[data-week-task]').forEach(button=>button.addEventListener('click',()=>openEdit(button.dataset.weekTask)));
  renderDay();
}
function openEdit(id){
  const task=tasks.find(item=>item.id===Number(id));if(!task)return;
  const form=document.querySelector('#taskForm');form.reset();form.elements.id.value=task.id;
  document.querySelector('#taskModalTitle').textContent='Edit task';document.querySelector('#taskSubmitLabel').textContent='Save changes';
  ['title','subject','kind','duration_minutes','notes'].forEach(key=>form.elements[key].value=task[key]??'');
  form.elements.due_at.value=task.due_at?task.due_at.slice(0,16):'';
  form.querySelector(`[name="priority"][value="${task.priority}"]`).checked=true;
  document.querySelector('#taskModal').classList.add('open');document.querySelector('#taskModal').setAttribute('aria-hidden','false');
}
function renderDay(){
  const dayTitle=document.querySelector('#selectedDayTitle');const list=document.querySelector('#plannerDayTasks');if(!list)return;
  const date=new Date(`${selectedDate}T12:00:00`);dayTitle.textContent=date.toLocaleDateString(undefined,{weekday:'long',month:'long',day:'numeric'});
  const dayTasks=tasks.filter(task=>task.due_at?.slice(0,10)===selectedDate).sort((a,b)=>a.due_at.localeCompare(b.due_at));
  list.innerHTML=dayTasks.length?dayTasks.map(task=>`<div class="timeline-row"><span class="timeline-hour">${timeLabel(task.due_at)}</span><div class="timeline-content ${colorFor(task.subject)}"><i class="subject-dot ${colorFor(task.subject)}"></i><div><strong>${escapeHtml(task.title)}</strong><small>${escapeHtml(task.subject)} · ${task.duration_minutes} min · ${task.status==='done'?'Completed':'Planned'}</small></div></div></div>`).join(''):emptyState('A little space to plan','Add a task with this day’s date and it will appear here.');
  if(!dayTasks.length)track('planner_day_viewed',{date:selectedDate});
}
