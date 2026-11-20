import {hydrateIcons} from './core/icons.js';
import {get,post,patch,remove,track} from './core/api.js';
import {toast,openModal,closeModal} from './core/ui.js';
import {setProfile} from './core/utils.js';

hydrateIcons();
setProfile(document.body.dataset.accountName||'Student');
let taskFormOpenedAt=0;

document.addEventListener('click',event=>{
  const control=event.target.closest('button,a,[role="button"]');
  if(!control)return;
  const label=(control.getAttribute('aria-label')||control.innerText||control.title||'control').trim().replace(/\s+/g,' ').slice(0,80);
  track('ui_click',{view:document.body.dataset.page,control:label});
});

function closeSidebar(){document.querySelector('#sidebar')?.classList.remove('open');document.querySelector('#mobileScrim')?.classList.remove('show')}
document.querySelector('#menuButton')?.addEventListener('click',()=>{document.querySelector('#sidebar')?.classList.toggle('open');document.querySelector('#mobileScrim')?.classList.toggle('show')});
document.querySelector('#mobileScrim')?.addEventListener('click',closeSidebar);
document.querySelectorAll('[data-open-task]').forEach(button=>button.addEventListener('click',()=>openTaskForm()));
document.querySelectorAll('[data-close-modal]').forEach(button=>button.addEventListener('click',()=>closeModal(button.dataset.closeModal)));
document.querySelectorAll('.modal-backdrop').forEach(backdrop=>backdrop.addEventListener('click',event=>{if(event.target===backdrop)closeModal(backdrop.id)}));
document.addEventListener('keydown',event=>{if(event.key==='Escape'){document.querySelectorAll('.modal-backdrop.open').forEach(el=>closeModal(el.id));closeSidebar()}if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();document.querySelector('#globalSearch')?.focus()}});

function openTaskForm(task=null){
  const form=document.querySelector('#taskForm');if(!form)return;
  taskFormOpenedAt=performance.now();
  form.reset();form.elements.id.value=task?.id||'';
  document.querySelector('#taskModalTitle').textContent=task?'Edit task':'Add a task';
  document.querySelector('#taskSubmitLabel').textContent=task?'Save changes':'Add to my plan';
  if(task){for(const key of ['title','subject','kind','duration_minutes','notes'])if(form.elements[key])form.elements[key].value=task[key]??'';form.elements.due_at.value=task.due_at?String(task.due_at).slice(0,16):'';form.querySelector(`[name="priority"][value="${task.priority}"]`).checked=true}
  openModal('taskModal');
}

document.querySelector('#taskForm')?.addEventListener('submit',async event=>{
  event.preventDefault();const form=event.currentTarget;const body=Object.fromEntries(new FormData(form).entries());
  const id=body.id;delete body.id;body.duration_minutes=Number(body.duration_minutes);
  try{if(id)await patch(`/tasks/${id}`,body);else await post('/tasks',body);await track(id?'task_updated':'task_created',{kind:body.kind},Math.round(performance.now()-taskFormOpenedAt));closeModal('taskModal');toast(id?'Task updated':'Added to your plan');location.reload()}
  catch(error){toast(error.message,'error')}
});

document.addEventListener('change',async event=>{
  const checkbox=event.target.closest('[data-task-check]');if(!checkbox)return;
  const id=checkbox.dataset.taskCheck;
  try{await patch(`/tasks/${id}`,{status:checkbox.checked?'done':'todo'});await track(checkbox.checked?'task_completed':'task_reopened');toast(checkbox.checked?'Nice work — task complete':'Task moved back to your plan');location.reload()}
  catch(error){checkbox.checked=!checkbox.checked;toast(error.message,'error')}
});
document.addEventListener('click',async event=>{
  const edit=event.target.closest('[data-edit-task]');if(edit){try{const tasks=await get('/tasks');openTaskForm(tasks.find(task=>String(task.id)===edit.dataset.editTask))}catch(error){toast(error.message,'error')}return}
  const del=event.target.closest('[data-delete-task]');if(del){if(!confirm('Delete this task from your plan?'))return;try{await remove(`/tasks/${del.dataset.deleteTask}`);await track('task_deleted');toast('Task deleted');location.reload()}catch(error){toast(error.message,'error')}}
});

document.querySelector('#notificationButton')?.addEventListener('click',async()=>{
  try{const tasks=await get('/tasks');const due=tasks.filter(task=>task.status==='todo'&&task.due_at&&new Date(task.due_at)<new Date(Date.now()+86400000));toast(due.length?`${due.length} task${due.length===1?'':'s'} due in the next 24 hours`:'You are all caught up for the next 24 hours.')}catch{toast('Your reminders are ready when you add a due date.')}
});

const search=document.querySelector('#globalSearch');let searchTimer;
search?.addEventListener('input',()=>{clearTimeout(searchTimer);searchTimer=setTimeout(()=>runSearch(search.value.trim()),180)});
search?.addEventListener('keydown',event=>{if(event.key==='Escape')document.querySelector('.search-results')?.remove();if(event.key==='Enter')document.querySelector('.search-results .search-result')?.click()});
async function runSearch(query){
  document.querySelector('.search-results')?.remove();if(!query)return;
  try{const [tasks,exams]=await Promise.all([get('/tasks'),get('/exams')]);const all=[...tasks.filter(t=>`${t.title} ${t.subject}`.toLowerCase().includes(query.toLowerCase())).map(t=>({label:t.title,sub:t.subject,url:'/assignments',kind:'task'})),...exams.filter(e=>`${e.title} ${e.subject}`.toLowerCase().includes(query.toLowerCase())).map(e=>({label:e.title,sub:e.subject,url:'/exams',kind:'exam'}))].slice(0,7);
    const box=document.createElement('div');box.className='search-results';box.innerHTML=all.length?all.map(item=>`<a class="search-result" href="${item.url}"><i class="subject-dot ${item.kind==='exam'?'violet':''}"></i><span>${item.label.replace(/[&<>"']/g,'')}</span><small>${item.sub.replace(/[&<>"']/g,'')}</small></a>`).join(''):'<div class="search-empty">No matches found.</div>';
    document.querySelector('.topbar').append(box);box.querySelectorAll('a').forEach(link=>link.addEventListener('click',()=>track('search_result_opened',{query_length:query.length})));
  }catch{}
}
document.addEventListener('click',event=>{if(!event.target.closest('.topbar'))document.querySelector('.search-results')?.remove()});

get('/tasks').then(tasks=>{const el=document.querySelector('#navTaskCount');if(el)el.textContent=tasks.filter(task=>task.status==='todo').length}).catch(()=>{});

const page=document.body.dataset.page;
const pageModules={dashboard:()=>import('./pages/dashboard.js'),planner:()=>import('./pages/planner.js'),assignments:()=>import('./pages/assignments.js'),exams:()=>import('./pages/exams.js'),focus:()=>import('./pages/focus.js'),insights:()=>import('./pages/insights.js'),research:()=>import('./pages/research.js'),settings:()=>import('./pages/settings.js')};
pageModules[page]?.().then(module=>module.init()).catch(error=>{console.error(error);toast('This page could not load its data. Refresh to try again.','error')});
