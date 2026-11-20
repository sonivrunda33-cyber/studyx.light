import {escapeHtml,dateLabel,timeLabel,colorFor} from './utils.js';
import {icon} from './icons.js';
export function taskRow(task){
  const done=task.status==='done';const due=task.due_at?`${dateLabel(task.due_at,{month:'short',day:'numeric'})} · ${timeLabel(task.due_at)}`:'No due date';
  const overdue=task.due_at&&!done&&new Date(task.due_at)<new Date();
  return `<article class="task-row ${done?'is-done':''}" data-task-id="${task.id}">
    <input class="task-check" type="checkbox" data-task-check="${task.id}" aria-label="Mark ${escapeHtml(task.title)} complete" ${done?'checked':''}>
    <div class="task-title-wrap"><h3 class="task-title">${escapeHtml(task.title)}</h3><div class="task-meta"><i class="subject-dot ${colorFor(task.subject)}"></i>${escapeHtml(task.subject)}<span>·</span>${escapeHtml(task.kind||'study')}</div></div>
    <span class="priority-tag ${escapeHtml(task.priority)}">${escapeHtml(task.priority)}</span>
    <span class="task-due ${overdue?'overdue':''}">${escapeHtml(due)}</span>
    <div class="task-actions"><button class="tiny-action" data-edit-task="${task.id}" title="Edit task" aria-label="Edit task">${icon('edit')}</button><button class="tiny-action" data-delete-task="${task.id}" title="Delete task" aria-label="Delete task">${icon('trash')}</button></div>
  </article>`
}
export function courseCard(course){
  const color=escapeHtml(course.color||colorFor(course.name));const progress=Number(course.syllabus_progress)||0;
  return `<article class="course-card ${color}"><span class="course-swatch ${color}">${escapeHtml(course.name.slice(0,1))}</span><div class="course-body"><h4>${escapeHtml(course.name)}</h4><p>${escapeHtml(course.semester||'Current semester')}</p><div class="progress-track"><div class="progress-fill" style="width:${progress}%"></div></div><div class="course-bottom"><span>Course progress</span><span>${progress}%</span></div></div></article>`
}
