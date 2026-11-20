import {get,track} from '../core/api.js';
import {emptyState} from '../core/ui.js';
import {taskRow,courseCard} from '../core/renderers.js';
import {dateLabel} from '../core/utils.js';

let tasks=[],filter='all',ascending=true;
export async function init(){
  [tasks]=await Promise.all([get('/tasks')]);
  render();
  get('/courses').then(courses=>{document.querySelector('#assignmentCourses').innerHTML=courses.map(courseCard).join('')}).catch(()=>{});
  document.querySelector('#taskFilters')?.addEventListener('click',event=>{const chip=event.target.closest('[data-task-filter]');if(!chip)return;filter=chip.dataset.taskFilter;document.querySelectorAll('[data-task-filter]').forEach(item=>item.classList.toggle('active',item===chip));render()});
  document.querySelector('#sortTasksButton')?.addEventListener('click',()=>{ascending=!ascending;tasks.sort((a,b)=>(a.due_at||'9999').localeCompare(b.due_at||'9999')*(ascending?1:-1));render()});
}
function render(){
  const list=document.querySelector('#assignmentList');if(!list)return;
  let shown=[...tasks];if(filter==='todo'||filter==='done')shown=shown.filter(task=>task.status===filter);if(filter==='high')shown=shown.filter(task=>task.priority==='high');
  shown.sort((a,b)=>(a.due_at||'9999').localeCompare(b.due_at||'9999')*(ascending?1:-1));
  document.querySelector('#taskListSubtitle').textContent=`${tasks.filter(task=>task.status==='todo').length} to do · ${tasks.filter(task=>task.status==='done').length} completed`;
  list.innerHTML=shown.length?shown.map(taskRow).join(''):emptyState('Nothing in this view','Try another filter or add a task to your plan.');
}
